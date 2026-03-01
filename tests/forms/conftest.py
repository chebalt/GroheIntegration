"""
forms — FormsApi conftest.

Module-scoped fixture: checks if FormsApi is available, then yields sessions.

Infrastructure required: make infra-forms-up

WireMock stubs: fixtures/mocks/mulesoft/contact-form.json
               fixtures/mocks/mulesoft/quote-form.json
               fixtures/mocks/recaptcha/verify-success.json
"""

import os

import pytest
import requests

FORMS_API_HOST = os.environ.get("FORMS_API_HOST", "localhost:8092")


def _is_api_available(host: str, path: str = "/health", timeout: float = 3.0) -> bool:
    try:
        resp = requests.get(f"http://{host}{path}", timeout=timeout)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def forms_result():
    """
    Check FormsApi availability, yield session.
    Skips if the service is not running.
    """
    if not _is_api_available(FORMS_API_HOST):
        pytest.skip(
            f"FormsApi not running at {FORMS_API_HOST}. "
            "Run 'make infra-forms-up' to start it."
        )

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})

    yield session
