"""
shopping-cart — ShoppingCartApi conftest.

Module-scoped fixture: checks if ShoppingCartApi is available, seeds Firestore,
and yields (anon_session, auth_session, firestore_client).

Infrastructure required: make infra-shopping-cart-up

WireMock stubs: fixtures/mocks/hybris/cart-*.json
"""

import os
import time

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST  = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
SHOPPING_CART_API_HOST   = os.environ.get("SHOPPING_CART_API_HOST", "localhost:8087")
WIREMOCK_HOST            = os.environ.get("WIREMOCK_HOST", "localhost:8081")

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    """Return True if the service is reachable at /health."""
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def shopping_cart_result(firestore_client):
    """
    Check ShoppingCartApi availability, seed Firestore if needed, yield sessions.

    Skips the entire module if the service is not running.

    Yields:
        (anon_session, auth_session, firestore_client)
    """
    if not _is_api_available(SHOPPING_CART_API_HOST):
        pytest.skip(
            f"ShoppingCartApi not running at {SHOPPING_CART_API_HOST}. "
            "Run 'make infra-shopping-cart-up' to start it."
        )

    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    anon_session = requests.Session()
    anon_session.headers.update({"Content-Type": "application/json"})

    auth_session = requests.Session()
    auth_session.headers.update({
        "Content-Type": "application/json",
        # Integration JWT — service accepts any non-empty token in Integration env
        "Authorization": "Bearer integration-test-token",
    })

    yield anon_session, auth_session, firestore_client
