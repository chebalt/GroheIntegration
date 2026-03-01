"""
redirections — Redirect reverse proxy conftest.

Module-scoped fixture: checks if the redirect reverse proxy is available,
then yields a session for making redirect-following requests.

Infrastructure required: make infra-redirections-up

The redirect proxy is a lightweight HTTP service that resolves vanity URLs
and SEO redirects stored in Sitecore (mocked via WireMock sitecore-edge stubs).
"""

import os

import pytest
import requests

REDIRECTIONS_API_HOST = os.environ.get("REDIRECTIONS_API_HOST", "localhost:8093")


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def redirections_result():
    """
    Check redirect proxy availability, yield session (no redirect following).
    Skips if the service is not running.
    """
    if not _is_api_available(REDIRECTIONS_API_HOST):
        pytest.skip(
            f"Redirections proxy not running at {REDIRECTIONS_API_HOST}. "
            "Run 'make infra-redirections-up' to start it."
        )

    # Do NOT follow redirects — we want to assert the 301/302 response itself
    session = requests.Session()
    session.max_redirects = 0
    session.headers.update({"Accept": "text/html,application/json"})

    yield session
