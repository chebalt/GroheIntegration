"""
checkout — OrderApi + PaymentApi conftest.

Module-scoped fixture: checks if OrderApi is available, then yields sessions.

Infrastructure required: make infra-checkout-up

WireMock stubs: fixtures/mocks/hybris/order-create.json
               fixtures/mocks/adyen/payment-sessions.json
               fixtures/mocks/adyen/payment-methods.json
"""

import os

import pytest
import requests

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
ORDER_API_HOST          = os.environ.get("ORDER_API_HOST", "localhost:8090")


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def checkout_result():
    """
    Check OrderApi availability, yield auth_session.
    Skips if the service is not running.
    """
    if not _is_api_available(ORDER_API_HOST):
        pytest.skip(
            f"OrderApi not running at {ORDER_API_HOST}. "
            "Run 'make infra-checkout-up' to start it."
        )

    auth_session = requests.Session()
    auth_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": "Bearer integration-test-token",
    })

    yield auth_session
