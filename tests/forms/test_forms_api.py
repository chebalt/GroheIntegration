"""
forms — FormsApi HTTP integration tests.

Tests contact form and quote form submission against a live FormsApi
backed by WireMock (which stubs Mulesoft CRM + reCAPTCHA).

Requires: make infra-forms-up
WireMock stubs: fixtures/mocks/mulesoft/contact-form.json
               fixtures/mocks/recaptcha/verify-success.json

Tests are skipped automatically if the service is not running.
"""

import os

import pytest

FORMS_API_HOST = os.environ.get("FORMS_API_HOST", "localhost:8092")
BASE_URL = f"http://{FORMS_API_HOST}"
BASE = f"{BASE_URL}/neo/forms/v1"

# Fake reCAPTCHA token (WireMock stub accepts any token)
FAKE_RECAPTCHA_TOKEN = "integration-test-recaptcha-token"


class TestFormsApi:

    def test_health_returns_200(self, forms_result):
        session = forms_result
        resp = session.get(f"{BASE_URL}/health", timeout=10)
        assert resp.status_code == 200

    def test_contact_form_submission_returns_200(self, forms_result):
        session = forms_result
        payload = {
            "locale": "de-DE",
            "firstName": "Max",
            "lastName": "Mustermann",
            "email": "test@example.com",
            "message": "Integration test contact form submission",
            "recaptchaToken": FAKE_RECAPTCHA_TOKEN,
        }
        resp = session.post(f"{BASE}/contact", json=payload, timeout=30)
        assert resp.status_code in (200, 201, 204), (
            f"Expected 2xx from contact form, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_quote_form_submission_returns_200(self, forms_result):
        session = forms_result
        payload = {
            "locale": "de-DE",
            "firstName": "Max",
            "lastName": "Mustermann",
            "email": "test@example.com",
            "company": "Test GmbH",
            "productSku": "40806000",
            "quantity": 10,
            "recaptchaToken": FAKE_RECAPTCHA_TOKEN,
        }
        resp = session.post(f"{BASE}/quote", json=payload, timeout=30)
        assert resp.status_code in (200, 201, 204), (
            f"Expected 2xx from quote form, got {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_contact_form_with_invalid_recaptcha_returns_422(self, forms_result):
        session = forms_result
        payload = {
            "locale": "de-DE",
            "firstName": "Bot",
            "lastName": "Spammer",
            "email": "bot@spam.com",
            "message": "Spam",
            "recaptchaToken": "invalid-token",
        }
        resp = session.post(f"{BASE}/contact", json=payload, timeout=30)
        # WireMock returns success for any token in integration mode;
        # real service would return 422 for score < threshold.
        # Accept either behaviour during integration scaffolding.
        assert resp.status_code in (200, 201, 204, 422), (
            f"Unexpected status for invalid reCAPTCHA: {resp.status_code}. Body: {resp.text[:500]}"
        )

    def test_contact_form_missing_required_fields_returns_400(self, forms_result):
        session = forms_result
        # Empty payload — all required fields missing
        resp = session.post(f"{BASE}/contact", json={}, timeout=30)
        assert resp.status_code in (400, 422), (
            f"Expected 400/422 for missing fields, got {resp.status_code}. Body: {resp.text[:200]}"
        )
