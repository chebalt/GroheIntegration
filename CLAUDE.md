# CLAUDE.md — Integration Test Harness

## Purpose

Cross-project integration tests for the Grohe NEO platform. Spins up a local
Firestore emulator (and WireMock in Phase 2+) and validates behaviour across repos.

**Phase 1 ✅** ETL pipeline → Firestore state assertions — **44 passed**
**Phase 2 ✅** Sync logic (`sync_product_index.py`) — **7 passed**
**Phase 3 ✅** IndexingApi → WireMock — **5 passed** (requires `infra-phase3-up`)
**Phase 4 ✅** .NET ProductsApi + NavigationApi HTTP tests — **10 passed** (requires `infra-phase4-up`)
**Phase 5 ✅** SearchApi HTTP tests — **5 passed** (requires `infra-phase5-up`, no Firestore seeding)

---

## Quick Start

```bash
# 1. One-time setup (create virtualenv + install pytest deps)
make setup

# 2a. Start Phase 1+2 infrastructure (fast)
make infra-up          # Firestore emulator (8080) + WireMock (8081)

# 2b. Start Phase 3 infrastructure (slow — builds .NET IndexingApi from source)
make infra-phase3-up   # Firestore (8080) + WireMock (8081) + IndexingApi (8082)

# 2c. Start Phase 4 infrastructure (slow — builds NavigationApi + ProductsApi)
make infra-phase4-up   # Firestore (8080) + WireMock (8081) + NavigationApi (8083) + ProductsApi (8084)

# 2d. Start Phase 5 infrastructure (SearchApi — no Firestore needed)
make infra-phase5-up   # WireMock (8081) + SearchApi (8085)

# 3. Run tests
make test-pipeline     # Layer 1: ETL pipeline (~10-11 min)
make test-sync         # Layer 2: sync logic  (~15 sec)
make test-indexing     # Layer 4: IndexingApi → WireMock (~30 sec, needs Phase 3 infra)
make test-services     # Layer 3: NavigationApi + ProductsApi + SearchApi (~60 sec, needs Phase 4+5 infra)
make test-search       # Phase 5: SearchApi only (~30 sec, needs Phase 5 infra)
make test-all          # All layers

# 4. Stop containers when done
make infra-down            # Phase 1+2
make infra-phase3-down     # Phase 3 (all containers)
make infra-phase4-down     # Phase 4 (all containers)
make infra-phase5-down     # Phase 5 (all containers)
```

---

## Full Command Reference

| Command | What it does |
|---|---|
| `make setup` | Create `.venv` and install test dependencies |
| `make infra-up` | Start Firestore emulator + WireMock via Docker Compose |
| `make infra-down` | Stop Phase 1+2 Docker containers |
| `make wait` | Wait until emulator responds (health check) |
| `make infra-phase3-up` | Build + start all Phase 3 services (IndexingApi included) |
| `make infra-phase3-down` | Stop all Phase 3 Docker containers |
| `make wait-indexing-api` | Wait until IndexingApi /health responds |
| `make seed-config` | Seed Firestore `configuration` collection (required for Phase 4) |
| `make infra-phase4-up` | Seed config + build + start NavigationApi + ProductsApi |
| `make infra-phase4-down` | Stop all Phase 4 Docker containers |
| `make wait-navigation-api` | Wait until NavigationApi /health responds |
| `make wait-products-api` | Wait until ProductsApi /health responds |
| `make infra-phase5-up` | Build + start SearchApi (no Firestore seeding needed) |
| `make infra-phase5-down` | Stop all Phase 5 Docker containers |
| `make wait-search-api` | Wait until SearchApi /health responds |
| `make test-pipeline` | Layer 1: ETL pipeline tests → `reports/pipeline.json` |
| `make test-sync` | Layer 2: sync logic tests → `reports/sync.json` |
| `make test-indexing` | Layer 4: IndexingApi → WireMock → `reports/indexing.json` |
| `make test-services` | Layer 3: NavigationApi + ProductsApi + SearchApi → `reports/services.json` |
| `make test-search` | Phase 5: SearchApi only → `reports/search.json` |
| `make test-all` | All available layers → `reports/results.json` |
| `make fix-loop` | Run all tests + emit `reports/results.json` (Claude fix loop) |
| `make report` | Open HTML report in browser |
| `make clean` | Remove reports and cache |

---

## Prerequisites

1. **Docker Desktop** running (for Firestore emulator + WireMock)
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
├── docker-compose.yml        Firestore emulator (8080) + WireMock 3.4.2 (8081)
│                             IndexingApi (8082, profile=phase3 — built from source)
│                             NavigationApi (8083, profile=phase4 — built from source)
│                             ProductsApi (8084, profile=phase4 — built from source)
│                             SearchApi (8085, profile=phase5 — no Firestore)
├── Makefile                  All orchestration commands
├── requirements.txt          pytest, pytest-json-report, pytest-html, google-cloud-firestore
├── pytest.ini                Test discovery config + markers (pythonpath = .)
├── fixtures/
│   ├── csv/                  Real de/DE CSV batch (17 files from NEO/data_input/)
│   └── mocks/                WireMock stub definitions
│       ├── sitecore-search/
│       │   ├── ingestion-update.json   PUT stub → {"enqueued":true,"incremental_update_id":"..."}
│       │   ├── ingestion-delete.json   DELETE stub → {"enqueued":true,"incremental_update_ids":[...]}
│       │   └── discovery-search.json   POST stub → SearchResults with 1 product (Phase 5)
│       ├── hybris/           (empty)
│       ├── sitecore-edge/    (empty — Phase 5)
│       └── idp/              (empty — Phase 5)
├── tests/
│   ├── conftest.py           Session fixtures: firestore_client, pipeline_result, clean_firestore
│   ├── pipeline/             Layer 1: ETL → Firestore (44 tests)
│   │   ├── test_pipeline_runs.py
│   │   ├── test_collections.py
│   │   └── test_document_structure.py
│   ├── sync/                 Layer 2: sync_product_index.py → products-index-updates (7 tests)
│   │   ├── _data.py          Shared constants + compute_hash()
│   │   ├── conftest.py       sync_result module fixture
│   │   └── test_sync_logic.py
│   ├── indexing/             Layer 4: IndexingApi → WireMock (5 tests)
│   │   ├── conftest.py       indexing_result module fixture
│   │   └── test_indexing_pipeline.py
│   └── services/             Layer 3: NavigationApi + ProductsApi + SearchApi HTTP tests (15 tests)
│       ├── navigation/
│       │   ├── conftest.py   navigation_result module fixture
│       │   └── test_navigation_api.py
│       ├── products/
│       │   ├── conftest.py   products_result module fixture
│       │   └── test_products_api.py
│       └── search/           Phase 5: SearchApi (no Firestore dependency)
│           ├── conftest.py   search_result module fixture (waits for SearchApi only)
│           └── test_search_api.py
├── scripts/
│   ├── wait_for_emulator.py  Generic service health-check poller (--host, --path, --timeout)
│   └── seed_config.py        Seeds configuration collection before Phase 4 services start
└── reports/                  Generated test output (gitignored)
```

---

## How the Tests Work

### Infrastructure

- Firestore emulator runs at `localhost:8080` (Docker)
- WireMock runs at `localhost:8081` (Docker, used from Phase 3 onwards)
- All tests set `FIRESTORE_EMULATOR_HOST=localhost:8080`

### Layer 1 — Pipeline (session-scoped)

Fixtures in `tests/conftest.py`:
- `firestore_client` — connects to the emulator (session-scoped)
- `pipeline_result` — clears the emulator, runs `main.py` via subprocess (session-scoped, ~10 min)
- `clean_firestore` — clears all collections after each test (function-scoped)

### Layer 2 — Sync (module-scoped)

Fixtures in `tests/sync/conftest.py`:
- `sync_result` — module-scoped. Clears `ProductIndexData` and `products-index-updates`,
  seeds 4 controlled documents, runs `sync_product_index.py --use-emulator --sync-database (default)`,
  yields `(CompletedProcess, firestore_client)`.

**Why `--sync-database (default)`:** The gcloud Firestore emulator only supports the
`(default)` database — named databases are not supported. Using `(default)` for both
main and sync databases is safe because the two collections (`ProductIndexData` and
`products-index-updates`) have distinct names.

**Test isolation:** sync tests run alphabetically after pipeline tests (`sync` > `pipeline`),
so clearing `ProductIndexData` at the start of `sync_result` does not affect pipeline
tests that have already completed.

**Fixture data:** 4 minimal in-memory documents with unrealistic BaseSKUs (10000–40000)
to avoid clashing with real fixture data. Constants live in `tests/sync/_data.py`.

### Layer 4 — Indexing (Phase 3 ✅)

5 tests in `tests/indexing/test_indexing_pipeline.py`. Requires `infra-phase3-up`.

Fixture in `tests/indexing/conftest.py` (`indexing_result`, module-scoped):
1. Clears `products-index-updates`
2. Seeds `IDX_0_de_DE` (operation=Update) + `IDX_1_de_DE` (operation=Delete)
3. Waits for IndexingApi `/health`
4. Resets WireMock request journal
5. Calls `GET /v1/indexing/products/initialize`
6. Fetches WireMock journal
7. Yields `(response, wiremock_requests, firestore_client)`

### Layer 3 — Services (Phase 4+5 ✅)

15 tests in `tests/services/`. Requires `infra-phase4-up` (Navigation + Products) and `infra-phase5-up` (SearchApi).

#### NavigationApi (5 tests in `tests/services/navigation/`)

Fixture `navigation_result` (module-scoped):
1. Clears `PLCategory`
2. Seeds NAV_PARENT (ID=9001, Language="de", Market="DE", MenuVisibility=True)
   and NAV_CHILD (ID=9002, ParentId=9001)
3. Waits for NavigationApi `/health` (localhost:8083)
4. Yields `(session, firestore_client)`

Tests: 200 for valid locale, CategoryMenuItems non-empty, required fields present,
Language/Market match de/DE, 400 for invalid locale format.

#### ProductsApi (5 tests in `tests/services/products/`)

Fixture `products_result` (module-scoped):
1. Clears `PLProductContent`, `PLVariant`, `PLCategory`
2. Seeds PLProductContent (SKU=PROD-001, de/DE), PLVariant (de/DE, FinishId=1),
   PLCategory (ID=5001, de/DE, MenuVisibility=True)
3. Waits for ProductsApi `/health` (localhost:8084)
4. Yields `(session, firestore_client)`

Tests: 200 for known SKU, SKU field in response, 404 for unknown SKU,
category endpoint 200/204, variants endpoint 200.

#### SearchApi (5 tests in `tests/services/search/`)

Fixture `search_result` (module-scoped):
1. Waits for SearchApi `/health` (localhost:8085)
2. Yields `session` (no Firestore — SearchApi has no Firestore dependency)

WireMock stub `fixtures/mocks/sitecore-search/discovery-search.json` intercepts
`POST /discover/v2/integration` and returns one product item.

Tests: health 200, POST /product/v1/search → 200 or 204, result items non-empty when 200,
missing `lang` → 400, POST /autosuggest/v1/suggest → 200 or 204.

---

## Test data

**Layer 1 — real CSV fixtures:**
- Known SKUs: `66838000`, `40806000`
- Known ProductIndexData IDs: `66838_0_de_DE`, `40806_0_de_DE`

**Layer 2 — seeded in-memory:**
- `PRODUCT_NEW_ID = "10000_0_de_DE"` — in ProductIndexData only → creates Update record
- `PRODUCT_CHANGED_ID = "20000_0_de_DE"` — hash mismatch → rewrites record
- `PRODUCT_UNCHANGED_ID = "30000_0_de_DE"` — hash matches → skipped
- `PRODUCT_DELETED_ID = "40000_0_de_DE"` — in sync only → sets operation=Delete

**Layer 4 — seeded in-memory:**
- `INDEXING_UPDATE_DOC_ID = "IDX_0_de_DE"` — operation=Update → PUT to Sitecore Search
- `INDEXING_DELETE_DOC_ID = "IDX_1_de_DE"` — operation=Delete → DELETE to Sitecore Search

**Layer 3 (Navigation) — seeded in-memory:**
- `NAV_PARENT_DOC_ID = "9001_de_DE"` — top-level category, MenuVisibility=True
- `NAV_CHILD_DOC_ID = "9002_de_DE"` — child of 9001, ParentId=9001

**Layer 3 (Products) — seeded in-memory:**
- `PRODUCT_DOC_ID = "PROD-001_de_DE"` — PLProductContent, SKU=PROD-001, CategoryIDs=[5001]
- `VARIANT_DOC_ID = "PROD-001_de_DE"` — PLVariant, one finish (Alpine White, FinishId=1)
- `CATEGORY_DOC_ID = "5001_de_DE"` — PLCategory, ID=5001, MenuVisibility=True

**Phase 5 (SearchApi) — no Firestore seeding, WireMock stub only:**
- WireMock stub returns `{"widgets":[{"rfk_id":"rfkid_7","content":[{"id":"PROD-001","name":"Test Product 001","base_sku":"PROD-001",...}],"total_item":1}]}`
- Source locale `"de_de"` mapped to source ID `"integration"` (appsettings.Integration.json)

---

## Reading Test Results (for Claude)

After `make fix-loop`, read `reports/results.json`:

```json
{
  "tests": [
    {
      "nodeid": "tests/services/navigation/test_navigation_api.py::TestNavigationApi::test_navigation_returns_200_for_valid_locale",
      "outcome": "failed",
      "call": {
        "longrepr": "AssertionError: Expected 200, got 500. Body: ..."
      }
    }
  ]
}
```

**Trace from test name to source file:**

| Test file | Covers | Likely root cause |
|---|---|---|
| `pipeline/test_pipeline_runs.py` | Pipeline exits + reports | `grohe-neo-data-loader/main.py` |
| `pipeline/test_collections.py` | Collection presence + IDs | `grohe-neo-data-loader/transformer.py`, `firestore_loader.py` |
| `pipeline/test_document_structure.py::TestPLProductContentStructure` | PLProductContent fields | `output_models/pl_product_content.py`, `transformer.py` |
| `pipeline/test_document_structure.py::TestProductIndexDataStructure` | ProductIndexData fields | `output_models/product_index_data.py`, `transformer.py` |
| `pipeline/test_document_structure.py::TestPLCategoryStructure` | PLCategory fields | `transformer.py` |
| `pipeline/test_document_structure.py::TestPLVariantStructure` | PLVariant fields | `transformer.py` |
| `sync/test_sync_logic.py::TestSyncLogic` | sync_product_index.py behaviour | `grohe-neo-data-loader/sync_product_index.py` |
| `indexing/test_indexing_pipeline.py::TestIndexingPipeline` | IndexingApi → Sitecore Search | `grohe-neo-services/GroheNeo.IndexingApi/` |
| `services/navigation/test_navigation_api.py::TestNavigationApi` | NavigationApi HTTP | `grohe-neo-services/GroheNeo.ProductsDynamicNavigationApi/` |
| `services/products/test_products_api.py::TestProductsApi` | ProductsApi HTTP | `grohe-neo-services/GroheNeo.ProductsApi/` |
| `services/search/test_search_api.py::TestSearchApi` | SearchApi HTTP | `grohe-neo-services/GroheNeo.SearchApi/` |

---

## The Automated Fix Loop

When Claude is given a task that touches the data-loader or its Firestore output:

1. Claude makes changes across the relevant repos
2. Claude runs the relevant layer:
   - `make test-sync` for sync-only changes (~15 sec)
   - `make fix-loop` for full pipeline + sync verification (~10-11 min)
3. Claude reads `reports/results.json`
4. If failures exist: Claude fixes code → re-runs from step 2
5. When all green: Claude summarises changes

---

## Timing

| Layer | Runtime | Notes |
|---|---|---|
| Layer 1 (pipeline) | ~10–11 min | ETL transform is CPU-bound (292k records → 17k products); subprocess timeout: 900s |
| Layer 2 (sync) | ~15 sec | Seeds 4 docs directly, no ETL; subprocess timeout: 120s |
| Layer 4 (indexing) | ~30 sec | Seeds 2 docs, calls IndexingApi, inspects WireMock journal |
| Layer 3 (services) | ~90 sec | Seeds minimal docs (Nav+Products), calls NavigationApi + ProductsApi + SearchApi |
| IndexingApi Docker build | ~5–10 min (first time) | Subsequent builds are cached |
| NavigationApi Docker build | ~2–3 min (first time) | No Chrome; subsequent builds cached |
| ProductsApi Docker build | ~15–20 min (first time) | Installs Chrome ~100MB; subsequent builds cached |
| SearchApi Docker build | ~2–3 min (first time) | No Chrome, no Firestore; subsequent builds cached |

---

## Windows Encoding (critical)

`firestore_loader.py` and `sync_product_index.py` print emoji to stdout. On Windows
(cp1252), this crashes the subprocess reader. Both conftest.py files fix this with:

- `env["PYTHONUTF8"] = "1"` — makes the child process write UTF-8
- `subprocess.run(..., encoding="utf-8")` — makes the parent read UTF-8

**Both are required.** If you see `UnicodeEncodeError` or `stdout=None` in test
failures, check that these are present in the relevant conftest.py.

---

## Adding New Tests

### New Firestore field (Layer 1)
```python
# tests/pipeline/test_document_structure.py → appropriate class
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

