# Grohe NEO — Integration Test Harness

## Status

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | ETL pipeline → Firestore state | ✅ **44 passed, 1 xfailed** — `make test-pipeline` green |
| **Phase 2** | Sync logic + Indexing API + WireMock | 🔲 Planned |
| **Phase 3** | .NET service HTTP tests | 🔲 Planned |
| **Phase 4** | Business scenario tests (acceptance gate) | 🔲 Planned |

---

## Vision

A cross-project test harness that spins up the full Grohe NEO backend stack locally —
Firestore emulator, mocked external APIs, real .NET services — so that **multi-repo tasks
can be validated end-to-end automatically**, and Claude can run tests, read failures,
fix code across repos, and iterate to green without manual intervention.

---

## The Problem This Solves

Most tasks in Grohe NEO touch **multiple repos**. Example:

> "Add field `sustainability_label` to PLProductContent and expose it in the Products API."

Changes needed:
- `grohe-neo-data-loader` — `transformer.py`, `output_models/pl_product_content.py`
- `grohe-neo-services` — `ProductsApi` models, mappings, controller

Validating that today requires: running the loader against real Firestore, starting
the service locally, testing via Postman. Slow, risky, manual.

**This project eliminates all of that.**

---

## Quick Start (Phase 1)

```bash
# One-time setup
make setup

# Start Firestore emulator (requires Docker Desktop)
make infra-up

# Run ETL pipeline tests
make test-pipeline

# Stop emulator
make infra-down
```

### Prerequisites
- Docker Desktop running
- Python 3.11+ on PATH
- data-loader venv set up:
  ```bash
  cd ../grohe-neo-data-loader
  python -m venv .venv
  .venv/Scripts/pip install -r requirements.txt   # Windows
  .venv/bin/pip install -r requirements.txt       # Linux/Mac
  ```

---

## Repository Layout

```
integration/
├── docker-compose.yml          Firestore emulator (port 8080)          [Phase 1 ✅]
│                               WireMock (port 8081)                    [Phase 2 🔲]
├── Makefile                    All orchestration commands
├── requirements.txt            pytest, pytest-json-report, google-cloud-firestore
├── pytest.ini                  Test discovery + markers
├── CLAUDE.md                   Claude's run guide + failure→source trace table
├── fixtures/
│   ├── csv/                    Real de/DE CSV batch — 17 files from NEO/data_input/
│   └── mocks/                  WireMock stub definitions                [Phase 2 🔲]
│       ├── hybris/             Hybris API stubs
│       ├── sitecore-search/    Ingestion capture + Discovery stubs
│       ├── sitecore-edge/      GraphQL response stubs
│       └── idp/                OAuth token + JWT public key stubs
├── tests/
│   ├── conftest.py             Shared fixtures: firestore_client, pipeline_result
│   ├── pipeline/               Layer 1: ETL → Firestore assertions      [Phase 1 ✅]
│   ├── sync/                   Layer 2: ProductIndexData → index queue  [Phase 2 🔲]
│   ├── services/               Layer 3: .NET service HTTP tests         [Phase 3 🔲]
│   ├── indexing/               Layer 4: Indexing API → WireMock capture [Phase 2 🔲]
│   └── scenarios/              Layer 5: Cross-repo business scenarios   [Phase 4 🔲]
├── scripts/
│   └── wait_for_emulator.py   Portable health-check poller
└── reports/                    Generated test output — gitignored
```

---

## Makefile Commands

```bash
# Setup
make setup              # Create .venv + install test deps

# Infrastructure
make infra-up           # Start Docker containers
make infra-down         # Stop Docker containers
make wait               # Poll until emulator is ready

# Tests
make test-pipeline      # Layer 1: ETL pipeline tests
make test-sync          # Layer 2: sync tests              [Phase 2]
make test-services      # Layer 3: .NET service tests      [Phase 3]
make test-indexing      # Layer 4: indexing tests          [Phase 2]
make test-scenarios     # Layer 5: scenario tests          [Phase 4]
make test-all           # All available layers

# Claude fix loop
make fix-loop           # Run all tests → reports/results.json

# Reporting
make report             # Open HTML report in browser
make clean              # Remove reports + caches
```

---

## Infrastructure

### Phase 1 (implemented): Firestore emulator only

```yaml
firestore-emulator:
  image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
  port: 8080
  project: demo-project
```

The data-loader supports this out of the box via `--firestore-emulator` (targets `localhost:8080`).

### Phase 2 (planned): Add WireMock

```yaml
wiremock:
  image: wiremock/wiremock:latest
  port: 8081
  volumes: ./fixtures/mocks:/home/wiremock/mappings
```

