"""
shopping-cart — ShoppingCartApi HTTP integration tests.

Tests anonymous and authenticated cart operations against a live ShoppingCartApi
container backed by WireMock (which stubs Hybris REST API).

Requires: make infra-shopping-cart-up
WireMock stubs: fixtures/mocks/hybris/cart-*.json

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

SHOPPING_CART_API_HOST = os.environ.get("SHOPPING_CART_API_HOST", "localhost:8087")
BASE_URL = f"http://{SHOPPING_CART_API_HOST}"
BASE = f"{BASE_URL}/neo/cart/v1"


class TestShoppingCartApi:

    def test_health_returns_200(self, shopping_cart_result):
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200, (
            f"Expected 200 from ShoppingCartApi /health, got {resp.status_code}."
        )

    def test_create_anonymous_cart_returns_cart_id(self, shopping_cart_result):
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.post(f"{BASE}/carts", json={"locale": "de-DE"}, timeout=30)
        assert resp.status_code in (200, 201), (
            f"Expected 200/201 from cart creation, got {resp.status_code}. Body: {resp.text[:500]}"
        )
        body = resp.json()
        cart_id = body.get("cartId") or body.get("CartId") or body.get("code") or body.get("guid")
        assert cart_id, f"Response missing cart ID. Body: {body}"

    def test_get_cart_returns_200_for_existing_cart(self, shopping_cart_result):
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.get(
            f"{BASE}/carts",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from GET carts, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_add_item_to_cart_returns_200(self, shopping_cart_result):
        _, auth_session, _ = shopping_cart_result
        resp = auth_session.post(
            f"{BASE}/carts/00000001/entries",
            json={"productCode": "40806000", "quantity": 1, "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 201), (
            f"Expected 200/201 from add-to-cart, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_delete_cart_returns_200(self, shopping_cart_result):
        _, auth_session, _ = shopping_cart_result
        resp = auth_session.delete(
            f"{BASE}/carts/00000001",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from DELETE cart, got {resp.status_code}. Body: {resp.text[:200]}"
        )
