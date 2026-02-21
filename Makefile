# ─────────────────────────────────────────────────────────────────────────────
# Grohe NEO — Integration Test Harness
# ─────────────────────────────────────────────────────────────────────────────

SHELL := bash

# Paths (relative to this Makefile)
INTEGRATION_DIR := $(shell pwd)
REPO_ROOT       := $(INTEGRATION_DIR)/..
DATA_LOADER_DIR := $(REPO_ROOT)/grohe-neo-data-loader
FIXTURES_CSV    := $(INTEGRATION_DIR)/fixtures/csv
REPORTS_DIR     := $(INTEGRATION_DIR)/reports

# Python — use integration venv if it exists, else system python
ifeq ($(OS),Windows_NT)
  PYTHON := $(INTEGRATION_DIR)/.venv/Scripts/python.exe
  PYTEST := $(INTEGRATION_DIR)/.venv/Scripts/pytest.exe
else
  PYTHON := $(INTEGRATION_DIR)/.venv/bin/python
  PYTEST := $(INTEGRATION_DIR)/.venv/bin/pytest
endif

ifeq ($(wildcard $(PYTHON)),)
  PYTHON := python
  PYTEST := pytest
endif

# Firestore emulator / service hosts
EMULATOR_HOST        := localhost:8080
INDEXING_API_HOST    := localhost:8082
NAVIGATION_API_HOST  := localhost:8083
PRODUCTS_API_HOST    := localhost:8084
SEARCH_API_HOST      := localhost:8085

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@echo ""
	@echo "Grohe NEO Integration Test Harness — Phase 1 + 2 + 3 + 4"
	@echo ""
	@echo "  make setup               Install Python test dependencies"
	@echo ""
	@echo "  Phase 1 + 2 infrastructure (fast — no Docker build):"
	@echo "  make infra-up            Start Firestore emulator + WireMock (Docker)"
	@echo "  make infra-down          Stop and remove containers"
	@echo "  make wait                Wait until emulator is ready"
	@echo ""
	@echo "  Phase 3 infrastructure (slow — builds .NET IndexingApi from source):"
	@echo "  make infra-phase3-up     Build + start all services incl. IndexingApi"
	@echo "  make infra-phase3-down   Stop all Phase 3 containers"
	@echo "  make wait-indexing-api   Wait until IndexingApi /health responds"
	@echo ""
	@echo "  Phase 4 infrastructure (slow — builds NavigationApi + ProductsApi):"
	@echo "  make seed-config         Seed Firestore configuration collection"
	@echo "  make infra-phase4-up     Seed config + build + start NavigationApi + ProductsApi"
	@echo "  make infra-phase4-down   Stop all Phase 4 containers"
	@echo "  make wait-navigation-api Wait until NavigationApi /health responds"
	@echo "  make wait-products-api   Wait until ProductsApi /health responds"
	@echo ""
	@echo "  Phase 5 infrastructure (SearchApi — no Firestore, build ~2-3 min):"
	@echo "  make infra-phase5-up     Build + start SearchApi (no config seeding needed)"
	@echo "  make infra-phase5-down   Stop all Phase 5 containers"
	@echo "  make wait-search-api     Wait until SearchApi /health responds"
	@echo ""
	@echo "  Tests:"
	@echo "  make test-pipeline       Layer 1: ETL pipeline tests (requires emulator)"
	@echo "  make test-sync           Layer 2: sync_product_index.py tests"
	@echo "  make test-indexing       Layer 4: Indexing API tests (requires Phase 3 infra)"
	@echo "  make test-services       Layer 3: NavigationApi + ProductsApi + SearchApi tests (requires Phase 4+5 infra)"
	@echo "  make test-all            All layers"
	@echo "  make fix-loop            Run tests + emit reports/results.json (for Claude)"
	@echo ""
	@echo "  make report              Open HTML report in browser"
	@echo "  make clean               Remove reports and __pycache__"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: setup