Replaces all external HTTP dependencies:

| External System | WireMock path prefix |
|---|---|
| Hybris (SAP Commerce) | `/hybris` |
| Sitecore Search Ingestion | `/sitecore-ingestion` → `discover-euc1.sitecorecloud.io/ingestion/v1` |
| Sitecore Search Discovery | `/sitecore-discovery` → `discover-euc1.sitecorecloud.io/discover/v2/{domainId}` |
| Sitecore Edge GraphQL | `/sitecore-edge` → `edge-platform.sitecorecloud.io` |
| IDP / OAuth2 | `/idp` |
| Google Places API | `/places` |
| Vercel revalidation | `/vercel` |

WireMock's **request journal** lets tests assert *what payload was sent* to Sitecore Search.

### Phase 3 (planned): Add .NET services

```yaml
products-api:
  build: ../grohe-neo-services
  environment:
    FIRESTORE_EMULATOR_HOST: firestore-emulator:8080
    HYBRIS_BASE_URL: http://wiremock:8081/hybris
    SITECORE_SEARCH_INGESTION_URL: http://wiremock:8081/sitecore-ingestion
```

Only services needed per scenario run (keep startup fast).

---

## Test Layers

### Layer 1 — Pipeline tests ✅ `tests/pipeline/`

**Scope:** data-loader subprocess only. No .NET services, no WireMock.
**How:** Runs `main.py --to-firestore --firestore-emulator`, asserts Firestore state.
**Fixture data:** Real de/DE CSV batch (`fixtures/csv/`, 17 files).

Implemented tests:

| File | Tests |
|---|---|
| `test_pipeline_runs.py` | Exit code 0, completion message, no critical errors, all collections mentioned |
| `test_collections.py` | All 6 collections populated, document IDs match `{SKU}_de_DE` / `{BaseSKU}_{Seq}_de_DE` format |
| `test_document_structure.py` | PLProductContent fields (SKU, EAN, Slug, images, Finish, Variants, <900KB), ProductIndexData fields (finish_definitions, all_category_ids, image_url, tag_definitions), PLCategory (Language/Market), PLVariant (SKU identifier) |

Known fixture SKUs: `66838000`, `40806000`
Known ProductIndexData IDs: `66838_0_de_DE`, `40806_0_de_DE`

**xfailed:** `test_pl_feature_content_is_populated` — `PLFeatureContent` is never
populated because no CSV in `FILE_MODEL_MAP` maps to the `'featurecontent'` extractor
key that `transformer.py` looks for. All other 44 tests pass.

**Timing:** Phase 2 transform (292k records → 17k products) takes ~6–7 min. Total
pipeline test run is ~10–11 min on a developer machine.

### Layer 2 — Sync tests 🔲 `tests/sync/`

**Scope:** `sync_product_index.py` only.
**Verifies:** `products-index-updates` collection state after sync.

Planned tests:
```
test_new_product_creates_update_record_with_operation_update
test_changed_product_updates_record_when_hash_differs
test_unchanged_product_is_skipped
test_removed_product_marks_record_as_delete
test_finished_flag_is_set_to_false_on_change
```

### Layer 3 — Service tests 🔲 `tests/services/`

**Scope:** Running .NET services via HTTP. Firestore pre-loaded, WireMock for external deps.
**Verifies:** API response shape and content for known inputs.

Planned tests:
```
test_products_api_returns_product_by_sku
test_products_api_returns_category_tree
test_products_api_returns_variants_grouped_by_finish
test_navigation_api_returns_category_routes
test_search_api_forwards_request_to_wiremock
test_indexing_api_reads_unfinished_queue_records
```

### Layer 4 — Indexing tests 🔲 `tests/indexing/`

**Scope:** Full pipeline: Firestore queue → Indexing API → Sitecore Search (WireMock).
**Verifies:** Exact payload sent to Sitecore Search Ingestion API.

Planned tests:
```
test_full_product_indexing_pipeline_sends_correct_payload
test_deleted_product_sends_delete_operation_to_sitecore
test_updated_product_sends_update_with_correct_fields
test_ingestion_payload_includes_finish_definitions
test_ingestion_payload_locale_is_correct
```

### Layer 5 — Scenario tests 🔲 `tests/scenarios/`

**Scope:** Business-level, multi-project. Named after real task patterns.
**Purpose:** These are the **acceptance criteria for tasks given to Claude**.

