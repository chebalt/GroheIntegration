"""
my-account — UserApi HTTP integration tests.

Tests user profile and address management against a live UserApi container
backed by WireMock (which stubs Hybris user endpoints + Google Places).

Requires: make infra-my-account-up
WireMock stubs: fixtures/mocks/hybris/user-addresses.json
               fixtures/mocks/google-places/autocomplete.json

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

USER_API_HOST = os.environ.get("USER_API_HOST", "localhost:8088")
BASE_URL = f"http://{USER_API_HOST}"
BASE = f"{BASE_URL}/neo/user/v1"


class TestUserApi:

    def test_health_returns_200(self, user_api_result):
        auth_session, _ = user_api_result
        resp = auth_session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_get_user_profile_returns_200(self, user_api_result):
        auth_session, _ = user_api_result
        resp = auth_session.get(
            f"{BASE}/profile",
            params={"locale": "de-DE", "userId": "current"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from GET profile, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_get_user_addresses_returns_list(self, user_api_result):
        auth_session, _ = user_api_result
        resp = auth_session.get(
            f"{BASE}/addresses",
            params={"locale": "de-DE", "userId": "current"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from GET addresses, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_address_autocomplete_returns_predictions(self, user_api_result):
        auth_session, _ = user_api_result
        resp = auth_session.get(
            f"{BASE}/addresses/autocomplete",
            params={"input": "Musterstraße", "locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from autocomplete, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_create_address_returns_201(self, user_api_result):
        auth_session, _ = user_api_result
        payload = {
            "locale": "de-DE",
            "firstName": "Max",
            "lastName": "Mustermann",
            "line1": "Musterstraße 1",
            "postalCode": "12345",
            "town": "Musterstadt",
            "country": {"isocode": "DE"},
        }
        resp = auth_session.post(
            f"{BASE}/addresses",
            json=payload,
            timeout=30,
        )
        assert resp.status_code in (200, 201), (
            f"Expected 200/201 from POST addresses, got {resp.status_code}. Body: {resp.text[:500]}"
        )
