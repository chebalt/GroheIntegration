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
EMULATOR_HOST             := localhost:8080
INDEXING_API_HOST         := localhost:8082
NAVIGATION_API_HOST       := localhost:8083
PRODUCTS_API_HOST         := localhost:8084
SEARCH_API_HOST           := localhost:8085
PROJECT_LISTS_API_HOST    := localhost:8086
SHOPPING_CART_API_HOST    := localhost:8087
USER_API_HOST             := localhost:8088
PRICING_API_HOST          := localhost:8089
ORDER_API_HOST            := localhost:8090
FORMS_API_HOST            := localhost:8092
REDIRECTIONS_API_HOST     := localhost:8093

.DEFAULT_GOAL := help

# ─────────────────────────────────────────────────────────────────────────────
# Help
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: help
help:
	@echo ""
	@echo "Grohe NEO Integration Test Harness"
	@echo ""
	@echo "  make bootstrap               First-time setup (venv + deps + .env)"
	@echo "  make setup                   Install Python test dependencies only"
	@echo ""
	@echo "  Core infrastructure (always needed):"
	@echo "  make infra-up                Start Firestore emulator + WireMock"
	@echo "  make infra-down              Stop core containers"
	@echo "  make wait                    Wait until emulator is ready"
	@echo ""
	@echo "  Batch A feature infrastructure:"
	@echo "  make infra-product-indexing-up/down     IndexingApi (port 8082)"
	@echo "  make infra-dynamic-navigation-up/down   NavigationApi (port 8083)"
	@echo "  make infra-pdp-up/down                  ProductsApi (port 8084)"
	@echo "  make infra-search-up/down               SearchApi (port 8085)"
	@echo "  make infra-project-list-up/down         ProductsApi + ProjectListsApi (8084+8086)"
	@echo ""
	@echo "  Batch B feature infrastructure (requires service in docker-compose):"
	@echo "  make infra-shopping-cart-up/down        ShoppingCartApi (port 8087)"
	@echo "  make infra-my-account-up/down           UserApi (port 8088)"
	@echo "  make infra-pricing-up/down              PricingApi (port 8089)"
	@echo "  make infra-checkout-up/down             OrderApi (port 8090)"
	@echo "  make infra-forms-up/down                FormsApi (port 8092)"
	@echo "  make infra-store-locator-up             Run store-locator one-shot job"
	@echo "  make infra-redirections-up/down         Redirect reverse proxy (port 8093)"
	@echo ""
	@echo "  Tests (Batch A):"
	@echo "  make test-data-loader        data-loader ETL + sync tests (~10-11 min)"
	@echo "  make test-product-indexing   IndexingApi → WireMock (~30s)"
	@echo "  make test-dynamic-navigation NavigationApi HTTP tests (~60s)"
	@echo "  make test-pdp                ProductsApi HTTP tests (~60s)"
	@echo "  make test-search             SearchApi HTTP tests (~30s)"
	@echo "  make test-project-list       ProjectListsApi CRUD + PDF (~60s)"
	@echo ""
	@echo "  Tests (Batch B — skip gracefully if service not running):"
	@echo "  make test-shopping-cart      ShoppingCartApi HTTP tests"
	@echo "  make test-my-account         UserApi HTTP tests"
	@echo "  make test-pricing            PricingApi HTTP tests"
	@echo "  make test-checkout           OrderApi + Adyen payment tests"
	@echo "  make test-forms              FormsApi form submission tests"
	@echo "  make test-store-locator      Store-locator job → Firestore"
	@echo "  make test-redirections       Redirect proxy HTTP tests"
	@echo ""
	@echo "  make test-all                All features (skips unavailable Batch B services)"
	@echo "  make fix-loop                test-all + emit reports/results.json (for agent)"
	@echo ""
	@echo "  make seed-config             Seed Firestore configuration collection"
	@echo "  make report                  Open HTML report in browser"
	@echo "  make clean                   Remove reports and __pycache__"
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap — first-time setup for new team members
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: bootstrap
bootstrap:
	@echo "→ Setting up Grohe NEO integration environment..."
	cp -n .env.example .env 2>/dev/null || true
	python -m venv .venv
	$(PYTHON) -m pip install --upgrade pip -q
	$(PYTHON) -m pip install -r requirements.txt -q
	@echo ""
	@echo "✓ Bootstrap complete."
	@echo ""
	@echo "  Next steps:"
	@echo "  1. Edit .env if you need non-default settings (e.g. SITECORE_MODE=qa)"
	@echo "  2. make infra-up"
	@echo "  3. make test-data-loader"
	@echo ""
	@echo "  To run full suite with all services:"
	@echo "  make infra-product-indexing-up && make infra-search-up && make test-all"
	@echo ""
	@echo "  See agents/README.md for the Claude Code multi-agent workflow."

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
# Infrastructure — Core (Firestore + WireMock — always needed)
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
# Infrastructure — product-indexing (+ .NET IndexingApi)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-product-indexing-up
infra-product-indexing-up:
	@echo "→ Building IndexingApi Docker image (first run takes several minutes)..."
	docker compose --profile product-indexing build indexing-api
	@echo "→ Starting product-indexing services..."
	docker compose --profile product-indexing up -d
	@echo "→ Waiting for Firestore emulator..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Waiting for IndexingApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(INDEXING_API_HOST) --path /health --timeout 180
	@echo "✓ product-indexing infrastructure ready."

