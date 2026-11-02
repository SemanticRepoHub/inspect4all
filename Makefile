.PHONY: help install dev-install test smoke test-cov lint format type-check clean build libenry pre-commit-install pre-commit-run all-checks docker-build docker-build-multiplatform docker-down docker-test docker-lint

# go-enry release used to build the language-detection shared library
GO_ENRY_VERSION ?= v2.9.4

# Shared-library extension is platform-specific; keep this in sync with
# default_lib_name() in src/inspect4all/discovery/enry.py.
ifeq ($(OS),Windows_NT)
	LIBENRY_NAME := libenry.dll
else ifeq ($(shell uname -s),Darwin)
	LIBENRY_NAME := libenry.dylib
else
	LIBENRY_NAME := libenry.so
endif

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

smoke: ## Run ground-truth smoke validation (requires dissertation dataset)
	uv run pytest -m smoke tests/smoke

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

libenry: ## Build the go-enry shared library into src/inspect4all/libs/ (requires Go)
	rm -rf build/go-enry
	git clone --quiet --depth 1 --branch $(GO_ENRY_VERSION) \
		https://github.com/go-enry/go-enry.git build/go-enry
	cd build/go-enry/shared && CGO_ENABLED=1 go build -buildmode=c-shared \
		-o $(CURDIR)/src/inspect4all/libs/$(LIBENRY_NAME) enry.go
	rm -f $(CURDIR)/src/inspect4all/libs/libenry.h
	rm -rf build/go-enry

docker-build: ## Build production Docker image
	RAW_VERSION=$$(uv run python -c "from importlib.metadata import version; print(version('inspect4all'))" 2>/dev/null || echo "0.0.0"); \
	DOCKER_VERSION=$$(echo "$$RAW_VERSION" | tr '+' '_'); \
	docker build --target production \
		-t inspect4all \
		-t "inspect4all:$$DOCKER_VERSION" \
		--build-arg "SETUPTOOLS_SCM_PRETEND_VERSION=$$RAW_VERSION" \
		.

docker-build-all: ## Build production image for multi-platform (amd64 and arm64)
	RAW_VERSION=$$(uv run python -c "from importlib.metadata import version; print(version('inspect4all'))" 2>/dev/null || echo "0.0.0"); \
	DOCKER_VERSION=$$(echo "$$RAW_VERSION" | tr '+' '_'); \
	docker buildx build --platform linux/amd64,linux/arm64 \
		--target production \
		-t inspect4all \
		-t "inspect4all:$$DOCKER_VERSION" \
		--build-arg "SETUPTOOLS_SCM_PRETEND_VERSION=$$RAW_VERSION" \
		.

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

all-checks: lint format-check type-check test smoke ## Run all quality checks

# Development workflow
dev-setup: dev-install pre-commit-install ## Set up development environment
	@echo "Development environment set up successfully!"
	@echo "Run 'make help' to see available commands."

ci: all-checks ## Run CI-like checks locally
