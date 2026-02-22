"""
Phase 6 — ProjectListsApi HTTP integration tests.

10 tests covering CRUD operations and PDF generation.

Infrastructure: docker compose --profile phase6 up -d --build
Run: PROJECT_LISTS_API_HOST=localhost:8086 pytest tests/services/project-lists/ -v
"""

import os

import pytest

# ─── Connection constants (mirrors conftest.py) ───────────────────────────────

PROJECT_LISTS_API_HOST = os.environ.get("PROJECT_LISTS_API_HOST", "localhost:8086")

SEEDED_LIST_ID   = "integration-test-list-001"
SEEDED_DELETE_ID = "integration-test-list-002"
SEEDED_USER_ID   = "test-user-id"

BASE = f"http://{PROJECT_LISTS_API_HOST}/neo/project-lists/v1"


class TestProjectListsApi:

    # ── Test 1 — Health ───────────────────────────────────────────────────────

    def test_health_returns_200(self, project_lists_result):
        anon_session, _, _ = project_lists_result
        resp = anon_session.get(f"http://{PROJECT_LISTS_API_HOST}/health")
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )

    # ── Test 2 — GET public list (200) ────────────────────────────────────────

    def test_get_public_list_returns_200_for_known_id(self, project_lists_result):
        anon_session, _, _ = project_lists_result
        resp = anon_session.get(
            f"{BASE}/projectList",
            params={"projectListId": SEEDED_LIST_ID, "locale": "de-de"},
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        assert "projectListId" in body or "ProjectListId" in body, (
            f"Response missing projectListId field. Body: {body}"
        )

    # ── Test 3 — GET public list contains correct name ────────────────────────

    def test_get_public_list_contains_correct_name(self, project_lists_result):
        anon_session, _, _ = project_lists_result
        resp = anon_session.get(
            f"{BASE}/projectList",
            params={"projectListId": SEEDED_LIST_ID, "locale": "de-de"},
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        name = body.get("projectListName") or body.get("ProjectListName") or ""
        assert name == "Integration Test List", (
            f"Expected 'Integration Test List', got '{name}'. Body: {body}"
        )

    # ── Test 4 — GET public list 404 for unknown ID ───────────────────────────

    def test_get_public_list_returns_404_for_unknown_id(self, project_lists_result):
        anon_session, _, _ = project_lists_result
        resp = anon_session.get(
            f"{BASE}/projectList",
            params={"projectListId": "does-not-exist-xyz", "locale": "de-de"},
        )
        assert resp.status_code == 404, (
            f"Expected 404, got {resp.status_code}. Body: {resp.text}"
        )

    # ── Test 5 — GET public list 400 without params ───────────────────────────

    def test_get_public_list_returns_400_without_params(self, project_lists_result):
        anon_session, _, _ = project_lists_result
        resp = anon_session.get(f"{BASE}/projectList")
        assert resp.status_code == 400, (
            f"Expected 400, got {resp.status_code}. Body: {resp.text}"
        )

    # ── Test 6 — POST createList with JWT ────────────────────────────────────

    def test_create_project_list_returns_200_with_jwt(self, project_lists_result):
        _, auth_session, _ = project_lists_result
        payload = {
            "locale": "en",
            "projectListName": "Created By Integration Test",
            "sections": [],
        }
        resp = auth_session.post(f"{BASE}/createList", json=payload)
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        created_id = body.get("projectListId") or body.get("ProjectListId")
        assert created_id, f"Response missing projectListId. Body: {body}"

    # ── Test 7 — GET user lists returns seeded list ───────────────────────────

    def test_get_user_lists_returns_seeded_list(self, project_lists_result):
        _, auth_session, _ = project_lists_result
        resp = auth_session.get(
            f"{BASE}/user",
            params={"userId": SEEDED_USER_ID, "locale": "en"},
        )
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        # Response may be a list or wrapped
        items = body if isinstance(body, list) else body.get("items", body.get("value", [body]))
        assert len(items) > 0, f"Expected non-empty list of project lists. Body: {body}"

    # ── Test 8 — POST update project list changes name ────────────────────────

    def test_update_project_list_changes_name(self, project_lists_result):
        _, auth_session, _ = project_lists_result
        new_name = "Updated By Integration Test"
        payload = {
            "locale": "en",
            "projectListId": SEEDED_LIST_ID,
            "projectListName": new_name,
            "sections": [],
        }
        resp = auth_session.post(f"{BASE}/projectList", json=payload)
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )
        body = resp.json()
        returned_name = body.get("projectListName") or body.get("ProjectListName") or ""
        assert returned_name == new_name, (
            f"Expected '{new_name}', got '{returned_name}'. Body: {body}"
        )

    # ── Test 9 — DELETE project list returns 200 ─────────────────────────────

    def test_delete_project_list_returns_200(self, project_lists_result):
        """Deletes SEEDED_DELETE_ID so SEEDED_LIST_ID remains for the PDF test."""
        _, auth_session, _ = project_lists_result
        payload = {
            "locale": "en",
            "projectListId": SEEDED_DELETE_ID,
        }
        resp = auth_session.delete(f"{BASE}/projectList", json=payload)
        assert resp.status_code == 200, (
            f"Expected 200, got {resp.status_code}. Body: {resp.text}"
        )

    # ── Test 10 — POST specificationDocument returns PDF ─────────────────────

    def test_generate_specification_document_returns_pdf(self, project_lists_result):
        """
        Request PDF generation for SEEDED_LIST_ID (still exists after test 9 deleted
        SEEDED_DELETE_ID).  WireMock stubs provide:
          - POST /oauth/token           → fake token (XMCloud auth)
          - GET  /neo/product/v1/PROD-001* → product detail
          - GET  /neo/product/v1/variants* → variants
          - POST /graphql               → empty dictionary items
        """
        _, auth_session, _ = project_lists_result

        # Minimal 1×1 transparent PNG as data URL for cover image
        cover_image = (
            "data:image/png;base64,"
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
            "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )

        payload = {
            "locale": "en",
            "projectList": {
                "projectListId": SEEDED_LIST_ID,
                "projectListName": "Integration Test List",
                "projectListDescription": "PDF generation test",
                "userId": SEEDED_USER_ID,
                "sections": [
                    {
                        "sectionId": "section-001",
                        "sectionName": "Test Section",
                        "items": [
                            {
                                "productSku": "PROD-001",
                                "productName": "Test Product 001",
                                "quantity": 2,
                                "productUrl": "https://www.grohe.com/de-de/test-product",
                            }
                        ],
                    }
                ],
            },
            "specificationDocumentOptions": {
                "headline": "Integration Test Specification",
                "description": "Generated by Phase 6 integration tests",
                "lang": "de-de",
                "coverImage": cover_image,
            },
        }

        resp = auth_session.post(
            f"{BASE}/specificationDocument",
            json=payload,
            timeout=120,
        )

        assert resp.status_code == 200, (
            f"Expected 200 (PDF), got {resp.status_code}. Body: {resp.text[:500]}"
        )
        content_type = resp.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, (
            f"Expected Content-Type: application/pdf, got '{content_type}'"
        )
        assert len(resp.content) > 0, "PDF response body is empty"
