# Grohe NEO — Integration Test Harness

## Vision

A cross-project test harness that spins up the full Grohe NEO backend stack locally —
Firestore emulator, mocked external APIs, and real .NET services — so that multi-repo tasks
can be validated end-to-end automatically, and Claude can run tests, analyze failures,
and fix code across repos without manual intervention.

---

## The Problem This Solves

Most tasks in Grohe NEO touch **multiple repos**. A typical example:

> "Add field `sustainability_label` to PLProductContent and expose it in the Products API."

This requires changes in:
- `grohe-neo-data-loader` — `transformer.py`, `pl_product_content.py`
- `grohe-neo-services` — `ProductsApi` models, mappings, controller

Right now, validating that change requires:
1. Running the loader against real Firestore (slow, risky)
2. Starting the service locally (manual config)
3. Testing via Postman or browser (manual)

**This project eliminates all of that.**

---

## Architecture

```
integration/
├── docker-compose.yml        ← Firestore emulator + WireMock + .NET services
├── Makefile                  ← Orchestration: make test-all / make pipeline / etc.
├── CLAUDE.md                 ← Instructions for Claude: how to run, read, and fix
├── fixtures/
│   ├── csv/                  ← Controlled test CSV batches (complete, small)
│   │   ├── minimal/          ← 1-2 products, all 18 CSV types present
│   │   └── full/             ← ~10 products, realistic batch for broader tests
│   └── mocks/
│       ├── hybris/           ← WireMock stubs: cart, orders, users, pricing
│       ├── sitecore-search/  ← WireMock stubs: ingestion capture + discovery
│       ├── sitecore-edge/    ← WireMock stubs: GraphQL layout/content responses
│       └── idp/              ← WireMock stubs: OAuth token + JWT public keys
├── tests/
│   ├── conftest.py           ← pytest fixtures: Firestore client, HTTP clients, WireMock
│   ├── pipeline/             ← ETL: loader → Firestore state assertions
│   ├── sync/                 ← Sync: ProductIndexData → products-index-updates
│   ├── services/             ← .NET service HTTP tests (Products, Search, etc.)
│   ├── indexing/             ← Indexing API → assert WireMock captured correct payload
│   └── scenarios/            ← Business scenario tests (named after real task types)
├── scripts/
│   ├── wait-for-services.sh  ← Health-check poller before tests run
│   └── run-pipeline.sh       ← Runs data-loader with emulator flags
└── reports/                  ← pytest JSON + HTML output (gitignored)
```

---

## Infrastructure Layer

Three containers via Docker Compose:

### 1. Firestore Emulator
```yaml
firestore-emulator:
  image: gcr.io/google.com/cloudsdktool/google-cloud-cli
  port: 8080
```
The data-loader already supports this out of the box (`--firestore-emulator` flag, targets `localhost:8080`).
.NET services connect via `FIRESTORE_EMULATOR_HOST=localhost:8080` env var.

### 2. WireMock
```yaml
wiremock:
  image: wiremock/wiremock:latest
  port: 8081
  volumes: ./fixtures/mocks:/home/wiremock/mappings
```

Replaces **all** external HTTP dependencies with a single container:

| External System | WireMock replaces |
|---|---|
| Hybris (SAP Commerce) | Cart, orders, users, pricing endpoints |
| Sitecore Search Ingestion | `discover-euc1.sitecorecloud.io/ingestion/v1` |
| Sitecore Search Discovery | `discover-euc1.sitecorecloud.io/discover/v2/{domainId}` |
| Sitecore Edge GraphQL | `edge-platform.sitecorecloud.io` |
| IDP / OAuth2 | Token endpoint + JWT public keys |
| Google Places API | Address autocomplete |
| Vercel revalidation | Cache invalidation endpoint |

WireMock's **request capture** feature lets tests assert *what was sent* to Sitecore Search,
not just that the call happened.

