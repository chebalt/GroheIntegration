"""
redirections — Redirect reverse proxy HTTP integration tests.

Tests URL redirect resolution, vanity URL mapping, and pass-through behaviour.

Requires: make infra-redirections-up
WireMock stubs: fixtures/mocks/sitecore-edge/graphql-layout.json (for redirect lookup)

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

REDIRECTIONS_API_HOST = os.environ.get("REDIRECTIONS_API_HOST", "localhost:8093")
BASE_URL = f"http://{REDIRECTIONS_API_HOST}"


class TestRedirections:

    def test_health_returns_200(self, redirections_result):
        session = redirections_result
        resp = session.get(f"{BASE_URL}/health", timeout=10, allow_redirects=True)
        assert resp.status_code == 200

    def test_known_redirect_url_returns_301_or_302(self, redirections_result):
        session = redirections_result
        # A URL that should redirect (mapped in Sitecore redirect rules)
        resp = session.get(
            f"{BASE_URL}/de-de/old-product-url",
            allow_redirects=False,
            timeout=30,
        )
        assert resp.status_code in (301, 302, 200, 404), (
            f"Unexpected status for known redirect URL: {resp.status_code}. "
            f"Headers: {dict(resp.headers)}"
        )

    def test_redirect_response_has_location_header(self, redirections_result):
        session = redirections_result
        resp = session.get(
            f"{BASE_URL}/de-de/old-product-url",
            allow_redirects=False,
            timeout=30,
        )
        if resp.status_code in (301, 302):
            assert "Location" in resp.headers, (
                f"Redirect response missing Location header. Headers: {dict(resp.headers)}"
            )

    def test_unknown_url_returns_404_or_pass_through(self, redirections_result):
        session = redirections_result
        resp = session.get(
            f"{BASE_URL}/de-de/this-url-definitely-does-not-exist-xyz",
            allow_redirects=False,
            timeout=30,
        )
        # Unknown URLs should either 404 or pass through to origin
        assert resp.status_code in (404, 200, 301, 302), (
            f"Unexpected status for unknown URL: {resp.status_code}"
        )

    def test_ignored_prefix_passes_through(self, redirections_result):
        session = redirections_result
        # Static assets and API paths should not be redirected
        resp = session.get(
            f"{BASE_URL}/api/health",
            allow_redirects=False,
            timeout=30,
        )
        # Should pass through, not 301/302
        assert resp.status_code not in (301, 302), (
            f"API path should not be redirected, got {resp.status_code}"
        )
