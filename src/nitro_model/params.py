"""Flatten Assumptions into the plain, JSON-serializable params dict the engine runs on.

The engine (cohorts.py) never sees the assumptions table: it only sees this dict. The website gets the same
dict as JSON and its sliders edit keys in it, so Python and the browser run identical inputs through identical code.
"""
from __future__ import annotations


from nitro_model.arpu import PLANS, PLATFORMS
from nitro_model.assumptions import Assumptions

REGIONS = ("US_CA", "EUROPE", "LATAM", "APAC", "ROW")
CURRENCIES = ("USD", "EUR", "BRL", "JPY", "INR")
BILLING = {"NITRO_M": "MONTHLY", "NITRO_A": "ANNUAL", "BASIC_M": "MONTHLY", "BASIC_A": "ANNUAL"}
REACT_INTO = {"NITRO_M": "NITRO_M", "NITRO_A": "NITRO_M", "BASIC_M": "BASIC_M", "BASIC_A": "BASIC_M"}
M = 1e6


def build_params(a: Assumptions, scenario: str = "base") -> dict:
    g = lambda id, seg="all": a.get(id, seg, scenario)  # noqa: E731
    plans = list(PLANS)
    start_year = int(g("model_start_year"))
    horizon = int(g("horizon_months"))
    fx_segs = set(a.segments("fx_weight"))
    return {
        "scenario": scenario,
        "regions": list(REGIONS),
        "plans": plans,
        "platforms": list(PLATFORMS),
        "months": [f"{start_year + t // 12}-{t % 12 + 1:02d}" for t in range(horizon)],
        # demand
        "mau0": g("mau_jan2025") * M,
        "mau_growth_first": g("mau_growth_first"),
        "mau_growth_last": g("mau_growth_last"),
        "mau_share": [g("mau_share", r) for r in REGIONS],
        "conv_rate": [g("conv_rate", r) for r in REGIONS],
        "conv_multiplier": g("conv_multiplier"),
        "plan_mix": [g("plan_mix", p) for p in plans],
        "platform_mix": [[g("platform_mix", f"{r}|{pl}") for pl in PLATFORMS] for r in REGIONS],
        # trials
        "trial_share": g("trial_share"),
        "trial_months": int(g("trial_months")),
        "trial_to_paid": g("trial_to_paid"),
        "count_trials_as_subs": int(g("count_trials_as_subs")),
        # retention
        "is_annual": [BILLING[p] == "ANNUAL" for p in plans],
        "churn_m1": g("churn_m1", "MONTHLY"),
        "churn_m2": g("churn_m2", "MONTHLY"),
        "churn_m3": g("churn_m3", "MONTHLY"),
        "churn_tail": g("churn_tail", "MONTHLY"),
        "annual_renewal_first": g("annual_renewal_first", "ANNUAL"),
        "annual_renewal_later": g("annual_renewal_later", "ANNUAL"),
        "react_rate": g("react_rate"),
        "react_window_months": int(g("react_window_months")),
        "react_churn_tail": g("react_churn_tail"),
        "react_into": [plans.index(REACT_INTO[p]) for p in plans],
        # opening book
        "open_subs": g("open_subs") * M,
        "open_plan_mix": [g("open_plan_mix", p) for p in plans],
        "open_region_mix": [g("open_region_mix", r) for r in REGIONS],
        "open_churn_tail": g("open_churn_tail", "MONTHLY"),
        "open_y1_share": g("open_y1_share"),
        # FX: rates are local currency per USD; prices are fixed in local currency at FY2025 average rates
        "currencies": list(CURRENCIES),
        "fx_weights": [[a.get("fx_weight", f"{r}|{c}") if f"{r}|{c}" in fx_segs else 0.0 for c in CURRENCIES]
                       for r in REGIONS],
        "fx_avg": [g("fx_avg_2025", c) for c in CURRENCIES],
        "fx_spot": [g("fx_spot", c) for c in CURRENCIES],
        "fx_spot_t": int(g("fx_spot_month_index")) - 1,
        "policy_rate": [g("policy_rate", c) for c in CURRENCIES],
        "fx_shock": g("fx_shock"),
        "fx_shock_dir": 0,  # scenario control: +1 = USD 10% stronger from Nov 2026, -1 = weaker
        # pricing (USD-equivalent at reference FX)
        "list_price": [g("list_price", p) for p in plans],
        "billing_months": [PLANS[p] for p in plans],
        "price_index": [g("price_index", r) for r in REGIONS],
        "indirect_tax": [g("indirect_tax", r) for r in REGIONS],
        "avg_discount": g("avg_discount"),
        "fee_web": g("store_fee", "WEB"),
        "fee_ios_y1": g("store_fee", "IOS_Y1"),
        "fee_ios_later": g("store_fee", "IOS_LATER"),
        "fee_android": g("store_fee", "ANDROID"),
        # calibration
        "cal_target_subs": g("cal_subs_mid2025") * M,
        "cal_subs_low": a.bounds("cal_subs_mid2025")[0] * M,
        "cal_subs_high": a.bounds("cal_subs_mid2025")[1] * M,
        "cal_month_index": int(g("cal_month_index")),
        "cal_rev_low": a.bounds("cal_nitro_rev_2025")[0] * M,
        "cal_rev_high": a.bounds("cal_nitro_rev_2025")[1] * M,
    }


def slider_specs(a: Assumptions, scenario: str = "base") -> list[dict]:
    """Website sliders: params key, assumption row, bounds from the CSV, and the row's sources."""
    picks = [
        ("conv_multiplier", "conv_multiplier", "all", "Conversion multiplier"),
        ("churn_m1", "churn_m1", "MONTHLY", "Month-1 churn (monthly plans)"),
        ("churn_tail", "churn_tail", "MONTHLY", "Tail churn per month"),
        ("annual_renewal_first", "annual_renewal_first", "ANNUAL", "Annual plan first renewal"),
        ("trial_share", "trial_share", "all", "Share of sign-ups on a free trial"),
        ("trial_to_paid", "trial_to_paid", "all", "Trial-to-paid conversion"),
        ("react_rate", "react_rate", "all", "Monthly reactivation rate"),
        ("mau_growth_first", "mau_growth_first", "all", "MAU growth, 2025"),
    ]
    rows = a.table
    out = []
    for key, aid, seg, label in picks:
        r = rows[(rows["id"] == aid) & (rows["segment"] == seg) & rows["scenario"].isin([scenario, "all"])]
        r = r.sort_values("scenario", key=lambda s: s.eq("all")).iloc[0]
        lo, hi = a.bounds(aid, seg, scenario)
        if lo != lo or hi != hi:  # no range on this row (e.g. base multiplier = 1 by design): span all scenarios
            every = rows[(rows["id"] == aid) & (rows["segment"] == seg)]
            lo = float(every[["low", "value"]].min().min())
            hi = float(every[["high", "value"]].max().max())
        out.append({"key": key, "label": label, "value": float(r["value"]), "low": lo, "high": hi,
                    "unit": r["unit"], "status": r["status"], "sources": r["source_ids"], "as_of": r["as_of"]})
    return out
