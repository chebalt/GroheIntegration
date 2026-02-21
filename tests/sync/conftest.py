"""
Fixtures for Layer 2 sync tests (sync_product_index.py).

Strategy
--------
Four test products are seeded directly into the Firestore emulator — no ETL pipeline
needed. This keeps sync tests fast (seconds, not minutes).

The sync script is run once per module with `--sync-database (default)`. Both the
ProductIndexData collection (main DB) and products-index-updates collection (sync DB)
live in the same `(default)` database, which the gcloud Firestore emulator supports.

Scenario matrix
---------------
  PRODUCT_NEW       in ProductIndexData only                 → sync creates Update record
  PRODUCT_CHANGED   in both; sync doc has stale hash         → sync rewrites Update record
  PRODUCT_UNCHANGED in both; sync doc has matching hash      → sync skips (no write)
  PRODUCT_DELETED   in products-index-updates only           → sync sets operation=Delete

The fixture clears both collections before seeding and cleans up test docs afterward.
If the full pipeline ran first (make test-all), its data is cleared here; pipeline
tests have already completed by the time pytest reaches tests/sync/ (alphabetical order).
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest
from google.cloud import firestore

from tests.sync._data import (
    PRODUCT_CHANGED_DATA,
    PRODUCT_CHANGED_ID,
    PRODUCT_DELETED_ID,
    PRODUCT_NEW_DATA,
    PRODUCT_NEW_ID,
    PRODUCT_UNCHANGED_DATA,
    PRODUCT_UNCHANGED_ID,
    compute_hash,
)

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT       = Path(__file__).parent.parent.parent.parent   # NEO/
DATA_LOADER_DIR = REPO_ROOT / "grohe-neo-data-loader"

if platform.system() == "Windows":
    DATA_LOADER_PYTHON = DATA_LOADER_DIR / ".venv" / "Scripts" / "python.exe"
else:
    DATA_LOADER_PYTHON = DATA_LOADER_DIR / ".venv" / "bin" / "python"

if not DATA_LOADER_PYTHON.exists():
    DATA_LOADER_PYTHON = Path(sys.executable)

EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
PROJECT_ID    = "demo-project"
SYNC_DATABASE = "(default)"   # Named databases not supported by the gcloud emulator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _delete_all_docs(client: firestore.Client, collection_name: str) -> None:
    """Delete every document in a collection using batched writes (500 per batch)."""
    batch = client.batch()
    count = 0
    for doc in client.collection(collection_name).stream():
        batch.delete(doc.reference)
        count += 1
        if count >= 500:
            batch.commit()
            batch = client.batch()
            count = 0
    if count > 0:
        batch.commit()


# ── Module-scoped fixture ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sync_result(firestore_client):
    """
    Seed Firestore, run sync_product_index.py once, yield (CompletedProcess, client).

    Module-scoped so the sync runs once and all TestSyncLogic methods share the result.
    The `firestore_client` fixture from tests/conftest.py handles emulator availability;
    if the emulator is not running it skips at that level.
    """
    # ── Clear both collections (may contain real ETL data from pipeline tests) ─
    _delete_all_docs(firestore_client, "ProductIndexData")
    _delete_all_docs(firestore_client, "products-index-updates")

    # ── Seed ProductIndexData (new + changed + unchanged; NOT deleted) ─────────
    pid = firestore_client.collection("ProductIndexData")
    pid.document(PRODUCT_NEW_ID).set(PRODUCT_NEW_DATA)
    pid.document(PRODUCT_CHANGED_ID).set(PRODUCT_CHANGED_DATA)
    pid.document(PRODUCT_UNCHANGED_ID).set(PRODUCT_UNCHANGED_DATA)

    # ── Seed products-index-updates (pre-existing sync state) ─────────────────
    piu = firestore_client.collection("products-index-updates")

    # CHANGED: stale hash → sync will detect difference and rewrite
    piu.document(PRODUCT_CHANGED_ID).set({
        "content_hash": "stale_hash_that_does_not_match",
        "culture": "de_de",
        "finished": True,    # should be reset to False when sync rewrites
        "operation": "Update",
        "domain_id": "9175162892",
        "identifier": "20000-0",
        "data": {"document": {"fields": {}, "id": "20000-0", "locale": "de_de"}},
        "incremental_update_id": None,
        "status": "unknown",
    })

    # UNCHANGED: correct hash → sync will compare equal and skip (no write)
    piu.document(PRODUCT_UNCHANGED_ID).set({
        "content_hash": compute_hash(PRODUCT_UNCHANGED_DATA),
        "culture": "de_de",
        "finished": True,    # should remain True — sync never writes this doc
        "operation": "Update",
        "domain_id": "9175162892",
        "identifier": "30000-0",
        "data": {"document": {"fields": {}, "id": "30000-0", "locale": "de_de"}},
        "incremental_update_id": None,
        "status": "unknown",
    })

    # DELETED: in sync but not in ProductIndexData → sync will set operation=Delete
    piu.document(PRODUCT_DELETED_ID).set({
        "content_hash": "some_old_hash",
        "culture": "de_de",
        "finished": False,
        "operation": "Update",   # will be changed to "Delete"
        "domain_id": "9175162892",
        "identifier": "40000-0",
        "data": {"document": {"fields": {}, "id": "40000-0", "locale": "de_de"}},
        "incremental_update_id": None,
        "status": "unknown",
    })

    # ── Run sync ──────────────────────────────────────────────────────────────
    env = {
        **os.environ,
        "FIRESTORE_EMULATOR_HOST": EMULATOR_HOST,
        "GCLOUD_PROJECT":          PROJECT_ID,
        "PYTHONUTF8":              "1",
    }

    proc = subprocess.run(
        [
            str(DATA_LOADER_PYTHON), "sync_product_index.py",
            "--use-emulator",
            "--sync-database", SYNC_DATABASE,
            "--log-level", "INFO",
        ],
        cwd=DATA_LOADER_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )

    yield proc, firestore_client

    # ── Cleanup: remove only the 4 test docs ─────────────────────────────────
    for doc_id in (PRODUCT_NEW_ID, PRODUCT_CHANGED_ID, PRODUCT_UNCHANGED_ID):
        firestore_client.collection("ProductIndexData").document(doc_id).delete()
    for doc_id in (PRODUCT_NEW_ID, PRODUCT_CHANGED_ID, PRODUCT_UNCHANGED_ID, PRODUCT_DELETED_ID):
        firestore_client.collection("products-index-updates").document(doc_id).delete()
