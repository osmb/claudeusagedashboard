# ccusage — Project Context

Claude API usage tracker. Collects daily/weekly usage data from the `ccusage` CLI,
stores it in SQLite, and displays it in a Streamlit dashboard.

## Stack

- **Runtime**: Python 3.13, uv
- **Dashboard**: Streamlit + Plotly + Pandas
- **Linting**: ruff (lint + format)
- **Type checking**: ty (Astral)
- **Testing**: pytest + pytest-cov (80% branch coverage minimum)
- **Task runner**: just

## Module layout

```
src/ccusage/
  config.py      — load_config() reads NPX_PATH and DB_PATH from .env
  db.py          — get_connection() context manager; single ensure_schema()
  errors.py      — CcusageError, CollectorError, HistoryImportError
  collector.py   — run_collector(config): fetches daily data via ccusage CLI
  importer.py    — import_history(config): fetches weekly history via ccusage CLI
  data.py        — pure data/aggregation logic for the dashboard (unit-testable)
  dashboard.py   — Streamlit entry point; rendering only, no business logic
```

## Key decisions

- `dashboard.py` is excluded from coverage — Streamlit executes top-level code on
  import, making it incompatible with pytest without a full harness.
- `npx_path` in subprocess calls is from trusted config (not user input) — S603 suppressed.
- DB path defaults to `data/claude_usage.db` (gitignored). Copy your DB there after cloning.

## Common commands

```bash
just run              # start Streamlit dashboard
just collect          # fetch today's usage
just import-history   # fetch full weekly history
just check            # lint + typecheck + tests
just test             # tests only
just fmt              # auto-format
```

## Environment

Copy `.env.example` to `.env` and set `NPX_PATH` to your local `npx` binary (`which npx`).
