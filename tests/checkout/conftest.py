"""
checkout — OrderApi + PaymentApi conftest.

Module-scoped fixture: checks if OrderApi is available, then yields sessions.

Infrastructure required: make infra-checkout-up

WireMock stubs:
  fixtures/mocks/hybris/order-history.json     → GET /{site}/users/{user}/orders
  fixtures/mocks/hybris/order-detail.json      → GET /{site}/users/{user}/orders/{code}
  fixtures/mocks/hybris/payment-checkout-config.json → GET /{site}/users/{user}/carts/{cart}/adyen/checkout-configuration
  fixtures/mocks/hybris/hybris-token.json      → GET /token (anonymous Hybris token)

Auth: plain Bearer token (no JWT validation on GET endpoints).
INTEGRATION_TEST_MODE=true bypasses GoogleIdTokenHandler GCP calls.
"""

import os

import pytest
import requests

ORDER_API_HOST   = os.environ.get("ORDER_API_HOST",   "localhost:8090")
PAYMENT_API_HOST = os.environ.get("PAYMENT_API_HOST", "localhost:8091")


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def checkout_result():
    """
    Check OrderApi availability, yield (order_session, payment_session).
    Skips if OrderApi is not running. PaymentApi tests skip individually if unavailable.
    """
    if not _is_api_available(ORDER_API_HOST):
        pytest.skip(
            f"OrderApi not running at {ORDER_API_HOST}. "
            "Run 'make infra-checkout-up' to start it."
        )

    order_session = requests.Session()
    order_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": "Bearer integration-test-token",
    })

    payment_session = requests.Session()
    payment_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": "Bearer integration-test-token",
    })

    yield order_session, payment_session
