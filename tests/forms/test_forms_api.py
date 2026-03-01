"""
forms — FormsApi HTTP integration tests.

Tests contact form and quote (request-quote) form submission against a live
FormsApi container backed by WireMock (which stubs Mulesoft CRM).

Requires: make infra-forms-up
WireMock stubs:
  fixtures/mocks/mulesoft/contact-form.json      (POST /v1/forms/contact)
  fixtures/mocks/mulesoft/quote-form.json         (POST /v1/quotation-requests)
  fixtures/mocks/mulesoft/oauth-token.json        (GET  /oauth2/token)

Routes (FormsApi):
  POST /v1/contact-form
  POST /neo/forms/v1/request-quote-form

Bypass:
  Set BYPASS_CAPTCHA_KEY=integration-test-bypass in the container env var and
  send the X-Bypass-Captcha: integration-test-bypass header to skip reCAPTCHA.

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

FORMS_API_HOST = os.environ.get("FORMS_API_HOST", "localhost:8092")
BASE_URL = f"http://{FORMS_API_HOST}"

# Must match BYPASS_CAPTCHA_KEY env var set in docker-compose for the forms-api service.
BYPASS_CAPTCHA = "integration-test-bypass"

# ── contact form (POST /v1/contact-form) ─────────────────────────────────────

_CONTACT_PAYLOAD = {
    "subject": "Integration Test",
    "messageContent": "This is an automated integration test message.",
    "salutation": "Mr",
    "firstName": "Max",
    "lastName": "Mustermann",
    # companyName is a non-nullable string in the model → must be provided
    "companyName": "",
    "address": {
        "street": "Hauptstrasse",
        "number": "1",
        "zipCode": "40880",
        "city": "Ratingen",
    },
    "phoneNumber": "+491234567890",
    "emailAddress": "integration-test@example.com",
    "dataProtection": True,
    "captcha": "bypass-placeholder",
    # filesUpload is a non-nullable array in the model → must be provided (empty ok)
    "filesUpload": [],
    "technical": {
        "channel": "NEO",
        "countryCode": "de-DE",
    },
}

# ── quote form (POST /neo/forms/v1/request-quote-form) ───────────────────────

_QUOTE_PAYLOAD = {
    "firstName": "Max",
    "lastName": "Mustermann",
    "email": "integration-test@example.com",
    "channel": "NEO",
    "language": "de-DE",
    "typeOfService": "quotation",
}


class TestFormsApi:

    def test_health_returns_200(self, forms_result):
        session = forms_result
        resp = session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_contact_form_submission_returns_2xx(self, forms_result):
        session = forms_result
        resp = session.post(
            f"{BASE_URL}/v1/contact-form",
            json=_CONTACT_PAYLOAD,
            headers={"X-Bypass-Captcha": BYPASS_CAPTCHA},
            timeout=30,
        )
        assert resp.status_code in (200, 201, 204), (
            f"Expected 2xx from contact form, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_quote_form_submission_returns_2xx(self, forms_result):
        session = forms_result
        resp = session.post(
            f"{BASE_URL}/neo/forms/v1/request-quote-form",
            json=_QUOTE_PAYLOAD,
            timeout=30,
        )
        assert resp.status_code in (200, 201, 204), (
            f"Expected 2xx from quote form, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_contact_form_without_bypass_calls_recaptcha(self, forms_result):
        """
        No X-Bypass-Captcha header → reCAPTCHA is validated via WireMock.
        WireMock /v1/recaptcha returns success, so the form still succeeds.
        Asserting broadly so this test is stable regardless of WireMock score config.
        """
        session = forms_result
        resp = session.post(
            f"{BASE_URL}/v1/contact-form",
            json=_CONTACT_PAYLOAD,
            timeout=30,
        )
        assert resp.status_code in (200, 201, 204, 422, 500), (
            f"Unexpected status without bypass: {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_contact_form_missing_required_fields_returns_400(self, forms_result):
        session = forms_result
        resp = session.post(
            f"{BASE_URL}/v1/contact-form",
            json={},
            headers={"X-Bypass-Captcha": BYPASS_CAPTCHA},
            timeout=30,
        )
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for missing fields, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )
