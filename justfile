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

# Run all checks (lint + typecheck + tests + dependency audit)
check: lint typecheck test audit

# Audit dependencies for known vulnerabilities
audit:
    uv audit

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

# Remove disposable scratch files
clean:
    rm -rf tmp/*
    touch tmp/.gitkeep

# Install dashboard as macOS background service (auto-starts at login)
service-install:
    cp launchd/com.osmb.ccusage.plist ~/Library/LaunchAgents/
    launchctl load ~/Library/LaunchAgents/com.osmb.ccusage.plist
    @echo "Service installed. Dashboard available at http://localhost:8501"

# Remove dashboard service
service-uninstall:
    launchctl unload ~/Library/LaunchAgents/com.osmb.ccusage.plist
    rm -f ~/Library/LaunchAgents/com.osmb.ccusage.plist
    @echo "Service removed."

# Start dashboard service manually
service-start:
    launchctl start com.osmb.ccusage

# Stop dashboard service
service-stop:
    launchctl stop com.osmb.ccusage

# Show service status and last log lines
service-status:
    @launchctl list | grep ccusage || echo "Service not running"
    @echo "--- last 20 log lines ---"
    @tail -20 tmp/dashboard.log 2>/dev/null || echo "(no log yet)"
