"""
my-account — UserApi conftest.

Module-scoped fixture: checks if UserApi is available, then yields sessions.

Infrastructure required: make infra-my-account-up

WireMock stubs:
  fixtures/mocks/hybris/user-addresses.json        (GET delivery-addresses)
  fixtures/mocks/hybris/user-billing-addresses.json (GET billing-addresses)
  fixtures/mocks/hybris/user-address-create.json   (POST addresses)
  fixtures/mocks/hybris/user-address-delete.json   (DELETE addresses/{id})
  fixtures/mocks/idp/oidc-certs.json               (GET JWKS — for JWT RSA validation)
  fixtures/mocks/hybris/hybris-token.json          (GET /token — anonymous Hybris token)
  fixtures/mocks/google-places/places-autocomplete.json (POST /places:autocomplete)
  fixtures/mocks/google-places/places-detail.json       (GET /places/{placeId})

Auth token: real RS256-signed JWT matching oidc-certs.json public key.
  kid=dev-test-key-1, sub=dev-user-001, email=dev.user@test.grohe.com,
  country=GB, exp=2208988800 (year 2039).
  UserApi's ValidateToken() fetches JWKS from WireMock, validates RSA signature locally.
"""

import os

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
USER_API_HOST           = os.environ.get("USER_API_HOST", "localhost:8088")

# Real RS256-signed JWT that matches the public key in fixtures/mocks/idp/oidc-certs.json.
# kid=dev-test-key-1 | sub=dev-user-001 | email=dev.user@test.grohe.com | country=GB
# exp=2208988800 (year 2039 — effectively non-expiring for tests)
INTEGRATION_JWT = (
    "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImRldi10ZXN0LWtleS0xIn0"
    ".eyJzdWIiOiJkZXYtdXNlci0wMDEiLCJlbWFpbCI6ImRldi51c2VyQHRlc3QuZ3JvaGUu"
    "Y29tIiwiZ2l2ZW5fbmFtZSI6IkRldiIsImZhbWlseV9uYW1lIjoiVXNlciIsInNhbHV0YX"
    "Rpb24iOiJNciIsImNvdW50cnkiOiJHQiIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJu"
    "ZW8iLCJjdXN0b21lciJdfSwiaWF0IjoxNzcyMTM1OTQzLCJleHAiOjIyMDg5ODg4MDB9"
    ".gcmlG24CC3-djPqOlR8OBX-Qb-yM_aiHujWrhW9gIoZZtRn36I4TExmFk_fPiHbiLaoG"
    "OpUJIByNRGe3pkin0sWmiXDI4gNrxFUeBDzb9oIb1osZiSDxeZW-oAPNisa8sDGiursZtG"
    "AuTj69Rw9-LgJ8PcXn4U9b4dBAixpvy-TcLoB5cXISoSuPistYQaOm3HIXM_O2n3twLdp"
    "Y8Oqy7FunzbXv5HVtn_96R7xiZLzzW30XrHAbvNjUBplPVq4CuoFMLKn-XdqeOksEEvlsZ"
    "Qn0dODk-iIaiW3UkmtHuuMO2oV0TzC_N7fTTSlAy_vYiNwjcY8wm4aTzXBnNir4lw"
)


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

    auth_session uses a real RS256-signed JWT so that ValidateToken() (which
    fetches JWKS from WireMock and validates RSA signature) passes for
    endpoints that require it (e.g. POST /v1/address).
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
        "Authorization": f"Bearer {INTEGRATION_JWT}",
    })

    yield auth_session, firestore_client
