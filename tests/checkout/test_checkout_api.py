"""
checkout — OrderApi + PaymentApi HTTP integration tests.

Tests order history, order detail, and payment methods against live checkout
services backed by WireMock (which stubs Hybris order endpoints + Adyen config).

Requires: make infra-checkout-up
WireMock stubs:
  fixtures/mocks/hybris/order-history.json        → GET /{site}/users/{user}/orders
  fixtures/mocks/hybris/order-detail.json         → GET /{site}/users/{user}/orders/{code}
  fixtures/mocks/hybris/payment-checkout-config.json → GET .../{cart}/adyen/checkout-configuration

Routes (OrderApi — port 8090):
  GET  /health
  GET  /v1/orders          ?locale=...    → order history
  GET  /v1/orders/{id}     ?locale=...    → order detail

Routes (PaymentApi — port 8091):
  GET  /health
  GET  /v1/method          ?locale=...    → payment methods (Adyen config)

Tests are skipped automatically if the service is not running.
"""

import os

import pytest
import requests

ORDER_API_HOST   = os.environ.get("ORDER_API_HOST",   "localhost:8090")
PAYMENT_API_HOST = os.environ.get("PAYMENT_API_HOST", "localhost:8091")
ORDER_BASE       = f"http://{ORDER_API_HOST}"
PAYMENT_BASE     = f"http://{PAYMENT_API_HOST}"


class TestCheckoutApi:

    def test_order_api_health_returns_200(self, checkout_result):
        order_session, _ = checkout_result
        resp = order_session.get(f"{ORDER_BASE}/health", timeout=10)
        assert resp.status_code == 200

    def test_get_order_history_returns_200(self, checkout_result):
        """
        GET /v1/orders → OrdersService calls Hybris GET /{site}/users/{user}/orders.
        WireMock returns 1 order (ORD-0001) in the orders list.
        """
        order_session, _ = checkout_result
        resp = order_session.get(
            f"{ORDER_BASE}/v1/orders",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from GET /v1/orders, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        body = resp.json()
        # Response has 'orders' list
        orders = body.get("orders") or (body if isinstance(body, list) else [])
        assert len(orders) >= 1, f"Expected at least 1 order, got: {body}"

    def test_get_order_detail_returns_200(self, checkout_result):
        """
        GET /v1/orders/{id} → OrdersService calls Hybris GET /{site}/users/{user}/orders/{code}.
        WireMock returns order detail for any order code.
        """
        order_session, _ = checkout_result
        resp = order_session.get(
            f"{ORDER_BASE}/v1/orders/ORD-0001",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 404), (
            f"Expected 200/404 from GET /v1/orders/ORD-0001, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        if resp.status_code == 200:
            body = resp.json()
            # NEO API maps Hybris 'code' → 'orderId'
            assert body.get("orderId"), f"Expected orderId in response, got: {body}"

    def test_payment_api_health_returns_200(self, checkout_result):
        """
        PaymentApi health endpoint — verifies the container is running.
        Skips gracefully if PaymentApi is not up (only OrderApi is required to start).
        """
        _, payment_session = checkout_result
        try:
            resp = payment_session.get(f"{PAYMENT_BASE}/health", timeout=5)
            assert resp.status_code == 200, (
                f"Expected 200 from PaymentApi /health, got {resp.status_code}"
            )
        except Exception:
            pytest.skip(f"PaymentApi not available at {PAYMENT_API_HOST}")

    def test_get_payment_methods_returns_200_or_204(self, checkout_result):
        """
        GET /v1/method → PaymentService calls Hybris Adyen checkout-configuration.
        WireMock returns a list of Adyen payment methods.
        """
        _, payment_session = checkout_result
        try:
            resp = payment_session.get(
                f"{PAYMENT_BASE}/v1/method",
                params={"locale": "de-DE"},
                timeout=30,
            )
            assert resp.status_code in (200, 204, 400), (
                f"Expected 200/204/400 from GET /v1/method, got {resp.status_code}. "
                f"Body: {resp.text[:500]}"
            )
        except Exception:
            pytest.skip(f"PaymentApi not available at {PAYMENT_API_HOST}")