setup:
	@echo "→ Creating integration virtualenv..."
	python -m venv .venv
	$(PYTHON) -m pip install --upgrade pip -q
	$(PYTHON) -m pip install -r requirements.txt -q
	@echo "✓ Integration environment ready."
	@echo ""
	@echo "  If the data-loader venv is missing, run:"
	@echo "  cd $(DATA_LOADER_DIR) && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt"

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — Phase 1 + 2 (Firestore + WireMock only)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-up
infra-up:
	@echo "→ Starting Firestore emulator + WireMock..."
	docker compose up -d
	@echo "→ Waiting for emulator to be ready..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "✓ Infrastructure ready."

.PHONY: infra-down
infra-down:
	@echo "→ Stopping containers..."
	docker compose down
	@echo "✓ Infrastructure stopped."

.PHONY: wait
wait:
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 60

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — Phase 3 (+ .NET IndexingApi — requires Docker build)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-phase3-up
infra-phase3-up:
	@echo "→ Building IndexingApi Docker image (first run takes several minutes)..."
	docker compose --profile phase3 build indexing-api
	@echo "→ Starting all Phase 3 services..."
	docker compose --profile phase3 up -d
	@echo "→ Waiting for Firestore emulator..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Waiting for IndexingApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(INDEXING_API_HOST) --path /health --timeout 180
	@echo "✓ Phase 3 infrastructure ready."

.PHONY: infra-phase3-down
infra-phase3-down:
	@echo "→ Stopping all Phase 3 containers..."
	docker compose --profile phase3 down
	@echo "✓ Phase 3 infrastructure stopped."

.PHONY: wait-indexing-api
wait-indexing-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(INDEXING_API_HOST) --path /health --timeout 180

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — Phase 4 (+ NavigationApi + ProductsApi — requires Docker build)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: seed-config
seed-config:
	@echo "→ Seeding Firestore configuration collection..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	$(PYTHON) scripts/seed_config.py
	@echo "✓ Configuration seeded."

.PHONY: infra-phase4-up
infra-phase4-up:
	@echo "→ Ensuring emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Seeding configuration collection (required before services start)..."
	$(MAKE) seed-config
	@echo "→ Building Phase 4 Docker images (first run: NavigationApi ~3 min, ProductsApi ~20 min)..."
	docker compose --profile phase4 build
	@echo "→ Starting Phase 4 services..."
	docker compose --profile phase4 up -d
	@echo "→ Waiting for NavigationApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(NAVIGATION_API_HOST) --path /health --timeout 180
	@echo "→ Waiting for ProductsApi /health (up to 5 min — Chrome install on first build)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(PRODUCTS_API_HOST) --path /health --timeout 300
	@echo "✓ Phase 4 infrastructure ready."

.PHONY: infra-phase4-down
infra-phase4-down:
	@echo "→ Stopping all Phase 4 containers..."
	docker compose --profile phase4 down
	@echo "✓ Phase 4 infrastructure stopped."

.PHONY: wait-navigation-api
wait-navigation-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(NAVIGATION_API_HOST) --path /health --timeout 180

.PHONY: wait-products-api
wait-products-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(PRODUCTS_API_HOST) --path /health --timeout 300

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — Phase 5 (+ SearchApi — no Firestore, no Chrome, fast build)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-phase5-up
infra-phase5-up:
	@echo "→ Ensuring WireMock is running (no Firestore seeding needed for SearchApi)..."
	docker compose up -d wiremock
	$(PYTHON) scripts/wait_for_emulator.py --host localhost:8081 --path /__admin/health --timeout 30
	@echo "→ Building Phase 5 Docker image (first run: ~2-3 min)..."
	docker compose --profile phase5 build search-api
	@echo "→ Starting Phase 5 services..."
	docker compose --profile phase5 up -d
	@echo "→ Waiting for SearchApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(SEARCH_API_HOST) --path /health --timeout 180
	@echo "✓ Phase 5 infrastructure ready."

