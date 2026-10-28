"""Price and ARPU math. One convention for currency, one order for deductions.

Currency convention (FX applied exactly once):
  A region's price is fixed in local currency. `price_index` states that local price in USD terms at the
  reference rates (FY2025 average, `fx_avg_2025`). USD value at any other rates = list x price_index x fx_index,
  where fx_index = sum over the region's currency basket of weight x (reference rate / current rate).
  At reference rates fx_index is exactly 1, so price_index is never converted twice.

Deduction order (multiplicative, so the order changes labels not totals; written out for audit):
  list (USD-equivalent) -> discount -> remove VAT (VAT-inclusive regions only) -> store/processing fee on the
  net-of-VAT price -> net revenue to Discord.
"""
from __future__ import annotations

from dataclasses import dataclass

from nitro_model.assumptions import Assumptions

PLANS = {"NITRO_M": 1, "NITRO_A": 12, "BASIC_M": 1, "BASIC_A": 12}  # value = billing period in months
PLATFORMS = ("WEB", "IOS", "ANDROID")


def region_currencies(a: Assumptions, region: str) -> dict[str, float]:
    """Currency basket for a region: {currency: weight}."""
    return {seg.split("|")[1]: a.get("fx_weight", seg) for seg in a.segments("fx_weight") if seg.startswith(region + "|")}


def fx_index(a: Assumptions, region: str, rates: dict[str, float] | None = None) -> float:
    """USD value multiplier vs reference rates. `rates` are local per USD; None means reference rates (index = 1)."""
    if rates is None:
        return 1.0
    return sum(w * a.get("fx_avg_2025", ccy) / rates[ccy] for ccy, w in region_currencies(a, region).items())


def monthly_list_usd(a: Assumptions, plan: str, region: str, rates: dict[str, float] | None = None) -> float:
    """Monthly-equivalent list price in USD (annual plans recognized ratably over 12 months)."""
    return a.get("list_price", plan) / PLANS[plan] * a.get("price_index", region) * fx_index(a, region, rates)


def store_fee(a: Assumptions, platform: str, first_year: bool) -> float:
    if platform == "IOS":
        return a.get("store_fee", "IOS_Y1" if first_year else "IOS_LATER")
    return a.get("store_fee", platform)


@dataclass(frozen=True)
class PriceSteps:
    list_usd: float
    after_discount: float
    after_tax: float
    net: float


def net_price(a: Assumptions, plan: str, region: str, platform: str, first_year: bool,
              rates: dict[str, float] | None = None) -> PriceSteps:
    """Net monthly revenue per paying subscriber for one plan / region / platform / tenure cell."""
    gross = monthly_list_usd(a, plan, region, rates)
    after_discount = gross * (1 - a.get("avg_discount"))
    after_tax = after_discount * (1 - a.get("indirect_tax", region))
    net = after_tax * (1 - store_fee(a, platform, first_year))
    return PriceSteps(gross, after_discount, after_tax, net)


def book_arpu_walk(a: Assumptions) -> list[tuple[str, float]]:
    """ARPU walk ($/paying sub/month) for the opening subscriber book at reference FX.

    Weights: open_plan_mix x open_region_mix x platform_mix(region) x tenure (open_y1_share).
    Excludes trialists; the cohort engine adds trial dilution when count_trials_as_subs = 1.
    """
    y1 = a.get("open_y1_share")
    totals = dict.fromkeys(["US list", "regional pricing", "discount", "VAT", "store fees"], 0.0)
    for plan in PLANS:
        for region in a.segments("open_region_mix"):
            for platform in PLATFORMS:
                w_base = a.get("open_plan_mix", plan) * a.get("open_region_mix", region) * a.get("platform_mix", f"{region}|{platform}")
                for first_year, w_ten in ((True, y1), (False, 1 - y1)):
                    w = w_base * w_ten
                    s = net_price(a, plan, region, platform, first_year)
                    totals["US list"] += w * a.get("list_price", plan) / PLANS[plan]
                    totals["regional pricing"] += w * s.list_usd
                    totals["discount"] += w * s.after_discount
                    totals["VAT"] += w * s.after_tax
                    totals["store fees"] += w * s.net
    return list(totals.items())


def main() -> None:
    a = Assumptions.load()
    walk = book_arpu_walk(a)
    prev = None
    for step, v in walk:
        factor = "" if prev is None else f"x{v / prev:.3f}"
        print(f"{step:18s} {factor:>7s}  ${v:5.2f}/mo  ${v * 12:6.2f}/yr")
        prev = v
    lo, hi = a.bounds("cal_nitro_rev_2025")
    subs = a.get("cal_subs_mid2025")
    print(f"Public range implies ${lo / subs:.2f}-${hi / subs:.2f} per counted sub per year")


if __name__ == "__main__":
    main()
