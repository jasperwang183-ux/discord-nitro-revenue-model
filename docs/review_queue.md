# Assumption review queue

77 rows with `status=proposed`, generated from `data/assumptions.csv` by `python -m nitro_model.review_queue`.
For each row, fill in Decision: **accept**, **change to X**, or **needs source**. Then update the CSV status.

## High impact, weakest evidence (24)

| id | segment | scenario | value | unit | range | sources | notes | Decision |
|---|---|---|---|---|---|---|---|---|
| conv_rate | US_CA | all | 0.0045 | gross adds / MAU / month | 0.003–0.006 | A01 | Back-solved: ~0.65M gross adds/mo holds ~7.3M subs at a ~13-month blended lifetime. Split by willingness to pay. Recalibrated in M3 | |
| conv_rate | EUROPE | all | 0.0032 | gross adds / MAU / month | 0.002–0.0045 | A01 |  | |
| conv_rate | LATAM | all | 0.0015 | gross adds / MAU / month | 0.0008–0.0025 | A01 |  | |
| conv_rate | APAC | all | 0.0018 | gross adds / MAU / month | 0.001–0.0028 | A01 |  | |
| conv_rate | ROW | all | 0.0015 | gross adds / MAU / month | 0.0008–0.0025 | A01 |  | |
| conv_multiplier | all | upside | 1.1 | x | 1.05–1.2 | A01 |  | |
| conv_multiplier | all | downside | 0.9 | x | 0.8–0.95 | A01 |  | |
| plan_mix | NITRO_M | all | 0.45 | share of gross adds | 0.35–0.55 | A01 | No public plan mix. Drives most of the ARPU gap vs list price | |
| plan_mix | NITRO_A | all | 0.15 | share of gross adds | 0.08–0.25 | S15;A01 | Duolingo shows annual share can reach 47-71% when pushed hard; Discord does not push annual that hard | |
| plan_mix | BASIC_M | all | 0.32 | share of gross adds | 0.2–0.45 | A01 |  | |
| plan_mix | BASIC_A | all | 0.08 | share of gross adds | 0.03–0.15 | A01 |  | |
| open_plan_mix | NITRO_M | all | 0.4 | share | 0.3–0.5 | A01 | Tenured book skews to annual vs gross adds | |
| open_plan_mix | NITRO_A | all | 0.22 | share | 0.12–0.3 | A01 |  | |
| open_plan_mix | BASIC_M | all | 0.28 | share | 0.2–0.4 | A01 |  | |
| open_plan_mix | BASIC_A | all | 0.1 | share | 0.05–0.15 | A01 |  | |
| price_index | EUROPE | all | 1.1 | x US price in USD at 2025 avg FX | 1–1.15 | A01 | Assumes EUR 9.99 VAT-inclusive (~$11.30 at 2025 avg FX). EUR price NOT verified: check at checkout | |
| price_index | LATAM | all | 0.45 | x US price in USD at 2025 avg FX | 0.3–0.6 | S10;A01 | Localized pricing exists in Brazil per forum posts; level unverified | |
| price_index | APAC | all | 0.75 | x US price in USD at 2025 avg FX | 0.5–1 | S10;A01 | Japan localized; India reportedly not localized (~INR 850 = ~$10) | |
| price_index | ROW | all | 0.6 | x US price in USD at 2025 avg FX | 0.3–0.8 | S10;A01 | Turkey ~$3.20 per forum anecdote; RoW blends deep and no discounts | |
| trial_share | all | all | 0.15 | share of gross adds starting on a free trial | 0–0.4 | A01 | Partner promos and free trial months. Trialists pay $0 while in trial, then convert or leave | |
| trial_to_paid | all | base | 0.4 | share of trialists converting to paid | 0.25–0.6 | S16;A01 | No public Discord rate. RevenueCat (S16) shows trial conversion clusters at install day but the rate is not in the public preview | |
| trial_to_paid | all | upside | 0.5 | share of trialists converting to paid | 0.25–0.6 | A01 |  | |
| trial_to_paid | all | downside | 0.3 | share of trialists converting to paid | 0.25–0.6 | A01 |  | |
| count_trials_as_subs | all | all | 1 | flag | 0–1 | S13;A01 | Definition: does the 7.3M anchor count trialists? Spotify counts trialists as subscribers (S13). Unknown for the third-party Discord figure | |

