# Grohe NEO — Integration Test Harness

## Status

| Phase | Scope | Status |
|---|---|---|
| **Phase 1** | ETL pipeline → Firestore state | ✅ **44 passed** — `test-pipeline` green |
| **Phase 2** | Sync logic + WireMock infrastructure | ✅ **7 passed** — `test-sync` green |
| **Phase 3** | IndexingApi → WireMock ingestion capture | ✅ **5 passed** — `test-indexing` (requires `infra-phase3-up`) |
| **Phase 4** | ProductsApi + NavigationApi HTTP tests | ✅ **10 passed** — `test-services` (requires `infra-phase4-up`) |
| **Phase 5** | SearchApi HTTP tests (Sitecore Search integration) | ✅ **5 passed** — `test-search` (requires `infra-phase5-up`) |

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

## Quick Start

```bash
# One-time setup
make setup

# Phase 1+2: Start Firestore emulator + WireMock (fast)
make infra-up
make test-pipeline     # Layer 1: ETL pipeline (~10-11 min)
make test-sync         # Layer 2: sync logic  (~15 seconds)
make infra-down

# Phase 3: Start all services including IndexingApi (slow — Docker build on first run)
make infra-phase3-up
make test-indexing     # Layer 4: IndexingApi → WireMock (~30 sec)
make infra-phase3-down

# Phase 4: Start NavigationApi + ProductsApi (slow — first build ~20 min for ProductsApi)
make infra-phase4-up   # seeds config + builds + starts both services
make test-services     # Layer 3: NavigationApi + ProductsApi + SearchApi (~90 sec)
make infra-phase4-down

# Phase 5: Start SearchApi only (no Firestore seeding — build ~2-3 min first time)
make infra-phase5-up   # WireMock (8081) + SearchApi (8085)
make test-search       # Phase 5: SearchApi HTTP tests (~30 sec)
make infra-phase5-down
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
│                               WireMock (port 8081)                    [Phase 2 ✅]
│                               IndexingApi (port 8082, profile=phase3) [Phase 3 ✅]
│                               NavigationApi (port 8083, profile=phase4)[Phase 4 ✅]
│                               ProductsApi (port 8084, profile=phase4)  [Phase 4 ✅]
│                               SearchApi (port 8085, profile=phase5)   [Phase 5 ✅]
├── Makefile                    All orchestration commands
├── requirements.txt            pytest, pytest-json-report, pytest-html, google-cloud-firestore
├── pytest.ini                  Test discovery + markers (pythonpath = .)
├── CLAUDE.md                   Claude's run guide + failure→source trace table
├── fixtures/
│   ├── csv/                    Real de/DE CSV batch — 17 files from NEO/data_input/
│   └── mocks/                  WireMock stub definitions
│       ├── sitecore-search/    Ingestion stubs (PUT + DELETE) [Phase 3 ✅]
│       │                       Discovery stub (POST search)  [Phase 5 ✅]
│       ├── hybris/             Hybris API stubs                        [planned]
│       ├── sitecore-edge/      GraphQL response stubs                  [planned]
│       └── idp/                OAuth token + JWT public key stubs      [planned]
├── tests/
│   ├── conftest.py             Shared fixtures: firestore_client, pipeline_result, clean_firestore
│   ├── pipeline/               Layer 1: ETL → Firestore assertions      [Phase 1 ✅]
│   ├── sync/                   Layer 2: ProductIndexData → index queue  [Phase 2 ✅]
│   │   ├── _data.py            Shared constants + compute_hash()
│   │   ├── conftest.py         sync_result fixture (seeds + runs sync)
│   │   └── test_sync_logic.py  7 sync behaviour tests
│   ├── indexing/               Layer 4: IndexingApi → Sitecore Search   [Phase 3 ✅]
│   │   ├── conftest.py         indexing_result fixture (seeds + calls API)
│   │   └── test_indexing_pipeline.py  5 tests (PUT + DELETE + payload assertions)
│   ├── services/               Layer 3: NavigationApi + ProductsApi + SearchApi [Phase 4+5 ✅]
│   │   ├── navigation/
│   │   │   ├── conftest.py     navigation_result fixture (seeds PLCategory + waits)
│   │   │   └── test_navigation_api.py  5 tests
│   │   ├── products/
│   │   │   ├── conftest.py     products_result fixture (seeds PLProductContent + waits)
│   │   │   └── test_products_api.py    5 tests
│   │   └── search/             Phase 5: SearchApi (no Firestore dependency)  [Phase 5 ✅]
│   │       ├── conftest.py     search_result fixture (waits for SearchApi only)
│   │       └── test_search_api.py      5 tests
│   └── scenarios/              Layer 5: Cross-repo business scenarios   [planned]
├── scripts/
│   └── wait_for_emulator.py    Generic health-check poller (--host, --path, --timeout)
└── reports/                    Generated test output — gitignored
```

---

## Makefile Commands

```bash
# Setup
make setup                  # Create .venv + install test deps

# Phase 1+2 Infrastructure (fast)
make infra-up               # Start Firestore emulator + WireMock (Docker)
make infra-down             # Stop Phase 1+2 containers
make wait                   # Poll until emulator is ready

# Phase 3 Infrastructure (slow — Docker build on first run)
make infra-phase3-up        # Build + start all services incl. IndexingApi
make infra-phase3-down      # Stop all Phase 3 containers
make wait-indexing-api      # Poll until IndexingApi /health responds

# Phase 4 Infrastructure (slow — first build ~20 min for ProductsApi)
make seed-config            # Seed Firestore configuration collection (before containers start)
make infra-phase4-up        # Seed config + build + start NavigationApi + ProductsApi
make infra-phase4-down      # Stop all Phase 4 containers
make wait-navigation-api    # Poll until NavigationApi /health responds
make wait-products-api      # Poll until ProductsApi /health responds

# Phase 5 Infrastructure (fast — no Firestore, no Chrome, build ~2-3 min first time)
make infra-phase5-up        # Build + start SearchApi (WireMock + SearchApi only)
make infra-phase5-down      # Stop all Phase 5 containers
make wait-search-api        # Poll until SearchApi /health responds

# Tests
make test-pipeline          # Layer 1: ETL pipeline tests                     [Phase 1 ✅]
make test-sync              # Layer 2: sync logic tests                       [Phase 2 ✅]
make test-indexing          # Layer 4: IndexingApi → WireMock                 [Phase 3 ✅]
make test-services          # Layer 3: NavigationApi + ProductsApi + SearchApi [Phase 4+5 ✅]
make test-search            # Phase 5: SearchApi only                         [Phase 5 ✅]
make test-all               # All layers

# Claude fix loop
make fix-loop               # Run all tests → reports/results.json

# Reporting
make report                 # Open HTML report in browser
make clean                  # Remove reports + caches
```

---

## Infrastructure

### Phase 1 ✅ — Firestore emulator

```yaml
firestore-emulator:
  image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
  port: 8080
  project: demo-project
```

The data-loader supports this out of the box via `--firestore-emulator` (targets `localhost:8080`).

**Emulator limitation:** the gcloud Firestore emulator only supports the `(default)` database.
Named databases are not supported. Sync tests work around this by passing
`--sync-database (default)`, so both `ProductIndexData` and `products-index-updates`
collections share the same database instance.

### Phase 2 ✅ — WireMock

```yaml
wiremock:
  image: wiremock/wiremock:3.4.2
  port: 8081   # host port; internal is 8080
  volumes: ./fixtures/mocks:/home/wiremock/mappings
```

Replaces all external HTTP dependencies for Phase 3+ tests:

| External System | Stub directory |
|---|---|
| Hybris (SAP Commerce) | `fixtures/mocks/hybris/` |
| Sitecore Search Ingestion | `fixtures/mocks/sitecore-search/` |
| Sitecore Search Discovery | `fixtures/mocks/sitecore-search/` |
| Sitecore Edge GraphQL | `fixtures/mocks/sitecore-edge/` |
| IDP / OAuth2 | `fixtures/mocks/idp/` |

WireMock's **request journal** (`GET http://localhost:8081/__admin/requests`) lets
tests assert the exact payload that was sent to Sitecore Search.

Phase 3 stubs loaded from `fixtures/mocks/sitecore-search/`:
- `ingestion-update.json` — matches `PUT /ingestion/v1/domains/…` → 200 `{"enqueued":true}`
- `ingestion-delete.json` — matches `DELETE /ingestion/v1/domains/…` → 200 `{"enqueued":true}`

### Phase 3 ✅ — IndexingApi (.NET)

