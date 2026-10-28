"""Flatten Assumptions into the plain, JSON-serializable params dict the engine runs on.

The engine (cohorts.py) never sees the assumptions table: it only sees this dict. The website gets the same
dict as JSON and its sliders edit keys in it, so Python and the browser run identical inputs through identical code.

History vs forecast: FY2025 is the calibration year and is the same in every scenario. The ERA_SPEC keys exist twice:
`params["hist"]` holds base values used before the forecast start, and the top-level keys hold the scenario's values
used for sign-ups, trials and reactivations from the forecast start. Sliders edit the top-level (forecast) keys.
"""
from __future__ import annotations

from nitro_model.arpu import PLANS, PLATFORMS
from nitro_model.assumptions import Assumptions

REGIONS = ("US_CA", "EUROPE", "LATAM", "APAC", "ROW")
CURRENCIES = ("USD", "EUR", "BRL", "JPY", "INR")
BILLING = {"NITRO_M": "MONTHLY", "NITRO_A": "ANNUAL", "BASIC_M": "MONTHLY", "BASIC_A": "ANNUAL"}
REACT_INTO = {"NITRO_M": "NITRO_M", "NITRO_A": "NITRO_M", "BASIC_M": "BASIC_M", "BASIC_A": "BASIC_M"}
M = 1e6

# (params key, assumption id, segment): drivers that can differ between history and forecast.
ERA_SPEC = [
    ("conv_multiplier", "conv_multiplier", "all"), ("trial_share", "trial_share", "all"),
    ("trial_to_paid", "trial_to_paid", "all"), ("churn_m1", "churn_m1", "MONTHLY"), ("churn_m2", "churn_m2", "MONTHLY"),
    ("churn_m3", "churn_m3", "MONTHLY"), ("churn_tail", "churn_tail", "MONTHLY"),
    ("annual_renewal_first", "annual_renewal_first", "ANNUAL"), ("annual_renewal_later", "annual_renewal_later", "ANNUAL"),
    ("react_rate", "react_rate", "all"), ("react_window_months", "react_window_months", "all"),
    ("react_churn_tail", "react_churn_tail", "all"),
]
INT_KEYS = {"react_window_months"}


def build_params(a: Assumptions, scenario: str = "base") -> dict:
    g = lambda id, seg="all": a.get(id, seg, scenario)  # noqa: E731
    plans = list(PLANS)
    start_year = int(g("model_start_year"))
    horizon = int(g("horizon_months"))
    fx_segs = set(a.segments("fx_weight"))

    def era(scen: str) -> dict:
        vals = {k: a.get(aid, seg, scen) for k, aid, seg in ERA_SPEC}
        return {k: int(v) if k in INT_KEYS else v for k, v in vals.items()}

    return era(scenario) | {
        "scenario": scenario,
        "regions": list(REGIONS),
        "plans": plans,
        "platforms": list(PLATFORMS),
        "months": [f"{start_year + t // 12}-{t % 12 + 1:02d}" for t in range(horizon)],
        # demand
        "mau0": g("mau_jan2025") * M,
        "mau_growth_2025": g("mau_growth_2025"),
        "mau_growth_first": g("mau_growth_first"),
        "mau_growth_last": g("mau_growth_last"),
        "mau_share": [g("mau_share", r) for r in REGIONS],
        "conv_rate": [g("conv_rate", r) for r in REGIONS],
        "plan_mix": [g("plan_mix", p) for p in plans],
        "platform_mix": [[g("platform_mix", f"{r}|{pl}") for pl in PLATFORMS] for r in REGIONS],
        # history vs forecast
        "hist": era("base"),
        "forecast_start_t": int(g("forecast_start_month_index")) - 1,
        # experiment (cohort-based churn change; conversion and price change apply by calendar month)
        "exp_enabled": int(g("exp_enabled")),
        "exp_start_t": int(g("exp_start_month_index")) - 1,
        "exp_conv_lift": g("exp_conv_lift"),
        "exp_churn_change": g("exp_churn_change"),
        "exp_price_change": g("exp_price_change"),
        # trials
        "trial_months": int(g("trial_months")),
        "count_trials_as_subs": int(g("count_trials_as_subs")),
        # retention
        "is_annual": [BILLING[p] == "ANNUAL" for p in plans],
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


SLIDERS = [
    ("mau_growth_first", "mau_growth_first", "all", "MAU growth, 2026"),
    ("conv_multiplier", "conv_multiplier", "all", "Conversion multiplier"),
    ("churn_m1", "churn_m1", "MONTHLY", "Month-1 churn (monthly plans)"),
    ("churn_tail", "churn_tail", "MONTHLY", "Tail churn per month"),
    ("annual_renewal_first", "annual_renewal_first", "ANNUAL", "Annual plan first renewal"),
    ("trial_share", "trial_share", "all", "Share of sign-ups on a free trial"),
    ("trial_to_paid", "trial_to_paid", "all", "Trial-to-paid conversion"),
    ("react_rate", "react_rate", "all", "Monthly reactivation rate"),
]
EXPERIMENT_SLIDERS = [
    ("exp_conv_lift", "exp_conv_lift", "all", "Conversion lift"),
    ("exp_churn_change", "exp_churn_change", "all", "Churn change (new sign-ups)"),
    ("exp_price_change", "exp_price_change", "all", "Price change (everyone)"),
]


def slider_specs(a: Assumptions, scenario: str = "base", picks=SLIDERS) -> list[dict]:
    """Website sliders: params key, bounds spanning every scenario's documented range, sources, and status."""
    rows = a.table
    out = []
    for key, aid, seg, label in picks:
        r = rows[(rows["id"] == aid) & (rows["segment"] == seg) & rows["scenario"].isin([scenario, "all"])]
        r = r.sort_values("scenario", key=lambda s: s.eq("all")).iloc[0]
        every = rows[(rows["id"] == aid) & (rows["segment"] == seg)]
        lo = float(every[["low", "value"]].min().min())
        hi = float(every[["high", "value"]].max().max())
        out.append({"key": key, "label": label, "value": float(r["value"]), "low": lo, "high": hi,
                    "unit": r["unit"], "status": r["status"], "sources": r["source_ids"], "as_of": r["as_of"]})
    return out