## Medium impact (47)

| id | segment | scenario | value | unit | range | sources | notes | Decision |
|---|---|---|---|---|---|---|---|---|
| mau_jan2025 | all | all | 225 | M users | 200–260 | S06;S02;S03;A01 | Discord says 200M+ (May 2025); trackers say 227.7M (2024) to 250-259M (2025). Start below tracker midpoint: trackers likely mix visits and registered users | |
| mau_share | US_CA | all | 0.31 | share | 0.27–0.35 | S07;A01 | Semrush web traffic US 29.1% plus Canada. Caveat: web traffic misses desktop-app and mobile-app use so regional mix may skew; conv_rate by region absorbs part of the error | |
| mau_share | EUROPE | all | 0.28 | share | 0.22–0.32 | S07;A01 | No direct Europe figure found; judgment from country traffic tail (DE/FR/UK/PL) | |
| mau_share | LATAM | all | 0.14 | share | 0.1–0.18 | S07;A01 | Brazil 7.25% of traffic plus rest of LatAm | |
| mau_share | APAC | all | 0.15 | share | 0.1–0.2 | S07;A01 | India 4.9% of traffic plus Japan/SEA/ANZ | |
| mau_share | ROW | all | 0.12 | share | 0.08–0.16 | S07;A01 | Turkey, Russia, MENA, Africa | |
| mau_growth_first | all | base | 0.1 | YoY | 0.06–0.14 | S02;S03;A01 | Tracker YoY 2024-25: 8.7% (Resourcera) to 13.8% (Feedough); applies to 2025 | |
| mau_growth_first | all | upside | 0.13 | YoY | 0.1–0.16 | S02;A01 | Near the high tracker growth rate | |
| mau_growth_first | all | downside | 0.06 | YoY | 0.03–0.09 | A01 |  | |
| mau_growth_last | all | base | 0.04 | YoY | 0.02–0.06 | A01 | Applies to 2030; linear fade from first-year growth | |
| mau_growth_last | all | upside | 0.06 | YoY | 0.04–0.08 | A01 |  | |
| mau_growth_last | all | downside | 0 | YoY | -0.03–0.02 | A01 | Flat MAU by 2030 | |
| platform_mix | US_CA|WEB | all | 0.55 | share of gross adds | 0.45–0.65 | A01 | Desktop-first product; web/desktop billing avoids app store fees | |
| platform_mix | US_CA|IOS | all | 0.3 | share of gross adds | 0.2–0.4 | A01 | High iPhone share in US | |
| platform_mix | US_CA|ANDROID | all | 0.15 | share of gross adds | 0.1–0.2 | A01 |  | |
| platform_mix | EUROPE|WEB | all | 0.6 | share of gross adds | 0.5–0.7 | A01 |  | |
| platform_mix | EUROPE|IOS | all | 0.22 | share of gross adds | 0.15–0.3 | A01 |  | |
| platform_mix | EUROPE|ANDROID | all | 0.18 | share of gross adds | 0.12–0.25 | A01 |  | |
| platform_mix | LATAM|WEB | all | 0.55 | share of gross adds | 0.45–0.65 | A01 |  | |
| platform_mix | LATAM|IOS | all | 0.1 | share of gross adds | 0.05–0.15 | A01 | Android-dominant region | |
| platform_mix | LATAM|ANDROID | all | 0.35 | share of gross adds | 0.25–0.45 | A01 |  | |
| platform_mix | APAC|WEB | all | 0.55 | share of gross adds | 0.45–0.65 | A01 |  | |
| platform_mix | APAC|IOS | all | 0.2 | share of gross adds | 0.1–0.3 | A01 | Japan iOS-heavy; India Android-heavy | |
| platform_mix | APAC|ANDROID | all | 0.25 | share of gross adds | 0.15–0.35 | A01 |  | |
| platform_mix | ROW|WEB | all | 0.55 | share of gross adds | 0.45–0.65 | A01 |  | |
| platform_mix | ROW|IOS | all | 0.15 | share of gross adds | 0.1–0.2 | A01 |  | |
| platform_mix | ROW|ANDROID | all | 0.3 | share of gross adds | 0.2–0.4 | A01 |  | |
| annual_renewal_later | ANNUAL | base | 0.65 | share renewing | 0.55–0.75 | A01 | No public second-renewal data found; tenured renewers are stickier | |
| annual_renewal_later | ANNUAL | upside | 0.75 | share renewing | 0.65–0.85 | A01 |  | |
| annual_renewal_later | ANNUAL | downside | 0.55 | share renewing | 0.45–0.65 | A01 |  | |
| react_rate | all | base | 0.015 | share of churned pool / month | 0.005–0.03 | A01 | No public win-back data; churned users within the window return at this rate | |
| react_rate | all | upside | 0.02 | share of churned pool / month | 0.01–0.03 | A01 |  | |
| react_rate | all | downside | 0.01 | share of churned pool / month | 0.005–0.02 | A01 |  | |
| react_window_months | all | all | 24 | months | 12–36 | A01 | Churned users older than this drop out of the pool | |
| react_churn_tail | all | all | 0.07 | share of survivors / month | 0.05–0.1 | A01 | Reactivated users rejoin on monthly plans; flatter than new-user month-1 churn but above base tail | |
| open_region_mix | US_CA | all | 0.45 | share | 0.38–0.52 | A01 | Payers skew to high-income regions vs MAU mix | |
| open_region_mix | EUROPE | all | 0.3 | share | 0.25–0.35 | A01 |  | |
| open_region_mix | LATAM | all | 0.08 | share | 0.05–0.12 | A01 |  | |
| open_region_mix | APAC | all | 0.1 | share | 0.06–0.14 | A01 |  | |
| open_region_mix | ROW | all | 0.07 | share | 0.04–0.1 | A01 |  | |
| open_y1_share | all | all | 0.35 | share of book in first year of tenure | 0.25–0.45 | A01 | Drives the Apple 30% vs 15% fee split for the opening book only; new cohorts get tenure from the cohort engine | |
| indirect_tax | EUROPE | all | 0.167 | share of gross price | 0.15–0.18 | A01 | Prices shown VAT-inclusive. A ~20% VAT rate removes 0.20/1.20 = 16.7% of the gross price; EU rates run 17-27% | |
| indirect_tax | LATAM | all | 0.12 | share of gross price | 0.05–0.2 | A01 | Digital services taxes vary by country | |
| indirect_tax | APAC | all | 0.1 | share of gross price | 0.05–0.15 | A01 | Japan consumption tax 10%; India GST 18% | |
| indirect_tax | ROW | all | 0.1 | share of gross price | 0.05–0.2 | A01 |  | |
| avg_discount | all | all | 0.05 | share of list price | 0–0.15 | A01 | Average discount on paying subscribers (sale pricing; first-month offers) | |
| store_fee | WEB | all | 0.03 | share of gross | 0.02–0.04 | A01 | Card processing on direct web/desktop billing | |

## Low impact (6)

| id | segment | scenario | value | unit | range | sources | notes | Decision |
|---|---|---|---|---|---|---|---|---|
| trial_months | all | all | 1 | months | 1–3 | A01 | Length of the free period | |
| fx_weight | APAC|JPY | all | 0.5 | weight | 0.3–0.7 | A01 | APAC basket: JPY/INR blend | |
| fx_weight | APAC|INR | all | 0.5 | weight | 0.3–0.7 | A01 |  | |
| exp_conv_lift | all | all | 0.05 | relative | 0–0.15 | A01 | Example: new perk lifts conversion 5% relative (hypothetical A/B readout) | |
| exp_churn_change | all | all | -0.03 | relative | -0.1–0.05 | A01 | Negative = lower churn | |
| exp_price_change | all | all | 0 | relative | -0.2–0.2 | A01 | Set e.g. 0.10 to test a 10% price increase | |
