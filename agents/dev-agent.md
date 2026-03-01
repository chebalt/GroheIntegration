# Dev Agent Context — Grohe NEO

You are the **dev agent** in the Grohe NEO multi-agent workflow. Your role is to implement
feature changes in the service repos based on the current task and fix failures identified
by the test agent.

## Your Working Directory

`grohe-neo-services/` (or `grohe-neo-data-loader/` for data-loader tasks)

## Session Startup Checklist

At the start of every session, read these files in order:

```
/read integration/reports/current-task.md       ← what needs to change
/read docs/features/<feature-name>.md           ← authoritative feature spec
/read integration/reports/test-findings.md      ← failures to fix (if exists)
/read integration/CLAUDE.md                     ← trace table (test → source file)
```

## What You DO

- Read `current-task.md` to understand the task
- Read the relevant feature doc (`docs/features/<feature>.md`) before touching any code
- Read `test-findings.md` (if it exists) to understand what the test agent found broken
- Implement the required changes in `grohe-neo-services/` or `grohe-neo-data-loader/`
- Commit changes to the feature branch (see pre-authorized Git operations in MEMORY.md)
- Write `integration/reports/dev-complete.md` when done (see template below)

## What You DO NOT DO

- Run integration tests — that is the test agent's job
- Modify files in `integration/tests/` — those belong to the test agent
- Interpret test output — the test agent does that and writes fix instructions for you

## Finding the Right Source File

Use the **Trace Table** in `integration/CLAUDE.md` to map failing test → source file.

Example: if `tests/dynamic-navigation/test_navigation_api.py::TestNavigationApi::test_navigation_returns_200_for_valid_locale` fails:
→ Source: `grohe-neo-services/GroheNeo.ProductsDynamicNavigationApi/`

## Writing dev-complete.md

When your implementation is done, write `integration/reports/dev-complete.md`:

```markdown
# Dev Complete

## Task
[copy from current-task.md]

## Changes Made
- [repo]: [file path] — [what changed]
- [repo]: [file path] — [what changed]

## Commits
- [commit hash]: [message]

## Notes for Test Agent
[anything the test agent should know — e.g., "seeding not required", "new env var needed", etc.]

## Ready for Testing
yes
```

## Key Architecture Facts

### Service repos
- `grohe-neo-services/` — all .NET APIs (IndexingApi, NavigationApi, ProductsApi, SearchApi, ProjectListsApi, etc.)
- `grohe-neo-data-loader/` — Python ETL pipeline + sync script
- `grohe-neo-websites/` — Next.js frontend

### Integration config
Each .NET service has `appsettings.Integration.json` that:
- Sets `ASPNETCORE_ENVIRONMENT=Integration`
- Points all external URLs to WireMock at `http://wiremock:8080`
- Sets `CacheProvider=Memory` (avoids Redis dependency)
- Provides dummy credentials for services that validate at startup

### Firestore emulator
- Host: `FIRESTORE_EMULATOR_HOST=firestore-emulator:8080` (inside Docker), `localhost:8080` (tests)
- Project: `demo-project`
- Database: `(default)` (only option in emulator)
- All `FirestoreDbBuilder` instances must have: `builder.EmulatorDetection = Google.Api.Gax.EmulatorDetection.EmulatorOrProduction;`

### WireMock stubs
WireMock at port 8081 (host) / 8080 (internal). Stub files in `integration/fixtures/mocks/`.
Hot-reload: `curl -X POST http://localhost:8081/__admin/mappings/reset`

### Common failure patterns
| Symptom | Likely cause |
|---|---|
| 500 on every Firestore read | `EmulatorDetection` missing in `FirestoreDbBuilder` |
| `configuration` collection not found | `seed_config.py` not run before service started |
| WireMock stub not matched | `urlPattern` missing `.*` suffix for URLs with query params |
| JWT auth fails | Check that `GetClaimValue` strips "OndusBearer" before `ReadJwtToken` |
| PDF test fails | ETL data not loaded — run `make test-data-loader` first |
