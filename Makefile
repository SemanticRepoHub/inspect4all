.PHONY: help install dev-install test test-cov lint format type-check clean build pre-commit-install pre-commit-run all-checks docker-build docker-build-multiplatform docker-down docker-test docker-lint

# Default target
# .DEFAULT_GOAL := build
.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	uv sync --no-dev

dev-install: ## Install development dependencies
	uv sync --dev

test: ## Run tests
	uv run pytest

test-cov: ## Run tests with coverage
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html

lint: ## Run linting
	uv run ruff check .

lint-fix: ## Run linting with auto-fix
	uv run ruff check . --fix

format: ## Format code
	uv run ruff format .

format-check: ## Check code formatting
	uv run ruff format . --check

type-check: ## Run type checking
	uv run mypy src

clean: ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build: ## Build wheel and sdist for release
	uv build

docker-build: ## Build production Docker image
	docker build --target production -t inspect4all .

docker-build-all: ## Build production image for multi-platform (amd64 and arm64)
	docker buildx build --platform linux/amd64,linux/arm64 --target production -t inspect4all .

docker-down: ## Stop Docker containers
	docker compose down

docker-test: ## Run tests in Docker
	docker compose run --rm test

docker-lint: ## Run linting in Docker
	docker compose run --rm lint

pre-commit-install: ## Install pre-commit hooks
	uv run pre-commit install

pre-commit-run: ## Run pre-commit on all files
	uv run pre-commit run --all-files

all-checks: lint format-check type-check test ## Run all quality checks

# Development workflow
dev-setup: dev-install pre-commit-install ## Set up development environment
	@echo "Development environment set up successfully!"
	@echo "Run 'make help' to see available commands."

ci: all-checks ## Run CI-like checks locally
