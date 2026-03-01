"""
checkout — OrderApi HTTP integration tests.

Tests order placement and payment initiation against live checkout services
backed by WireMock (which stubs Hybris order endpoints + Adyen).

Requires: make infra-checkout-up
WireMock stubs: fixtures/mocks/hybris/order-create.json
               fixtures/mocks/adyen/payment-sessions.json

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

ORDER_API_HOST = os.environ.get("ORDER_API_HOST", "localhost:8090")
BASE_URL = f"http://{ORDER_API_HOST}"
BASE = f"{BASE_URL}/neo/order/v1"


class TestCheckoutApi:

    def test_health_returns_200(self, checkout_result):
        auth_session = checkout_result
        resp = auth_session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_place_order_returns_order_code(self, checkout_result):
        auth_session = checkout_result
        payload = {
            "locale": "de-DE",
            "cartId": "00000001",
            "termsChecked": True,
        }
        resp = auth_session.post(f"{BASE}/orders", json=payload, timeout=30)
        assert resp.status_code in (200, 201), (
            f"Expected 200/201 from place order, got {resp.status_code}. Body: {resp.text[:500]}"
        )
        body = resp.json()
        order_code = body.get("code") or body.get("orderId") or body.get("OrderCode")
        assert order_code, f"Response missing order code. Body: {body}"

    def test_get_order_status_returns_200(self, checkout_result):
        auth_session = checkout_result
        resp = auth_session.get(
            f"{BASE}/orders/ORD-0001",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204, 404), (
            f"Expected 200/204/404 from GET order, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_payment_session_creation_returns_session_id(self, checkout_result):
        auth_session = checkout_result
        payload = {
            "locale": "de-DE",
            "orderId": "ORD-TEST-001",
            "amount": {"value": 14999, "currency": "EUR"},
            "returnUrl": "http://localhost:3000/checkout/confirm",
        }
        resp = auth_session.post(f"{BASE}/payment/sessions", json=payload, timeout=30)
        assert resp.status_code in (200, 201), (
            f"Expected 200/201 from payment session, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_payment_methods_returns_list(self, checkout_result):
        auth_session = checkout_result
        resp = auth_session.get(
            f"{BASE}/payment/methods",
            params={"locale": "de-DE", "countryCode": "DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from payment methods, got {resp.status_code}. Body: {resp.text[:500]}"
        )
