"""
Layer 4 — Indexing pipeline tests.

Scope: Firestore products-index-updates → .NET Indexing API → Sitecore Search (WireMock).

Infrastructure required:
  docker compose --profile phase3 up -d

The IndexingApi (grohe-neo-services/GroheNeo.IndexingApi) is built from source and runs
at localhost:8082. WireMock stubs in fixtures/mocks/sitecore-search/ capture ingestion
calls so tests can assert the exact requests sent to Sitecore Search.

Trigger endpoint: GET /v1/indexing/products/initialize
WireMock journal:  GET http://localhost:8081/__admin/requests
"""

import json

import pytest

from tests.indexing.conftest import (
    INDEXING_DELETE_DOC_ID,
    INDEXING_UPDATE_DOC_ID,
    _decode_wiremock_body,
)


def _put_requests(wiremock_requests: list) -> list:
    """Filter WireMock journal to PUT requests (Sitecore Search Update)."""
    return [r for r in wiremock_requests if r["request"]["method"] == "PUT"]


def _delete_requests(wiremock_requests: list) -> list:
    """Filter WireMock journal to DELETE requests (Sitecore Search Delete)."""
    return [r for r in wiremock_requests if r["request"]["method"] == "DELETE"]


@pytest.mark.indexing
class TestIndexingPipeline:
    """
    Full pipeline: products-index-updates (Firestore) → Indexing API → Sitecore Search (WireMock).

    The module-scoped fixture in conftest.py:
      - Clears products-index-updates
      - Seeds one Update doc (IDX_0_de_DE) and one Delete doc (IDX_1_de_DE)
      - Waits for the IndexingApi /health endpoint
      - Resets the WireMock request journal
      - Calls GET /v1/indexing/products/initialize
      - Yields (response, wiremock_requests, firestore_client)
    """

    def test_full_product_indexing_pipeline_sends_correct_payload(self, indexing_result):
        """
        GET /v1/indexing/products/initialize returns HTTP 200 and WireMock received
        at least one PUT request to the Sitecore Search Ingestion endpoint.
        """
        response, wiremock_requests, client = indexing_result
        assert response.status_code == 200, (
            f"IndexingApi returned {response.status_code}: {response.text[:500]}"
        )
        put_reqs = _put_requests(wiremock_requests)
        all_methods = [r["request"]["method"] for r in wiremock_requests]
        assert len(put_reqs) >= 1, (
            f"Expected at least 1 PUT request to Sitecore Search Ingestion. "
            f"WireMock received: {all_methods}"
        )

    def test_deleted_product_sends_delete_operation_to_sitecore(self, indexing_result):
        """
        A product queued as operation=Delete (IDX_1_de_DE) triggers a DELETE request
        to the Sitecore Search Ingestion API.
        """
        response, wiremock_requests, client = indexing_result
        delete_reqs = _delete_requests(wiremock_requests)
        all_methods = [r["request"]["method"] for r in wiremock_requests]
        assert len(delete_reqs) >= 1, (
            f"Expected at least 1 DELETE request to Sitecore Search Ingestion. "
            f"WireMock received: {all_methods}"
        )

    def test_updated_product_sends_update_with_correct_fields(self, indexing_result):
        """
        The PUT payload for the Updated product contains the document fields seeded
        in Firestore — specifically the 'name' field must match.
        """
        response, wiremock_requests, client = indexing_result
        put_reqs = _put_requests(wiremock_requests)
        assert len(put_reqs) >= 1, "No PUT request found in WireMock journal"

        body_str = _decode_wiremock_body(put_reqs[0]["request"])
        assert body_str, "PUT request body is empty"

        payload = json.loads(body_str)
        doc = payload.get("document", {})
        fields = doc.get("fields", {})

        assert "name" in fields, (
            f"'name' field missing from Sitecore Search payload. "
            f"Available fields: {sorted(fields.keys())}"
        )
        assert fields["name"] == "Test Indexing Product", (
            f"Expected name='Test Indexing Product', got: {fields['name']}"
        )

    def test_ingestion_payload_includes_finish_definitions(self, indexing_result):
        """
        finish_definitions must appear in the PUT payload so Sitecore Search can
        filter products by finish/colour. Asserts the array is non-empty.
        """
        response, wiremock_requests, client = indexing_result
        put_reqs = _put_requests(wiremock_requests)
        assert len(put_reqs) >= 1, "No PUT request found in WireMock journal"

        body_str = _decode_wiremock_body(put_reqs[0]["request"])
        payload = json.loads(body_str)
        doc = payload.get("document", {})
        fields = doc.get("fields", {})

        assert "finish_definitions" in fields, (
            f"'finish_definitions' missing from Sitecore Search payload. "
            f"Available fields: {sorted(fields.keys())}"
        )
        assert len(fields["finish_definitions"]) > 0, (
            "finish_definitions array is empty — expected at least 1 finish entry"
        )

    def test_ingestion_payload_locale_is_correct(self, indexing_result):
        """
        The locale query parameter in the Sitecore Search PUT URL must match
        the document's culture (de_de).
        """
        response, wiremock_requests, client = indexing_result
        put_reqs = _put_requests(wiremock_requests)
        assert len(put_reqs) >= 1, "No PUT request found in WireMock journal"

        url = put_reqs[0]["request"]["url"]
        assert "locale=de_de" in url, (
            f"Expected 'locale=de_de' in PUT URL, got: {url}"
        )