.PHONY: infra-product-indexing-down
infra-product-indexing-down:
	@echo "→ Stopping product-indexing containers..."
	docker compose --profile product-indexing down
	@echo "✓ product-indexing infrastructure stopped."

.PHONY: wait-indexing-api
wait-indexing-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(INDEXING_API_HOST) --path /health --timeout 180

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — dynamic-navigation (+ NavigationApi)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: seed-config
seed-config:
	@echo "→ Seeding Firestore configuration collection..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	$(PYTHON) scripts/seed_config.py
	@echo "✓ Configuration seeded."

.PHONY: infra-dynamic-navigation-up
infra-dynamic-navigation-up:
	@echo "→ Ensuring emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Seeding configuration collection..."
	$(MAKE) seed-config
	@echo "→ Building NavigationApi Docker image (first run: ~3 min)..."
	docker compose --profile dynamic-navigation build
	@echo "→ Starting dynamic-navigation services..."
	docker compose --profile dynamic-navigation up -d
	@echo "→ Waiting for NavigationApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(NAVIGATION_API_HOST) --path /health --timeout 180
	@echo "✓ dynamic-navigation infrastructure ready."

.PHONY: infra-dynamic-navigation-down
infra-dynamic-navigation-down:
	@echo "→ Stopping dynamic-navigation containers..."
	docker compose --profile dynamic-navigation down
	@echo "✓ dynamic-navigation infrastructure stopped."

.PHONY: wait-navigation-api
wait-navigation-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(NAVIGATION_API_HOST) --path /health --timeout 180

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — pdp (+ ProductsApi)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-pdp-up
infra-pdp-up:
	@echo "→ Ensuring emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Seeding configuration collection (required before ProductsApi starts)..."
	$(MAKE) seed-config
	@echo "→ Building ProductsApi Docker image (first run: ~20 min — installs Chrome)..."
	docker compose --profile pdp build
	@echo "→ Starting pdp services..."
	docker compose --profile pdp up -d
	@echo "→ Waiting for ProductsApi /health (up to 5 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(PRODUCTS_API_HOST) --path /health --timeout 300
	@echo "✓ pdp infrastructure ready."

.PHONY: infra-pdp-down
infra-pdp-down:
	@echo "→ Stopping pdp containers..."
	docker compose --profile pdp down
	@echo "✓ pdp infrastructure stopped."

.PHONY: wait-products-api
wait-products-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(PRODUCTS_API_HOST) --path /health --timeout 300

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — search (+ SearchApi — no Firestore, fast build)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-search-up
infra-search-up:
	@echo "→ Ensuring WireMock is running (no Firestore seeding needed for SearchApi)..."
	docker compose up -d wiremock
	$(PYTHON) scripts/wait_for_emulator.py --host localhost:8081 --path /__admin/health --timeout 30
	@echo "→ Building SearchApi Docker image (first run: ~2-3 min)..."
	docker compose --profile search build search-api
	@echo "→ Starting search services..."
	docker compose --profile search up -d
	@echo "→ Waiting for SearchApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(SEARCH_API_HOST) --path /health --timeout 180
	@echo "✓ search infrastructure ready."

.PHONY: infra-search-down
infra-search-down:
	@echo "→ Stopping search containers..."
	docker compose --profile search down
	@echo "✓ search infrastructure stopped."

