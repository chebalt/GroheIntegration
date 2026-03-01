"""
store-locator — Store locator job conftest.

The store-locator runs as a one-shot job (not a persistent service). Tests verify
that after the job runs, the `stores-index-updates` Firestore collection is populated
and the IndexingApi picks up the new store records.

Infrastructure required: make infra-store-locator-up
  (runs the job, which populates stores-index-updates)

WireMock stubs: sitecore-search/ingestion-update.json (reused from product-indexing)
"""

import os
import time

import pytest
import requests
from google.cloud import firestore

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
INDEXING_API_HOST       = os.environ.get("INDEXING_API_HOST", "localhost:8082")
STORE_LOCATOR_COLLECTION = "stores-index-updates"


def _collection_has_docs(client: firestore.Client, collection: str) -> bool:
    """Return True if the collection has at least one document."""
    docs = list(client.collection(collection).limit(1).stream())
    return len(docs) > 0


@pytest.fixture(scope="module")
def store_locator_result(firestore_client):
    """
    Check if stores-index-updates collection has data (populated by the store-locator job).
    Skips if no store data is present (job hasn't run or infrastructure isn't up).

    Yields:
        (firestore_client, indexing_api_available) where:
          - firestore_client         — connected to emulator
          - indexing_api_available   — bool, True if IndexingApi is running
    """
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    if not _collection_has_docs(firestore_client, STORE_LOCATOR_COLLECTION):
        pytest.skip(
            f"Collection '{STORE_LOCATOR_COLLECTION}' is empty — store-locator job has not run. "
            "Run 'make infra-store-locator-up' to execute the job."
        )

    # Check if IndexingApi is available for end-to-end store indexing tests
    indexing_api_available = False
    try:
        resp = requests.get(f"http://{INDEXING_API_HOST}/health", timeout=3)
        indexing_api_available = resp.status_code == 200
    except Exception:
        pass

    yield firestore_client, indexing_api_available
