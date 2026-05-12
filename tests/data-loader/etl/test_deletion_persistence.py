"""
End-to-end regression for NEO-5268: a SKU removed from `1_product_data.csv`
between two pipeline runs MUST disappear from Firestore after the second
run. Before the NEO-5268 fix this didn't happen — `_clear_collection_by_name`
swallowed "Transaction too big" errors, the orphan documents survived, and
Phase 2's `set()`-only writes never touched them.

This test is gated by the `slow` marker because it runs the full ETL pipeline
twice (transform is CPU-bound, ~6–7 min per run, ~22 min total including the
Firestore load). To run:

    pytest -m "" tests/data-loader/etl/test_deletion_persistence.py
    # or include the slow tests in a full run:
    pytest -m "" tests/

The default test discovery still includes pipeline tests (no marker filter is
applied by `pytest.ini`), but `-m "slow"` will run ONLY this one, and
`-m "not slow"` will skip it. The CLAUDE.md QA handoff documents the gate.
"""
from __future__ import annotations

import csv
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.slow,
    pytest.mark.pipeline,
    pytest.mark.requires_emulator,
]


# Paths copied/adapted from tests/conftest.py — this test is intentionally
# self-contained because it does NOT use the session-scoped pipeline_result
# fixture (it needs to drive the pipeline twice, against a mutable tempdir).
REPO_ROOT       = Path(__file__).parent.parent.parent.parent.parent   # NEO/
INTEGRATION_DIR = REPO_ROOT / "integration"
DATA_LOADER_DIR = REPO_ROOT / "grohe-neo-data-loader"
FIXTURES_CSV    = INTEGRATION_DIR / "fixtures" / "csv"

if platform.system() == "Windows":
    DATA_LOADER_PYTHON = DATA_LOADER_DIR / ".venv" / "Scripts" / "python.exe"
else:
    DATA_LOADER_PYTHON = DATA_LOADER_DIR / ".venv" / "bin" / "python"

if not DATA_LOADER_PYTHON.exists():
    DATA_LOADER_PYTHON = Path(sys.executable)

EMULATOR_HOST = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
PROJECT_ID    = "demo-project"

# Subprocess timeout per run — the conftest fixture uses 900s. We give each
# of the two runs the same headroom.
RUN_TIMEOUT = 900

# A SKU known to live in the fixture batch and to produce documents in
# PLProductContent, PLVariant, and ProductIndexData. The fixture is en/GB
# (verified by inspecting `2_product_content.csv` columns 9+10 for this SKU).
#
# NOTE: `tests/data-loader/etl/test_collections.py` still asserts on `de_DE`
# / `66838_0_de_DE`. That is a stale fixture assumption — the actual seeded
# locale is `en_GB`. This NEO-5268 test is decoupled from that file and uses
# the correct, verified locale.
TARGET_SKU      = "40806000"
TARGET_BASE_SKU = "40806"
LOCALE          = "en_GB"


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _clear_emulator(client) -> None:
    """Delete every document in every known collection.

    Mirrors the helper in tests/conftest.py — duplicated here so this test
    does not need to import conftest internals.
    """
    collections = [
        "PLProductContent", "PLCategory",
        "PLVariant", "ProductIndexData", "CategoryRouting",
        "PLProductCollection",
        "cacheEntries", "cacheRegions",
    ]
    for name in collections:
        for doc in client.collection(name).stream():
            doc.reference.delete()


def _run_pipeline(input_dir: Path) -> subprocess.CompletedProcess:
    """Run main.py --to-firestore against the given input dir, return the
    CompletedProcess. Raises on non-zero exit (so the test fails loudly with
    the captured stdout/stderr)."""
    env = {
        **os.environ,
        "FIRESTORE_EMULATOR_HOST": EMULATOR_HOST,
        "GCLOUD_PROJECT":          PROJECT_ID,
        "PYTHONUTF8":              "1",
    }
    proc = subprocess.run(
        [
            str(DATA_LOADER_PYTHON), "main.py",
            "--input-dir",    str(input_dir),
            "--to-firestore",
            "--firestore-emulator",
            "--log-level",    "INFO",
        ],
        cwd=DATA_LOADER_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=RUN_TIMEOUT,
    )
    assert proc.returncode == 0, (
        f"Pipeline exited with code {proc.returncode}.\n"
        f"STDOUT (last 2 KB):\n{proc.stdout[-2000:]}\n"
        f"STDERR:\n{proc.stderr}"
    )
    return proc


