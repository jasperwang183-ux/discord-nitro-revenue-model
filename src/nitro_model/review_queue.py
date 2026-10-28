"""Write docs/review_queue.md: every status=proposed assumption, grouped by expected revenue impact."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from nitro_model.assumptions import Assumptions

OUT = Path(__file__).resolve().parents[2] / "docs" / "review_queue.md"

TIERS = {
    "High impact, weakest evidence": [
        "trial_share", "trial_to_paid", "count_trials_as_subs", "plan_mix", "open_plan_mix",
        "price_index", "conv_rate", "conv_multiplier",
    ],
    "Medium impact": [
        "mau_jan2025", "mau_share", "mau_growth_first", "mau_growth_last", "platform_mix", "indirect_tax",
        "avg_discount", "annual_renewal_later", "react_rate", "react_window_months", "react_churn_tail",
        "open_region_mix", "open_y1_share", "store_fee",
    ],
}


def _fmt(v) -> str:
    return "" if pd.isna(v) else f"{v:g}"


def render(a: Assumptions) -> str:
    q = a.review_queue().copy()
    tier_of = {aid: tier for tier, ids in TIERS.items() for aid in ids}
    q["tier"] = q["id"].map(tier_of).fillna("Low impact")
    lines = [
        "# Assumption review queue",
        "",
        f"{len(q)} rows with `status=proposed`, generated from `data/assumptions.csv` by `python -m nitro_model.review_queue`.",
        "For each row, fill in Decision: **accept**, **change to X**, or **needs source**. Then update the CSV status.",
        "",
    ]
    for tier in [*TIERS, "Low impact"]:
        rows = q[q["tier"] == tier]
        if rows.empty:
            continue
        lines += [f"## {tier} ({len(rows)})", "",
                  "| id | segment | scenario | value | unit | range | sources | notes | Decision |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for _, r in rows.iterrows():
            rng = f"{_fmt(r['low'])}–{_fmt(r['high'])}" if pd.notna(r["low"]) else ""
            notes = "" if pd.isna(r["notes"]) else str(r["notes"]).replace("|", "/")
            lines.append(f"| {r['id']} | {r['segment']} | {r['scenario']} | {_fmt(r['value'])} | {r['unit']} | "
                         f"{rng} | {r['source_ids']} | {notes} | |")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT.write_text(render(Assumptions.load()), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
