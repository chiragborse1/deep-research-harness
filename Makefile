# Makefile for deep-research-harness.
# Every target must work on a clean checkout with no API key set.

UV      := uv
PY      := $(UV) run python
PKG     := drh

.DEFAULT_GOAL := help
.PHONY: help install build test lint format typecheck bench demo security scan-docs \
        check clean ci quickstart

help:  ## Show this help.
	@echo "deep-research-harness - available targets:"
	@grep -E "^[a-zA-Z_-]+:.*?## .*$$" $(MAKEFILE_LIST) \
		| awk "BEGIN {FS = ":.*?## "} {printf "  \\033[36m%-16s\\033[0m %s\\n", $$1, $$2}"

install:  ## Sync the dev environment.
	$(UV) sync --all-extras

build:  ## Build the wheel and sdist.
	$(UV) build

test:  ## Run the test suite with coverage (>=80% gate).
	$(UV) run pytest -m "not slow and not network"

lint:  ## Run ruff check, ruff format --check, and the docstring gate.
	$(UV) run ruff check .
	$(UV) run ruff format --check --diff .
	$(PY) scripts/check_docs.py

format:  ## Auto-format the code.
	$(UV) run ruff format .
	$(UV) run ruff check --fix .

typecheck:  ## Run mypy --strict and the endpoint-independence gate.
	$(UV) run mypy
	$(PY) scripts/check_endpoint_independence.py

security:  ## Run pip-audit and bandit.
	$(UV) export --format requirements-txt --no-emit-project --no-hashes -o requirements-audit.txt
	$(UV) export --format requirements-txt --no-emit-project --no-hashes -o requirements-audit.txt
	$(UV) run pip-audit --strict -r requirements-audit.txt
	$(UV) run bandit -r src --severity-level medium

bench:  ## Run the committed benchmark suite.
	$(UV) run pytest bench -m benchmark --benchmark-only --benchmark-json=bench/results/latest.json

demo:  ## Run the offline end-to-end demo (no API key required).
	$(UV) run python -m drh.cli demo

quickstart:  ## Verify the README quickstart is real and runnable.
	$(PY) scripts/verify_quickstart.py

scan-docs:  ## Alias for the docstring gate.
	$(PY) scripts/check_docs.py

ci: build test lint typecheck security  ## Run every gate CI runs.

clean:  ## Remove build and cache artifacts.
	@echo "Cleaning..."
	$(UV) run python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in (pathlib.Path('dist'), pathlib.Path('build'), pathlib.Path('.pytest_cache'), pathlib.Path('.mypy_cache'), pathlib.Path('.ruff_cache'), pathlib.Path('.benchmarks'))]"
	@echo "Done."