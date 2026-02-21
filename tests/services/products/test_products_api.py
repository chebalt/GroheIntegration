"""
Phase 4 — ProductsApi HTTP integration tests.

Tests the /neo/product/v1/ endpoints against a live ProductsApi container
connected to the Firestore emulator.

Requires: docker compose --profile phase4 up -d
  (with seed_config.py already run before starting the containers)
"""

import os

import pytest

PRODUCTS_API_HOST = os.environ.get("PRODUCTS_API_HOST", "localhost:8084")
BASE_URL = f"http://{PRODUCTS_API_HOST}"


class TestProductsApi:
    def test_products_api_returns_product_for_known_sku(self, products_result):
        session, _ = products_result
        resp = session.get(
            f"{BASE_URL}/neo/product/v1/PROD-001",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 for known SKU 'PROD-001', got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_product_response_contains_sku_field(self, products_result):
        session, _ = products_result
        resp = session.get(
            f"{BASE_URL}/neo/product/v1/PROD-001",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200
        body = resp.json()
        # ASP.NET Core camelCase serialization → "sku"; accept "SKU" as fallback
        sku_value = body.get("sku") or body.get("SKU")
        assert sku_value is not None, (
            f"Response missing 'sku' field. Got keys: {list(body.keys())}"
        )
        assert sku_value == "PROD-001", (
            f"Expected sku='PROD-001', got {sku_value!r}"
        )

    def test_products_api_returns_404_for_unknown_sku(self, products_result):
        session, _ = products_result
        resp = session.get(
            f"{BASE_URL}/neo/product/v1/UNKNOWN-SKU-99999",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 404, (
            f"Expected 404 for unknown SKU, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )

    def test_category_endpoint_returns_data_for_locale(self, products_result):
        session, _ = products_result
        resp = session.get(
            f"{BASE_URL}/neo/product/v1/category",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200 or 204 from category endpoint, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        if resp.status_code == 200:
            body = resp.json()
            # Response wraps items in "categories" key
            categories = body.get("categories") or body.get("Categories") or body
            assert categories is not None, (
                f"Category response has unexpected shape: {list(body.keys())}"
            )

    def test_variants_endpoint_returns_variants_for_known_sku(self, products_result):
        session, _ = products_result
        resp = session.get(
            f"{BASE_URL}/neo/product/v1/variants",
            params={"sku": "PROD-001", "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from variants endpoint for PROD-001, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
