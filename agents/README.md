# Multi-Agent Workflow — Grohe NEO Closed Ecosystem

## Overview

Two Claude Code sessions collaborate to develop and validate features autonomously:

| Role | Terminal directory | Reads | Writes |
|---|---|---|---|
| **Dev agent** | `grohe-neo-services/` | `current-task.md`, feature doc, `test-findings.md` | code changes, commits, `dev-complete.md` |
| **Test agent** | `integration/` | `dev-complete.md`, `CLAUDE.md` | `test-findings.md` (via `make fix-loop`) |

Both agents are **standard Claude Code sessions** — no special tooling required.
Role context is delivered by pasting `agents/dev-agent.md` or `agents/test-agent.md`
into the session at startup (or via `/read agents/dev-agent.md`).

---

## File-Based Handoff Protocol

```
reports/
  current-task.md     ← Human writes this to start a task
  dev-complete.md     ← Dev agent writes this when implementation is ready
  test-findings.md    ← Test agent writes this after make fix-loop
  results.json        ← pytest-json-report output (gitignored — generated)
```

### Workflow

```
1. Human writes reports/current-task.md
          ↓
2. Dev agent session (grohe-neo-services/):
   - /read integration/reports/current-task.md
   - /read docs/features/<feature>.md
   - /read integration/reports/test-findings.md  (if exists from previous run)
   - Implements changes
   - Commits to feature branch
   - Writes integration/reports/dev-complete.md
          ↓
3. Test agent session (integration/):
   - /read reports/dev-complete.md
   - Runs: make fix-loop
   - Reads: reports/results.json
   - Writes: reports/test-findings.md
          ↓
4a. ALL GREEN → Human reviews PR
4b. FAILURES → Go to step 2 (dev agent reads test-findings.md → fixes)
```

---

## Starting a Dev Agent Session

Open Claude Code in `grohe-neo-services/` and paste at session start:

```
/read integration/agents/dev-agent.md
/read integration/reports/current-task.md
/read docs/features/<feature-name>.md
```

If fixing failures from a previous run, also:
```
/read integration/reports/test-findings.md
```

## Starting a Test Agent Session

Open Claude Code in `integration/` and paste at session start:

```
/read agents/test-agent.md
/read reports/dev-complete.md
```

Then run:
```
make fix-loop
```

---

## Sitecore Mode

By default all tests run with `SITECORE_MODE=mock` — all Sitecore calls go to WireMock.
To test against a real Sitecore environment, set in `.env`:

```env
SITECORE_MODE=qa
SITECORE_EDGE_CONTEXT_ID=<your-context-id>
SITECORE_EDGE_API_KEY=<your-api-key>
```

---

## Adding a New Feature to the Closed Ecosystem

1. Add WireMock stubs in `fixtures/mocks/<external-system>/<feature>-*.json`
2. Add service to `docker-compose.yml` with a named profile matching the feature
3. Add `tests/<feature>/conftest.py` + `tests/<feature>/test_<feature>_api.py`
4. Add `make infra-<feature>-up/down` and `make test-<feature>` targets to Makefile
5. Update `CLAUDE.md` trace table with the new test file → source file mapping
6. Add feature doc to `docs/features/<feature>.md` in the websites repo