```yaml
indexing-api:
  profiles: ["phase3"]
  build:
    context: ../grohe-neo-services
    dockerfile: src/GroheNeo.IndexingApi/Dockerfile
  ports: ["8082:8080"]
  environment:
    ASPNETCORE_ENVIRONMENT: Integration   # loads appsettings.Integration.json
    FIRESTORE_EMULATOR_HOST: firestore-emulator:8080
```

Config overrides live in `grohe-neo-services/src/GroheNeo.IndexingApi/appsettings.Integration.json`:
- Firestore → emulator (`demo-project`, `(default)` database)
- Sitecore Search Ingestion → `http://wiremock:8080/ingestion/v1`
- XMCloud Edge → `http://wiremock:8080/graphql` (fails gracefully, fallback URL used)
- Source locale mapping: `"test-source-123": ["de_de"]`

> **Note:** `FirestoreDataStorageService.cs` in `grohe-neo-services` requires
> `builder.EmulatorDetection = Google.Api.Gax.EmulatorDetection.EmulatorOrProduction`
> for the .NET Firestore SDK to respect `FIRESTORE_EMULATOR_HOST`. Without it the
> service crashes with an ADC credentials error. This fix is already applied at
> `FirestoreDataStorageService.cs:54`.

### Phase 4 ✅ — NavigationApi + ProductsApi

```yaml
navigation-api:
  profiles: ["phase4"]
  build: { context: ../grohe-neo-services, dockerfile: src/GroheNeo.ProductsDynamicNavigationApi/Dockerfile }
  ports: ["8083:8080"]
  environment:
    ASPNETCORE_ENVIRONMENT: Integration   # loads appsettings.Integration.json
    FIRESTORE_EMULATOR_HOST: firestore-emulator:8080
    configuration_project_id: demo-project
    configuration_table: (default)
    Neo_XMCloudApi_BaseUrl: http://wiremock:8080

products-api:
  profiles: ["phase4"]
  build: { context: ../grohe-neo-services, dockerfile: src/GroheNeo.ProductsApi/Dockerfile }
  ports: ["8084:8080"]
  environment:
    ASPNETCORE_ENVIRONMENT: Integration
    FIRESTORE_EMULATOR_HOST: firestore-emulator:8080
    configuration_project_id: demo-project
    configuration_table: (default)
    NeoXMCloudApiBaseUrl: http://wiremock:8080
```

**Configuration bootstrapping:** Both services call `FirebaseConfigurationService.LoadConfigurationAsync()`
at startup to load per-locale database IDs. The `configuration` Firestore collection must be
seeded BEFORE the containers start — `make seed-config` / `scripts/seed_config.py` handles this.

**EmulatorDetection fix:** Applied to 3 files in `grohe-neo-services`:
- `FirebaseConfigurationService.cs` — builder for the config Firestore connection
- `GroheNeo.ProductsDynamicNavigationApi/FireStoreDbResolver.cs` — per-locale Firestore builder
- `GroheNeo.ProductsApi/FireStoreDbResolver.cs` — per-locale Firestore builder

**XMCloud calls:** NavigationApi's `GetProductAndInspirationGuides` has a top-level try-catch →
returns `Result.Failure` → categories still returned. ProductsApi's XMCloud calls point to
WireMock, receive 404, and fall back gracefully. No stubs needed.

### Phase 5 ✅ — SearchApi (.NET)

```yaml
search-api:
  profiles: ["phase5"]
  build:
    context: ../grohe-neo-services
    dockerfile: src/GroheNeo.SearchApi/Dockerfile
  ports: ["8085:8080"]
  environment:
    ASPNETCORE_ENVIRONMENT: Integration   # loads appsettings.Integration.json
```

Config overrides live in `grohe-neo-services/src/GroheNeo.SearchApi/appsettings.Integration.json`:
- Sitecore Search Discovery → `http://wiremock:8080/discover/v2/integration`
- Source locale mapping: `"integration": ["de_de"]` (so `lang=de-de` resolves to WireMock stub)
- XM Cloud → `http://wiremock:8080` (via `CrossApiServicesSettings.Integration.json`; returns 404 → graceful fallback)

> **No Firestore dependency** — SearchApi only calls Sitecore Search Discovery API and
> optionally XM Cloud. No `FIRESTORE_EMULATOR_HOST`, no `seed-config` needed.

