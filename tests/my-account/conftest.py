"""
my-account — UserApi conftest.

Module-scoped fixture: checks if UserApi is available, then yields sessions.

Infrastructure required: make infra-my-account-up

WireMock stubs: fixtures/mocks/hybris/user-*.json
               fixtures/mocks/google-places/autocomplete.json
               fixtures/mocks/recaptcha/verify-success.json
"""

import os

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
USER_API_HOST           = os.environ.get("USER_API_HOST", "localhost:8088")


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def user_api_result(firestore_client):
    """
    Check UserApi availability, yield (auth_session, firestore_client).
    Skips if the service is not running.
    """
    if not _is_api_available(USER_API_HOST):
        pytest.skip(
            f"UserApi not running at {USER_API_HOST}. "
            "Run 'make infra-my-account-up' to start it."
        )

    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    auth_session = requests.Session()
    auth_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": "Bearer integration-test-token",
    })

    yield auth_session, firestore_client
