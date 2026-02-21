"""
Layer 2 — Sync logic tests.

Verifies that sync_product_index.py correctly mirrors ProductIndexData into the
products-index-updates collection. One sync run covers all four scenarios; each
test method asserts a different outcome.

Scenario recap (seeded by conftest.sync_result):
  PRODUCT_NEW       10000_0_de_DE   in ProductIndexData only   → Update record created
  PRODUCT_CHANGED   20000_0_de_DE   hash mismatch              → Update record rewritten
  PRODUCT_UNCHANGED 30000_0_de_DE   hash matches               → no write (skipped)
  PRODUCT_DELETED   40000_0_de_DE   sync-only, no main doc     → operation set to Delete
"""

import pytest

from tests.sync._data import (
    PRODUCT_CHANGED_ID,
    PRODUCT_DELETED_ID,
    PRODUCT_NEW_ID,
    PRODUCT_UNCHANGED_DATA,
    PRODUCT_UNCHANGED_ID,
    compute_hash,
)


@pytest.mark.sync
class TestSyncLogic:
    """sync_product_index.py → products-index-updates assertions."""

    # ── Process-level ──────────────────────────────────────────────────────────

    def test_sync_script_exits_successfully(self, sync_result):
        proc, _ = sync_result
        assert proc.returncode == 0, (
            f"sync_product_index.py exited {proc.returncode}\n"
            f"--- stderr ---\n{proc.stderr}\n"
            f"--- stdout ---\n{proc.stdout}"
        )

    # ── New product ────────────────────────────────────────────────────────────

    def test_new_product_creates_update_record_with_operation_update(self, sync_result):
        _, client = sync_result
        doc = client.collection("products-index-updates").document(PRODUCT_NEW_ID).get()
        assert doc.exists, f"Expected products-index-updates/{PRODUCT_NEW_ID} to be created"
        data = doc.to_dict()
        assert data["operation"] == "Update"
        assert data["finished"] is False

    def test_new_product_record_has_correct_structure(self, sync_result):
        _, client = sync_result
        data = client.collection("products-index-updates").document(PRODUCT_NEW_ID).get().to_dict()
        assert data["identifier"] == "10000-0"
        assert data["culture"] == "de_de"
        assert "domain_id" in data
        assert "content_hash" in data
        inner = data["data"]["document"]
        assert "fields" in inner
        assert inner["id"] == "10000-0"
        assert inner["locale"] == "de_de"

    # ── Changed product ────────────────────────────────────────────────────────

    def test_changed_product_updates_record_when_hash_differs(self, sync_result):
        _, client = sync_result
        data = client.collection("products-index-updates").document(PRODUCT_CHANGED_ID).get().to_dict()
        assert data["operation"] == "Update"
        assert data["content_hash"] != "stale_hash_that_does_not_match", (
            "Hash should be updated to reflect current ProductIndexData content"
        )

    def test_finished_flag_is_set_to_false_on_change(self, sync_result):
        """Changed product had finished=True in the sync DB; sync must reset it to False."""
        _, client = sync_result
        data = client.collection("products-index-updates").document(PRODUCT_CHANGED_ID).get().to_dict()
        assert data["finished"] is False, (
            "finished should be reset to False when content hash changes"
        )

    # ── Unchanged product ──────────────────────────────────────────────────────

    def test_unchanged_product_is_skipped(self, sync_result):
        """Unchanged product must not be rewritten — finished stays True, hash is preserved."""
        _, client = sync_result
        data = client.collection("products-index-updates").document(PRODUCT_UNCHANGED_ID).get().to_dict()
        assert data["finished"] is True, (
            "finished should remain True for unchanged products (sync never writes this doc)"
        )
        assert data["content_hash"] == compute_hash(PRODUCT_UNCHANGED_DATA), (
            "content_hash should be unchanged for skipped products"
        )

    # ── Deleted product ────────────────────────────────────────────────────────

    def test_removed_product_marks_record_as_delete(self, sync_result):
        _, client = sync_result
        doc = client.collection("products-index-updates").document(PRODUCT_DELETED_ID).get()
        assert doc.exists, f"Expected products-index-updates/{PRODUCT_DELETED_ID} to still exist"
        data = doc.to_dict()
        assert data["operation"] == "Delete"
        assert data["finished"] is False