### 3. .NET Services (per test scenario)
```yaml
products-api:
  build: ../grohe-neo-services
  environment:
    FIRESTORE_EMULATOR_HOST: firestore-emulator:8080
    HYBRIS_BASE_URL: http://wiremock:8081/hybris
    SITECORE_SEARCH_INGESTION_URL: http://wiremock:8081/sitecore-ingestion
    # ... etc.
```

Only the services needed for the current test scenario run, to keep startup time low.

---

## Test Layers

### Layer 1 — Pipeline tests (`tests/pipeline/`)
**Scope:** data-loader only. No .NET services.
**Verifies:** Firestore document state after ETL.

```
test_extracts_all_csv_types_without_errors
test_pl_product_content_has_correct_fields
test_pl_category_hierarchy_is_correct
test_pl_variant_groups_by_finish
test_blue_green_database_switch_toggles_correctly
test_collections_are_cleared_before_load
test_document_size_stays_below_900kb
```

### Layer 2 — Sync tests (`tests/sync/`)
**Scope:** `sync_product_index.py` only.
**Verifies:** `products-index-updates` collection after sync.

```
test_new_product_creates_update_record_with_operation_update
test_changed_product_updates_record_when_hash_differs
test_unchanged_product_is_skipped
test_removed_product_marks_record_as_delete
test_finished_flag_is_set_to_false_on_change
```

### Layer 3 — Service tests (`tests/services/`)
**Scope:** .NET services via HTTP. Firestore pre-loaded with known data.
**Verifies:** API responses for known inputs.

```
test_products_api_returns_product_by_sku
test_products_api_returns_category_tree
test_products_api_returns_variants_grouped_by_finish
test_navigation_api_returns_category_routes
test_search_api_forwards_request_to_wiremock
test_indexing_api_reads_unfinished_queue_records
```

### Layer 4 — Indexing tests (`tests/indexing/`)
**Scope:** Full pipeline from Firestore queue to Sitecore Search.
**Verifies:** What the Indexing API *sent* to Sitecore Search (via WireMock capture).

```
test_full_product_indexing_pipeline_sends_correct_payload
test_deleted_product_sends_delete_operation_to_sitecore
test_updated_product_sends_update_with_correct_fields
test_ingestion_payload_includes_finish_definitions
test_ingestion_payload_locale_is_correct
```

### Layer 5 — Scenario tests (`tests/scenarios/`)
**Scope:** Business-level, multi-project, named after real task types.
**These become the acceptance criteria for tasks given to Claude.**

```
test_scenario__new_field_in_loader_appears_in_products_api_and_search_index
test_scenario__new_locale_flows_through_full_pipeline
test_scenario__deleted_product_is_removed_from_sitecore_search
test_scenario__category_routing_change_reflected_in_navigation_api
test_scenario__product_content_update_triggers_incremental_sync
```

---

## Makefile Commands

```makefile
make infra-up          # Start Firestore emulator + WireMock
make infra-down        # Stop and clean up containers
make seed              # Load fixture CSVs into emulator via data-loader

make test-pipeline     # Layer 1: pipeline tests only
make test-sync         # Layer 2: sync tests only
make test-services     # Layer 3: service API tests
make test-indexing     # Layer 4: indexing + WireMock capture tests
make test-scenarios    # Layer 5: business scenario tests
make test-all          # All layers, sequential

make report            # Open HTML report in browser
make fix-loop          # Run test-all → emit reports/results.json (for Claude)
```

---

## The Automated Fix Loop

This is what enables Claude to work autonomously across repos.

### Workflow

```
1. You give Claude a task (e.g. "Add field X to PLProductContent and Products API")

2. Claude identifies affected repos and files

3. Claude makes changes across repos

4. Claude runs: make fix-loop
   → Produces: reports/results.json (pytest JSON output)

5. Claude reads results.json:
   - Green: reports what was changed and why
   - Red: reads failing test names + assertion messages
         → traces failure back to source files
         → fixes code
         → re-runs from step 4

6. When all tests pass: Claude summarises the changes made
```

### Why pytest JSON output works for this

```json
{
  "tests": [
    {
      "nodeid": "tests/pipeline/test_pl_product_content.py::test_field_sustainability_label_present",
      "outcome": "failed",
      "call": {
        "longrepr": "AssertionError: 'sustainability_label' not found in document fields\nActual keys: ['sku', 'name', 'description', ...]"
      }
    }
  ]
}
```

The test name + assertion message directly tells Claude:
- **Which layer failed** (pipeline vs sync vs service)
- **Which file to look at** (`test_pl_product_content.py` → `pl_product_content.py`)
- **What was expected vs actual**

### Test naming convention for traceability

Test names follow the pattern: `test_{what}_{condition}_{expected_outcome}`

And scenario tests are named after the task type they validate:
`test_scenario__new_field_in_loader_appears_in_products_api`

This means Claude can match a task description to a relevant scenario test directly.

---

## Implementation Phases

### Phase 1 — Pipeline foundation ← Start here

**Goal:** `make test-pipeline` works end-to-end.

1. `docker-compose.yml` — Firestore emulator only
2. `fixtures/csv/minimal/` — complete set of all 18 CSV types, 2-3 products
   (extend from `grohe-neo-data-loader/small_input/`)
3. `tests/pipeline/` — pytest tests that run `main.py --firestore-emulator`
   and assert Firestore document shape
4. `Makefile` with `infra-up`, `seed`, `test-pipeline`, `infra-down`
5. `CLAUDE.md` — run instructions + failure guide

**Deliverable:** Full ETL pipeline testable locally in ~60 seconds.

### Phase 2 — Sync + Indexing

**Goal:** `make test-indexing` validates the full product → Sitecore Search pipeline.

1. Add WireMock to Docker Compose, load Sitecore Search stubs
2. `tests/sync/` — sync logic assertions
3. `tests/indexing/` — add Indexing API to Docker Compose, assert WireMock captures
4. Update Makefile

**Deliverable:** Can verify that a change in the data-loader produces the correct Sitecore Search ingestion payload.

### Phase 3 — Service tests

**Goal:** `make test-services` validates .NET service API responses.

1. Add Products API + Search API to Docker Compose
2. WireMock stubs for Hybris, Sitecore Edge GraphQL
3. `tests/services/` — HTTP tests against running services
4. Pre-seeded Firestore fixture data (JSON snapshots)

**Deliverable:** Can validate API contract changes without touching real cloud infrastructure.

### Phase 4 — Scenario tests

**Goal:** `make test-scenarios` is the acceptance gate for cross-repo tasks.

1. Write scenario tests that map to common task patterns
2. Each scenario test becomes a task acceptance criterion
3. Full `make fix-loop` command documented in `CLAUDE.md`

**Deliverable:** Claude can receive a task, run the relevant scenario test, and iterate to green autonomously.

---

## Tech Stack

| Concern | Choice | Reason |
|---|---|---|
| Test framework | **pytest** | Data-loader is Python; services testable via HTTP; excellent JSON output |
| HTTP mocking | **WireMock** | Captures + asserts requests; single container for all external APIs |
| Firestore | **Official emulator** | Already supported by data-loader (`--firestore-emulator` flag) |
| .NET services | **Docker Compose** | Real binaries, real config, connects to emulator |
| Orchestration | **Makefile** | Simple, universal, no extra tooling |
| Report format | **pytest-json-report** | Machine-readable; Claude parses for the fix loop |
| Fixtures | **CSV files** (extend `small_input/`) | Already validated format, version-controlled |

---

## Key Design Principles

1. **Fast by default** — Phase 1 (pipeline only) runs in ~60s with no .NET services
2. **Incremental** — each phase adds a layer; early phases stay green as later ones are added
3. **Traceable** — test names map directly to source files and business concepts
4. **Self-contained** — no cloud credentials needed; everything mocked locally
5. **Claude-friendly** — JSON output, clear failure messages, documented fix patterns
