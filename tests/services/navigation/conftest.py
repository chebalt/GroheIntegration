"""
Phase 4 — NavigationApi conftest.

Module-scoped fixture: clears PLCategory, seeds 2 controlled documents
(NAV_PARENT + NAV_CHILD), waits for NavigationApi /health, then yields
(requests_session, firestore_client).

Infrastructure required: docker compose --profile phase4 up -d
(with seed_config.py already run before starting the containers).
"""

import os
import time

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
NAVIGATION_API_HOST     = os.environ.get("NAVIGATION_API_HOST", "localhost:8083")

# ─── Test document IDs ────────────────────────────────────────────────────────

NAV_PARENT_DOC_ID = "9001_de_DE"
NAV_CHILD_DOC_ID  = "9002_de_DE"

# ─── Test document data ───────────────────────────────────────────────────────

NAV_PARENT_DOC = {
    "ID": 9001,
    "Language": "de",
    "Market": "DE",
    "Name": "Test Navigation Category",
    "Slug": "test-navigation-category",
    "MenuVisibility": True,
    "Priority": 1,
    "Type": "category",
    "Path": "/test-navigation-category",
    "ParentId": None,
    "Ancestors": [],
    "Image": None,
}

NAV_CHILD_DOC = {
    "ID": 9002,
    "Language": "de",
    "Market": "DE",
    "Name": "Test Sub Category",
    "Slug": "test-sub-category",
    "MenuVisibility": True,
    "Priority": 2,
    "Type": "category",
    "Path": "/test-navigation-category/test-sub-category",
    "ParentId": 9001,
    "Ancestors": [
        {
            "CategoryId": 9001,
            "CategoryName": "Test Navigation Category",
            "CategorySlug": "test-navigation-category",
            "Path": "/test-navigation-category",
        }
    ],
    "Image": None,
}

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _wait_for_navigation_api(timeout: int = 180) -> None:
    """Poll GET /health until the NavigationApi responds with 200."""
    url = f"http://{NAVIGATION_API_HOST}/health"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                print(
                    f"NavigationApi ready at {NAVIGATION_API_HOST} (attempt {attempt})",
                    flush=True,
                )
                return
        except Exception:
            pass
        remaining = int(deadline - time.time())
        print(
            f"Waiting for NavigationApi at {NAVIGATION_API_HOST}... ({remaining}s remaining)",
            flush=True,
        )
        time.sleep(3)

    raise RuntimeError(
        f"NavigationApi at {NAVIGATION_API_HOST} did not respond on /health within {timeout}s. "
        "Run 'docker compose --profile phase4 up -d' and wait for the containers to start."
    )


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def navigation_result(firestore_client):
    """
    Seed PLCategory, wait for NavigationApi, and yield (session, firestore_client).

    Yields:
        (session, firestore_client) where:
          - session          — requests.Session (use with full URL http://NAVIGATION_API_HOST/...)
          - firestore_client — google.cloud.firestore.Client (connected to emulator)
    """
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    # ── Clear PLCategory ───────────────────────────────────────────────────────
    col = firestore_client.collection("PLCategory")
    for snap in col.stream():
        snap.reference.delete()

    # ── Seed controlled documents ──────────────────────────────────────────────
    col.document(NAV_PARENT_DOC_ID).set(NAV_PARENT_DOC)
    col.document(NAV_CHILD_DOC_ID).set(NAV_CHILD_DOC)

    # ── Wait for NavigationApi to be healthy ───────────────────────────────────
    _wait_for_navigation_api()

    # ── Build requests session ─────────────────────────────────────────────────
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    yield session, firestore_client
