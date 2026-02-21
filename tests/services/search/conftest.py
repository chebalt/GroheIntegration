"""
Phase 5 — SearchApi conftest.

Module-scoped fixture: waits for SearchApi /health, then yields a
requests.Session. No Firestore seeding — SearchApi has no Firestore dependency.

Infrastructure required: docker compose --profile phase5 up -d
"""

import os
import time

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

SEARCH_API_HOST = os.environ.get("SEARCH_API_HOST", "localhost:8085")

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _wait_for_search_api(timeout: int = 180) -> None:
    """Poll GET /health until the SearchApi responds with 200."""
    url = f"http://{SEARCH_API_HOST}/health"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                print(
                    f"SearchApi ready at {SEARCH_API_HOST} (attempt {attempt})",
                    flush=True,
                )
                return
        except Exception:
            pass
        remaining = int(deadline - time.time())
        print(
            f"Waiting for SearchApi at {SEARCH_API_HOST}... ({remaining}s remaining)",
            flush=True,
        )
        time.sleep(3)

    raise RuntimeError(
        f"SearchApi at {SEARCH_API_HOST} did not respond on /health within {timeout}s. "
        "Run 'docker compose --profile phase5 up -d' and wait for the container to start."
    )


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def search_result():
    """
    Wait for SearchApi and yield a requests.Session.

    No Firestore seeding is needed — SearchApi talks only to Sitecore Search
    (stubbed by WireMock) and optionally to XM Cloud (also stubbed, graceful 404).

    Yields:
        session — requests.Session with Accept: application/json header
    """
    _wait_for_search_api()

    session = requests.Session()
    session.headers.update({
        "Accept": "application/json",
        "Content-Type": "application/json",
    })

    yield session