.PHONY: infra-phase5-down
infra-phase5-down:
	@echo "→ Stopping all Phase 5 containers..."
	docker compose --profile phase5 down
	@echo "✓ Phase 5 infrastructure stopped."

.PHONY: wait-search-api
wait-search-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(SEARCH_API_HOST) --path /health --timeout 180

# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

$(REPORTS_DIR):
	mkdir -p $(REPORTS_DIR)

.PHONY: test-pipeline
test-pipeline: $(REPORTS_DIR)
	@echo "→ Running ETL pipeline tests..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	$(PYTEST) tests/pipeline/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/pipeline.json \
		--html=$(REPORTS_DIR)/pipeline.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ Pipeline tests complete. Report: reports/pipeline.html"

.PHONY: test-sync
test-sync: $(REPORTS_DIR)
	@echo "→ Running sync tests (Layer 2)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	$(PYTEST) tests/sync/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/sync.json \
		--html=$(REPORTS_DIR)/sync.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ Sync tests complete. Report: reports/sync.html"

.PHONY: test-indexing
test-indexing: $(REPORTS_DIR)
	@echo "→ Running indexing tests (Layer 4 — requires Phase 3 infrastructure)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	$(PYTEST) tests/indexing/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/indexing.json \
		--html=$(REPORTS_DIR)/indexing.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ Indexing tests complete. Report: reports/indexing.html"

.PHONY: test-search
test-search: $(REPORTS_DIR)
	@echo "→ Running SearchApi tests (Phase 5 — requires Phase 5 infrastructure)..."
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	$(PYTEST) tests/services/search/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/search.json \
		--html=$(REPORTS_DIR)/search.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ SearchApi tests complete. Report: reports/search.html"

.PHONY: test-services
test-services: $(REPORTS_DIR)
	@echo "→ Running service tests (Layer 3 — requires Phase 4+5 infrastructure)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	NAVIGATION_API_HOST=$(NAVIGATION_API_HOST) \
	PRODUCTS_API_HOST=$(PRODUCTS_API_HOST) \
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	$(PYTEST) tests/services/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/services.json \
		--html=$(REPORTS_DIR)/services.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ Service tests complete. Report: reports/services.html"

.PHONY: test-all
test-all: $(REPORTS_DIR)
	@echo "→ Running all available tests..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	NAVIGATION_API_HOST=$(NAVIGATION_API_HOST) \
	PRODUCTS_API_HOST=$(PRODUCTS_API_HOST) \
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	$(PYTEST) tests/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/results.json \
		--html=$(REPORTS_DIR)/results.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ All tests complete. Report: reports/results.html"

# The fix-loop target: always produces reports/results.json for Claude to read.
# Returns exit code 0 even on test failures so Claude can continue and fix.
.PHONY: fix-loop
fix-loop: $(REPORTS_DIR)
	@echo "→ Running fix-loop (tests + JSON report)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	NAVIGATION_API_HOST=$(NAVIGATION_API_HOST) \
	PRODUCTS_API_HOST=$(PRODUCTS_API_HOST) \
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	$(PYTEST) tests/ \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/results.json \
		--html=$(REPORTS_DIR)/results.html \
		--self-contained-html \
		-p no:cacheprovider \
		--tb=short \
	; EXIT_CODE=$$?; \
	echo ""; \
	echo "────────────────────────────────────────────"; \
	if [ $$EXIT_CODE -eq 0 ]; then \
		echo "✓ All tests passed."; \
	else \
		echo "✗ Some tests failed — see reports/results.json"; \
	fi; \
	echo "────────────────────────────────────────────"; \
	exit $$EXIT_CODE

# ─────────────────────────────────────────────────────────────────────────────
# Reports
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: report
report:
ifeq ($(OS),Windows_NT)
	start reports/results.html
else ifeq ($(shell uname),Darwin)
	open reports/results.html
else
	xdg-open reports/results.html
endif

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: clean
clean:
	rm -rf reports/ .pytest_cache/ tests/__pycache__/ tests/**/__pycache__/
	@echo "✓ Cleaned."
