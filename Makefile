# Run `make help` for the list.
PY ?= python3.12
VENV ?= .venv
BIN = $(VENV)/bin

.PHONY: help setup api web jobs test lint format check golden build

help:            ## Show this help
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

setup:           ## Create the virtualenv and install Python + frontend dependencies
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -e ".[dev,ai,api]"
	npm ci

api:             ## Run the API on http://localhost:8000 (docs at /docs)
	$(BIN)/uvicorn gauge.api.app:app --reload

web:             ## Run the frontend on http://localhost:5173
	npm run dev

jobs:            ## Run the daily job pipeline once (ingest, watch, health)
	$(BIN)/python -m gauge.jobs daily

test:            ## Python tests
	$(BIN)/pytest

lint:            ## Python lint + format check, frontend type check
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .
	npm run check

format:          ## Format Python
	$(BIN)/ruff format .

golden:          ## End-to-end golden path on fixtures
	$(BIN)/python -m gauge.golden

build:           ## Production frontend build
	npm run build

check: lint test golden build  ## Everything CI runs
