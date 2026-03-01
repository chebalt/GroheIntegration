"""
shopping-cart — ShoppingCartApi HTTP integration tests.

Tests anonymous cart operations against a live ShoppingCartApi container
backed by WireMock (which stubs the Hybris REST API).

Requires: make infra-shopping-cart-up
WireMock stubs:
  fixtures/mocks/hybris/cart-create.json    (POST /{site}/users/{user}/carts)
  fixtures/mocks/hybris/cart-add-entry.json (POST /{site}/users/{user}/carts/{id}/entries)
  fixtures/mocks/hybris/cart-delete.json    (DELETE /{site}/users/{user}/carts/{id})
  fixtures/mocks/hybris/hybris-token.json   (GET /token → Hybris bearer token)

Routes (ShoppingCartApi):
  GET    /neo/cart/v1/detail      ?locale=de-DE[&cartId=...]
  POST   /neo/cart/v1/addEntry    body: {locale, sku, quantity[, cartId]}
  DELETE /neo/cart/v1/delete      body: {locale[, cartId]}

Anonymous-user behavior (no Authorization header):
  - GET detail, no cartId  → 200 empty cart (no Hybris call)
  - POST addEntry, no cartId → creates Hybris cart then adds entry → 200
  - DELETE delete, no cartId → 400 immediately (cartId required for anonymous)
  - DELETE delete, with cartId → deletes Hybris cart → 200

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

    def test_get_detail_anonymous_without_cart_id_returns_empty_cart(self, shopping_cart_result):
        """
        Anonymous user with no cartId → service returns empty CartDetailResponse
        immediately without calling Hybris (fast path in ShoppingCartService).
        """
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.get(
            f"{BASE}/detail",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 for anonymous empty cart, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_add_entry_anonymous_without_cart_id_creates_cart_and_returns_200(self, shopping_cart_result):
        """
        Anonymous user, no cartId → service calls CreateCart then AddEntryToShoppingCart
        via WireMock. WireMock cart-create returns guid='test-cart-guid-002'.
        """
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.post(
            f"{BASE}/addEntry",
            json={"locale": "de-DE", "sku": "40806000", "quantity": 1},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from addEntry, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        body = resp.json()
        assert body.get("sku") == "40806000", f"Expected sku=40806000 in response, got: {body}"
        assert body.get("cartId") == "test-cart-guid-002", (
            f"Expected cartId=test-cart-guid-002 (from WireMock stub), got: {body.get('cartId')}"
        )

    def test_delete_cart_without_cart_id_returns_400(self, shopping_cart_result):
        """
        Anonymous user with no cartId → service returns 400 immediately:
        'Cart deletion failed: CartId must be provided for anonymous user.'
        """
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.delete(
            f"{BASE}/delete",
            json={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 400, (
            f"Expected 400 for anonymous delete without cartId, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )

    def test_delete_cart_with_cart_id_returns_200(self, shopping_cart_result):
        """
        Anonymous user with cartId='00000001' → service calls DeleteShoppingCart
        via WireMock. WireMock cart-delete returns 200.
        """
        anon_session, _, _ = shopping_cart_result
        resp = anon_session.delete(
            f"{BASE}/delete",
            json={"locale": "de-DE", "cartId": "00000001"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 for anonymous delete with cartId, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )
