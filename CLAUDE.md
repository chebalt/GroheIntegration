# CLAUDE.md — Integration Test Harness

## Purpose

Cross-project integration tests for the Grohe NEO platform. Spins up a local
Firestore emulator and runs the real data-loader against real fixture CSVs.

**Phase 1 (green):** ETL pipeline → Firestore state assertions — **44 passed, 0 xfailed**
**Phase 2 (planned):** Sync logic + Indexing API + WireMock
**Phase 3 (planned):** .NET service HTTP tests
**Phase 4 (planned):** Business scenario tests

---

## Quick Start

```bash
# 1. One-time setup (create virtualenv + install pytest deps)
make setup

# 2. Start Firestore emulator (Docker required)
make infra-up

# 3. Run pipeline tests
make test-pipeline

# 4. Stop emulator when done
make infra-down
```

---

## Full Command Reference

| Command | What it does |
|---|---|
| `make setup` | Create `.venv` and install test dependencies |
| `make infra-up` | Start Firestore emulator via Docker Compose |
| `make infra-down` | Stop Docker containers |
| `make wait` | Wait until emulator responds (health check) |
| `make test-pipeline` | Run ETL pipeline tests → `reports/pipeline.json` |
| `make test-all` | Run all available tests → `reports/results.json` |
| `make fix-loop` | Run all tests + emit `reports/results.json` (Claude fix loop) |
| `make report` | Open HTML report in browser |
| `make clean` | Remove reports and cache |

---

## Prerequisites

1. **Docker Desktop** running (for Firestore emulator)
2. **Python 3.11+** on PATH (for integration venv setup)
3. **data-loader venv** set up:
   ```bash
   cd ../grohe-neo-data-loader
   python -m venv .venv
   .venv/Scripts/pip install -r requirements.txt   # Windows
   # or
   .venv/bin/pip install -r requirements.txt       # Linux/Mac
   ```

---

## Project Layout

```
integration/
├── docker-compose.yml        Firestore emulator service
├── Makefile                  All orchestration commands
├── requirements.txt          pytest + google-cloud-firestore
├── pytest.ini                Test discovery config + markers
├── fixtures/
│   └── csv/                  Real de/DE CSV batch (17 files from NEO/data_input/)
├── tests/
│   ├── conftest.py           Shared fixtures: firestore_client, pipeline_result
│   └── pipeline/
│       ├── test_pipeline_runs.py        Exit code, completion message
│       ├── test_collections.py          Collection population + document IDs
│       └── test_document_structure.py   Field shape + size assertions
├── scripts/
│   └── wait_for_emulator.py  Health-check poller
└── reports/                  Generated test output (gitignored)
```

---

## How the Tests Work

### Infrastructure
- Firestore emulator runs at `localhost:8080` (Docker)
- All tests set `FIRESTORE_EMULATOR_HOST=localhost:8080`

### Session fixtures (run once per `pytest` invocation)
- `firestore_client` — connects to the emulator
- `pipeline_result` — clears the emulator, then runs `main.py` via subprocess,
  returns the `CompletedProcess` (stdout/stderr/returncode)

### Test data
- Fixtures are real CSV files from `NEO/data_input/` (de/DE market)
- Known SKUs in the fixture: `66838000`, `40806000`
- Known ProductIndexData IDs: `66838_0_de_DE`, `40806_0_de_DE`

---

## Reading Test Results (for Claude)

After `make fix-loop`, read `reports/results.json`:

```json
{
  "tests": [
    {
      "nodeid": "tests/pipeline/test_collections.py::TestDocumentIds::test_pl_product_content_document_exists_for_known_sku[66838000]",
      "outcome": "failed",
      "call": {
        "longrepr": "AssertionError: Expected document '66838000_de_DE' in PLProductContent."
      }
    }
  ]
}
```

**Trace from test name to source file:**

| Test file | Covers | Likely root cause repo |
|---|---|---|
| `test_pipeline_runs.py` | Pipeline exits + reports | `grohe-neo-data-loader/main.py` |
| `test_collections.py` | Collection presence + IDs | `grohe-neo-data-loader/transformer.py`, `firestore_loader.py` |
| `test_document_structure.py::TestPLProductContentStructure` | PLProductContent fields | `output_models/pl_product_content.py`, `transformer.py` |
| `test_document_structure.py::TestProductIndexDataStructure` | ProductIndexData fields | `output_models/product_index_data.py`, `transformer.py` |
| `test_document_structure.py::TestPLCategoryStructure` | PLCategory fields | `transformer.py` |
| `test_document_structure.py::TestPLVariantStructure` | PLVariant fields | `transformer.py` |

---

## The Automated Fix Loop

When Claude is given a task that touches the data-loader or its Firestore output:

1. Claude makes changes across the relevant repos
2. Claude runs: `make fix-loop`
3. Claude reads `reports/results.json`
4. If failures exist: Claude fixes code → re-runs from step 2
5. When all green: Claude summarises changes

**Example task:**
> "Add field `sustainability_label` to PLProductContent"

Expected fix loop:
- `test_document_structure.py::TestPLProductContentStructure::test_has_sustainability_label` → FAIL
- Claude adds field to `output_models/pl_product_content.py` + `transformer.py`
- Re-run → PASS

---

## Known State (Phase 1)

### Timing

Phase 2 transform is CPU-bound and silent — 292k records → 17k products takes
**~6–7 min** on a developer machine. Total pipeline fixture run (including Firestore
load) is **~10–11 min**. The subprocess timeout in `conftest.py` is set to 900s.

### Windows encoding

`firestore_loader.py` prints emoji to stdout. On Windows (cp1252), this crashes the
subprocess reader. `conftest.py` fixes this with:

- `env["PYTHONUTF8"] = "1"` — makes the child process write UTF-8
- `subprocess.run(..., encoding="utf-8")` — makes the parent read UTF-8

**Both are required.** If you see `UnicodeEncodeError` or `stdout=None` in test
failures, check that these are present in `conftest.py`.

---

## Adding New Tests

### For a new Firestore field
Add a test to `test_document_structure.py` in the appropriate class:
```python
def test_has_sustainability_label(self):
    assert "SustainabilityLabel" in self._doc
```

### For a new collection
Add a test to `test_collections.py`:
```python
def test_new_collection_is_populated(self, pipeline_result, firestore_client):
    ids = collection_doc_ids(firestore_client, "NewCollection")
    assert len(ids) > 0
```

### For a new scenario (Phase 4)
Add to `tests/scenarios/` following the `test_scenario__*` naming convention.

---

## Updating CSV Fixtures

When a new data batch is available in `NEO/data_input/`:
```bash
cp ../data_input/*.csv fixtures/csv/
```
Then re-run tests to confirm nothing broke.

---

## Emulator Notes

- Project ID: `demo-project` (hardcoded, emulator doesn't validate)
- Database: `(default)`
- Collections are cleared before each pipeline run (in `conftest.py`)
- Emulator state is lost when the container stops (`infra-down`)
- Port: `8080` — do not run the real Firebase emulator on the same port
