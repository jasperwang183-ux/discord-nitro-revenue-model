# Reconciling the public estimates

Discord is private. It filed confidentially for an IPO on 2026-01-06 ([S20](../data/sources.csv)), and no public S-1 existed as of 2026-10-21 ([S23](../data/sources.csv)). One May 2026 report claims a 277-page public S-1 ([S22](../data/sources.csv)), but more recent sources contradict it, so I treat it as unconfirmed. Every anchor below is therefore a third-party estimate, and the estimates disagree. This page records how each disagreement was settled. Source IDs refer to [`data/sources.csv`](../data/sources.csv).

## 1. Nitro subscribers: one number, little disagreement
| Estimate | Date | Source |
|---|---|---|
| 7.3M (+17% YoY) | mid-2025 | Feedough (S02), Komo (S01), Resourcera (S03) |
| 5M–8M | 2024 | analyst roundups |

**Decision:** I calibrate to 7.3M in mid-2025, with a ±10% test band. Backing out 17% YoY growth gives an opening book of 7.3 / 1.17^0.5 ≈ **6.75M in Jan 2025**.
**Caveat:** every site repeats the same figure, so this is probably *one* estimate echoed many times, not three independent ones.

## 2. Nitro revenue (FY2025): reconcile definitions before drivers
| Estimate | Implied $/sub/yr at 7.3M | Nitro share of total | Source |
|---|---|---|---|
| $280M | $38.36 | 29.5% of $950M | Resourcera (S03) |
| ~$450M | $61.64 | ~80% of $561M | Feedough (S02) |

**Step 1: the two figures probably don't measure the same thing.** The gap is mostly definitional, not behavioral:
- **What "Nitro" includes.** Resourcera splits Server Boosts out as a separate $430M line (45% of its total). Feedough has no Boosts line, and Nitro at ~80% of $561M leaves room for little else. So Feedough's "Nitro" most likely includes Boosts, which are sold to Nitro holders and largely paid by the same people.
- **What "total revenue" means.** The two totals ($561M vs $950M) are 1.7x apart, and the low cluster contradicts itself (section 3). Applying a share to an incompatible total produces an incompatible Nitro figure.
- **Gross vs net.** Neither source says whether its figure is before or after app store fees and VAT. That alone is worth 15–25%.

So the band is **not** "how many subscribers pay $0". Modeling a free-subscriber share sized to close it would be a plug.

**Step 2: then see where the bottom-up drivers land.** Run `python -m nitro_model.arpu`. It prices the opening book per **paying** subscriber, with one FX convention and a fixed deduction order (see the docstring in [`arpu.py`](../src/nitro_model/arpu.py)):

| Step | Factor | $/paying sub/mo | $/yr |
|---|---|---|---|
| US list price at book plan mix (40/22/28/10 across Nitro M/A and Basic M/A) | — | $6.92 | $83.00 |
| Regional pricing | ×0.933 | $6.45 | $77.43 |
| Discounts | ×0.950 | $6.13 | $73.56 |
| VAT (VAT-inclusive regions only) | ×0.924 | $5.66 | $67.95 |
| App store and processing fees, on the net-of-VAT price | ×0.905 | **$5.12** | **$61.47** |

Paying-subscriber ARPU lands at **$61/yr**, the top of the $38–$62 band. That is consistent with the higher estimate *if* that estimate is net revenue on paying subscribers.

**Step 3: promos are modeled as cohorts, not a flat share.** A share `trial_share` of gross adds start on a free trial lasting `trial_months`. A share `trial_to_paid` then convert and follow the paid churn curve. The rest leave. Whether trialists count in the 7.3M anchor is a separate definitional flag (`count_trials_as_subs`; Spotify counts them, per S13). The cohort engine (M2) works out how much trialists dilute ARPU per counted subscriber. Nothing is back-solved to hit $280M.

**Decision (proposed, needs owner sign-off):** the calibration test is that modeled FY2025 Nitro revenue falls inside **[$280M, $450M]**, a band rather than a point. The ARPU test checks the same band per subscriber. The memo will say which end the model sits nearer and which definition that implies.

## 3. Total revenue: two clusters that can't both be right
| Estimate | Source |
|---|---|
| $561M (2025, +29%) | Feedough (S02) |
| ~$725M ARR (end-2024) | Sacra (S04) |
| $879M (2024), $950M (2025) | Resourcera (S03) |
| $1.1B–$1.2B (2025) | Revenue Memo (S05) |

The low cluster contradicts itself. $725M ARR at end-2024 is not compatible with $561M of 2025 revenue growing 29%. That would require revenue to *fall* below the exit run-rate. Most likely the sources measure different things: ARR vs. recognized revenue, gross vs. net of app store fees, or with vs. without Boosts.
**Decision:** total revenue is out of scope. It is used only as a sanity check on Nitro's share (25% to 80% depending on the pairing, which is itself a sign the sources aren't comparable). Boosts appear as one context row ($430M to $520M, S03).