Add constants to `tests/sync/_data.py` if new product docs are needed, then:
```python
# tests/sync/test_sync_logic.py → TestSyncLogic
def test_new_behaviour(self, sync_result):
    proc, client = sync_result
    doc = client.collection("products-index-updates").document(PRODUCT_NEW_ID).get()
    assert doc.to_dict()["some_field"] == "expected_value"
```

If the new test requires a different seeding scenario, add it to the `sync_result`
fixture in `tests/sync/conftest.py`.

### New service endpoint test (Layer 3 / Phase 4)
```python
# tests/services/navigation/test_navigation_api.py or products equivalent
def test_new_endpoint_behaviour(self, navigation_result):
    session, client = navigation_result
    resp = session.get(f"http://{NAVIGATION_API_HOST}/neo/product/v1/...", params=...)
    assert resp.status_code == 200
```

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
- Database: `(default)` — the only database supported by the gcloud Firestore emulator
- `ProductIndexData` and `products-index-updates` both live in `(default)` for sync tests
- Collections are cleared before each pipeline and sync run (in respective conftest.py)
- Emulator state is lost when the container stops (`infra-down`)
- Port `8080` — do not run the real Firebase emulator on the same port

## IndexingApi Notes (Phase 3)

- Host port: `8082`; container internal port: `8080`
- Docker profile: `phase3` — only started with `docker compose --profile phase3 up -d`
- Build context: `../grohe-neo-services` (entire services monorepo — build is slow first time)
- Health endpoint: `GET http://localhost:8082/health` → HTTP 200
- Trigger endpoint: `GET http://localhost:8082/v1/indexing/products/initialize`
- Config override: `ASPNETCORE_ENVIRONMENT=Integration` loads `appsettings.Integration.json`
  (file lives in `grohe-neo-services/src/GroheNeo.IndexingApi/appsettings.Integration.json`)
