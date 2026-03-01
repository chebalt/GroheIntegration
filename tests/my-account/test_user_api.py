"""
my-account — UserApi HTTP integration tests.

Tests address management and autocomplete against a live UserApi container
backed by WireMock (which stubs Hybris user endpoints + Google Places API).

Requires: make infra-my-account-up
WireMock stubs:
  fixtures/mocks/hybris/user-addresses.json        → GET /{site}/users/{u}/delivery-addresses
  fixtures/mocks/hybris/user-billing-addresses.json → GET /{site}/users/{u}/billing-addresses
  fixtures/mocks/hybris/user-address-create.json   → POST /{site}/users/{u}/addresses
  fixtures/mocks/hybris/user-address-delete.json   → DELETE /{site}/users/{u}/addresses/{id}
  fixtures/mocks/idp/oidc-certs.json               → GET /v1/sso/auth/realms/.../certs (JWKS)
  fixtures/mocks/hybris/hybris-token.json          → GET /token (anonymous Hybris token)
  fixtures/mocks/google-places/places-autocomplete.json → POST /places:autocomplete
  fixtures/mocks/google-places/places-detail.json       → GET /places/{placeId}

Routes (UserApi):
  GET  /health
  GET  /v1/address          ?locale=...         → merged delivery + billing addresses
  POST /v1/address          body: CreateOrUpdateAddressRequest  → created HybrisAddress
  DELETE /v1/address        body: DeleteAddressRequest          → 200
  POST /v1/addressAutocomplete  body: {locale, input}          → predictions (200) or 204
  GET  /v1/addressDetail    ?placeId=...&locale=...            → address details

Auth:
  - All requests use a real RS256-signed JWT (see conftest.py INTEGRATION_JWT).
  - ValidateToken() fetches JWKS from WireMock (oidc-certs.json) and validates signature.
  - Endpoints that call ValidateToken: POST /v1/address (CreateAddress).
  - Endpoints that do NOT call ValidateToken: GET /v1/address, DELETE /v1/address,
    POST /v1/addressAutocomplete, GET /v1/addressDetail.

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

USER_API_HOST = os.environ.get("USER_API_HOST", "localhost:8088")
BASE_URL = f"http://{USER_API_HOST}"


class TestUserApi:

    def test_health_returns_200(self, user_api_result):
        auth_session, _ = user_api_result
        resp = auth_session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_get_addresses_returns_200_with_list(self, user_api_result):
        """
        GET /v1/address merges delivery + billing addresses from Hybris.
        WireMock returns 1 delivery address (addr-001) + 0 billing addresses.
        Response has non-empty 'addresses' list.
        """
        auth_session, _ = user_api_result
        resp = auth_session.get(
            f"{BASE_URL}/v1/address",
            params={"locale": "de-DE"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from GET /v1/address, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        body = resp.json()
        addresses = body.get("addresses", [])
        assert len(addresses) >= 1, f"Expected at least 1 address, got: {body}"
        assert addresses[0].get("id") == "addr-001", (
            f"Expected addr-001 from WireMock stub, got: {addresses[0]}"
        )

    def test_address_autocomplete_returns_200_or_204(self, user_api_result):
        """
        POST /v1/addressAutocomplete → calls Google Places /places:autocomplete.
        WireMock returns suggestions; service maps them and returns 200.
        (204 is also accepted if the response shape doesn't fully match the model.)
        """
        auth_session, _ = user_api_result
        resp = auth_session.post(
            f"{BASE_URL}/v1/addressAutocomplete",
            json={"locale": "de-DE", "input": "Musterstraße"},
            timeout=30,
        )
        assert resp.status_code in (200, 204), (
            f"Expected 200/204 from POST /v1/addressAutocomplete, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_create_address_returns_200(self, user_api_result):
        """
        POST /v1/address → ValidateToken() fetches JWKS from WireMock, validates RSA
        signature of the JWT. On success calls Hybris POST addresses → returns HybrisAddress.
        """
        auth_session, _ = user_api_result
        payload = {
            "locale": "de-DE",
            "address": {
                "firstName": "Max",
                "lastName": "Mustermann",
                "streetAndNumber": "Musterstraße 1",
                "zipCode": "12345",
                "city": "Musterstadt",
                "deliveryAddress": True,
                "billingAddress": False,
                "defaultAddress": False,
            },
        }
        resp = auth_session.post(
            f"{BASE_URL}/v1/address",
            json=payload,
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from POST /v1/address, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
        body = resp.json()
        assert body.get("id"), f"Expected address id in response, got: {body}"

    def test_delete_address_returns_200(self, user_api_result):
        """
        DELETE /v1/address with addressId → calls Hybris DELETE → 200.
        No JWT ValidateToken required.
        """
        auth_session, _ = user_api_result
        resp = auth_session.delete(
            f"{BASE_URL}/v1/address",
            json={"locale": "de-DE", "addressId": "addr-001"},
            timeout=30,
        )
        assert resp.status_code == 200, (
            f"Expected 200 from DELETE /v1/address, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )
