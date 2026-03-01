# Test Agent Context — Grohe NEO

You are the **test agent** in the Grohe NEO multi-agent workflow. Your role is to run
the integration test suite, read the results, and produce a clear findings report for
the dev agent to act on.

## Your Working Directory

`integration/`

## Session Startup Checklist

```
/read agents/test-agent.md          ← this file (confirms your role)
/read reports/dev-complete.md       ← what the dev agent just implemented
/read CLAUDE.md                     ← trace table + infrastructure commands
```

## What You DO

1. Read `reports/dev-complete.md` to understand what changed
2. Determine which features are affected (check trace table in `CLAUDE.md`)
3. Ensure the relevant infrastructure is running (if not, start it)
4. Run `make fix-loop` (or targeted `make test-<feature>` for speed)
5. Read `reports/results.json` for pass/fail details
6. Write `reports/test-findings.md` with actionable fix instructions

## What You DO NOT DO

- Modify source code in `grohe-neo-services/` or `grohe-neo-data-loader/`
- Modify test files in `tests/` (unless the task explicitly involves the test harness)
- Interpret business logic — focus on test failures and their trace to source

## Running Tests

```bash
# Full suite (use when unsure which features are affected):
make fix-loop

# Targeted (faster when you know which feature changed):
make test-data-loader          # ~10-11 min (ETL is slow)
make test-product-indexing     # ~30s
make test-dynamic-navigation   # ~60s
make test-pdp                  # ~60s
make test-search               # ~30s
make test-project-list         # ~60s
```

## Starting Infrastructure (if not running)

Check Docker status first. Then:

```bash
make infra-up                          # always needed (Firestore + WireMock)
make infra-product-indexing-up        # for product-indexing tests
make infra-dynamic-navigation-up      # for dynamic-navigation tests
make infra-pdp-up                     # for pdp tests
make infra-search-up                  # for search tests
make infra-project-list-up            # for project-list tests
```

## Writing test-findings.md

After `make fix-loop`, write `reports/test-findings.md`:

```markdown
# Test Findings

## Run Summary
- Total: N tests
- Passed: N
- Failed: N
- Errored: N
- Date: YYYY-MM-DD HH:MM

## Failed Tests

### <test_node_id>
**Feature**: <feature name>
**Assertion**: <exact error from longrepr>
**Source file** (from trace table): <grohe-neo-services/...>
**Fix instruction**: <what the dev agent needs to change>

### <test_node_id>
...

## All-Green Confirmation
[ ] Not yet — see failures above
[x] ALL TESTS PASSED — dev agent can proceed to PR

## Notes
[anything unusual about the run — e.g., skipped tests, infrastructure issues]
```

## Reading results.json

```python
import json
with open("reports/results.json") as f:
    data = json.load(f)

# Summary
summary = data["summary"]  # {"passed": N, "failed": N, "total": N}

# Failures
failures = [t for t in data["tests"] if t["outcome"] == "failed"]
for f in failures:
    print(f["nodeid"])
    print(f["call"]["longrepr"])  # full assertion error
```

## Trace Table (test → source file)

| Test file | Feature | Source repo/file |
|---|---|---|
| `data-loader/etl/test_pipeline_runs.py` | data-loader | `grohe-neo-data-loader/main.py` |
| `data-loader/etl/test_collections.py` | data-loader | `grohe-neo-data-loader/transformer.py` |
| `data-loader/etl/test_document_structure.py` | data-loader | `grohe-neo-data-loader/output_models/`, `transformer.py` |
| `data-loader/sync/test_sync_logic.py` | data-loader | `grohe-neo-data-loader/sync_product_index.py` |
| `product-indexing/test_indexing_pipeline.py` | product-indexing | `grohe-neo-services/GroheNeo.IndexingApi/` |
| `dynamic-navigation/test_navigation_api.py` | dynamic-navigation | `grohe-neo-services/GroheNeo.ProductsDynamicNavigationApi/` |
| `pdp/test_products_api.py` | pdp | `grohe-neo-services/GroheNeo.ProductsApi/` |
| `search/test_search_api.py` | search | `grohe-neo-services/GroheNeo.SearchApi/` |
| `project-list/test_project_lists_api.py` | project-list | `grohe-neo-services/GroheNeo.ProjectListsApi/` |