- Connects to Firestore emulator via `FIRESTORE_EMULATOR_HOST=firestore-emulator:8080`
- Sends ingestion requests to WireMock at `http://wiremock:8080/ingestion/v1` (internal network)
- XMCloud Edge calls (for product detail URL) fail gracefully — service falls back to `/{locale}/product/`

**Critical — `EmulatorDetection` (already fixed):**
`FirestoreDbBuilder` in `FirestoreDataStorageService.cs` must have:
```csharp
builder.EmulatorDetection = Google.Api.Gax.EmulatorDetection.EmulatorOrProduction;
```
Without this line, the .NET Firestore SDK ignores `FIRESTORE_EMULATOR_HOST` and tries to
authenticate with real Google ADC — which doesn't exist in the container → HTTP 500 on
every request. The fix is already in `grohe-neo-services` (`FirestoreDataStorageService.cs:54`).
If this is ever reverted or a new Firestore service is added, this will break Phase 3 tests.

**Windows / Git Bash — `--path` argument expansion:**
`make wait-indexing-api` calls `wait_for_emulator.py --path /health`, but Git Bash
expands `/health` to `C:/Program Files/Git/health` before Python sees it → timeout error.
This does NOT affect the Python test conftest (it calls `_wait_for_indexing_api()` directly,
no shell). To check health manually on Windows, use:
```bash
MSYS_NO_PATHCONV=1 curl -s http://localhost:8082/health
```

## NavigationApi Notes (Phase 4)

- Host port: `8083`; container internal port: `8080`
- Docker profile: `phase4` — started with `docker compose --profile phase4 up -d`
- Build context: `../grohe-neo-services`; build time: ~2–3 min (first time, no Chrome)
- Health endpoint: `GET http://localhost:8083/health` → HTTP 200
- Main endpoint: `GET /neo/product/v1/category-navigation?locale=de-DE`
- Config override: `ASPNETCORE_ENVIRONMENT=Integration` loads `appsettings.Integration.json`
  (file: `grohe-neo-services/src/GroheNeo.ProductsDynamicNavigationApi/appsettings.Integration.json`)
- Cache backend: `Memory` (overridden in appsettings.Integration.json — avoids Firestore cache writes)
- Reads `configuration` collection at startup → needs `make seed-config` first
- Queries `PLCategory` filtered by Language/Market/MenuVisibility=true
- XMCloud call (`GetProductAndInspirationGuides`) fails gracefully — categories still returned

**Critical — EmulatorDetection must be present in 3 places:**
- `FirebaseConfigurationService.cs` (reads `configuration` collection at startup)
- `FireStoreDbResolver.cs` in NavigationApi (builds per-locale Firestore connections)
- `FireStoreDbResolver.cs` in ProductsApi (same)

