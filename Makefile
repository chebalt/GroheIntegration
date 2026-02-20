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

# Firestore emulator
EMULATOR_HOST := localhost:8080

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@echo ""
	@echo "Grohe NEO Integration Test Harness — Phase 1 (Pipeline)"
	@echo ""
	@echo "  make setup          Install Python test dependencies"
	@echo "  make infra-up       Start Firestore emulator (Docker)"
	@echo "  make infra-down     Stop and remove containers"
	@echo "  make wait           Wait until emulator is ready"
	@echo ""
	@echo "  make test-pipeline  Run ETL pipeline tests (requires emulator)"
	@echo "  make test-all       Run all available tests"
	@echo "  make fix-loop       Run tests + emit reports/results.json (for Claude)"
	@echo ""
	@echo "  make report         Open HTML report in browser"
	@echo "  make clean          Remove reports and __pycache__"
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
# Infrastructure
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-up
infra-up:
	@echo "→ Starting Firestore emulator..."
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

.PHONY: test-all
test-all: $(REPORTS_DIR)
	@echo "→ Running all available tests..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
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