.PHONY: wait-search-api
wait-search-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(SEARCH_API_HOST) --path /health --timeout 180

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — project-list (+ ProductsApi + ProjectListsApi — Chrome install)
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-project-list-up
infra-project-list-up:
	@echo "→ Ensuring Firestore emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Seeding configuration collection (required for ProductsApi)..."
	$(MAKE) seed-config
	@echo "→ Building Docker images (first run: ProductsApi + ProjectListsApi ~15-20 min each — installs Chrome)..."
	docker compose --profile project-list build
	@echo "→ Starting project-list services (ProductsApi + ProjectListsApi)..."
	docker compose --profile project-list up -d
	@echo "→ Waiting for ProductsApi /health (up to 5 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(PRODUCTS_API_HOST) --path /health --timeout 300
	@echo "→ Waiting for ProjectListsApi /health (up to 5 min — Chrome install on first build)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(PROJECT_LISTS_API_HOST) --path /health --timeout 300
	@echo "✓ project-list infrastructure ready."

.PHONY: infra-project-list-down
infra-project-list-down:
	@echo "→ Stopping project-list containers..."
	docker compose --profile project-list down
	@echo "✓ project-list infrastructure stopped."

.PHONY: wait-project-lists-api
wait-project-lists-api:
	$(PYTHON) scripts/wait_for_emulator.py --host $(PROJECT_LISTS_API_HOST) --path /health --timeout 300

# ─────────────────────────────────────────────────────────────────────────────
# Infrastructure — Batch B (shopping-cart, my-account, pricing, checkout,
#                           forms, store-locator, redirections)
# These targets follow the same pattern as Batch A above.
# The Docker Compose service profiles must be added to docker-compose.yml for
# each service before these targets will fully work. Tests skip gracefully
# (pytest.skip) when the service is not yet running.
# ─────────────────────────────────────────────────────────────────────────────

.PHONY: infra-shopping-cart-up
infra-shopping-cart-up:
	@echo "→ Ensuring Firestore emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Building ShoppingCartApi Docker image..."
	docker compose --profile shopping-cart build
	@echo "→ Starting shopping-cart services..."
	docker compose --profile shopping-cart up -d
	@echo "→ Waiting for ShoppingCartApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(SHOPPING_CART_API_HOST) --path /health --timeout 180
	@echo "✓ shopping-cart infrastructure ready."

.PHONY: infra-shopping-cart-down
infra-shopping-cart-down:
	docker compose --profile shopping-cart down
	@echo "✓ shopping-cart infrastructure stopped."

.PHONY: infra-my-account-up
infra-my-account-up:
	@echo "→ Ensuring Firestore emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Building UserApi Docker image..."
	docker compose --profile my-account build
	@echo "→ Starting my-account services..."
	docker compose --profile my-account up -d
	@echo "→ Waiting for UserApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(USER_API_HOST) --path /health --timeout 180
	@echo "✓ my-account infrastructure ready."

.PHONY: infra-my-account-down
infra-my-account-down:
	docker compose --profile my-account down
	@echo "✓ my-account infrastructure stopped."

.PHONY: infra-pricing-up
infra-pricing-up:
	@echo "→ Ensuring Firestore emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Building PricingApi Docker image..."
	docker compose --profile pricing build
	@echo "→ Starting pricing services..."
	docker compose --profile pricing up -d
	@echo "→ Waiting for PricingApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(PRICING_API_HOST) --path /health --timeout 180
	@echo "✓ pricing infrastructure ready."

.PHONY: infra-pricing-down
infra-pricing-down:
	docker compose --profile pricing down
	@echo "✓ pricing infrastructure stopped."

.PHONY: infra-checkout-up
infra-checkout-up:
	@echo "→ Ensuring Firestore emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Building checkout services (OrderApi + PaymentApi)..."
	docker compose --profile checkout build
	@echo "→ Starting checkout services..."
	docker compose --profile checkout up -d
	@echo "→ Waiting for OrderApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(ORDER_API_HOST) --path /health --timeout 180
	@echo "✓ checkout infrastructure ready."

.PHONY: infra-checkout-down
infra-checkout-down:
	docker compose --profile checkout down
	@echo "✓ checkout infrastructure stopped."

.PHONY: infra-forms-up
infra-forms-up:
	@echo "→ Ensuring WireMock is running (Mulesoft + reCAPTCHA stubs)..."
	docker compose up -d wiremock
	$(PYTHON) scripts/wait_for_emulator.py --host localhost:8081 --path /__admin/health --timeout 30
	@echo "→ Building FormsApi Docker image..."
	docker compose --profile forms build
	@echo "→ Starting forms services..."
	docker compose --profile forms up -d
	@echo "→ Waiting for FormsApi /health (up to 3 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(FORMS_API_HOST) --path /health --timeout 180
	@echo "✓ forms infrastructure ready."

.PHONY: infra-forms-down
infra-forms-down:
	docker compose --profile forms down
	@echo "✓ forms infrastructure stopped."

