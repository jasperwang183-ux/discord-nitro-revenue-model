"""Single source of model inputs: data/assumptions.csv, cited against data/sources.csv.

Every number the engine uses comes through `Assumptions.get`. Nothing is hardcoded downstream.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

REQUIRED_COLUMNS = [
    "id", "group", "segment", "scenario", "value", "unit",
    "low", "high", "status", "source_ids", "as_of", "notes",
]
STATUSES = {"verified", "anchor", "benchmark", "derived", "proposed", "design"}
SCENARIOS = ("base", "upside", "downside")
ANALYST_SOURCE = "A01"

# Groups of rows whose values must sum to 1 within each key (id, prefix of segment before "|").
SHARE_GROUPS = ["mau_share", "plan_mix", "platform_mix", "open_plan_mix", "open_region_mix", "fx_weight"]


class AssumptionError(ValueError):
    pass


@dataclass(frozen=True)
class Assumptions:
    table: pd.DataFrame
    sources: pd.DataFrame

    @classmethod
    def load(cls, data_dir: Path = DATA_DIR) -> "Assumptions":
        table = pd.read_csv(data_dir / "assumptions.csv", dtype={"source_ids": str, "segment": str})
        sources = pd.read_csv(data_dir / "sources.csv", dtype=str)
        obj = cls(table, sources)
        obj.validate()
        return obj

    def get(self, id: str, segment: str = "all", scenario: str = "base") -> float:
        """Return a value, preferring a scenario-specific row over an `all` row."""
        rows = self.table[(self.table["id"] == id) & (self.table["segment"] == segment)]
        exact = rows[rows["scenario"] == scenario]
        if len(exact) == 0:
            exact = rows[rows["scenario"] == "all"]
        if len(exact) != 1:
            raise AssumptionError(f"{id}[{segment}, {scenario}]: expected 1 row, found {len(exact)}")
        return float(exact["value"].iloc[0])

    def bounds(self, id: str, segment: str = "all", scenario: str = "base") -> tuple[float, float]:
        rows = self.table[(self.table["id"] == id) & (self.table["segment"] == segment)
                          & self.table["scenario"].isin([scenario, "all"])]
        row = rows.sort_values("scenario", key=lambda s: s.eq("all")).iloc[0]
        return float(row["low"]), float(row["high"])

    def segments(self, id: str) -> list[str]:
        return list(dict.fromkeys(self.table.loc[self.table["id"] == id, "segment"]))

    def validate(self) -> None:
        errors = validation_errors(self.table, self.sources)
        if errors:
            raise AssumptionError("Assumptions failed validation:\n  " + "\n  ".join(errors))

    def review_queue(self) -> pd.DataFrame:
        """Rows still waiting on owner sign-off (status=proposed)."""
        return self.table[self.table["status"] == "proposed"]


def validation_errors(table: pd.DataFrame, sources: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in table.columns]
    if missing:
        return [f"missing columns: {missing}"]

    dupes = table[table.duplicated(["id", "segment", "scenario"], keep=False)]
    for _, r in dupes.iterrows():
        errors.append(f"duplicate key {r['id']}[{r['segment']}, {r['scenario']}]")

    known_sources = set(sources["source_id"])
    for i, r in table.iterrows():
        key = f"row {i + 2} {r['id']}[{r['segment']}, {r['scenario']}]"
        if r["status"] not in STATUSES:
            errors.append(f"{key}: unknown status {r['status']!r}")
        if r["scenario"] not in (*SCENARIOS, "all"):
            errors.append(f"{key}: unknown scenario {r['scenario']!r}")
        if pd.isna(r["value"]):
            errors.append(f"{key}: missing value")
        if pd.isna(r["as_of"]) or not str(r["as_of"]).strip():
            errors.append(f"{key}: missing as_of date")
        ids = [] if pd.isna(r["source_ids"]) else [s.strip() for s in str(r["source_ids"]).split(";") if s.strip()]
        if not ids:
            errors.append(f"{key}: missing source_ids")
        for s in ids:
            if s not in known_sources:
                errors.append(f"{key}: unknown source {s!r}")
        if ids == [ANALYST_SOURCE] and r["status"] != "proposed":
            errors.append(f"{key}: analyst-only source must have status=proposed")
        lo, hi, v = r["low"], r["high"], r["value"]
        if pd.notna(lo) and pd.notna(hi) and lo > hi:
            errors.append(f"{key}: low {lo} > high {hi}")
        if pd.notna(lo) and pd.notna(v) and v < lo:
            errors.append(f"{key}: value {v} below low {lo}")
        if pd.notna(hi) and pd.notna(v) and v > hi:
            errors.append(f"{key}: value {v} above high {hi}")

    for gid in SHARE_GROUPS:
        rows = table[table["id"] == gid].copy()
        rows["bucket"] = rows["segment"].str.split("|").str[0].where(rows["segment"].str.contains(r"\|"), "all")
        for (bucket, scen), grp in rows.groupby(["bucket", "scenario"]):
            total = grp["value"].sum()
            if abs(total - 1.0) > 1e-9:
                errors.append(f"{gid}[{bucket}, {scen}]: shares sum to {total:.4f}, expected 1")

    # A scenario-specific input must be defined for every scenario, or not at all.
    scen_rows = table[table["scenario"] != "all"]
    for (aid, seg), grp in scen_rows.groupby(["id", "segment"]):
        missing_sc = set(SCENARIOS) - set(grp["scenario"])
        if missing_sc:
            errors.append(f"{aid}[{seg}]: missing scenarios {sorted(missing_sc)}")
    return errors
