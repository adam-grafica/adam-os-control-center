.PHONY: help install dev build deploy clean test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (Python + npm)
	@echo "==> Installing Python dependencies..."
	python3 -m venv venv || virtualenv venv
	. venv/bin/activate && pip install -e . 2>/dev/null || \
		. venv/bin/activate && pip install fastapi uvicorn sqlalchemy aiosqlite python-dotenv pydantic
	@echo "==> Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✓ All dependencies installed."

dev: ## Start development servers (frontend + backend)
	@./scripts/dev.sh

build: ## Build frontend for production
	@./scripts/build_frontend.sh

deploy: ## Generate deployment instructions and systemd service
	@./scripts/deploy.sh

clean: ## Remove generated files and caches
	@echo "==> Cleaning..."
	rm -rf __pycache__ .pytest_cache .mypy_cache
	rm -rf frontend/node_modules frontend/build
	rm -rf venv
	rm -rf build dist *.egg-info
	find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
	@echo "✓ Clean complete."

test: ## Run backend tests
	@echo "==> Running backend tests..."
	cd backend && python -m pytest -v
