"""
Firestore collection tests — verifies all 5 collections are populated
with the expected number and shape of documents after the pipeline runs.
"""

import pytest


pytestmark = [pytest.mark.pipeline, pytest.mark.requires_emulator]

# ── Known values from fixtures/csv/ (de/DE batch) ────────────────────────────

LOCALE    = "de_DE"
LANGUAGE  = "de"
MARKET    = "DE"

# SKUs present in 1_product_data.csv
KNOWN_SKUS = ["66838000", "40806000"]

# BaseSKU → Sequence mapping (from 1_product_data.csv: base_sku, sequence columns)
# 66838000: base_sku=66838, sequence=0  →  ProductIndexData id = "66838_0_de_DE"
# 40806000: base_sku=40806, sequence=0  →  ProductIndexData id = "40806_0_de_DE"
KNOWN_PRODUCT_INDEX_IDS = ["66838_0_de_DE", "40806_0_de_DE"]


# ── Helper ────────────────────────────────────────────────────────────────────

def collection_doc_ids(client, collection_name: str) -> set:
    return {doc.id for doc in client.collection(collection_name).stream()}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestCollectionsPopulated:

    def test_pl_product_content_is_populated(self, pipeline_result, firestore_client):
        ids = collection_doc_ids(firestore_client, "PLProductContent")
        assert len(ids) > 0, "PLProductContent should not be empty after pipeline run"

    def test_pl_category_is_populated(self, pipeline_result, firestore_client):
        ids = collection_doc_ids(firestore_client, "PLCategory")
        assert len(ids) > 0, "PLCategory should not be empty after pipeline run"

    def test_pl_variant_is_populated(self, pipeline_result, firestore_client):
        ids = collection_doc_ids(firestore_client, "PLVariant")
        assert len(ids) > 0, "PLVariant should not be empty after pipeline run"

    def test_product_index_data_is_populated(self, pipeline_result, firestore_client):
        ids = collection_doc_ids(firestore_client, "ProductIndexData")
        assert len(ids) > 0, "ProductIndexData should not be empty after pipeline run"

    def test_category_routing_is_populated(self, pipeline_result, firestore_client):
        ids = collection_doc_ids(firestore_client, "CategoryRouting")
        assert len(ids) > 0, "CategoryRouting should not be empty after pipeline run"


class TestDocumentIds:

    @pytest.mark.parametrize("sku", KNOWN_SKUS)
    def test_pl_product_content_document_exists_for_known_sku(self, pipeline_result, firestore_client, sku):
        doc_id = f"{sku}_{LOCALE}"
        doc = firestore_client.collection("PLProductContent").document(doc_id).get()
        assert doc.exists, (
            f"Expected document '{doc_id}' in PLProductContent.\n"
            f"Existing IDs (first 10): {list(collection_doc_ids(firestore_client, 'PLProductContent'))[:10]}"
        )

    @pytest.mark.parametrize("index_id", KNOWN_PRODUCT_INDEX_IDS)
    def test_product_index_data_document_exists(self, pipeline_result, firestore_client, index_id):
        doc = firestore_client.collection("ProductIndexData").document(index_id).get()
        assert doc.exists, (
            f"Expected document '{index_id}' in ProductIndexData.\n"
            f"Existing IDs (first 10): {list(collection_doc_ids(firestore_client, 'ProductIndexData'))[:10]}"
        )

    @pytest.mark.parametrize("sku", KNOWN_SKUS)
    def test_pl_product_content_id_format_is_sku_locale(self, pipeline_result, firestore_client, sku):
        """Document IDs must follow the {SKU}_{language}_{market} pattern."""
        doc_id = f"{sku}_{LOCALE}"
        doc = firestore_client.collection("PLProductContent").document(doc_id).get()
        assert doc.exists, f"Document ID format check failed — '{doc_id}' not found"

    def test_pl_category_ids_contain_locale(self, pipeline_result, firestore_client):
        """Category document IDs should contain the language/market."""
        ids = collection_doc_ids(firestore_client, "PLCategory")
        locale_ids = [i for i in ids if LANGUAGE in i or MARKET in i]
        assert len(locale_ids) > 0, (
            f"No PLCategory documents contained language '{LANGUAGE}' or market '{MARKET}' in their ID.\n"
            f"Sample IDs: {list(ids)[:10]}"
        )
