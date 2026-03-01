# CLAUDE.md — Integration Test Harness

## Purpose

Cross-project integration tests for the Grohe NEO platform. Spins up a local
Firestore emulator and WireMock and validates behaviour across repos, organized
by feature rather than implementation phase.

**Batch A (6 features, 81 tests — all verified green)**

**data-loader ✅** ETL pipeline → Firestore state assertions — **44 passed** (tests/data-loader/etl/)
**data-loader ✅** Sync logic (`sync_product_index.py`) — **7 passed** (tests/data-loader/sync/)
**product-indexing ✅** IndexingApi → WireMock — **5 passed** (requires `infra-product-indexing-up`)
**dynamic-navigation ✅** NavigationApi HTTP tests — **5 passed** (requires `infra-dynamic-navigation-up`)
**pdp ✅** ProductsApi HTTP tests — **5 passed** (requires `infra-pdp-up`)
**search ✅** SearchApi HTTP tests — **5 passed** (requires `infra-search-up`, no Firestore seeding)
**project-list ✅** ProjectListsApi CRUD + PDF tests — **10 passed** (requires `infra-project-list-up`)

**Batch B (7 features — all active, 34 passed + 1 skip, verified 2026-03-01)**

**shopping-cart ✅** ShoppingCartApi HTTP tests — **5 passed** (tests/shopping-cart/, port 8087)
**pricing ✅** PricingApi HTTP tests — **5 passed** (tests/pricing/, port 8089)
**forms ✅** FormsApi form submission tests — **5 passed** (tests/forms/, port 8092)
**my-account ✅** UserApi HTTP tests — **5 passed** (tests/my-account/, port 8088)
**checkout ✅** OrderApi + PaymentApi tests — **5 passed** (tests/checkout/, ports 8090+8091)
**store-locator ✅** Store-locator job → Firestore — **4 passed + 1 skip** (tests/store-locator/)
**redirections ✅** Redirect reverse proxy HTTP tests — **5 passed** (tests/redirections/, port 8093)

---

## Quick Start

```bash
# 1. One-time setup (create virtualenv + install pytest deps)
make bootstrap          # copies .env.example → .env, creates venv, installs deps
# or just:
make setup

# 2a. Start core infrastructure (fast — always needed)
make infra-up           # Firestore emulator (8080) + WireMock (8081)

# 2b. Start Batch A feature-specific infrastructure (slow — builds .NET services from source)
make infra-product-indexing-up     # + IndexingApi (8082)
make infra-dynamic-navigation-up   # + NavigationApi (8083) — seeds config first
make infra-pdp-up                  # + ProductsApi (8084) — seeds config first
make infra-search-up               # + SearchApi (8085) — no Firestore seeding
make infra-project-list-up         # + ProductsApi (8084) + ProjectListsApi (8086)

# 2c. Start Batch B feature infrastructure (requires service added to docker-compose.yml first)
make infra-shopping-cart-up        # + ShoppingCartApi (8087)
make infra-my-account-up           # + UserApi (8088)
make infra-pricing-up              # + PricingApi (8089)
make infra-checkout-up             # + OrderApi (8090)
make infra-forms-up                # + FormsApi (8092)
make infra-store-locator-up        # runs one-shot job → populates stores-index-updates
make infra-redirections-up         # + redirect reverse proxy (8093)

# 3. Run tests
make test-data-loader          # ETL pipeline + sync (~10-11 min + 15s)
make test-product-indexing     # IndexingApi → WireMock (~30s)
make test-dynamic-navigation   # NavigationApi HTTP (~60s)
make test-pdp                  # ProductsApi HTTP (~60s)
make test-search               # SearchApi HTTP (~30s)
make test-project-list         # ProjectListsApi CRUD + PDF (~60s)
# Batch B (skip gracefully if service not running):
make test-shopping-cart        # ShoppingCartApi HTTP
make test-my-account           # UserApi HTTP
make test-pricing              # PricingApi HTTP
make test-checkout             # OrderApi + Adyen
make test-forms                # FormsApi form submission
make test-store-locator        # Store-locator → Firestore
make test-redirections         # Redirect proxy HTTP
make test-all                  # All features (Batch B skips if unavailable)

# 4. Stop containers when done
make infra-down
make infra-product-indexing-down
make infra-dynamic-navigation-down
make infra-pdp-down
make infra-search-down
make infra-project-list-down
make infra-shopping-cart-down
make infra-my-account-down
make infra-pricing-down
make infra-checkout-down
make infra-forms-down
make infra-redirections-down
```

---

## Full Command Reference

| Command | What it does |
|---|---|
| `make bootstrap` | First-time setup: venv + deps + `.env` from template |
| `make setup` | Create `.venv` and install test dependencies |
| `make infra-up` | Start Firestore emulator + WireMock via Docker Compose |
| `make infra-down` | Stop core Docker containers |
| `make wait` | Wait until emulator responds (health check) |
| `make seed-config` | Seed Firestore `configuration` collection (required for navigation + pdp) |
| `make infra-product-indexing-up` | Build + start IndexingApi (8082) |
| `make infra-product-indexing-down` | Stop product-indexing containers |
| `make wait-indexing-api` | Wait until IndexingApi /health responds |
| `make infra-dynamic-navigation-up` | Seed config + build + start NavigationApi (8083) |
| `make infra-dynamic-navigation-down` | Stop dynamic-navigation containers |
| `make wait-navigation-api` | Wait until NavigationApi /health responds |
| `make infra-pdp-up` | Seed config + build + start ProductsApi (8084) |
| `make infra-pdp-down` | Stop pdp containers |
| `make wait-products-api` | Wait until ProductsApi /health responds |
| `make infra-search-up` | Build + start SearchApi (8085) — no Firestore seeding |
| `make infra-search-down` | Stop search containers |
| `make wait-search-api` | Wait until SearchApi /health responds |
| `make infra-project-list-up` | Seed config + build + start ProductsApi + ProjectListsApi (8084+8086) |
| `make infra-project-list-down` | Stop project-list containers |
| `make wait-project-lists-api` | Wait until ProjectListsApi /health responds |
| `make infra-shopping-cart-up` | Build + start ShoppingCartApi (8087) |
| `make infra-shopping-cart-down` | Stop shopping-cart containers |
| `make infra-my-account-up` | Build + start UserApi (8088) |
| `make infra-my-account-down` | Stop my-account containers |
| `make infra-pricing-up` | Build + start PricingApi (8089) |
| `make infra-pricing-down` | Stop pricing containers |
| `make infra-checkout-up` | Build + start OrderApi + PaymentApi (8090+8091) |
| `make infra-checkout-down` | Stop checkout containers |
| `make infra-forms-up` | Build + start FormsApi (8092) |
| `make infra-forms-down` | Stop forms containers |
| `make infra-store-locator-up` | Run store-locator one-shot job → populates stores-index-updates |
| `make infra-redirections-up` | Build + start redirect reverse proxy (8093) |
| `make infra-redirections-down` | Stop redirections containers |
| `make test-data-loader` | data-loader ETL + sync → `reports/data-loader.json` |
| `make test-product-indexing` | IndexingApi → WireMock → `reports/product-indexing.json` |
| `make test-dynamic-navigation` | NavigationApi HTTP → `reports/dynamic-navigation.json` |
| `make test-pdp` | ProductsApi HTTP → `reports/pdp.json` |
| `make test-search` | SearchApi HTTP → `reports/search.json` |
| `make test-project-list` | ProjectListsApi CRUD + PDF → `reports/project-list.json` |
| `make test-shopping-cart` | ShoppingCartApi HTTP → `reports/shopping-cart.json` |
| `make test-my-account` | UserApi HTTP → `reports/my-account.json` |
| `make test-pricing` | PricingApi HTTP → `reports/pricing.json` |
| `make test-checkout` | OrderApi + Adyen → `reports/checkout.json` |
| `make test-forms` | FormsApi form submission → `reports/forms.json` |
| `make test-store-locator` | Store-locator → Firestore → `reports/store-locator.json` |
| `make test-redirections` | Redirect proxy HTTP → `reports/redirections.json` |
| `make test-all` | All features (Batch B skips gracefully) → `reports/results.json` |
| `make fix-loop` | Run all tests + emit `reports/results.json` (test agent entry point) |
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
│                             IndexingApi (8082, profile=product-indexing)
│                             NavigationApi (8083, profile=dynamic-navigation)
│                             ProductsApi (8084, profile=pdp,project-list)
│                             SearchApi (8085, profile=search)
│                             ProjectListsApi (8086, profile=project-list)
├── Makefile                  All orchestration commands
├── .env.example              Template for .env (committed) — SITECORE_MODE etc.
├── requirements.txt          pytest, pytest-json-report, pytest-html, google-cloud-firestore
├── pytest.ini                Test discovery config (pythonpath = .)
├── reports/                  Generated test output (gitignored except .gitkeep)
│   ├── results.json          pytest-json-report output (gitignored — generated)
│   └── *.json                per-feature test reports (gitignored — generated)
├── fixtures/
│   ├── csv/                  Real de/DE CSV batch (17 files from NEO/data_input/)
│   └── mocks/                WireMock stub definitions (one subdir per external system)
│       ├── sitecore-search/  Ingestion + Discovery stubs
│       ├── sitecore-edge/    GraphQL layout + dictionary stubs
│       ├── project-lists/    XMCloud OAuth + GraphQL stubs (phase 6)
│       ├── hybris/           Cart, user, pricing, order stubs
│       ├── adyen/            Payment + 3DS stubs
│       ├── mulesoft/         CRM form submission stubs
│       ├── google-places/    Autocomplete stubs
│       ├── recaptcha/        Verify endpoint stubs
│       └── idp/              OIDC stubs for local dev + service-to-service auth
├── tests/
│   ├── conftest.py           Session fixtures: firestore_client, pipeline_result, clean_firestore
│   ├── data-loader/          data-loader feature tests
│   │   ├── etl/              ETL pipeline → Firestore (44 tests, ~10-11 min)
│   │   │   ├── test_pipeline_runs.py
│   │   │   ├── test_collections.py
│   │   │   └── test_document_structure.py
│   │   └── sync/             sync_product_index.py → products-index-updates (7 tests, ~15s)
│   │       ├── _data.py      Shared constants + compute_hash()
│   │       ├── conftest.py   sync_result module fixture
│   │       └── test_sync_logic.py
│   ├── product-indexing/     IndexingApi → WireMock (5 tests, ~30s)
│   │   ├── conftest.py       indexing_result module fixture
│   │   └── test_indexing_pipeline.py
│   ├── dynamic-navigation/   NavigationApi HTTP tests (5 tests, ~60s)
│   │   ├── conftest.py       navigation_result module fixture
│   │   └── test_navigation_api.py
│   ├── pdp/                  ProductsApi HTTP tests (5 tests, ~60s)
│   │   ├── conftest.py       products_result module fixture
│   │   └── test_products_api.py
│   ├── search/               SearchApi HTTP tests (5 tests, ~30s)
│   │   ├── conftest.py       search_result module fixture (no Firestore)
│   │   └── test_search_api.py
│   ├── project-list/         ProjectListsApi CRUD + PDF (10 tests, ~60s)
│   │   ├── conftest.py       project_lists_result module fixture
│   │   └── test_project_lists_api.py
│   ├── shopping-cart/        ✅ ShoppingCartApi HTTP tests (skips if unavailable)
│   │   ├── conftest.py       shopping_cart_result module fixture
│   │   └── test_shopping_cart_api.py
│   ├── my-account/           ✅ UserApi HTTP tests (skips if unavailable)
│   │   ├── conftest.py       user_result module fixture
│   │   └── test_user_api.py
│   ├── pricing/              ✅ PricingApi HTTP tests (skips if unavailable)
│   │   ├── conftest.py       pricing_result module fixture
│   │   └── test_pricing_api.py
│   ├── checkout/             ✅ OrderApi + PaymentApi tests (skips if unavailable)
│   │   ├── conftest.py       checkout_result module fixture
│   │   └── test_checkout_api.py
│   ├── forms/                ✅ FormsApi form submission tests (skips if unavailable)
│   │   ├── conftest.py       forms_result module fixture
│   │   └── test_forms_api.py
│   ├── store-locator/        ✅ Store-locator job Firestore tests (skips if collection empty)
│   │   ├── conftest.py       store_locator_result module fixture
│   │   └── test_store_locator.py
│   └── redirections/         ✅ Redirect proxy HTTP tests (skips if unavailable)
│       ├── conftest.py       redirections_result module fixture
│       └── test_redirections.py
├── scripts/
│   ├── wait_for_emulator.py  Generic service health-check poller
│   └── seed_config.py        Seeds configuration collection (required for navigation+pdp)
└── reports/                  Generated test output (gitignored except .md templates)
```

---

## How the Tests Work

### Infrastructure

- Firestore emulator runs at `localhost:8080` (Docker)
- WireMock runs at `localhost:8081` (Docker, used by all service tests)
- All tests set `FIRESTORE_EMULATOR_HOST=localhost:8080`

### data-loader/etl — ETL Pipeline (session-scoped)

Fixtures in `tests/conftest.py`:
- `firestore_client` — connects to the emulator (session-scoped)
- `pipeline_result` — clears the emulator, runs `main.py` via subprocess (session-scoped, ~10 min)
- `clean_firestore` — clears all collections after each test (function-scoped)

### data-loader/sync — Sync Logic (module-scoped)

Fixtures in `tests/data-loader/sync/conftest.py`:
- `sync_result` — module-scoped. Clears `ProductIndexData` and `products-index-updates`,
  seeds 4 controlled documents, runs `sync_product_index.py --use-emulator --sync-database (default)`,
  yields `(CompletedProcess, firestore_client)`.

### product-indexing (module-scoped)

5 tests in `tests/product-indexing/test_indexing_pipeline.py`. Requires `infra-product-indexing-up`.

Fixture in `tests/product-indexing/conftest.py` (`indexing_result`, module-scoped):
1. Clears `products-index-updates`
2. Seeds `IDX_0_de_DE` (operation=Update) + `IDX_1_de_DE` (operation=Delete)
3. Waits for IndexingApi `/health`
4. Resets WireMock request journal
5. Calls `GET /v1/indexing/products/initialize`
6. Fetches WireMock journal
7. Yields `(response, wiremock_requests, firestore_client)`

### dynamic-navigation (module-scoped)

5 tests in `tests/dynamic-navigation/test_navigation_api.py`. Requires `infra-dynamic-navigation-up`.

Fixture `navigation_result` (module-scoped):
1. Clears `PLCategory`
2. Seeds NAV_PARENT (ID=9001, Language="de", Market="DE", MenuVisibility=True)
   and NAV_CHILD (ID=9002, ParentId=9001)
3. Waits for NavigationApi `/health` (localhost:8083)
4. Yields `(session, firestore_client)`

### pdp (module-scoped)

5 tests in `tests/pdp/test_products_api.py`. Requires `infra-pdp-up`.

Fixture `products_result` (module-scoped):
1. Clears `PLProductContent`, `PLVariant`, `PLCategory`
2. Seeds PLProductContent (SKU=PROD-001, de/DE), PLVariant (de/DE, FinishId=1),
   PLCategory (ID=5001, de/DE, MenuVisibility=True)
3. Waits for ProductsApi `/health` (localhost:8084)
4. Yields `(session, firestore_client)`

### search (module-scoped)

5 tests in `tests/search/test_search_api.py`. Requires `infra-search-up`.

Fixture `search_result` (module-scoped):
1. Waits for SearchApi `/health` (localhost:8085)
2. Yields `session` (no Firestore — SearchApi has no Firestore dependency)

### project-list (module-scoped)

10 tests in `tests/project-list/test_project_lists_api.py`. Requires `infra-project-list-up`.

---

## Test data

**data-loader/etl — real CSV fixtures:**
- Known SKUs: `66838000`, `40806000`
- Known ProductIndexData IDs: `66838_0_de_DE`, `40806_0_de_DE`

**data-loader/sync — seeded in-memory:**
- `PRODUCT_NEW_ID = "10000_0_de_DE"` — in ProductIndexData only → creates Update record
- `PRODUCT_CHANGED_ID = "20000_0_de_DE"` — hash mismatch → rewrites record
- `PRODUCT_UNCHANGED_ID = "30000_0_de_DE"` — hash matches → skipped
- `PRODUCT_DELETED_ID = "40000_0_de_DE"` — in sync only → sets operation=Delete

**product-indexing — seeded in-memory:**
- `INDEXING_UPDATE_DOC_ID = "IDX_0_de_DE"` — operation=Update → PUT to Sitecore Search
- `INDEXING_DELETE_DOC_ID = "IDX_1_de_DE"` — operation=Delete → DELETE to Sitecore Search

**dynamic-navigation — seeded in-memory:**
- `NAV_PARENT_DOC_ID = "9001_de_DE"` — top-level category, MenuVisibility=True
- `NAV_CHILD_DOC_ID = "9002_de_DE"` — child of 9001, ParentId=9001

**pdp — seeded in-memory:**
- `PRODUCTS_CONTENT_DOC_ID = "PROD-001_de_DE"` — PLProductContent, SKU=PROD-001
- `PRODUCTS_VARIANT_DOC_ID = "PROD_0_de_DE"` — PLVariant, one finish (Alpine White)
- `PRODUCTS_CATEGORY_DOC_ID = "5001_de_DE"` — PLCategory, ID=5001, MenuVisibility=True

**search — no Firestore seeding, WireMock stub only:**
- WireMock stub returns one product item for `POST /discover/v2/integration`
- Source locale `"de_de"` mapped to source ID `"integration"` (appsettings.Integration.json)

**project-list — seeded in-memory, real ProductsApi for PDF:**
- `SEEDED_LIST_ID = "integration-test-list-001"` — used for read/update/PDF tests
- `SEEDED_DELETE_ID = "integration-test-list-002"` — deleted by test 9
- PDF test requires ETL data: run `make test-data-loader` before `make test-project-list`

---

## Reading Test Results (for the test agent)

After `make fix-loop`, read `reports/results.json`:

```json
{
  "tests": [
    {
      "nodeid": "tests/dynamic-navigation/test_navigation_api.py::TestNavigationApi::test_navigation_returns_200_for_valid_locale",
      "outcome": "failed",
      "call": {
        "longrepr": "AssertionError: Expected 200, got 500. Body: ..."
      }
    }
  ]
}
```

**Trace from test name to source file:**

| Test file | Feature | Covers | Likely root cause in source |
|---|---|---|---|
| `data-loader/etl/test_pipeline_runs.py` | data-loader | Pipeline exits + reports | `grohe-neo-data-loader/main.py` |
| `data-loader/etl/test_collections.py` | data-loader | Collection presence + IDs | `grohe-neo-data-loader/transformer.py`, `firestore_loader.py` |
| `data-loader/etl/test_document_structure.py::TestPLProductContentStructure` | data-loader | PLProductContent fields | `output_models/pl_product_content.py`, `transformer.py` |
| `data-loader/etl/test_document_structure.py::TestProductIndexDataStructure` | data-loader | ProductIndexData fields | `output_models/product_index_data.py`, `transformer.py` |
| `data-loader/etl/test_document_structure.py::TestPLCategoryStructure` | data-loader | PLCategory fields | `transformer.py` |
| `data-loader/etl/test_document_structure.py::TestPLVariantStructure` | data-loader | PLVariant fields | `transformer.py` |
| `data-loader/sync/test_sync_logic.py::TestSyncLogic` | data-loader | sync_product_index.py | `grohe-neo-data-loader/sync_product_index.py` |
| `product-indexing/test_indexing_pipeline.py::TestIndexingPipeline` | product-indexing | IndexingApi → Sitecore | `grohe-neo-services/GroheNeo.IndexingApi/` |
| `dynamic-navigation/test_navigation_api.py::TestNavigationApi` | dynamic-navigation | NavigationApi HTTP | `grohe-neo-services/GroheNeo.ProductsDynamicNavigationApi/` |
| `pdp/test_products_api.py::TestProductsApi` | pdp | ProductsApi HTTP | `grohe-neo-services/GroheNeo.ProductsApi/` |
| `search/test_search_api.py::TestSearchApi` | search | SearchApi HTTP | `grohe-neo-services/GroheNeo.SearchApi/` |
| `project-list/test_project_lists_api.py::TestProjectListsApi` | project-list | ProjectListsApi HTTP | `grohe-neo-services/GroheNeo.ProjectListsApi/` |
| `shopping-cart/test_shopping_cart_api.py::TestShoppingCartApi` | shopping-cart | ShoppingCartApi + Hybris cart | `grohe-neo-services/GroheNeo.ShoppingCartApi/` |
| `my-account/test_user_api.py::TestUserApi` | my-account | UserApi + Hybris user + Google Places | `grohe-neo-services/GroheNeo.UserApi/` |
| `pricing/test_pricing_api.py::TestPricingApi` | pricing | PricingApi + Hybris pricing | `grohe-neo-services/GroheNeo.PricingApi/` |
| `checkout/test_checkout_api.py::TestCheckoutApi` | checkout | OrderApi + Adyen payment | `grohe-neo-services/GroheNeo.OrderApi/` |
| `forms/test_forms_api.py::TestFormsApi` | forms | FormsApi + Mulesoft + reCAPTCHA | `grohe-neo-services/GroheNeo.FormsApi/` |
| `store-locator/test_store_locator.py::TestStoreLocator` | store-locator | Store-locator job → Firestore | `grohe-neo-services/GroheNeo.StoreLocatorJob/` |
| `redirections/test_redirections.py::TestRedirections` | redirections | Redirect proxy + Sitecore Edge | `grohe-neo-services/GroheNeo.RedirectReverseProxy/` |

---

## The Automated Fix Loop (multi-agent workflow)

See `../agents/README.md` for the full two-agent workflow. Handoff files live in `../reports/`.

1. Human writes `../reports/current-task.md`
2. **Dev agent** (grohe-neo-services/ or grohe-neo-data-loader/): reads task + feature doc + test-findings → implements → writes `../reports/dev-complete.md`
3. **Test agent** (integration/): reads `../reports/dev-complete.md` → runs `make fix-loop` → reads `reports/results.json` → writes `../reports/test-findings.md`
4. If failures: dev agent reads test-findings → fixes → loop
5. If all green: human reviews PR

**Agent startup** (from each agent's working directory):
- Dev: `/read ../agents/dev-agent.md` then `/read ../reports/current-task.md`
- Test: `/read ../agents/test-agent.md` then `/read ../reports/dev-complete.md`

---

## Timing

| Feature | Runtime | Notes |
|---|---|---|
| data-loader/etl (pipeline) | ~10–11 min | ETL transform is CPU-bound; subprocess timeout: 900s |
| data-loader/sync | ~15 sec | Seeds 4 docs directly, no ETL; subprocess timeout: 120s |
| product-indexing | ~30 sec | Seeds 2 docs, calls IndexingApi, inspects WireMock journal |
| dynamic-navigation | ~60 sec | Seeds minimal docs, calls NavigationApi |
| pdp | ~60 sec | Seeds minimal docs, calls ProductsApi |
| search | ~30 sec | No Firestore; calls SearchApi → WireMock |
| project-list | ~60 sec | Seeds 2 docs, CRUD + PDF generation |
| IndexingApi Docker build | ~5–10 min (first time) | Subsequent builds cached |
| NavigationApi Docker build | ~2–3 min (first time) | No Chrome; subsequent builds cached |
| ProductsApi Docker build | ~15–20 min (first time) | Installs Chrome ~100MB; subsequent builds cached |
| SearchApi Docker build | ~2–3 min (first time) | No Chrome, no Firestore; subsequent builds cached |
| ProjectListsApi Docker build | ~15–20 min (first time) | Installs Chrome ~100MB; subsequent builds cached |
| shopping-cart | ~30 sec | HTTP tests; Hybris cart stubs via WireMock |
| my-account | ~30 sec | HTTP tests; Hybris user + Google Places stubs via WireMock |
| pricing | ~30 sec | HTTP tests; Hybris pricing stubs via WireMock |
| checkout | ~60 sec | HTTP tests; Hybris order + Adyen stubs via WireMock |
| forms | ~30 sec | HTTP tests; Mulesoft + reCAPTCHA stubs via WireMock |
| store-locator | ~30 sec | Firestore assertions; requires job to have run first |
| redirections | ~30 sec | HTTP tests; Sitecore Edge stubs via WireMock |

---

## Windows Encoding (critical)

`firestore_loader.py` and `sync_product_index.py` print emoji to stdout. On Windows
(cp1252), this crashes the subprocess reader. Both conftest.py files fix this with:

- `env["PYTHONUTF8"] = "1"` — makes the child process write UTF-8
- `subprocess.run(..., encoding="utf-8")` — makes the parent read UTF-8

**Both are required.** If you see `UnicodeEncodeError` or `stdout=None` in test
failures, check that these are present in the relevant conftest.py.

---

## SITECORE_MODE

Set `SITECORE_MODE` in `.env` to control where Sitecore calls go:

```env
SITECORE_MODE=mock      # (default) — all Sitecore calls go to WireMock
SITECORE_MODE=qa        # real Sitecore QA environment
SITECORE_MODE=uat       # real Sitecore UAT environment
SITECORE_MODE=prod      # real Sitecore PROD environment (read-only)
```

When `SITECORE_MODE=mock`, the services use `http://wiremock:8080` for all Sitecore calls
and the WireMock stubs in `fixtures/mocks/sitecore-edge/` provide the responses.
When `SITECORE_MODE=qa`, the services call the real Sitecore Edge with credentials
from `SITECORE_EDGE_CONTEXT_ID` and `SITECORE_EDGE_API_KEY` (set in `.env`).

---

## Adding New Tests

### New Firestore field (data-loader/etl)
```python
# tests/data-loader/etl/test_document_structure.py → appropriate class
def test_has_sustainability_label(self):
    assert "SustainabilityLabel" in self._doc
```

### New sync behaviour (data-loader/sync)
```python
# tests/data-loader/sync/test_sync_logic.py → TestSyncLogic
def test_new_behaviour(self, sync_result):
    proc, client = sync_result
    doc = client.collection("products-index-updates").document(PRODUCT_NEW_ID).get()
    assert doc.to_dict()["some_field"] == "expected_value"
```

### New service endpoint (feature tests)
```python
# tests/dynamic-navigation/test_navigation_api.py (or equivalent)
def test_new_endpoint_behaviour(self, navigation_result):
    session, client = navigation_result
    resp = session.get(f"http://{NAVIGATION_API_HOST}/neo/product/v1/...", params=...)
    assert resp.status_code == 200
```

### New Batch B feature
Follow the pattern in `tests/shopping-cart/`, `tests/my-account/` etc.:
1. Add service to `docker-compose.yml` with the right profile
2. Add `fixtures/mocks/<system>/<feature>-*.json` WireMock stubs
3. Add `tests/<feature>/conftest.py` with module-scoped fixture
4. Add `tests/<feature>/test_<feature>_api.py` with 5–10 HTTP assertion tests
5. Add `make infra-<feature>-up/down` and `make test-<feature>` targets to Makefile

---

## Updating CSV Fixtures

```bash
cp ../data_input/*.csv fixtures/csv/
```
Then re-run `make test-data-loader` to confirm nothing broke.

---

## Emulator Notes

- Project ID: `demo-project` (hardcoded, emulator doesn't validate)
- Database: `(default)` — the only database supported by the gcloud Firestore emulator
- Collections are cleared before each pipeline and sync run (in respective conftest.py)
- Emulator state is lost when the container stops (`infra-down`)
- Port `8080` — do not run the real Firebase emulator on the same port

## IndexingApi Notes (product-indexing)

- Host port: `8082`; container internal port: `8080`
- Docker profile: `product-indexing`
- Health endpoint: `GET http://localhost:8082/health` → HTTP 200
- Trigger endpoint: `GET http://localhost:8082/v1/indexing/products/initialize`
- Config: `ASPNETCORE_ENVIRONMENT=Integration` loads `appsettings.Integration.json`
  (file: `grohe-neo-services/src/GroheNeo.IndexingApi/appsettings.Integration.json`)

**Critical — `EmulatorDetection` (already fixed):**
`FirestoreDbBuilder` in `FirestoreDataStorageService.cs` must have:
```csharp
builder.EmulatorDetection = Google.Api.Gax.EmulatorDetection.EmulatorOrProduction;
```

## NavigationApi Notes (dynamic-navigation)

- Host port: `8083`; container internal port: `8080`
- Docker profile: `dynamic-navigation`
- Health endpoint: `GET http://localhost:8083/health` → HTTP 200
- Reads `configuration` collection at startup → needs `make seed-config` first

**Critical — EmulatorDetection must be present in 3 places:**
- `FirebaseConfigurationService.cs`
- `FireStoreDbResolver.cs` in NavigationApi
- `FireStoreDbResolver.cs` in ProductsApi

## ProductsApi Notes (pdp)

- Host port: `8084`; container internal port: `8080`
- Docker profile: `pdp` (also `project-list` for PDF generation)
- Build time: ~15–20 min first time (installs Chrome v142 ~100MB + deps)
- Health endpoint: `GET http://localhost:8084/health` → HTTP 200
- Config: `ASPNETCORE_ENVIRONMENT=Integration` loads `appsettings.Integration.json`
  (file: `grohe-neo-services/src/GroheNeo.ProductsApi/appsettings.Integration.json`)

## SearchApi Notes (search)

- Host port: `8085`; container internal port: `8080`
- Docker profile: `search`
- Health endpoint: `GET http://localhost:8085/health` → HTTP 200
- **No Firestore dependency** — calls only Sitecore Search Discovery API (WireMock)
- Language format: `xx-xx` (5 chars), e.g. `"de-de"` → maps to source `"integration"`
- JSON request keys: `"lang"` (not `"language"`), `"q"` (not `"query"`)

## ProjectListsApi Notes (project-list)

- Host port: `8086`; container internal port: `8080`
- Docker profile: `project-list`
- Build time: ~15–20 min first time (installs Chrome v142 ~100MB + deps)
- Health endpoint: `GET http://localhost:8086/health` → HTTP 200
- Firestore collection: `project-lists` (PascalCase field names)
- `seed_config.py` IS required — ProductsApi reads `configuration` at startup
- PDF test requires ETL data in Firestore (run `make test-data-loader` first)
- JWT: unsigned fake JWT, no "Bearer " prefix — service strips "OndusBearer" prefix

## WireMock Notes

- Host port: `8081`; container internal port: `8080`
- Mappings directory: `fixtures/mocks/` (mounted to `/home/wiremock/mappings`)
- Admin API: `http://localhost:8081/__admin/` — health check + request journal
- Request journal: `GET http://localhost:8081/__admin/requests`
- Reset journal: `DELETE http://localhost:8081/__admin/requests`
- Hot-reload: `curl -s -X POST http://localhost:8081/__admin/mappings/reset`

**`urlPattern` requires `.*` suffix for URLs with query params:**
```json
"urlPattern": "^/neo/product/v1/PROD-001.*"
```

## ShoppingCartApi Notes (shopping-cart)

- Host port: `8087`; Docker profile: `shopping-cart`
- Health endpoint: `GET http://localhost:8087/health` → HTTP 200
- Hybris stubs: `fixtures/mocks/hybris/cart-*.json` (patterns: `^/[^/]+/users/...` — NO `/rest/v2` prefix!)
- Routes: `GET /neo/cart/v1/detail`, `POST /neo/cart/v1/addEntry`, `DELETE /neo/cart/v1/delete`
- Anonymous + no cartId: `GET /detail` → 200 empty cart; `POST /addEntry` → creates cart then adds entry (returns `cartId`); `DELETE /delete` → 400
- Anonymous + cartId: `DELETE /delete` → calls Hybris delete → 200
- WireMock token stub (`hybris-token.json`) required: ShoppingCartService calls `ITokenApi.GetToken()` even for anonymous requests
- `INTEGRATION_TEST_MODE=true` env var required in docker-compose (bypasses GoogleIdTokenHandler GCP metadata call)

## UserApi Notes (my-account)

- Host port: `8088`; Docker profile: `my-account`
- Health endpoint: `GET http://localhost:8088/health` → HTTP 200
- Hybris stubs: `fixtures/mocks/hybris/user-addresses.json`
- Google Places stubs: `fixtures/mocks/google-places/autocomplete.json`
- Tests: get profile, address CRUD, address autocomplete

## PricingApi Notes (pricing)

- Host port: `8089`; Docker profile: `pricing`
- Health endpoint: `GET http://localhost:8089/health` → HTTP 200
- **Route**: `GET /neo/product/v1/price` (NOT `/neo/pricing/v1/price`)
- Hybris stubs: `fixtures/mocks/hybris/pricing-get.json` (pattern: `^/[^/]+/users/[^/]+/products/prices.*`, NO `/rest/v2` prefix)
- WireMock stub response shape: `{products: [{code, currencyIso, originalPrice, userPrice, ...}]}`
- **JWT behavior**: non-JWT Bearer tokens → 401 (service tries `ReadJwtToken()`, fails, userId empty)
- `useMock=true` query param: bypasses JWT + Hybris, returns from in-memory MockPricingApi dict (SKU "36456000")
- Tests: health, anonymous price fetch (WireMock, SKU "40806000"), 401 for invalid JWT, useMock=true, cache repeat
- `INTEGRATION_TEST_MODE=true` env var required in docker-compose

## OrderApi / CheckoutApi Notes (checkout)

- Host port: `8090` (OrderApi); `8091` (PaymentApi); Docker profile: `checkout`
- Health endpoint: `GET http://localhost:8090/health` → HTTP 200
- Hybris stubs: `fixtures/mocks/hybris/order-history.json`, `order-detail.json`
- Tests: health, order history (GET /v1/orders), order detail (GET /v1/orders/{id}), PaymentApi health, payment methods
- **Critical — WireMock stub must include empty arrays**: `GetOrderMapper` calls `.Any()` on
  `Consignments`, `Invoices`, `AppliedVouchers`, and `Images` — all must be `[]` (not absent) or you get 500
- **Field rename**: Hybris `code` → NEO `orderId` — test assertions must use `body.get("orderId")`
- **URL pattern must allow `?fields=FULL`**: use `"urlPattern": "^/[^/]+/users/[^/]+/orders/[^/?]+(\\?.*)?$"`

## FormsApi Notes (forms)

- Host port: `8092`; Docker profile: `forms`
- Health endpoint: `GET http://localhost:8092/health` → HTTP 200
- Mulesoft stubs: `fixtures/mocks/mulesoft/contact-form.json`, `quote-form.json`
- reCAPTCHA stubs: `fixtures/mocks/recaptcha/verify-success.json`
- Base path: `/neo/forms/v1`
- Tests: contact form, quote form, reCAPTCHA validation, missing field validation

## Store-Locator Notes (store-locator)

- Runs as a **one-shot job** (not a persistent service) — `docker compose --profile store-locator run --rm store-locator-job`
- Writes to Firestore collection `stores-index-updates`
- Tests skip if the collection is empty (job hasn't run)
- Run `make infra-store-locator-up` to execute the job and populate the collection
- Tests: collection populated, required fields, valid operation type, document size < 900KB
- **EmulatorDetection required** (now fixed in `DependencyInjectionExtensions.cs`)
- **Config loading**: DI only loads `appsettings.json` + `appsettings.Development.json` (NOT Integration.json).
  Firestore config must be passed via `FIRESTORE__SOURCE__PROJECTID` and `FIRESTORE__SOURCE__DATABASEID` env vars
  (double underscore = .NET config section separator)

## Redirect Reverse Proxy Notes (redirections)

- Host port: `8093`; Docker profile: `redirections`
- Health endpoint: `GET http://localhost:8093/health` → HTTP 200
- Sitecore Edge stubs: `fixtures/mocks/sitecore-edge/graphql-layout.json`
- Test paths: `/de-de/old-product-url` (redirect), `/de-de/this-url-does-not-exist` (404/passthrough)
- Tests run with `allow_redirects=False` to assert the 301/302 response directly
- **Critical — `AcceptedHosts` must include all client Host headers**:
  `DomainAndLocaleConsolidationMiddleware` issues 301 if request Host is not in `AcceptedHosts`.
  Docker healthcheck sends `localhost:8080`; Python tests send `localhost:8093`.
  docker-compose must have `AcceptedHosts: "localhost|localhost:8080|localhost:8093"`
- **EmulatorDetection required** (now fixed in `DependencyInjectionExtensions.cs`)
- **Firestore config** added to `appsettings.Integration.json` (was missing)

---

## Windows / Git Bash — `--path` argument expansion

`make wait-*` targets call `wait_for_emulator.py --path /health`, but Git Bash
expands `/health` to `C:/Program Files/Git/health`. This does NOT affect conftest
fixtures (they call `_wait_for_*()` directly). To check health manually on Windows:
```bash
MSYS_NO_PATHCONV=1 curl -s http://localhost:8082/health
```