> **Language format:** SearchApi uses XM Cloud format `xx-xx` (5 chars). JSON request keys
> are `"lang"` (not `"language"`) and `"q"` (not `"query"`).

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
| `test_collections.py` | All 5 collections populated, document IDs match `{SKU}_de_DE` / `{BaseSKU}_{Seq}_de_DE` format |
| `test_document_structure.py` | PLProductContent fields (SKU, EAN, Slug, images, Finish, Variants, <900KB), ProductIndexData fields (finish_definitions, all_category_ids, image_url, tag_definitions), PLCategory (Language/Market), PLVariant (SKU identifier) |

Known fixture SKUs: `66838000`, `40806000`
Known ProductIndexData IDs: `66838_0_de_DE`, `40806_0_de_DE`

**Timing:** ETL transform (292k records → 17k products) takes ~6–7 min. Total
pipeline test run (transform + Firestore load + assertions) is ~10–11 min.

### Layer 2 — Sync tests ✅ `tests/sync/`

**Scope:** `sync_product_index.py` only. No .NET services, no WireMock.
**How:** Seeds `ProductIndexData` directly (no ETL), runs `sync_product_index.py --use-emulator --sync-database (default)`, asserts `products-index-updates`.
**Fixture data:** 4 minimal in-memory documents seeded by the `sync_result` fixture.

Implemented tests:

| Test | Scenario |
|---|---|
| `test_sync_script_exits_successfully` | Process exits 0 |
| `test_new_product_creates_update_record_with_operation_update` | New product → Update record created with `finished=False` |
| `test_new_product_record_has_correct_structure` | `identifier`, `culture`, `data.document.{fields,id,locale}` present |
| `test_changed_product_updates_record_when_hash_differs` | Stale hash → record rewritten, hash updated |
| `test_finished_flag_is_set_to_false_on_change` | `finished=True` pre-sync → reset to `False` on content change |
| `test_unchanged_product_is_skipped` | Matching hash → no write, `finished` stays `True` |
| `test_removed_product_marks_record_as_delete` | Absent from `ProductIndexData` → `operation=Delete` |

**Timing:** ~15 seconds (tiny dataset — 4 docs, no ETL).

### Layer 4 — Indexing tests ✅ `tests/indexing/`

**Scope:** Firestore `products-index-updates` → IndexingApi (Docker) → Sitecore Search (WireMock).
**Verifies:** Exact HTTP request sent to Sitecore Search Ingestion API (PUT/DELETE, URL, body fields).
**Infrastructure required:** `make infra-phase3-up` (builds IndexingApi from source — slow first time).

| Test | Scenario |
|---|---|
| `test_full_product_indexing_pipeline_sends_correct_payload` | GET /initialize returns 200; WireMock received ≥1 PUT |
| `test_deleted_product_sends_delete_operation_to_sitecore` | Delete-op doc → WireMock received ≥1 DELETE |
| `test_updated_product_sends_update_with_correct_fields` | PUT body contains correct `fields.name` |
| `test_ingestion_payload_includes_finish_definitions` | PUT body contains non-empty `fields.finish_definitions` |
| `test_ingestion_payload_locale_is_correct` | PUT URL contains `locale=de_de` |

**Timing:** ~30 seconds (2 docs, no ETL; IndexingApi startup already done by infra-phase3-up).

### Layer 3 — Service tests ✅ `tests/services/`

**Scope:** NavigationApi (8083) + ProductsApi (8084) + SearchApi (8085) via HTTP.
**Infrastructure required:** `make infra-phase4-up` (Navigation + Products), `make infra-phase5-up` (SearchApi)

#### NavigationApi (5 tests) `tests/services/navigation/`

| Test | Scenario |
|---|---|
| `test_navigation_returns_200_for_valid_locale` | GET /category-navigation?locale=de-DE → 200 |
| `test_navigation_response_contains_category_items` | Response has non-empty CategoryMenuItems |
| `test_navigation_category_item_has_required_fields` | First item has id, name, slug fields |
| `test_navigation_language_market_match_locale` | Item language='de', market='DE' |
| `test_navigation_returns_400_for_invalid_locale_format` | locale=invalid → 400 |

#### ProductsApi (5 tests) `tests/services/products/`

| Test | Scenario |
|---|---|
| `test_products_api_returns_product_for_known_sku` | GET /PROD-001?locale=de-DE → 200 |
| `test_product_response_contains_sku_field` | Response body has sku='PROD-001' |
| `test_products_api_returns_404_for_unknown_sku` | GET /UNKNOWN?locale=de-DE → 404 |
| `test_category_endpoint_returns_data_for_locale` | GET /category?locale=de-DE → 200 or 204 |
| `test_variants_endpoint_returns_variants_for_known_sku` | GET /variants?sku=PROD-001&locale=de-DE → 200 |

#### SearchApi (5 tests) `tests/services/search/`

**Infrastructure required:** `make infra-phase5-up` (WireMock + SearchApi — no Firestore)

| Test | Scenario |
|---|---|
| `test_search_api_health_returns_200` | GET /health → 200 |
| `test_product_search_returns_ok_for_valid_query` | POST /product/v1/search `{"lang":"de-de","q":"product",...}` → 200 or 204 |
| `test_product_search_response_contains_items_when_200` | Response body has non-empty `results` array |
| `test_product_search_returns_400_for_missing_language` | POST without `lang` field → 400 |
| `test_autosuggest_returns_ok_for_valid_query` | POST /autosuggest/v1/suggest `{"lang":"de-de","q":"product"}` → 200 or 204 |

### Layer 5 — Scenario tests `tests/scenarios/` (planned)

**Scope:** Business-level, multi-project. Named after real task patterns.
**Purpose:** Acceptance criteria for multi-repo tasks given to Claude.

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

### New Firestore field (Layer 1)
```python
# tests/pipeline/test_document_structure.py → TestPLProductContentStructure
def test_has_sustainability_label(self):
    assert "SustainabilityLabel" in self._doc
```

### New collection (Layer 1)
```python
# tests/pipeline/test_collections.py
def test_new_collection_is_populated(self, pipeline_result, firestore_client):
    ids = collection_doc_ids(firestore_client, "NewCollection")
    assert len(ids) > 0
```

### New sync behaviour (Layer 2)
```python
# tests/sync/_data.py — add new test product constants if needed
# tests/sync/test_sync_logic.py → TestSyncLogic
def test_new_sync_behaviour(self, sync_result):
    proc, client = sync_result
    doc = client.collection("products-index-updates").document(PRODUCT_NEW_ID).get()
    assert doc.to_dict()["some_field"] == "expected_value"
```

### New scenario (Phase 4)
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
| HTTP mocking | **WireMock 3.4.2** | Industry standard; captures + asserts requests; single container replaces all external APIs |
| Firestore | **Official Google emulator** | Already supported by data-loader (`--firestore-emulator` flag, port 8080) |
| .NET services | **Docker Compose** | Real compiled binaries; real config; connects to emulator via env var |
| Orchestration | **Makefile** | Universal, no extra tooling, readable targets |
| Report format | **pytest-json-report** | Machine-readable for Claude fix loop |
| Fixtures | **Real CSV files** (Layer 1) / **minimal in-memory dicts** (Layer 2) | Real data for pipeline; tiny controlled data for sync (fast, deterministic) |
| Test language | **Python only** (not .NET xUnit for integration) | Single language at integration layer; services tested black-box over HTTP |

### Rejected alternatives
- **pytest-xdist** (parallel tests): rejected — session-scoped pipeline fixture runs once
  and is shared; parallelism would require per-worker emulator instances.
- **Testcontainers** (Python): considered for programmatic container lifecycle; deferred in
  favour of explicit `make infra-up/down` for clarity and debuggability.
- **Importing data-loader modules directly**: rejected in favour of subprocess — black-box
  testing is more realistic and avoids dependency conflicts between the two venvs.
- **Named Firestore databases for sync tests**: rejected — the gcloud emulator only supports
  `(default)`; sync tests use `--sync-database (default)` so both collections share one DB.

---

## Windows Notes

`firestore_loader.py` prints emoji (🔥 ✅ ❌) to stdout. On Windows, the default
cp1252 encoding can't encode these, which causes the subprocess to crash. Both
`conftest.py` files (pipeline and sync) handle this with two settings:

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

1. **Fast by default** — Layer 1 (~10 min) is the ETL transform CPU cost, not infrastructure. Layer 2 (~15 sec) seeds minimal docs directly, no ETL needed.
2. **Incremental** — each phase adds a layer; earlier layers stay green
3. **Traceable** — test names → source files → repos; no ambiguity
4. **Self-contained** — no cloud credentials; everything mocked locally
5. **Claude-friendly** — JSON output, structured failures, documented trace table
