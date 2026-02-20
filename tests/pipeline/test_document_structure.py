"""
Document structure tests — verifies the shape and content of individual
Firestore documents written by the ETL pipeline.

Assertions are based on the known content of fixtures/csv/ (de/DE batch).
"""

import pytest


pytestmark = [pytest.mark.pipeline, pytest.mark.requires_emulator]

LOCALE = "de_DE"

# ── Fixtures helpers ──────────────────────────────────────────────────────────

def get_doc(client, collection: str, doc_id: str) -> dict:
    doc = client.collection(collection).document(doc_id).get()
    assert doc.exists, f"Document '{doc_id}' not found in '{collection}'"
    return doc.to_dict()


# ── PLProductContent ──────────────────────────────────────────────────────────

class TestPLProductContentStructure:

    SKU = "40806000"  # Seifenschale — has images, category, finish

    @pytest.fixture(autouse=True)
    def doc(self, pipeline_result, firestore_client):
        self._doc = get_doc(firestore_client, "PLProductContent", f"{self.SKU}_{LOCALE}")

    def test_has_sku_field(self):
        assert "SKU" in self._doc
        assert self._doc["SKU"] == self.SKU

    def test_has_ean_field(self):
        assert "EAN" in self._doc
        assert self._doc["EAN"] is not None

    def test_has_slug_field(self):
        assert "Slug" in self._doc
        assert isinstance(self._doc["Slug"], str)
        assert len(self._doc["Slug"]) > 0

    def test_has_base_sku(self):
        assert "BaseSKU" in self._doc
        assert self._doc["BaseSKU"] == "40806"

    def test_has_standard_images(self):
        assert "StandardImages" in self._doc
        images = self._doc["StandardImages"]
        assert isinstance(images, list)
        assert len(images) > 0, "StandardImages should not be empty for 40806000"
        assert all(img.startswith("http") for img in images)

    def test_has_finish_field(self):
        assert "Finish" in self._doc

    def test_has_finishes_list(self):
        assert "Finishes" in self._doc
        assert isinstance(self._doc["Finishes"], list)

    def test_has_variants_field(self):
        assert "Variants" in self._doc
        assert isinstance(self._doc["Variants"], dict)

    def test_has_size_variants(self):
        assert "SizeVariants" in self._doc
        assert isinstance(self._doc["SizeVariants"], list)

    def test_has_spare_parts(self):
        assert "SpareParts" in self._doc
        assert isinstance(self._doc["SpareParts"], list)

    def test_has_installation_fields(self):
        assert "NecessaryforInstallationIDs" in self._doc
        assert "OptionalForInstallationIDs" in self._doc

    def test_has_document_id(self):
        assert "DocumentID" in self._doc
        assert self._doc["DocumentID"] == f"{self.SKU}_{LOCALE}"

    def test_document_not_oversized(self):
        import json
        size = len(json.dumps(self._doc).encode("utf-8"))
        assert size < 900_000, (
            f"Document {self.SKU}_{LOCALE} is {size} bytes — "
            f"exceeds the 900KB safety limit (Firestore max: 1MB)"
        )


# ── ProductIndexData ──────────────────────────────────────────────────────────

class TestProductIndexDataStructure:

    INDEX_ID = "40806_0_de_DE"  # BaseSKU=40806, Sequence=0, de_DE

    @pytest.fixture(autouse=True)
    def doc(self, pipeline_result, firestore_client):
        self._doc = get_doc(firestore_client, "ProductIndexData", self.INDEX_ID)

    def test_has_id_field(self):
        assert "id" in self._doc
        assert self._doc["id"] == self.INDEX_ID

    def test_has_base_sku(self):
        assert "base_sku" in self._doc
        assert self._doc["base_sku"] == "40806"

    def test_has_finish_definitions(self):
        assert "finish_definitions" in self._doc
        defs = self._doc["finish_definitions"]
        assert isinstance(defs, list)
        assert len(defs) > 0, "finish_definitions should not be empty"

    def test_finish_definition_has_required_fields(self):
        first = self._doc["finish_definitions"][0]
        required = ["sku", "ean", "image", "slug", "color", "id",
                    "is_historical", "has_3d_files", "eu_taxonomy",
                    "recommended", "water_saving", "energy_saving"]
        for field in required:
            assert field in first, f"finish_definition missing field: '{field}'"

    def test_has_all_category_ids(self):
        assert "all_category_ids" in self._doc
        assert isinstance(self._doc["all_category_ids"], list)

    def test_has_colors(self):
        assert "colors" in self._doc
        assert isinstance(self._doc["colors"], list)

    def test_has_image_url(self):
        assert "image_url" in self._doc
        assert self._doc["image_url"].startswith("http"), (
            f"image_url should be an HTTP URL, got: {self._doc['image_url']}"
        )

    def test_is_historical_is_bool(self):
        assert "is_historical" in self._doc
        assert isinstance(self._doc["is_historical"], bool)

    def test_has_tag_definitions(self):
        assert "tag_definitions" in self._doc
        assert isinstance(self._doc["tag_definitions"], list)


# ── PLCategory ────────────────────────────────────────────────────────────────

class TestPLCategoryStructure:

    def test_category_docs_have_expected_fields(self, pipeline_result, firestore_client):
        docs = list(firestore_client.collection("PLCategory").limit(5).stream())
        assert len(docs) > 0

        required_fields = ["Language", "Market"]
        for doc in docs:
            data = doc.to_dict()
            for field in required_fields:
                assert field in data, (
                    f"PLCategory doc '{doc.id}' missing field '{field}'. "
                    f"Fields present: {list(data.keys())}"
                )

    def test_categories_have_correct_language(self, pipeline_result, firestore_client):
        docs = list(firestore_client.collection("PLCategory").limit(10).stream())
        for doc in docs:
            data = doc.to_dict()
            if "Language" in data:
                assert data["Language"] == "de", (
                    f"PLCategory '{doc.id}' has unexpected language: {data['Language']}"
                )


# ── PLVariant ─────────────────────────────────────────────────────────────────

class TestPLVariantStructure:

    def test_variant_docs_have_sku_field(self, pipeline_result, firestore_client):
        docs = list(firestore_client.collection("PLVariant").limit(5).stream())
        assert len(docs) > 0

        for doc in docs:
            data = doc.to_dict()
            assert "BaseSKU" in data or "SKU" in data, (
                f"PLVariant doc '{doc.id}' missing SKU identifier. "
                f"Fields: {list(data.keys())}"
            )

    def test_variant_ids_contain_known_sku(self, pipeline_result, firestore_client):
        ids = {doc.id for doc in firestore_client.collection("PLVariant").stream()}
        # At least one variant doc should reference a known SKU
        known_skus = ["66838000", "40806000"]
        matches = [i for i in ids if any(sku in i for sku in known_skus)]
        assert len(matches) > 0, (
            f"No PLVariant documents matched known SKUs. Sample IDs: {list(ids)[:10]}"
        )
