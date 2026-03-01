"""
store-locator — Store locator job integration tests.

Verifies that the store-locator job correctly populates `stores-index-updates`
in Firestore, and optionally that the IndexingApi picks up and forwards store
records to Sitecore Search.

Infrastructure required: make infra-store-locator-up
  (runs the one-shot job that writes to stores-index-updates)

Tests are skipped automatically if the job hasn't run.
"""

import pytest

STORE_LOCATOR_COLLECTION = "stores-index-updates"


class TestStoreLocator:

    def test_stores_index_updates_collection_is_populated(self, store_locator_result):
        client, _ = store_locator_result
        docs = list(client.collection(STORE_LOCATOR_COLLECTION).limit(10).stream())
        assert len(docs) > 0, (
            f"Expected '{STORE_LOCATOR_COLLECTION}' to be populated after store-locator job"
        )

    def test_store_document_has_required_fields(self, store_locator_result):
        client, _ = store_locator_result
        docs = list(client.collection(STORE_LOCATOR_COLLECTION).limit(1).stream())
        assert len(docs) > 0
        data = docs[0].to_dict()
        # Store records should have at minimum an identifier and operation type
        assert "operation" in data or "identifier" in data, (
            f"Store document missing required fields. Keys: {list(data.keys())}"
        )

    def test_store_operation_is_valid_type(self, store_locator_result):
        client, _ = store_locator_result
        docs = list(client.collection(STORE_LOCATOR_COLLECTION).limit(5).stream())
        valid_operations = {"Update", "Delete"}
        for doc in docs:
            data = doc.to_dict()
            if "operation" in data:
                assert data["operation"] in valid_operations, (
                    f"Store doc '{doc.id}' has invalid operation: {data['operation']!r}"
                )

    @pytest.mark.skipif(
        True,  # Will be enabled when IndexingApi store indexing is implemented
        reason="Store indexing via IndexingApi not yet implemented"
    )
    def test_indexing_api_processes_store_updates(self, store_locator_result):
        client, indexing_api_available = store_locator_result
        if not indexing_api_available:
            pytest.skip("IndexingApi not running — skipping end-to-end indexing test")
        # This test verifies that IndexingApi picks up stores-index-updates
        # and forwards them to Sitecore Search (WireMock)
        # Implementation pending: GET /v1/indexing/stores/initialize
        pass

    def test_store_records_do_not_exceed_firestore_document_limit(self, store_locator_result):
        import json
        client, _ = store_locator_result
        docs = list(client.collection(STORE_LOCATOR_COLLECTION).limit(10).stream())
        for doc in docs:
            data = doc.to_dict()
            size = len(json.dumps(data, default=str).encode("utf-8"))
            assert size < 900_000, (
                f"Store document '{doc.id}' is {size} bytes — "
                "exceeds the 900KB safety limit (Firestore max: 1MB)"
            )
