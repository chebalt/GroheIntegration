"""
pricing — PricingApi conftest.

Module-scoped fixture: checks if PricingApi is available, then yields sessions.

Infrastructure required: make infra-pricing-up

WireMock stubs: fixtures/mocks/hybris/pricing-get.json
"""

import os

import pytest
import requests

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
PRICING_API_HOST        = os.environ.get("PRICING_API_HOST", "localhost:8089")


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def pricing_result():
    """
    Check PricingApi availability, yield (anon_session, auth_session).
    Skips if the service is not running.
    """
    if not _is_api_available(PRICING_API_HOST):
        pytest.skip(
            f"PricingApi not running at {PRICING_API_HOST}. "
            "Run 'make infra-pricing-up' to start it."
        )

    anon_session = requests.Session()
    anon_session.headers.update({"Content-Type": "application/json"})

    auth_session = requests.Session()
    auth_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": "Bearer integration-test-token",
    })

    yield anon_session, auth_session
