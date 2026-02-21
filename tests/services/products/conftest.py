"""
Phase 4 — ProductsApi conftest.

Module-scoped fixture: clears PLProductContent, PLVariant, PLCategory, seeds
controlled documents (one product + one variant + one category), waits for
ProductsApi /health, then yields (requests_session, firestore_client).

Infrastructure required: docker compose --profile phase4 up -d
(with seed_config.py already run before starting the containers).
"""

import os
import time

import pytest
import requests

# ─── Connection constants ─────────────────────────────────────────────────────

FIRESTORE_EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
PRODUCTS_API_HOST       = os.environ.get("PRODUCTS_API_HOST", "localhost:8084")

# ─── Test document IDs ────────────────────────────────────────────────────────

PRODUCTS_CONTENT_DOC_ID  = "PROD-001_de_DE"
PRODUCTS_VARIANT_DOC_ID  = "PROD_0_de_DE"
PRODUCTS_CATEGORY_DOC_ID = "5001_de_DE"

# ─── Test document data ───────────────────────────────────────────────────────

PRODUCTS_CATEGORY_DOC = {
    "ID": 5001,
    "Language": "de",
    "Market": "DE",
    "Name": "Test Products Category",
    "Slug": "test-products-category",
    "MenuVisibility": True,
    "Priority": 1,
    "Type": "category",
    "Path": "/test-products-category",
    "ParentId": None,
    "Ancestors": [],
    "Image": None,
}

PRODUCTS_CONTENT_DOC = {
    "SKU": "PROD-001",
    "Language": "de",
    "Market": "DE",
    "ID": 1001,
    "EAN": 1234567890,
    "Slug": "prod-001",
    "BaseSKU": "PROD",
    "Sequence": "0",
    "Title": "Test Product 001",
    "Status": "Active",
    "Finish": 1,
    "CategoryIDs": [5001],
    "DefaultCategoryID": 5001,
    "CategorySlugs": ["test-products-category"],
    "StandardImages": [],
    "OtherImages": [],
    "AlternativeProducts": [],
    "SuggestedProducts": [],
    "InstallationTypes": [],
    "Materials": [],
    "Included": [],
    "NotIncluded": [],
    "Tags": [],
    "Features": [],
    "Finishes": [],
    "SpareParts": [],
    "Specifications": [],
    "Awards": [],
}

PRODUCTS_VARIANT_DOC = {
    "SKU": "PROD-001",
    "Language": "de",
    "Market": "DE",
    "GroupId": 0,
    "Variants": [
        {
            "SKU": "PROD-001",
            "FinishId": 1,
            "FinishCode": "AL",
            "FinishName": "Alpine White",
            "SizeLabel": None,
            "FinishIcon": None,
            "ColourNameGrohe": None,
        }
    ],
}

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _wait_for_products_api(timeout: int = 300) -> None:
    """Poll GET /health until the ProductsApi responds with 200."""
    url = f"http://{PRODUCTS_API_HOST}/health"
    deadline = time.time() + timeout
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                print(
                    f"ProductsApi ready at {PRODUCTS_API_HOST} (attempt {attempt})",
                    flush=True,
                )
                return
        except Exception:
            pass
        remaining = int(deadline - time.time())
        print(
            f"Waiting for ProductsApi at {PRODUCTS_API_HOST}... ({remaining}s remaining)",
            flush=True,
        )
        time.sleep(5)

    raise RuntimeError(
        f"ProductsApi at {PRODUCTS_API_HOST} did not respond on /health within {timeout}s. "
        "Run 'docker compose --profile phase4 up -d' and wait for the containers to start."
    )


def _clear_collection(firestore_client, name: str) -> None:
    col = firestore_client.collection(name)
    for snap in col.stream():
        snap.reference.delete()


# ─── Fixture ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def products_result(firestore_client):
    """
    Seed PLProductContent, PLVariant, PLCategory; wait for ProductsApi; yield.

    Yields:
        (session, firestore_client) where:
          - session          — requests.Session (use with full URL http://PRODUCTS_API_HOST/...)
          - firestore_client — google.cloud.firestore.Client (connected to emulator)
    """
    os.environ["FIRESTORE_EMULATOR_HOST"] = FIRESTORE_EMULATOR_HOST

    # ── Clear relevant collections ─────────────────────────────────────────────
    for col_name in ("PLProductContent", "PLVariant", "PLCategory"):
        _clear_collection(firestore_client, col_name)

    # ── Seed controlled documents ──────────────────────────────────────────────
    firestore_client.collection("PLCategory").document(PRODUCTS_CATEGORY_DOC_ID).set(
        PRODUCTS_CATEGORY_DOC
    )
    firestore_client.collection("PLProductContent").document(PRODUCTS_CONTENT_DOC_ID).set(
        PRODUCTS_CONTENT_DOC
    )
    firestore_client.collection("PLVariant").document(PRODUCTS_VARIANT_DOC_ID).set(
        PRODUCTS_VARIANT_DOC
    )

    # ── Wait for ProductsApi to be healthy ─────────────────────────────────────
    _wait_for_products_api()

    # ── Build requests session ─────────────────────────────────────────────────
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})

    yield session, firestore_client
