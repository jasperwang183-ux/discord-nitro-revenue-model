# Nitro revenue: where the next five years come from

> **DRAFT for Jasper to rewrite.** Claude Code drafted this from the model's outputs. Every number comes from `python -m nitro_model.run`, and all Discord figures are third-party estimates.

**To:** Revenue Finance · **Re:** Nitro subscription forecast, FY2026–30 · **Model:** [live](https://jasperwang183-ux.github.io/discord-nitro-revenue-model/) · [repo](https://github.com/jasperwang183-ux/discord-nitro-revenue-model)

## Bottom line
The model puts Nitro at ~$450M today (FY2025, net of VAT, discounts and store fees). In the base case it reaches **$656M by FY2030**, or **$2.9B cumulative over FY2026–30**. The plausible range is $2.2B–$3.9B, and **retention explains more of that range than anything else**. The single largest lever, though, is price, and it is untested: Nitro's US price hasn't changed in years.

## What the model says
- **FY2025 reconciles.** It is calibrated to the 7.3M-subscriber estimate, and net revenue lands at $447M, inside the $280–450M public range. Reaching the $280M end requires a Basic-heavy plan mix; trials and regional pricing can't get there alone.
- **Scenarios:** FY2026–30 revenue is $2.15B downside, $2.92B base, $3.94B upside. Retention is the largest step in both directions: +$587M up, −$340M down.
- **Value of each lever** (FY2026–30 revenue, everything else held):

| Lever | Revenue |
|---|---|
| Price +10%, everyone, if volume holds | **+$292M** |
| Conversion +10% | +$188M |
| Reactivation +0.5pt a month | +$100M |
| Tail churn −1pt a month | +$99M |
| USD +10% from Nov 2026 | −$97M |

## Recommendation
**Run a 10% Nitro price test before investing further in acquisition.** If volume holds, it is worth ~$290M over five years, more than a 10% conversion improvement. It still pays off unless it cuts conversion by more than ~14% or raises churn on new subscribers by more than ~24%. Those two thresholds are the test's success criteria. The model's experiment toggle reads a test result straight into the forecast.

## What would change this view
1. **Reactivation is unsourced but third-largest.** It swings forecast revenue by 17% across its range. Win-back data from Discord would tighten the forecast more than any other single input.
2. **Plan mix (Nitro vs Basic) decides which public estimate is right.** If Basic is the majority, FY2025 sits near $280M and every forecast number scales down.
3. **Trials are modeled as replacing paid sign-ups, not adding to them.** That understates their value. A trial holdout test would settle it.
4. **FX:** forwards imply the Brazilian real weakens about 10% a year (the Selic–Fed gap), so LatAm revenue falls ~23% in USD by 2030. Hedging or local repricing matters there.
