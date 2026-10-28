# Discord Nitro Subscription Revenue Model

A cohort-based, driver-level forecast of Discord Nitro and Nitro Basic revenue: monthly from Jan 2025 to Dec 2030, built up as subscribers × ARPU × FX, by plan, platform and region.

**[Live model →](https://jasperwang183-ux.github.io/discord-nitro-revenue-model/)** Move the sliders and the same Python engine the tests check reruns in your browser.

> **Work in progress.** Milestones 1–4 are done: assumptions, the cohort engine with Excel workbook and website, the drivers (ARPU walk, FX paths and shock), and scenarios with an experiment toggle, driver bridge and sensitivity. The exec memo is still to come.

> **Every Discord figure here is a third-party estimate.** Discord is private and has published no financial statements. This is an independent portfolio project, not affiliated with or endorsed by Discord, and it is about method rather than a precise estimate. See [docs/reconciliation.md](docs/reconciliation.md) for where each estimate comes from and how conflicting estimates were reconciled.

## How it works
1. **Sign-ups:** MAU × a conversion rate by region × plan mix (Nitro / Basic, monthly / annual). Some sign-ups start on a free trial.
2. **Cohorts:** each month's sign-ups decay along a survival curve. Monthly plans lose 30%, 14% and 9% in months 1–3, then 5% a month. Annual plans keep everyone for 12 months, then 45% renew.
3. **Reactivation:** 1.5% of the last 24 months' churners return each month, on a monthly plan.
4. **Revenue:** paying subscribers × net price × FX. Net price starts from list and applies regional pricing, discounts, VAT, and app store fees: Apple takes 30% in a subscriber's first year and 15% after, so the fee drops when each cohort ages past 12 months. Prices are fixed in local currency, so FX moves USD revenue: FY2025 is priced at average rates, then the rates move to the Oct 2026 spot, then follow interest-rate-parity forwards, with a ±10% USD shock.
5. **Calibration:** only one number is fitted, a conversion scalar, so subscribers hit the 7.3M anchor in Jun 2025. Churn comes from peer benchmarks. Revenue is checked against the $280–450M public range, never tuned to it.
6. **Scenarios:** FY2025 is fixed history. From Jan 2026, downside / base / upside change growth, conversion, trials, churn and reactivation for new sign-ups: FY2026–30 revenue is $2.15B / $2.92B / $3.94B. A driver bridge and a sensitivity chart show what moves it. Retention is the largest driver, and reactivation, an unsourced assumption, is the third.

## One engine, checked three ways
- [`src/nitro_model/cohorts.py`](src/nitro_model/cohorts.py) is the engine. It is numpy-only, so the website runs this exact file in the browser through Pyodide.
- [`outputs/Nitro_Revenue_Model.xlsx`](outputs/Nitro_Revenue_Model.xlsx) (plus `_upside` and `_downside` versions) is a formula-driven workbook generated from the same assumptions. Every number traces back to the Assumptions sheet, and `Cohort_US_NitroM` lays one segment out as a full cohort triangle.
- [`tests/`](tests/) contains 86 tests, including:
  - subscribers roll forward every month (opening + new + reactivated − churned = closing)
  - cohorts tie to the total
  - **the workbook matches Python to the dollar** in every month and segment, in every scenario and with the experiment on
  - calibration hits the anchor
  - every assumption has a source and date

  CI runs them all before each deploy.

## Repo map
| Path | What |
|---|---|
| [`data/assumptions.csv`](data/assumptions.csv) | Every input with value, range, status, source and date |
| [`data/sources.csv`](data/sources.csv) | Sources and how reliable each one is |
| [`docs/reconciliation.md`](docs/reconciliation.md) | How conflicting public estimates were reconciled; calibration order |
| [`docs/review_queue.md`](docs/review_queue.md) | Assumptions still awaiting sign-off |
| [`outputs/`](outputs/) | Workbooks per scenario; monthly forecast, scenario table, bridge and sensitivity CSVs |
| [`docs/ai_error_log.md`](docs/ai_error_log.md) | Errors I caught in Claude Code's drafts |
| [`site/`](site/) | The website (static; deployed to GitHub Pages by CI) |

## Run it
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt -e .   # Windows; use .venv/bin/python on macOS/Linux
.venv/Scripts/python -m pytest -q
.venv/Scripts/python -m nitro_model.run                        # workbook, monthly CSV, website data
.venv/Scripts/python -m http.server 8765 --directory site      # then open http://localhost:8765
```

Built with Claude Code as a drafting tool; I own the assumptions and the checks.