def _drop_sku_from_product_data(csv_path: Path, sku_to_drop: str) -> int:
    """Rewrite `csv_path` removing every row whose `sku` column matches
    `sku_to_drop`. Returns the number of rows removed.

    Note: 1_product_data.csv is *comma*-delimited (see fixtures/csv/) — we
    preserve the dialect by reading with csv.DictReader and writing with
    csv.DictWriter at the default settings.
    """
    rows_in: list[dict] = []
    removed = 0
    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        assert fieldnames is not None
        assert "sku" in fieldnames
        for row in reader:
            if row.get("sku") == sku_to_drop:
                removed += 1
                continue
            rows_in.append(row)

    # csv.DictWriter writes \r\n by default on Windows; specify the dialect
    # explicitly to keep things deterministic.
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows_in:
            writer.writerow(row)

    return removed


def _ids_with_prefix(client, collection: str, prefix: str) -> list[str]:
    """Return every doc id in `collection` whose id starts with `prefix`."""
    return [
        doc.id
        for doc in client.collection(collection).stream()
        if doc.id.startswith(prefix)
    ]


def _ids_with_base_sku_prefix(client, collection: str, base_sku: str, locale: str) -> list[str]:
    """ProductIndexData ids are `<BaseSKU>_<Sequence>_<lang>_<MARKET>`; match
    on `<BaseSKU>_` and the locale suffix to be precise.
    """
    suffix = "_" + locale
    matched = []
    for doc in client.collection(collection).stream():
        if doc.id.startswith(base_sku + "_") and doc.id.endswith(suffix):
            matched.append(doc.id)
    return matched


# --------------------------------------------------------------------------- #
# Test                                                                        #
# --------------------------------------------------------------------------- #


class TestDeletionPersistence:
    """A SKU dropped from the source CSV between two runs must be gone from
    Firestore after the second run."""

    def test_dropped_sku_is_removed_from_all_sku_keyed_collections(
        self,
        firestore_client,
        tmp_path: Path,
    ) -> None:
        # ── Arrange ──────────────────────────────────────────────────────────
        # Copy fixtures into a writable tempdir so we can mutate the CSV.
        tmp_input = tmp_path / "csv"
        shutil.copytree(FIXTURES_CSV, tmp_input)
        product_csv = tmp_input / "1_product_data.csv"
        assert product_csv.exists()

        # Start every run from a clean emulator (this test ignores any state
        # left by other test files in this directory).
        _clear_emulator(firestore_client)

        # ── Act 1: run pipeline with TARGET_SKU present ──────────────────────
        _run_pipeline(tmp_input)

        # Sanity: the target SKU is present after the first run.
        pc_first  = _ids_with_prefix(firestore_client, "PLProductContent", f"{TARGET_SKU}_")
        var_first = _ids_with_prefix(firestore_client, "PLVariant",        f"{TARGET_SKU}_")
        idx_first = _ids_with_base_sku_prefix(firestore_client, "ProductIndexData", TARGET_BASE_SKU, LOCALE)
        assert pc_first,  f"PLProductContent should contain a doc for {TARGET_SKU} after run 1"
        assert var_first, f"PLVariant should contain a doc for {TARGET_SKU} after run 1"
        assert idx_first, f"ProductIndexData should contain a doc for base_sku {TARGET_BASE_SKU} after run 1"

        # ── Act 2: drop the SKU, re-run pipeline ─────────────────────────────
        removed = _drop_sku_from_product_data(product_csv, TARGET_SKU)
        assert removed >= 1, f"Expected to drop at least one row with sku={TARGET_SKU}"

        _run_pipeline(tmp_input)

        # ── Assert: TARGET_SKU is gone from every SKU-keyed collection ──────
        pc_second  = _ids_with_prefix(firestore_client, "PLProductContent", f"{TARGET_SKU}_")
        var_second = _ids_with_prefix(firestore_client, "PLVariant",        f"{TARGET_SKU}_")
        idx_second = _ids_with_base_sku_prefix(firestore_client, "ProductIndexData", TARGET_BASE_SKU, LOCALE)

        assert pc_second == [], (
            f"PLProductContent still has orphan docs after SKU {TARGET_SKU} was removed: {pc_second}"
        )
        assert var_second == [], (
            f"PLVariant still has orphan docs after SKU {TARGET_SKU} was removed: {var_second}"
        )
        assert idx_second == [], (
            f"ProductIndexData still has orphan docs after base_sku {TARGET_BASE_SKU} was removed: {idx_second}"
        )