## 4. MAU: company figure vs. trackers
| Estimate | Source |
|---|---|
| 200M+ (May 2025, company) | S06 |
| 227.7M (2024) → 259.2M (2025) | Feedough (S02) |
| 230M (2024) → 250M (2025) | Resourcera (S03) |

**Decision (proposed):** **225M in Jan 2025**, growing 10% in 2025 in the base case and fading linearly to 4% by 2030. The company's own "200M+" sets a floor. Trackers likely blend visits and registered users, so I start below their midpoint. Implied penetration is 7.3M / ~235M ≈ 3.1%, between the 2.8% (259M) and 3.65% (200M) bounds.
**Regional mix** uses Semrush web traffic as a proxy (US 29.1%, Brazil 7.25%, India 4.9%; S07). Web traffic misses use of the desktop and mobile apps, so the regional mix may be skewed. Regional `conv_rate` absorbs part of that error, because calibration targets subscribers, not MAU. These shares are **proposed**.

## 5. Churn benchmarks: why the scenario mapping changed
The plan mapped *Duolingo-style* churn to the **upside** case. The data says otherwise. Duolingo's S-1 shows only **~9% of monthly subscribers renew at 12 months** and ~40% of annual subscribers (S15), which is steeper than Spotify. The mapping is therefore:

| Scenario | Monthly-plan peer | Annual-plan peer |
|---|---|---|
| Upside | Spotify mature markets: 1–2% monthly churn (S14) | ~55% first renewal |
| Base | Spotify global: 3.9–4.8% (S13, S14) plus RevenueCat app benchmarks (S16) | ~45% (Duolingo 40%, RevenueCat up to 36%) |
| Downside | Duolingo monthly / RevenueCat expensive-monthly 6.7% 12-mo retention (S15, S16) | ~35% |

Base monthly-plan survival at 12 months works out to about 34% (30% / 14% / 9% churn in months 1–3, then 5% a month).
**Caveat:** Spotify is a utility with lower churn than a discretionary perk bundle, so Nitro's base tail (5%) sits above Spotify's global 3.9–4.8%.

## 6. FX: the only primary-source data in the model
- **2025 actuals:** FRED annual averages (S17): USD/EUR 1.1306, JPY 149.57, BRL 5.589, INR 87.15.
- **Spot:** Banque de France, 2026-10-19 (S18), crossed through EUR to per-USD: EUR 0.8909, JPY 158.24, BRL 5.045, INR 94.93.
- **Forwards:** covered interest parity from spot, using policy rates (S19). **Weak source:** a June 2026 snapshot from a low-authority site, and the BoJ figure conflicts (0.75% vs 1.00%). Verify on the central bank sites before M3.
- **Path:** 2025 at the FY average, Jan–Oct 2026 linear to spot, then forwards. ±10% USD shock from Nov 2026 per the PRD.
- **Convention (FX applied once):** prices are fixed in local currency. `price_index` states that local price in USD at the FY2025 reference rates. USD revenue = list × `price_index` × FX index, where the index = Σ basket weight × reference rate ÷ current rate. At the reference rates the index is exactly 1, so nothing is converted twice. `fx_weight` only blends currencies within a region's basket (APAC = JPY/INR) and never touches price. Both rules are tested in `tests/test_arpu.py`.

## 7. Calibration order: one target can't pin three drivers
The subscriber anchor (7.3M in mid-2025, +17% YoY) is one stock figure. Conversion, churn and reactivation all move it, so fitting all three to it would be unidentified: any mix of the three could hit it. The order is fixed:
1. **Churn curves and annual renewal** come from external benchmarks (section 5). They are never fitted.
2. **Reactivation and trial conversion** are bounded judgment calls. The M4 sensitivity tests them; if 5-year revenue moves less than ~2% across their ranges, they stop being debated.
3. **Conversion is the only back-solved driver.** `conv_rate` is a monthly flow (gross adds per MAU per month, e.g. 0.45% in US/CA). It is not the ~3.1% penetration stock. The regional *pattern* stays as proposed, and calibration solves for **one scalar** on it, so subscribers hit 7.3M ± 10% in mid-2025.
4. **Revenue is not calibrated.** It is checked against the $280M–$450M band, and whatever lands is reported.

## Open items for the owner
1. Sign off on or replace every `status=proposed` row (see [review_queue.md](review_queue.md), regenerate with `python -m nitro_model.review_queue`).
2. Verify EUR, BRL and JPY Nitro prices at checkout (the regional price index is the weakest pricing input).
3. Check EDGAR for a public Discord S-1 before shipping. If one exists, swap in reported figures and log the variance.
4. Note that the Shattered / Storyboard18 sources named in the PRD were not found in search. The $725M ARR figure is attributed to Sacra (S04) instead.
