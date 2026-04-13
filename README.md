# ccusage — Claude Usage Dashboard

A local Streamlit dashboard that tracks Claude API usage costs and cache efficiency over time.
Usage data is collected via the [`ccusage`](https://github.com/ryanhex53/ccusage) CLI and stored in a local SQLite database.

![Python](https://img.shields.io/badge/python-3.13+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.45+-red)

## Prerequisites

- **Python 3.13+** with [uv](https://docs.astral.sh/uv/) installed
- **Node.js** with `npx` available (`node --version` to verify)
- **ccusage CLI** — no global install needed, `npx ccusage` fetches it automatically

## Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/ccusage.git
cd ccusage

# 2. Install Python dependencies
uv sync

# 3. Configure environment
cp .env.example .env
```

Edit `.env` and set `NPX_PATH` to your local `npx` binary:

```bash
which npx   # e.g. /opt/homebrew/bin/npx  or  /usr/local/bin/npx
```

## Usage

```bash
just import-history   # one-time: import full weekly history into the database
just collect          # fetch today's usage data (run manually or via cron)
just run              # open dashboard at http://localhost:8501
```

### Automating data collection (optional)

To collect usage automatically once per day, add a cron job:

```bash
crontab -e
# Example: collect every day at noon
0 12 * * * cd /path/to/ccusage && .venv/bin/python -m ccusage.collector
```

## Development

```bash
just check    # lint + type check + tests
just fmt      # auto-format with ruff
just test     # tests with coverage report
```

Requirements: 80% branch coverage minimum. Tests live in `tests/`.

## Project Structure

| Path | Purpose |
|------|---------|
| `src/ccusage/config.py` | Config loading from `.env` |
| `src/ccusage/db.py` | SQLite connection and schema |
| `src/ccusage/collector.py` | Daily usage collection via ccusage CLI |
| `src/ccusage/importer.py` | Historical weekly import |
| `src/ccusage/data.py` | Aggregation and data logic |
| `src/ccusage/dashboard.py` | Streamlit dashboard (rendering only) |
| `data/` | SQLite database — gitignored, created at runtime |
| `tmp/` | Scratch files — gitignored, wiped by `just clean` |

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NPX_PATH` | Full path to `npx` binary | `/opt/homebrew/bin/npx` |
| `DB_PATH` | Path to SQLite database file | `data/claude_usage.db` |

See `.env.example` for a template.

## License

MIT
