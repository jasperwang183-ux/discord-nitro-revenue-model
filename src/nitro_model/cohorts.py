"""Cohort engine. numpy only, so the website can run this exact file in the browser via Pyodide.

Conventions
- Month t = 0..T-1 is Jan 2025..Dec 2030. Arrays are shaped [region, plan, month].
- A cohort that starts in month c is counted in closing subscribers of month c (age 0) and pays for that month.
  survival[a] = share of the cohort still subscribed at age a; survival[0] = 1.
- Active subscribers = sum over cohorts c <= t of starts[c] * survival[t - c]: a convolution, computed by `window`.
  Churn in month t = sum of starts[c] * (survival[a-1] - survival[a]) with a = t - c.
- Monthly plans lose churn_m1/m2/m3 in months 1-3, then churn_tail. Annual plans keep everyone 12 months, then
  renew at annual_renewal_first, then annual_renewal_later at each later anniversary.
- Free trials last trial_months, pay $0, then trial_to_paid convert into a paid cohort; the rest leave.
- Reactivation: paid churners (new cohorts and opening book) wait in a pool; react_rate of what remains returns each
  month, for react_window_months. They rejoin the monthly plan of the same tier and churn at react_churn_tail.
  Reactivated users who churn again do not re-enter the pool.
- Opening book: monthly plans decay at open_churn_tail; annual plans renew in 12 equal monthly buckets at
  annual_renewal_later. Its first-year share (for the Apple fee) runs off linearly over 12 months.
- Revenue is at reference FX (FX path arrives in M3). Apple's fee is 30% for cohort ages 0-11, 15% after.
"""
from __future__ import annotations

import numpy as np


# ---------- curves ----------

def monthly_survival(p: dict, T: int) -> np.ndarray:
    hazard = np.full(T, p["churn_tail"])
    hazard[0] = 0.0
    hazard[1:4] = [p["churn_m1"], p["churn_m2"], p["churn_m3"]][: max(0, min(3, T - 1))]
    return np.cumprod(1 - hazard)


def annual_survival(p: dict, T: int) -> np.ndarray:
    renewals = np.arange(T) // 12
    s = np.where(renewals == 0, 1.0, p["annual_renewal_first"] * p["annual_renewal_later"] ** np.maximum(renewals - 1, 0))
    return s


def react_survival(p: dict, T: int) -> np.ndarray:
    return (1 - p["react_churn_tail"]) ** np.arange(T)


def churn_kernel(survival: np.ndarray) -> np.ndarray:
    d = np.zeros_like(survival)
    d[1:] = survival[:-1] - survival[1:]
    return d


def react_kernel(p: dict, T: int) -> np.ndarray:
    d = np.arange(T)
    rr = p["react_rate"]
    return np.where((d >= 1) & (d <= p["react_window_months"]), rr * (1 - rr) ** np.maximum(d - 1, 0), 0.0)


