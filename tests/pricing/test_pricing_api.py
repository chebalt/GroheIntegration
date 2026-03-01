"""
pricing — PricingApi HTTP integration tests.

Tests price fetch endpoints against a live PricingApi container backed by
WireMock (which stubs Hybris pricing + token endpoints).

Requires: make infra-pricing-up
WireMock stubs:
  fixtures/mocks/hybris/pricing-get.json  (GET /{site}/users/{user}/products/prices)
  fixtures/mocks/hybris/hybris-token.json (GET /token → Hybris bearer token)

Route (PricingApi):
  GET /neo/product/v1/price  ?sku=...&locale=...&useMock=false

Authentication:
  - Anonymous (no Authorization header): gets Hybris token via /token, calls Hybris
  - useMock=true: returns from in-memory hardcoded dataset, no JWT required
  - Authenticated with invalid JWT → 401 (JWT parse fails, email claim missing)

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

PRICING_API_HOST = os.environ.get("PRICING_API_HOST", "localhost:8089")
BASE_URL = f"http://{PRICING_API_HOST}"
PRICE_ENDPOINT = f"{BASE_URL}/neo/product/v1/price"

# SKU present in MockPricingApi's hardcoded dataset (first entry)
MOCK_SKU = "36456000"
# SKU present in the WireMock pricing-get.json stub
HYBRIS_SKU = "40806000"


class TestPricingApi:

    def test_health_returns_200(self, pricing_result):
        anon_session, _ = pricing_result
        resp = anon_session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_anonymous_price_fetch_returns_200(self, pricing_result):
        """
        Anonymous request (no Authorization header) → service calls GET /token
        (WireMock) then GET /products/prices (WireMock) → 200 with price data.
        """
        anon_session, _ = pricing_result
        resp = anon_session.get(
            PRICE_ENDPOINT,
            params={"sku": HYBRIS_SKU, "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from anonymous price fetch, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        body = resp.json()
        prices = body.get("prices", [])
        assert prices, f"Expected non-empty prices list, got: {body}"
        assert prices[0].get("currencyISO") == "EUR", (
            f"Expected currencyISO=EUR, got: {prices[0]}"
        )

    def test_authenticated_with_invalid_jwt_returns_401(self, pricing_result):
        """
        Bearer token that is not a valid JWT → PricingService cannot extract
        email claim → returns 401 'Not authorized'.
        This confirms the JWT validation guard works.
        """
        _, auth_session = pricing_result
        resp = auth_session.get(
            PRICE_ENDPOINT,
            params={"sku": HYBRIS_SKU, "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 401, (
            f"Expected 401 for invalid JWT, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )

    def test_mock_mode_returns_200_with_currency(self, pricing_result):
        """
        useMock=true → MockPricingApi returns from hardcoded in-memory dataset.
        No JWT validation, no Hybris call. SKU '36456000' is in the mock dataset.
        """
        anon_session, _ = pricing_result
        resp = anon_session.get(
            PRICE_ENDPOINT,
            params={"sku": MOCK_SKU, "locale": "de-DE", "useMock": "true"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from mock mode, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        body = resp.json()
        prices = body.get("prices", [])
        assert prices, f"Expected non-empty prices list in mock mode, got: {body}"
        assert prices[0].get("currencyISO"), (
            f"Expected currencyISO in mock response, got: {prices[0]}"
        )

    def test_cache_returns_same_status_on_repeat_call(self, pricing_result):
        """
        Two consecutive anonymous calls → second call hits in-memory cache
        (5-min TTL). Both should return the same status code.
        """
        anon_session, _ = pricing_result
        params = {"sku": HYBRIS_SKU, "locale": "de-DE"}
        resp1 = anon_session.get(PRICE_ENDPOINT, params=params, timeout=30)
        resp2 = anon_session.get(PRICE_ENDPOINT, params=params, timeout=30)
        assert resp1.status_code == resp2.status_code, (
            f"Cache inconsistency: first call {resp1.status_code}, second {resp2.status_code}"
        )
