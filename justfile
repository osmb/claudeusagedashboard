set dotenv-load := true

# Show available recipes
default:
    @just --list

# Start the Streamlit dashboard
run:
    uv run streamlit run src/ccusage/dashboard.py

# Collect today's usage data
collect:
    uv run python -m ccusage.collector

# Import full weekly history
import-history:
    uv run python -m ccusage.importer

# Run all checks (lint + typecheck + tests)
check: lint typecheck test

# Lint with ruff
lint:
    uv run ruff check src/ tests/
    uv run ruff format --check src/ tests/

# Format code
fmt:
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/

# Type check with ty
typecheck:
    uv run ty check src/

# Run tests with coverage
test:
    uv run pytest

# Check for unused dependencies
deps:
    uv run deptry src/
