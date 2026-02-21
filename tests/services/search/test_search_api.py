"""
Phase 5 — SearchApi HTTP integration tests.

Tests the SearchApi endpoints against a live SearchApi container backed by
WireMock (which stubs the Sitecore Search Discovery API).

Requires: docker compose --profile phase5 up -d
  (no seed_config.py needed — SearchApi has no Firestore dependency)

Language format: SearchApi expects XM Cloud format `xx-xx` (5 chars).
  'de-de' maps internally to locale 'de_de' → source 'integration' → WireMock stub.
JSON keys:  'lang' for language, 'q' for query (from BaseLimitlessSearchParameters).
"""

import os

import pytest

SEARCH_API_HOST = os.environ.get("SEARCH_API_HOST", "localhost:8085")
BASE_URL = f"http://{SEARCH_API_HOST}"


class TestSearchApi:
    def test_search_api_health_returns_200(self, search_result):
        session = search_result
        resp = session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200, (
            f"Expected 200 from SearchApi /health, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )

    def test_product_search_returns_ok_for_valid_query(self, search_result):
        session = search_result
        resp = session.post(
            f"{BASE_URL}/product/v1/search",
            json={"lang": "de-de", "q": "product", "limit": 10, "offset": 0},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200 or 204 from product search, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_product_search_response_contains_items_when_200(self, search_result):
        session = search_result
        resp = session.post(
            f"{BASE_URL}/product/v1/search",
            json={"lang": "de-de", "q": "product", "limit": 10, "offset": 0},
            timeout=30,
        )
        if resp.status_code == 204:
            pytest.skip("SearchApi returned 204 (empty results) — skipping content check")

        assert resp.status_code == 200
        body = resp.json()
        # Results<T>.ResultItems is serialized as "results" (JsonPropertyName attribute)
        assert "results" in body, (
            f"Response body has no 'results' key. Got keys: {list(body.keys())}"
        )
        assert len(body["results"]) > 0, (
            f"'results' is empty — WireMock stub returned 1 product, expected at least 1 mapped"
        )

    def test_product_search_returns_400_for_missing_language(self, search_result):
        session = search_result
        resp = session.post(
            f"{BASE_URL}/product/v1/search",
            json={"q": "product", "limit": 10, "offset": 0},
            timeout=30,
        )
        assert resp.status_code == 400, (
            f"Expected 400 when 'lang' is missing, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )

    def test_autosuggest_returns_ok_for_valid_query(self, search_result):
        session = search_result
        resp = session.post(
            f"{BASE_URL}/autosuggest/v1/suggest",
            json={"lang": "de-de", "q": "product"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200 or 204 from autosuggest, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