Planned tests:
```
test_scenario__new_field_in_loader_appears_in_products_api_and_search_index
test_scenario__new_locale_flows_through_full_pipeline
test_scenario__deleted_product_is_removed_from_sitecore_search
test_scenario__category_routing_change_reflected_in_navigation_api
test_scenario__product_content_update_triggers_incremental_sync
```

---

## The Automated Fix Loop

This is the core workflow for multi-repo tasks.

```
You give Claude a task
    ↓
Claude identifies affected repos + files
    ↓
Claude makes code changes across repos
    ↓
Claude runs: make fix-loop
    → reports/results.json produced
    ↓
Claude reads results.json
    ├── All green → summarise changes, done
    └── Failures → read test name + assertion
                → trace to source file (see CLAUDE.md table)
                → fix code
                → loop back to make fix-loop
```

### Why JSON output enables this

```json
{
  "tests": [{
    "nodeid": "tests/pipeline/test_document_structure.py::TestPLProductContentStructure::test_has_sustainability_label",
    "outcome": "failed",
    "call": {
      "longrepr": "AssertionError: 'SustainabilityLabel' not found in document fields.\nActual keys: ['SKU', 'EAN', 'Slug', ...]"
    }
  }]
}
```

Test name → layer → source file → fix. No ambiguity.

### Test naming conventions

- Unit-level: `test_{field/behaviour}_{condition}`
- Scenario-level: `test_scenario__{task_description_in_snake_case}`

Scenario test names map directly to task descriptions so Claude can identify
which test to run before and after making changes.

---

## How to Add Tests

### New Firestore field
```python
# tests/pipeline/test_document_structure.py → TestPLProductContentStructure
def test_has_sustainability_label(self):
    assert "SustainabilityLabel" in self._doc
```

### New collection
```python
# tests/pipeline/test_collections.py
def test_new_collection_is_populated(self, pipeline_result, firestore_client):
    ids = collection_doc_ids(firestore_client, "NewCollection")
    assert len(ids) > 0
```

### New scenario
```python
# tests/scenarios/test_new_locale.py
@pytest.mark.scenario
def test_scenario__new_locale_flows_through_full_pipeline(self, ...):
    ...
```

---

## Tech Stack Decisions

| Concern | Choice | Rationale |
|---|---|---|
| Test framework | **pytest** | Python-native (data-loader is Python); services testable via HTTP; excellent JSON report output |
| HTTP mocking | **WireMock** | Industry standard; captures + asserts requests; single container replaces all external APIs |
| Firestore | **Official Google emulator** | Already supported by data-loader (`--firestore-emulator` flag, port 8080) |
| .NET services | **Docker Compose** | Real compiled binaries; real config; connects to emulator via env var |
| Orchestration | **Makefile** | Universal, no extra tooling, readable targets |
| Report format | **pytest-json-report** | Machine-readable for Claude fix loop |
| Fixtures | **Real CSV files** from `NEO/data_input/` | Real data catches real bugs; format already validated by production |
| Test language | **Python only** (not .NET xUnit for integration) | Single language at integration layer; services tested black-box over HTTP |

### Rejected alternatives
- **pytest-xdist** (parallel tests): rejected for Phase 1 — session-scoped pipeline fixture
  runs once and is shared; parallelism would require per-worker emulator instances.
- **Testcontainers** (Python): considered for programmatic container lifecycle; deferred in
  favour of explicit `make infra-up/down` for clarity and debuggability.
- **Importing data-loader modules directly**: rejected in favour of subprocess — black-box
  testing is more realistic and avoids dependency conflicts between the two venvs.

---

## Windows Notes

`firestore_loader.py` prints emoji (🔥 ✅ ❌) to stdout. On Windows, the default
cp1252 encoding can't encode these, which causes the subprocess to crash. The
`conftest.py` fixture handles this with two settings:

```python
env  = { ..., "PYTHONUTF8": "1" }          # child writes UTF-8
proc = subprocess.run(..., encoding="utf-8") # parent reads UTF-8
```

Both are required — missing either one breaks the test run on Windows.

---

## Updating CSV Fixtures

When a new data batch is available in `NEO/data_input/`:

```bash
cp ../data_input/*.csv fixtures/csv/
# Then re-run tests to confirm format compatibility
make test-pipeline
```

---

## Design Principles

1. **Fast by default** — Phase 1 has no .NET services or external calls; the ~10 min runtime is the transform CPU cost on 292k records, not infrastructure overhead
2. **Incremental** — each phase adds a layer; earlier layers stay green
3. **Traceable** — test names → source files → repos; no ambiguity
4. **Self-contained** — no cloud credentials; everything mocked locally
5. **Claude-friendly** — JSON output, structured failures, documented trace table
