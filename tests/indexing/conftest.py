"""
Layer 4 — Indexing pipeline conftest.

Module-scoped fixture: clears products-index-updates, seeds one Update doc and one
Delete doc, waits for the IndexingApi, resets the WireMock request journal, triggers
GET /v1/indexing/products/initialize, then yields (response, wiremock_requests, client).
"""

import base64
import json
import os
import time

import pytest
import requests
from google.cloud import firestore

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
INDEXING_API_HOST       = os.environ.get("INDEXING_API_HOST", "localhost:8082")
WIREMOCK_HOST           = os.environ.get("WIREMOCK_HOST", "localhost:8081")

# ─── Test document IDs ────────────────────────────────────────────────────────

INDEXING_UPDATE_DOC_ID = "IDX_0_de_DE"   # operation=Update
INDEXING_DELETE_DOC_ID = "IDX_1_de_DE"   # operation=Delete

# ─── Test document data ───────────────────────────────────────────────────────

INDEXING_UPDATE_DOC = {
    "identifier": "IDX-0",
    "culture": "de_de",
    "operation": "Update",
    "finished": False,
    "incremental_update_id": None,
    "status": "unknown",
    "domain_id": "9175162892",
    "content_hash": "test-update-content-hash",
    "data": {
        "document": {
            "id": "IDX-0",
            "locale": "de_de",
            "fields": {
                "id": "IDX-0",
                "base_sku": "IDX",
                "locale": "de_de",
                "name": "Test Indexing Product",
                "is_spa": False,
                "is_watersystems": False,
                "is_spare_parts": False,
                "is_historical": False,
                "has_3d_files": False,
                "is_active": True,
                "online_buy_only": False,
                "primary_order": 0,
                "secondary_order": 0,
                "sku_lookup": ["IDX000001"],
                "ean_lookup": [],
                "variant_names": ["Test Indexing Product"],
                "price_groups": [],
                "finish_definitions": [
                    {
                        "id": 1,
                        "sku": "IDX000001",
                        "name": "Alpine White",
                        "slug": "alpine-white",
                        "url": "",
                        "has_3d_files": False,
                        "online_buy_only": False,
                        "is_historical": False,
                    }
                ],
            },
        }
    },
}

INDEXING_DELETE_DOC = {
    "identifier": "IDX-1",
    "culture": "de_de",
    "operation": "Delete",
    "finished": False,
    "incremental_update_id": None,
    "status": "unknown",
    "domain_id": "9175162892",
    "content_hash": "test-delete-content-hash",
}

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _wait_for_indexing_api(timeout: int = 180) -> None:
    """Poll GET /health until the IndexingApi responds with 200."""
    url = f"http://{INDEXING_API_HOST}/health"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                print(f"IndexingApi ready at {INDEXING_API_HOST} (attempt {attempt})", flush=True)
                return
        except Exception:
            pass
        remaining = int(deadline - time.time())
        print(f"Waiting for IndexingApi at {INDEXING_API_HOST}... ({remaining}s remaining)", flush=True)
        time.sleep(3)

    raise RuntimeError(
        f"IndexingApi at {INDEXING_API_HOST} did not respond on /health within {timeout}s. "
        "Run 'docker compose --profile phase3 up -d' and wait for the container to start."
    )


def _decode_wiremock_body(request_entry: dict) -> str:
    """Extract request body from a WireMock journal entry (handles base64 and plain)."""
    body = request_entry.get("body", "")
    if body:
        return body
    body_b64 = request_entry.get("bodyAsBase64", "")
    if body_b64:
        return base64.b64decode(body_b64).decode("utf-8")
    return ""


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def indexing_result(firestore_client):
    """
    Seed products-index-updates, trigger the IndexingApi, and yield results.

    Yields:
        (response, wiremock_requests, firestore_client) where:
          - response           — requests.Response from GET /v1/indexing/products/initialize
          - wiremock_requests  — list of request journal entries from WireMock /__admin/requests
          - firestore_client   — google.cloud.firestore.Client (connected to emulator)
    """
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    # ── Clear products-index-updates ──────────────────────────────────────────
    col = firestore_client.collection("products-index-updates")
    batch = firestore_client.batch()
    batch_count = 0
    for snap in col.stream():
        batch.delete(snap.reference)
        batch_count += 1
        if batch_count >= 500:
            batch.commit()
            batch = firestore_client.batch()
            batch_count = 0
    if batch_count:
        batch.commit()

    # ── Seed controlled documents ─────────────────────────────────────────────
    col.document(INDEXING_UPDATE_DOC_ID).set(INDEXING_UPDATE_DOC)
    col.document(INDEXING_DELETE_DOC_ID).set(INDEXING_DELETE_DOC)

    # ── Wait for IndexingApi to be healthy ────────────────────────────────────
    _wait_for_indexing_api()

    # ── Reset WireMock request journal ────────────────────────────────────────
    requests.delete(f"http://{WIREMOCK_HOST}/__admin/requests", timeout=5)

    # ── Trigger the indexing pipeline ─────────────────────────────────────────
    response = requests.get(
        f"http://{INDEXING_API_HOST}/v1/indexing/products/initialize",
        timeout=120,
    )

    # Small delay to ensure Firestore writes from the API have settled
    time.sleep(1)

    # ── Collect WireMock request journal ──────────────────────────────────────
    wm_resp = requests.get(f"http://{WIREMOCK_HOST}/__admin/requests", timeout=10)
    wiremock_requests = wm_resp.json().get("requests", [])

    yield response, wiremock_requests, firestore_client
