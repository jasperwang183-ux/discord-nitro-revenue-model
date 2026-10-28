"""Regenerate every output from data/assumptions.csv.

  python -m nitro_model.run            # workbook, monthly CSV, website data
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
from nitro_model.cohorts import payload, run
from nitro_model.params import build_params, slider_specs

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
SITE = ROOT / "site"


def build_site(a: Assumptions) -> Path:
    """site/data/base.json (inputs, sliders, precomputed base) and site/engine/cohorts.py (the engine itself)."""
    p = build_params(a, "base")
    data = {"params": p, "sliders": slider_specs(a, "base"), "base": payload(p)}
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "engine").mkdir(parents=True, exist_ok=True)
    out = SITE / "data" / "base.json"
    out.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    shutil.copyfile(Path(__file__).with_name("cohorts.py"), SITE / "engine" / "cohorts.py")
    return out


def write_monthly_csv(a: Assumptions) -> Path:
    p = build_params(a, "base")
    res = run(p)
    tot = lambda k: res[k].sum(axis=(0, 1))  # noqa: E731
    df = pd.DataFrame({"month": p["months"], "mau": res["mau"]} | {
        k: tot(k) for k in ("opening", "new", "reactivated", "churned", "closing", "paying", "revenue")})
    df["net_arpu_per_paying_sub"] = np.where(df["paying"] > 0, df["revenue"] / df["paying"], 0.0)
    path = OUTPUTS / "forecast_monthly_base.csv"
    OUTPUTS.mkdir(exist_ok=True)
    df.round(2).to_csv(path, index=False)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", action="store_true", help="only build website data")
    args = ap.parse_args()
    a = Assumptions.load()
    print("wrote", build_site(a))
    if not args.site:
        from nitro_model.excel_export import export
        print("wrote", write_monthly_csv(a))
        xlsx = OUTPUTS / "Nitro_Revenue_Model.xlsx"
        export(xlsx)
        print("wrote", xlsx)


if __name__ == "__main__":
    main()
