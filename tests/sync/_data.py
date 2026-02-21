"""
Shared test constants and helpers for sync tests.

Imported by both conftest.py (fixture setup) and test_sync_logic.py (assertions).
Using unrealistic BaseSKUs (10000–40000) to avoid clashing with real fixture data.
"""

import hashlib
import json

# ── Document IDs ──────────────────────────────────────────────────────────────
# Format: {BaseSKU}_{Sequence}_{Language}_{Market}

PRODUCT_NEW_ID       = "10000_0_de_DE"   # in ProductIndexData only     → expect Update record created
PRODUCT_CHANGED_ID   = "20000_0_de_DE"   # in both DBs, stale hash      → expect Update record replaced
PRODUCT_UNCHANGED_ID = "30000_0_de_DE"   # in both DBs, matching hash   → expect no write (skipped)
PRODUCT_DELETED_ID   = "40000_0_de_DE"   # NOT in ProductIndexData       → expect operation=Delete

# ── ProductIndexData payloads (stored in main collection) ────────────────────
# Minimal dicts — sync stores the whole dict verbatim; no schema validation here.

PRODUCT_NEW_DATA = {
    "base_sku": "10000",
    "locale": "de_de",
    "name": "Test New Product",
    "all_category_ids": ["cat_new"],
    "image_url": "https://img.example.com/new.jpg",
}

PRODUCT_CHANGED_DATA = {
    "base_sku": "20000",
    "locale": "de_de",
    "name": "Test Changed Product",
    "all_category_ids": ["cat_changed"],
    "image_url": "https://img.example.com/changed.jpg",
}

PRODUCT_UNCHANGED_DATA = {
    "base_sku": "30000",
    "locale": "de_de",
    "name": "Test Unchanged Product",
    "all_category_ids": ["cat_unchanged"],
    "image_url": "https://img.example.com/unchanged.jpg",
}

# ── Helper ─────────────────────────────────────────────────────────────────────

def compute_hash(data: dict) -> str:
    """Replicate sync_product_index.py._compute_hash for pre-computing expected hashes."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
