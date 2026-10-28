# Discord Nitro Subscription Revenue Model

A cohort-based, driver-level forecast of Discord Nitro and Nitro Basic revenue: monthly from Jan 2025 to Dec 2030, built up as subscribers × ARPU × FX, by plan, platform and region.

> **Work in progress.** Milestone 1 of 5 (assumptions and validation) is complete. The cohort engine, Excel workbook, scenarios and exec memo are still to come.

> **Every Discord figure here is a third-party estimate.** Discord is private and has published no financial statements. This is an independent portfolio project, not affiliated with or endorsed by Discord, and it is about method rather than a precise estimate. See [docs/reconciliation.md](docs/reconciliation.md) for where each estimate comes from and how conflicting estimates were reconciled.

## What's here so far
- [`data/assumptions.csv`](data/assumptions.csv): every model input, with a range, status, source and date. [`data/sources.csv`](data/sources.csv) lists the sources and rates how reliable each one is.
- [`docs/reconciliation.md`](docs/reconciliation.md): how the conflicting public estimates were reconciled, and the order calibration follows.
- [`src/nitro_model/`](src/nitro_model/): the assumptions loader and validator, and the ARPU walk with a single FX convention.
- [`tests/`](tests/): checks on assumption quality, FX, VAT and the ARPU band.

## Run it
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -e .   # Windows; use .venv/bin/python on macOS/Linux
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m nitro_model.arpu
```

Built with Claude Code as a drafting tool. The [AI error log](docs/ai_error_log.md) records the errors I caught in its drafts.
