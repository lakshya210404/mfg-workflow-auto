.PHONY: up down build logs test lint migrate seed simulate demo clean help

# ── Docker ────────────────────────────────────────────────────────────────────
up:          ## Start all services
	docker compose up -d

down:        ## Stop all services
	docker compose down

build:       ## Rebuild Docker images
	docker compose build

logs:        ## Tail API logs
	docker compose logs -f api

restart:     ## Restart API container
	docker compose restart api

# ── Database ──────────────────────────────────────────────────────────────────
migrate:     ## Run Alembic migrations
	docker compose exec api alembic upgrade head

seed:        ## Seed default stations + automation rules
	docker compose exec api python scripts/seed_db.py

# ── Simulation ────────────────────────────────────────────────────────────────
simulate:    ## Run 20-WO factory simulation
	python scripts/simulate_factory.py --api-url http://localhost:8000 --work-orders 20

demo:        ## One-command curl demo
	bash scripts/demo.sh

# ── Testing ───────────────────────────────────────────────────────────────────
test:        ## Run pytest with coverage
	pytest tests/ --cov=app --cov-report=term-missing -v

lint:        ## Lint with Ruff
	ruff check app/ tests/ scripts/

format:      ## Auto-fix lint issues
	ruff check --fix app/ tests/ scripts/

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:       ## Remove containers + volumes
	docker compose down -v --remove-orphans

# ── Help ──────────────────────────────────────────────────────────────────────
help:        ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
