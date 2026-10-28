"""Regenerate every output from data/assumptions.csv.

  python -m nitro_model.run            # workbooks, CSVs, website data
  python -m nitro_model.run --site     # website data only (used by the GitHub Pages workflow)
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from nitro_model.assumptions import Assumptions
from nitro_model.cohorts import forecast_revenue, payload, run, sensitivity
from nitro_model.params import EXPERIMENT_SLIDERS, build_params, slider_specs

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
SITE = ROOT / "site"
SCENARIOS = ("base", "upside", "downside")


def scenario_runs(a: Assumptions) -> dict:
    """params, payload (with the bridge from base) and sensitivity for every scenario."""
    base = build_params(a, "base")
    out = {}
    for sc in SCENARIOS:
        p = build_params(a, sc)
        out[sc] = {"params": p, "payload": payload(p, base=base), "sensitivity": sensitivity(p, slider_specs(a, sc))}
    return out


def build_site(a: Assumptions, runs: dict) -> Path:
    """site/data/base.json (inputs, sliders, precomputed scenarios) and site/engine/cohorts.py (the engine itself)."""
    data = {
        "sliders": slider_specs(a, "base"),
        "experiment_sliders": slider_specs(a, "base", EXPERIMENT_SLIDERS),
        "scenarios": runs,
    }
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "engine").mkdir(parents=True, exist_ok=True)
    out = SITE / "data" / "base.json"
    out.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    shutil.copyfile(Path(__file__).with_name("cohorts.py"), SITE / "engine" / "cohorts.py")
    return out


def write_csvs(runs: dict) -> list[Path]:
    OUTPUTS.mkdir(exist_ok=True)
    paths = []

    p = runs["base"]["params"]
    res = run(p)
    tot = lambda k: res[k].sum(axis=(0, 1))  # noqa: E731
    df = pd.DataFrame({"month": p["months"], "mau": res["mau"]} | {
        k: tot(k) for k in ("opening", "new", "reactivated", "churned", "closing", "paying", "revenue")})
    df["net_arpu_per_paying_sub"] = np.where(df["paying"] > 0, df["revenue"] / df["paying"], 0.0)
    paths.append(OUTPUTS / "forecast_monthly_base.csv")
    df.round(2).to_csv(paths[-1], index=False)

    rows = []
    for sc, r in runs.items():
        s = r["payload"]["summary"]
        rev = np.array(s["revenue"]).reshape(-1, 12).sum(axis=1)
        years = [m[:4] for m in s["months"][::12]]
        rows.append({"scenario": sc} | {f"FY{y} revenue $M": v / 1e6 for y, v in zip(years, rev)} | {
            "Dec subscribers final year (M)": s["closing"][-1] / 1e6,
            "Forecast revenue FY26-30 $M": r["payload"]["forecast_revenue"] / 1e6,
            "Revenue CAGR FY25-30": (rev[-1] / rev[0]) ** (1 / (len(rev) - 1)) - 1})
    paths.append(OUTPUTS / "scenario_table.csv")
    pd.DataFrame(rows).round(4).to_csv(paths[-1], index=False)

    bridge_rows = [{"scenario": sc, "step": st["name"], "delta $M": st["delta"] / 1e6}
                   for sc, r in runs.items() if r["payload"]["bridge"] for st in r["payload"]["bridge"]["steps"]]
    paths.append(OUTPUTS / "bridge_vs_base.csv")
    pd.DataFrame(bridge_rows).round(2).to_csv(paths[-1], index=False)

    sens = [{"scenario": sc, "assumption": x["label"], "low": x["low"], "high": x["high"],
             "revenue at low $M": x["rev_low"] / 1e6, "revenue at high $M": x["rev_high"] / 1e6,
             "swing % of forecast revenue": x["pct_swing"]} for sc, r in runs.items() for x in r["sensitivity"]]
    paths.append(OUTPUTS / "sensitivity.csv")
    pd.DataFrame(sens).round(4).to_csv(paths[-1], index=False)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", action="store_true", help="only build website data")
    args = ap.parse_args()
    a = Assumptions.load()
    runs = scenario_runs(a)
    print("wrote", build_site(a, runs))
    if not args.site:
        from nitro_model.excel_export import export
        for path in write_csvs(runs):
            print("wrote", path)
        for sc in SCENARIOS:
            xlsx = OUTPUTS / ("Nitro_Revenue_Model.xlsx" if sc == "base" else f"Nitro_Revenue_Model_{sc}.xlsx")
            export(xlsx, sc)
            print("wrote", xlsx)


if __name__ == "__main__":
    main()
