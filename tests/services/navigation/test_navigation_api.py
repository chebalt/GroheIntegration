"""
Phase 4 — NavigationApi HTTP integration tests.

Tests the GET /neo/product/v1/category-navigation endpoint against a live
NavigationApi container connected to the Firestore emulator.

Requires: docker compose --profile phase4 up -d
  (with seed_config.py already run before starting the containers)
"""

import os

import pytest

NAVIGATION_API_HOST = os.environ.get("NAVIGATION_API_HOST", "localhost:8083")
BASE_URL = f"http://{NAVIGATION_API_HOST}"
ENDPOINT = f"{BASE_URL}/neo/product/v1/category-navigation"


class TestNavigationApi:
    def test_navigation_returns_200_for_valid_locale(self, navigation_result):
        session, _ = navigation_result
        resp = session.get(ENDPOINT, params={"locale": "de-DE"}, timeout=30)
        assert resp.status_code == 200, (
            f"Expected 200 from NavigationApi, got {resp.status_code}. "
            f"Body: {resp.text[:500]}"
        )

    def test_navigation_response_contains_category_items(self, navigation_result):
        session, _ = navigation_result
        resp = session.get(ENDPOINT, params={"locale": "de-DE"}, timeout=30)
        assert resp.status_code == 200
        body = resp.json()
        # ASP.NET Core camelCase serialization → categoryMenuItems
        key = "categoryMenuItems" if "categoryMenuItems" in body else "CategoryMenuItems"
        assert key in body, (
            f"Response missing category items key. Got keys: {list(body.keys())}"
        )
        items = body[key]
        assert len(items) > 0, f"'{key}' is empty — seeded 2 docs, expected at least 1 returned"

    def test_navigation_category_item_has_required_fields(self, navigation_result):
        session, _ = navigation_result
        resp = session.get(ENDPOINT, params={"locale": "de-DE"}, timeout=30)
        assert resp.status_code == 200
        body = resp.json()
        key = "categoryMenuItems" if "categoryMenuItems" in body else "CategoryMenuItems"
        items = body[key]
        assert len(items) > 0
        first = items[0]
        for field in ("id", "name", "slug"):
            assert field in first, (
                f"CategoryMenuItem missing '{field}'. Got keys: {list(first.keys())}"
            )

    def test_navigation_language_market_match_locale(self, navigation_result):
        session, _ = navigation_result
        resp = session.get(ENDPOINT, params={"locale": "de-DE"}, timeout=30)
        assert resp.status_code == 200
        body = resp.json()
        key = "categoryMenuItems" if "categoryMenuItems" in body else "CategoryMenuItems"
        items = body[key]
        assert len(items) > 0
        first = items[0]
        assert first.get("language") == "de", (
            f"Expected language='de', got {first.get('language')!r}"
        )
        assert first.get("market") == "DE", (
            f"Expected market='DE', got {first.get('market')!r}"
        )

    def test_navigation_returns_400_for_invalid_locale_format(self, navigation_result):
        session, _ = navigation_result
        resp = session.get(ENDPOINT, params={"locale": "invalid"}, timeout=30)
        assert resp.status_code == 400, (
            f"Expected 400 for invalid locale format, got {resp.status_code}. "
            f"Body: {resp.text[:200]}"
        )
