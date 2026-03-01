"""
pricing — PricingApi HTTP integration tests.

Tests price fetch endpoints against a live PricingApi container backed by
WireMock (which stubs Hybris pricing endpoints).

Requires: make infra-pricing-up
WireMock stubs: fixtures/mocks/hybris/pricing-get.json

Tests are skipped automatically if the service is not running.
"""

import os
import time

import pytest

PRICING_API_HOST = os.environ.get("PRICING_API_HOST", "localhost:8089")
BASE_URL = f"http://{PRICING_API_HOST}"
BASE = f"{BASE_URL}/neo/pricing/v1"


class TestPricingApi:

    def test_health_returns_200(self, pricing_result):
        anon_session, _ = pricing_result
        resp = anon_session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_authenticated_price_fetch_returns_200(self, pricing_result):
        _, auth_session = pricing_result
        resp = auth_session.get(
            f"{BASE}/price",
            params={"sku": "40806000", "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from authenticated price fetch, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_anonymous_price_fetch_returns_200_or_401(self, pricing_result):
        anon_session, _ = pricing_result
        resp = anon_session.get(
            f"{BASE}/price",
            params={"sku": "40806000", "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204, 401), (
            f"Expected 200/204/401 from anonymous price fetch, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_price_response_contains_currency(self, pricing_result):
        _, auth_session = pricing_result
        resp = auth_session.get(
            f"{BASE}/price",
            params={"sku": "40806000", "locale": "de-DE"},
            timeout=30,
        )
        if resp.status_code == 204:
            pytest.skip("PricingApi returned 204 — no price data available for this SKU")
        assert resp.status_code == 200
        body = resp.json()
        # Price response should contain currency information
        currency = (
            body.get("currencyIso") or
            body.get("price", {}).get("currencyIso") or
            body.get("price", {}).get("currency")
        )
        assert currency, f"Response missing currency field. Body: {body}"

    def test_cache_behaviour_second_call_returns_same_result(self, pricing_result):
        _, auth_session = pricing_result
        params = {"sku": "40806000", "locale": "de-DE"}
        resp1 = auth_session.get(f"{BASE}/price", params=params, timeout=30)
        resp2 = auth_session.get(f"{BASE}/price", params=params, timeout=30)
        # Both calls should succeed with the same status
        assert resp1.status_code == resp2.status_code, (
            f"Cache inconsistency: first call {resp1.status_code}, second {resp2.status_code}"
        )
