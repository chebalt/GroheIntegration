"""
project-list — ProjectListsApi conftest.

Module-scoped fixture:
  1. Waits for ProjectListsApi /health (up to 300s — Chrome download on first build)
  2. Clears the `project-lists` Firestore collection
  3. Seeds two controlled project list documents
  4. Yields (anon_session, auth_session, firestore_client)

JWT notes:
  IdpTokenHelper.GetClaimValue() strips the "OndusBearer" prefix then calls
  JwtSecurityTokenHandler.ReadJwtToken() — no RSA signature verification.
  Sending the raw JWT (no "Bearer " prefix) as the Authorization header value
  means GetClaimValue("{raw_jwt}", "sub") → ReadJwtToken("{raw_jwt}") → reads
  the "sub" claim successfully.

Infrastructure required:
  make infra-project-list-up   (seeds config, builds ProductsApi + ProjectListsApi)

Product data required for PDF test (test 10):
  ETL data for SKU 1039960000 must be in Firestore — run `make test-data-loader`
  or `make load-etl-data` before running project-list tests.
"""

import base64
import json
import os
import time
from datetime import datetime, timezone

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST   = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
PROJECT_LISTS_API_HOST    = os.environ.get("PROJECT_LISTS_API_HOST", "localhost:8086")

# ─── Firestore collection ─────────────────────────────────────────────────────

COLLECTION = "project-lists"

# ─── Seeded document IDs and data ─────────────────────────────────────────────

SEEDED_LIST_ID = "integration-test-list-001"   # used for read/update/PDF tests
SEEDED_DELETE_ID = "integration-test-list-002"  # used for delete test

SEEDED_USER_ID = "test-user-id"

SEEDED_LIST_DOC = {
    "Id": SEEDED_LIST_ID,
    "UserId": SEEDED_USER_ID,
    "ProjectListName": "Integration Test List",
    "ProjectListDescription": "Created by integration test fixture",
    "CreatedTimestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
    "UpdatedTimestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
    "Sections": [
        {
            "Id": "section-001",
            "SectionName": "Test Section",
            "Items": [
                {
                    "ProductSku": "1039960000",
                    "ProductName": "GROHE Eurosmart",
                    "Quantity": 1,
                    "CustomLabels": [],
                }
            ],
        }
    ],
}

SEEDED_DELETE_DOC = {
    "Id": SEEDED_DELETE_ID,
    "UserId": SEEDED_USER_ID,
    "ProjectListName": "List To Delete",
    "ProjectListDescription": "This list will be deleted by the delete test",
    "CreatedTimestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
    "UpdatedTimestamp": datetime(2025, 1, 1, tzinfo=timezone.utc),
    "Sections": [],
}

# ─── JWT helper ───────────────────────────────────────────────────────────────


def _make_fake_jwt(user_id: str = SEEDED_USER_ID) -> str:
    """
    Build a minimal unsigned JWT with sub={user_id} in the payload.

    IdpTokenHelper.GetClaimValue(rawJwt, "sub") calls ReadJwtToken(rawJwt)
    which only base64-decodes the payload — no RSA signature check — so a
    fake signature suffix is sufficient.
    """
    def _b64(d: dict) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(d).encode())
            .rstrip(b"=")
            .decode()
        )

    header  = _b64({"alg": "RS256", "typ": "JWT"})
    payload = _b64({"sub": user_id, "exp": 9_999_999_999})
    return f"{header}.{payload}.fakesig"


# Raw JWT — no "Bearer " prefix.  The service strips "OndusBearer" not "Bearer".
TEST_JWT = _make_fake_jwt()

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _wait_for_project_lists_api(timeout: int = 300) -> None:
    """Poll GET /health until the ProjectListsApi responds 200."""
    url = f"http://{PROJECT_LISTS_API_HOST}/health"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print(
                    f"ProjectListsApi ready at {PROJECT_LISTS_API_HOST} (attempt {attempt})",
                    flush=True,
                )
                return
        except Exception:
            pass
        remaining = int(deadline - time.time())
        print(
            f"Waiting for ProjectListsApi at {PROJECT_LISTS_API_HOST}... ({remaining}s remaining)",
            flush=True,
        )
        time.sleep(5)

    raise RuntimeError(
        f"ProjectListsApi at {PROJECT_LISTS_API_HOST} did not respond on /health "
        f"within {timeout}s.  Run 'make infra-project-list-up' "
        "and wait for the container to start."
    )


def _clear_collection(firestore_client, name: str) -> None:
    col = firestore_client.collection(name)
    for snap in col.stream():
        snap.reference.delete()


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def project_lists_result(firestore_client):
    """
    Clear project-lists collection, seed two docs, wait for API, yield sessions.

    Yields:
        (anon_session, auth_session, firestore_client) where:
          - anon_session  — requests.Session with no Authorization header
          - auth_session  — requests.Session with Authorization: {fake_jwt}
          - firestore_client — google.cloud.firestore.Client (emulator)
    """
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    # ── Clear and seed ─────────────────────────────────────────────────────────
    _clear_collection(firestore_client, COLLECTION)

    firestore_client.collection(COLLECTION).document(SEEDED_LIST_ID).set(SEEDED_LIST_DOC)
    firestore_client.collection(COLLECTION).document(SEEDED_DELETE_ID).set(SEEDED_DELETE_DOC)

    # ── Wait for the API ───────────────────────────────────────────────────────
    _wait_for_project_lists_api()

    # ── Build sessions ─────────────────────────────────────────────────────────
    anon_session = requests.Session()
    anon_session.headers.update({"Content-Type": "application/json"})

    auth_session = requests.Session()
    auth_session.headers.update({
        "Content-Type": "application/json",
        "Authorization": TEST_JWT,
    })

    yield anon_session, auth_session, firestore_client