.PHONY: infra-store-locator-up
infra-store-locator-up:
	@echo "→ Ensuring Firestore emulator + WireMock are running..."
	docker compose up -d
	$(PYTHON) scripts/wait_for_emulator.py --host $(EMULATOR_HOST) --timeout 90
	@echo "→ Running store-locator one-shot job (profile=store-locator)..."
	docker compose --profile store-locator run --rm store-locator-job
	@echo "✓ store-locator job complete — 'stores-index-updates' should be populated."

.PHONY: infra-redirections-up
infra-redirections-up:
	@echo "→ Ensuring WireMock is running (Sitecore Edge stubs for redirect lookup)..."
	docker compose up -d wiremock
	$(PYTHON) scripts/wait_for_emulator.py --host localhost:8081 --path /__admin/health --timeout 30
	@echo "→ Building redirect reverse proxy Docker image..."
	docker compose --profile redirections build
	@echo "→ Starting redirections services..."
	docker compose --profile redirections up -d
	@echo "→ Waiting for redirect proxy /health (up to 2 min)..."
	$(PYTHON) scripts/wait_for_emulator.py --host $(REDIRECTIONS_API_HOST) --path /health --timeout 120
	@echo "✓ redirections infrastructure ready."

.PHONY: infra-redirections-down
infra-redirections-down:
	docker compose --profile redirections down
	@echo "✓ redirections infrastructure stopped."

# ─────────────────────────────────────────────────────────────────────────────
# Tests — Feature-level targets
# ─────────────────────────────────────────────────────────────────────────────

$(REPORTS_DIR):
	mkdir -p $(REPORTS_DIR)

.PHONY: test-data-loader
test-data-loader: $(REPORTS_DIR)
	@echo "→ Running data-loader tests (ETL pipeline + sync)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	$(PYTEST) tests/data-loader/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/data-loader.json \
		--html=$(REPORTS_DIR)/data-loader.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ data-loader tests complete. Report: reports/data-loader.html"

.PHONY: test-product-indexing
test-product-indexing: $(REPORTS_DIR)
	@echo "→ Running product-indexing tests (requires infra-product-indexing-up)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	$(PYTEST) tests/product-indexing/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/product-indexing.json \
		--html=$(REPORTS_DIR)/product-indexing.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ product-indexing tests complete. Report: reports/product-indexing.html"

.PHONY: test-dynamic-navigation
test-dynamic-navigation: $(REPORTS_DIR)
	@echo "→ Running dynamic-navigation tests (requires infra-dynamic-navigation-up)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	NAVIGATION_API_HOST=$(NAVIGATION_API_HOST) \
	$(PYTEST) tests/dynamic-navigation/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/dynamic-navigation.json \
		--html=$(REPORTS_DIR)/dynamic-navigation.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ dynamic-navigation tests complete. Report: reports/dynamic-navigation.html"

.PHONY: test-pdp
test-pdp: $(REPORTS_DIR)
	@echo "→ Running pdp tests (requires infra-pdp-up)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	PRODUCTS_API_HOST=$(PRODUCTS_API_HOST) \
	$(PYTEST) tests/pdp/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/pdp.json \
		--html=$(REPORTS_DIR)/pdp.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ pdp tests complete. Report: reports/pdp.html"

.PHONY: test-search
test-search: $(REPORTS_DIR)
	@echo "→ Running search tests (requires infra-search-up)..."
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	$(PYTEST) tests/search/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/search.json \
		--html=$(REPORTS_DIR)/search.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ search tests complete. Report: reports/search.html"

.PHONY: test-project-list
test-project-list: $(REPORTS_DIR)
	@echo "→ Running project-list tests (requires infra-project-list-up)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	PROJECT_LISTS_API_HOST=$(PROJECT_LISTS_API_HOST) \
	$(PYTEST) tests/project-list/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/project-list.json \
		--html=$(REPORTS_DIR)/project-list.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ project-list tests complete. Report: reports/project-list.html"

.PHONY: test-shopping-cart
test-shopping-cart: $(REPORTS_DIR)
	@echo "→ Running shopping-cart tests (skips if ShoppingCartApi not running)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	SHOPPING_CART_API_HOST=$(SHOPPING_CART_API_HOST) \
	$(PYTEST) tests/shopping-cart/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/shopping-cart.json \
		--html=$(REPORTS_DIR)/shopping-cart.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ shopping-cart tests complete. Report: reports/shopping-cart.html"

