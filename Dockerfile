# syntax=docker/dockerfile:1

# enry stage - builds the go-enry c-shared library for the target platform.
# The binary is gitignored and platform-specific, so it is compiled here
# rather than copied from the build context. Keep GO_ENRY_VERSION in sync
# with the Makefile.
FROM golang:1.22-bookworm AS enry-builder
ARG GO_ENRY_VERSION=v2.9.4
WORKDIR /build
RUN git clone --quiet --depth 1 --branch "${GO_ENRY_VERSION}" \
    https://github.com/go-enry/go-enry.git
RUN cd go-enry/shared && CGO_ENABLED=1 go build -buildmode=c-shared \
    -o /build/libenry.so enry.go

# Build stage - installs dependencies and builds the package
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv

WORKDIR /app

# Copy project files and source
COPY pyproject.toml uv.lock README.md hatch_build.py ./
COPY src/ ./src/

# Provide the compiled language-detection library expected by discovery/enry.py
COPY --from=enry-builder /build/libenry.so ./src/inspect4all/libs/libenry.so

# Allow version to be passed when .git is not in the build context
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# Install production dependencies and the package itself (non-editable so
# the package is fully contained within the venv for the production stage)
RUN uv sync --no-dev --frozen --no-editable

# Production stage - minimal image with just the venv
FROM python:3.12-slim AS production

LABEL org.opencontainers.image.title="inspect4all"
LABEL org.opencontainers.image.description="Language-agnostic tool for inspecting and understanding software repositories"

# Create non-root user
RUN useradd --create-home --no-log-init appuser

WORKDIR /app

# Copy virtual environment (with installed package) from builder
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

USER appuser

ENTRYPOINT ["inspect4all"]

# Development stage - includes dev tools and dependencies
FROM python:3.12-slim AS development

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files and source
COPY pyproject.toml uv.lock README.md hatch_build.py ./
COPY src/ ./src/

# Provide the compiled language-detection library expected by discovery/enry.py
COPY --from=enry-builder /build/libenry.so ./src/inspect4all/libs/libenry.so

# Allow version to be passed when .git is not in the build context
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# Install all dependencies including dev
RUN uv sync --dev --frozen

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Interactive shell for development
CMD ["bash"]