**Configuration seeding:**
The `configuration` Firestore document must exist BEFORE the services start (they read
it at startup in `Program.cs`). `make seed-config` or `scripts/seed_config.py` inserts:
```python
{ "project_id": "demo-project", "database_de_de": "(default)", "fallback_locale": "de_de" }
```
Locale resolution: `locale=de-DE` → key `database_de_de` → `(default)` → all queries go
to the single emulator database.

## ProductsApi Notes (Phase 4)

- Host port: `8084`; container internal port: `8080`
- Docker profile: `phase4`
- Build time: ~15–20 min first time (installs Chrome v142 ~100MB + deps); subsequent builds cached
- Health endpoint: `GET http://localhost:8084/health` → HTTP 200
- Main endpoint: `GET /neo/product/v1/{sku}?locale=de-DE`
- Config override: `ASPNETCORE_ENVIRONMENT=Integration` loads `appsettings.Integration.json`
  (file: `grohe-neo-services/src/GroheNeo.ProductsApi/appsettings.Integration.json`)
- Cache backend: `Memory` (appsettings.Integration.json override)
- XMCloud calls routed to WireMock (`http://wiremock:8080`) — 404 → graceful fallback

## SearchApi Notes (Phase 5)

- Host port: `8085`; container internal port: `8080`
- Docker profile: `phase5` — started with `docker compose --profile phase5 up -d`
- Build time: ~2–3 min first time (no Chrome); subsequent builds cached
- Health endpoint: `GET http://localhost:8085/health` → HTTP 200
- Search endpoint: `POST /product/v1/search` — body: `{"lang":"de-de","q":"...","limit":N,"offset":0}`
- Autosuggest endpoint: `POST /autosuggest/v1/suggest` — body: `{"lang":"de-de","q":"..."}`
- Config override: `ASPNETCORE_ENVIRONMENT=Integration` loads `appsettings.Integration.json`
  (file: `grohe-neo-services/src/GroheNeo.SearchApi/appsettings.Integration.json`)
- **No Firestore dependency** — SearchApi calls only Sitecore Search Discovery API (WireMock)
  and XM Cloud (WireMock, returns 404, handled gracefully by Refit `ApiResponse<T>`)
- WireMock stub: `fixtures/mocks/sitecore-search/discovery-search.json` intercepts
  all `POST /discover/v2/integration` and returns 1 product item

**Language format:** SearchApi uses XM Cloud format `xx-xx` (5 chars) validated by regex.
`"de-de"` → maps internally to `"de_de"` → source `"integration"` → WireMock stub.
JSON request key is `"lang"` (not `"language"`), query key is `"q"` (not `"query"`).

**XM Cloud graceful fallback:** `IXmCloudService.GetVariantOrderingSettings` is a Refit
`ApiResponse<T>` — WireMock returns 404, `settings.Content` is null, mapper handles null.

**CrossApiServices override:** `CrossApiServicesSettings.Integration.json` (in
`GroheNeo.Feature.CrossApiServices/`) overrides `ApiServices.XmCloudApi.BaseAddress` to
`http://wiremock:8080` so Refit calls WireMock instead of GCP during integration tests.
This file is added to the `.csproj` with `CopyToOutputDirectory: Always`.

## WireMock Notes

- Host port: `8081`; container internal port: `8080`
- Mappings directory: `fixtures/mocks/` (mounted to `/home/wiremock/mappings`)
- Admin API: `http://localhost:8081/__admin/` — use for health check + request journal
- Request journal: `GET http://localhost:8081/__admin/requests` — inspect what was sent
- WireMock stub files (`.json`) go in the relevant `fixtures/mocks/{service}/` subdirectory
- Phase 3 stubs in `fixtures/mocks/sitecore-search/`:
  - `ingestion-update.json` — matches PUT to ingestion endpoint → 200 success
  - `ingestion-delete.json` — matches DELETE to ingestion endpoint → 200 success
- Phase 5 stubs in `fixtures/mocks/sitecore-search/`:
  - `discovery-search.json` — matches POST to `/discover/v2/integration` → 200 with 1 product
- Reset journal between test runs: `DELETE http://localhost:8081/__admin/requests`

**Hot-reload:** WireMock does NOT auto-reload stubs from disk while running. If a new stub
file is added while the container is already up, trigger a reload with:
```bash
curl -s -X POST http://localhost:8081/__admin/mappings/reset
```
This is not needed in normal workflow because `infra-phase5-up` starts WireMock fresh.
It is only needed if the stub file was created after the container was already running.