.PHONY: test-my-account
test-my-account: $(REPORTS_DIR)
	@echo "→ Running my-account tests (skips if UserApi not running)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	USER_API_HOST=$(USER_API_HOST) \
	$(PYTEST) tests/my-account/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/my-account.json \
		--html=$(REPORTS_DIR)/my-account.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ my-account tests complete. Report: reports/my-account.html"

.PHONY: test-pricing
test-pricing: $(REPORTS_DIR)
	@echo "→ Running pricing tests (skips if PricingApi not running)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	PRICING_API_HOST=$(PRICING_API_HOST) \
	$(PYTEST) tests/pricing/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/pricing.json \
		--html=$(REPORTS_DIR)/pricing.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ pricing tests complete. Report: reports/pricing.html"

.PHONY: test-checkout
test-checkout: $(REPORTS_DIR)
	@echo "→ Running checkout tests (skips if OrderApi not running)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	ORDER_API_HOST=$(ORDER_API_HOST) \
	$(PYTEST) tests/checkout/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/checkout.json \
		--html=$(REPORTS_DIR)/checkout.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ checkout tests complete. Report: reports/checkout.html"

.PHONY: test-forms
test-forms: $(REPORTS_DIR)
	@echo "→ Running forms tests (skips if FormsApi not running)..."
	FORMS_API_HOST=$(FORMS_API_HOST) \
	$(PYTEST) tests/forms/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/forms.json \
		--html=$(REPORTS_DIR)/forms.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ forms tests complete. Report: reports/forms.html"

.PHONY: test-store-locator
test-store-locator: $(REPORTS_DIR)
	@echo "→ Running store-locator tests (skips if stores-index-updates collection is empty)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	$(PYTEST) tests/store-locator/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/store-locator.json \
		--html=$(REPORTS_DIR)/store-locator.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ store-locator tests complete. Report: reports/store-locator.html"

.PHONY: test-redirections
test-redirections: $(REPORTS_DIR)
	@echo "→ Running redirections tests (skips if redirect proxy not running)..."
	REDIRECTIONS_API_HOST=$(REDIRECTIONS_API_HOST) \
	$(PYTEST) tests/redirections/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/redirections.json \
		--html=$(REPORTS_DIR)/redirections.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ redirections tests complete. Report: reports/redirections.html"

.PHONY: test-all
test-all: $(REPORTS_DIR)
	@echo "→ Running all available tests (Batch B skips gracefully if services not running)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	NAVIGATION_API_HOST=$(NAVIGATION_API_HOST) \
	PRODUCTS_API_HOST=$(PRODUCTS_API_HOST) \
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	PROJECT_LISTS_API_HOST=$(PROJECT_LISTS_API_HOST) \
	SHOPPING_CART_API_HOST=$(SHOPPING_CART_API_HOST) \
	USER_API_HOST=$(USER_API_HOST) \
	PRICING_API_HOST=$(PRICING_API_HOST) \
	ORDER_API_HOST=$(ORDER_API_HOST) \
	FORMS_API_HOST=$(FORMS_API_HOST) \
	REDIRECTIONS_API_HOST=$(REDIRECTIONS_API_HOST) \
	$(PYTEST) tests/ \
		-v \
		--json-report \
		--json-report-file=$(REPORTS_DIR)/results.json \
		--html=$(REPORTS_DIR)/results.html \
		--self-contained-html \
		-p no:cacheprovider
	@echo "✓ All tests complete. Report: reports/results.html"

# The fix-loop target: always produces reports/results.json for the test agent to read.
# Returns exit code 0 even on test failures so the agent can continue and fix.
.PHONY: fix-loop
fix-loop: $(REPORTS_DIR)
	@echo "→ Running fix-loop (tests + JSON report)..."
	FIRESTORE_EMULATOR_HOST=$(EMULATOR_HOST) \
	INDEXING_API_HOST=$(INDEXING_API_HOST) \
	NAVIGATION_API_HOST=$(NAVIGATION_API_HOST) \
	PRODUCTS_API_HOST=$(PRODUCTS_API_HOST) \
	SEARCH_API_HOST=$(SEARCH_API_HOST) \
	PROJECT_LISTS_API_HOST=$(PROJECT_LISTS_API_HOST) \
	SHOPPING_CART_API_HOST=$(SHOPPING_CART_API_HOST) \
	USER_API_HOST=$(USER_API_HOST) \
	PRICING_API_HOST=$(PRICING_API_HOST) \
	ORDER_API_HOST=$(ORDER_API_HOST) \
	FORMS_API_HOST=$(FORMS_API_HOST) \
	REDIRECTIONS_API_HOST=$(REDIRECTIONS_API_HOST) \
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