def window(x: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """y[..., t] = sum_a x[..., t - a] * kernel[..., a]. kernel may be 1-D or broadcast per plan ([P, T])."""
    T = x.shape[-1]
    y = np.zeros_like(x)
    for a in range(T):
        y[..., a:] += x[..., : T - a] * kernel[..., a : a + 1]
    return y


def plan_curves(p: dict, T: int) -> tuple[np.ndarray, np.ndarray]:
    """Survival and churn kernels per plan: [P, T]."""
    ms, an = monthly_survival(p, T), annual_survival(p, T)
    surv = np.array([an if annual else ms for annual in p["is_annual"]])
    return surv, np.array([churn_kernel(s) for s in surv])


# ---------- prices ----------

def net_prices(p: dict) -> tuple[np.ndarray, np.ndarray]:
    """Net monthly revenue per paying sub [R, P], for first-year and later tenure. Mirrors arpu.net_price."""
    lst = np.array(p["list_price"]) / np.array(p["billing_months"])
    gross = np.array(p["price_index"])[:, None] * lst[None, :]
    after_tax = gross * (1 - p["avg_discount"]) * (1 - np.array(p["indirect_tax"]))[:, None]
    mix = np.array(p["platform_mix"])  # [R, (web, ios, android)]
    keep_y1 = mix @ np.array([1 - p["fee_web"], 1 - p["fee_ios_y1"], 1 - p["fee_android"]])
    keep_later = mix @ np.array([1 - p["fee_web"], 1 - p["fee_ios_later"], 1 - p["fee_android"]])
    return after_tax * keep_y1[:, None], after_tax * keep_later[:, None]


# ---------- engine ----------

def mau_path(p: dict, T: int) -> np.ndarray:
    years = T // 12
    yr = np.arange(T) // 12
    g = p["mau_growth_first"] + (p["mau_growth_last"] - p["mau_growth_first"]) * yr / max(years - 1, 1)
    factor = (1 + g) ** (1 / 12)
    factor[0] = 1.0
    return p["mau0"] * np.cumprod(factor)


def shift(x: np.ndarray, k: int) -> np.ndarray:
    y = np.zeros_like(x)
    if k < x.shape[-1]:
        y[..., k:] = x[..., : x.shape[-1] - k]
    return y


def run(p: dict, k_cal: float | None = None) -> dict:
    """Run the model. k_cal scales conversion; None solves it so subscribers hit the calibration anchor."""
    if k_cal is None:
        k_cal = calibrate(p)
    T = len(p["months"])
    R, P = len(p["regions"]), len(p["plans"])
    t = np.arange(T)

    mau = mau_path(p, T)
    mau_r = np.array(p["mau_share"])[:, None] * mau[None, :]
    gross_adds = (mau_r * (np.array(p["conv_rate"]) * p["conv_multiplier"] * k_cal)[:, None])[:, None, :] \
        * np.array(p["plan_mix"])[None, :, None]

    # trials
    k = p["trial_months"]
    trial_starts = gross_adds * p["trial_share"]
    direct = gross_adds - trial_starts
    trial_ending = shift(trial_starts, k)
    trial_converted = trial_ending * p["trial_to_paid"]
    trial_lost = trial_ending - trial_converted
    trial_active = np.cumsum(trial_starts, axis=-1) - np.cumsum(trial_ending, axis=-1)

    # paid cohorts
    surv, churn_k = plan_curves(p, T)
    paid_starts = direct + trial_converted
    paid_active = window(paid_starts, surv)
    paid_active_y1 = window(paid_starts, np.where(t < 12, surv, 0.0))
    paid_churn = window(paid_starts, churn_k)

    # opening book
    L0 = p["open_subs"] * np.array(p["open_region_mix"])[:, None] * np.array(p["open_plan_mix"])[None, :]
    q, m = t // 12, t % 12
    legacy_monthly = (1 - p["open_churn_tail"]) ** (t + 1)
    rl = p["annual_renewal_later"]
    legacy_annual = ((m + 1) * rl ** (q + 1) + (11 - m) * rl ** q) / 12
    legacy_curve = np.array([legacy_annual if annual else legacy_monthly for annual in p["is_annual"]])
    legacy = L0[:, :, None] * legacy_curve[None, :, :]
    legacy_prev = np.concatenate([L0[:, :, None], legacy[:, :, :-1]], axis=-1)
    legacy_churn = legacy_prev - legacy
    legacy_y1_frac = p["open_y1_share"] * np.maximum(0.0, 1 - t / 12)

    # reactivation
    react_out = window(paid_churn + legacy_churn, react_kernel(p, T))
    react_starts = np.zeros_like(react_out)
    for src, dst in enumerate(p["react_into"]):
        react_starts[:, dst, :] += react_out[:, src, :]
    rs = react_survival(p, T)
    react_active = window(react_starts, rs)
    react_active_y1 = window(react_starts, np.where(t < 12, rs, 0.0))
    react_churn = window(react_starts, churn_kernel(rs))

    # roll-forward (counted definition)
    cnt = p["count_trials_as_subs"]
    paying = legacy + paid_active + react_active
    closing = paying + cnt * trial_active
    new = direct + (trial_starts if cnt else trial_converted)
    churned = legacy_churn + paid_churn + react_churn + (trial_lost if cnt else 0.0)
    opening = np.concatenate([L0[:, :, None], closing[:, :, :-1]], axis=-1)

    # revenue
    p_y1, p_later = net_prices(p)
    y1 = paid_active_y1 + react_active_y1 + legacy * legacy_y1_frac
    revenue = y1 * p_y1[:, :, None] + (paying - y1) * p_later[:, :, None]

    return {
        "k_cal": k_cal, "months": p["months"], "mau": mau, "gross_adds": gross_adds,
        "trial_starts": trial_starts, "trial_active": trial_active, "trial_converted": trial_converted, "trial_lost": trial_lost,
        "direct": direct, "paid_starts": paid_starts, "paid_active": paid_active, "paid_churn": paid_churn,
        "legacy": legacy, "legacy_churn": legacy_churn, "react_out": react_out, "react_starts": react_starts,
        "react_active": react_active, "react_churn": react_churn,
        "opening": opening, "new": new, "reactivated": react_starts, "churned": churned, "closing": closing,
        "paying": paying, "revenue": revenue, "net_price_y1": p_y1, "net_price_later": p_later,
        "survival": surv, "react_survival": rs,
    }


def calibrate(p: dict) -> float:
    """Solve the conversion scalar so counted subscribers hit the anchor in the calibration month.

    Subscribers are affine in the scalar (new cohorts and their reactivations scale with it; the opening book and
    its reactivations do not), so two runs give the exact solution.
    """
    i = p["cal_month_index"] - 1
    s0 = run(p, 0.0)["closing"][..., i].sum()
    s1 = run(p, 1.0)["closing"][..., i].sum()
    return (p["cal_target_subs"] - s0) / (s1 - s0)


def cohort_triangle(p: dict, res: dict) -> np.ndarray:
    """Paid cohorts one by one: [R, P, cohort, month]. Independent of `window`, used to tie out paid_active."""
    T = len(p["months"])
    starts, surv = res["paid_starts"], res["survival"]
    tri = np.zeros(starts.shape[:2] + (T, T))
    for c in range(T):
        tri[:, :, c, c:] = starts[:, :, c : c + 1] * surv[None, :, : T - c]
    return tri


def summary(res: dict) -> dict:
    """Totals across regions and plans, as plain lists (for JSON and the website)."""
    tot = lambda k: res[k].sum(axis=(0, 1)).tolist()  # noqa: E731
    return {k: tot(k) for k in ("opening", "new", "reactivated", "churned", "closing", "paying", "revenue")} | {
        "k_cal": float(res["k_cal"]), "months": res["months"], "mau": res["mau"].tolist()}


# Sign-up years folded into one layer from this offset on (2028-2030), to keep the stack at seven bands.
LAYER_FOLD_FROM = 3


def layers(p: dict, res: dict) -> dict:
    """Closing subscribers split by where they came from: opening book, sign-up year, reactivated, in trial."""
    T = len(p["months"])
    start = int(p["months"][0][:4])
    years = np.minimum(np.arange(T) // 12, LAYER_FOLD_FROM)
    out = {"Opening book": res["legacy"].sum(axis=(0, 1)).tolist()}
    for y in range(LAYER_FOLD_FROM + 1):
        label = str(start + y) if y < LAYER_FOLD_FROM else f"{start + y}-{str(start + T // 12 - 1)[2:]}"
        starts = res["paid_starts"] * (years == y)
        out[f"Signed up {label}"] = window(starts, res["survival"]).sum(axis=(0, 1)).tolist()
    out["Reactivated"] = res["react_active"].sum(axis=(0, 1)).tolist()
    out["In free trial"] = (p["count_trials_as_subs"] * res["trial_active"]).sum(axis=(0, 1)).tolist()
    return out


def payload(p: dict, k_cal: float | None = None) -> dict:
    """Everything the website draws for one set of inputs, plus the live checks."""
    res = run(p, k_cal)
    lay = layers(p, res)
    gap = res["opening"] + res["new"] + res["reactivated"] - res["churned"] - res["closing"]
    tie = cohort_triangle(p, res).sum(axis=2) - res["paid_active"]
    stack = np.sum([np.array(v) for v in lay.values()], axis=0)
    i = p["cal_month_index"] - 1
    return {
        "summary": summary(res),
        "layers": lay,
        "checks": {
            "rollforward_gap": float(np.abs(gap).max()),
            "cohort_tie_gap": float(np.abs(tie).max()),
            "layers_tie_gap": float(np.abs(stack - res["closing"].sum(axis=(0, 1))).max()),
            "cal_subs": float(res["closing"][..., i].sum()),
            "cal_target": p["cal_target_subs"],
            "cal_band": [p["cal_subs_low"], p["cal_subs_high"]],
            "fy1_revenue": float(res["revenue"][..., :12].sum()),
            "band": [p["cal_rev_low"], p["cal_rev_high"]],
        },
    }
