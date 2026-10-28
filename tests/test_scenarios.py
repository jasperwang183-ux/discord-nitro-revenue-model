"""Scenarios, the experiment toggle, the driver bridge and sensitivity."""
import numpy as np
import pytest

from nitro_model.cohorts import bridge, calibrate, forecast_revenue, run, sensitivity
from nitro_model.params import build_params, slider_specs

SCENARIOS = ("base", "upside", "downside")


@pytest.fixture(scope="module")
def runs(assumptions):
    return {sc: (p := build_params(assumptions, sc), run(p)) for sc in SCENARIOS}


def test_history_is_identical_in_every_scenario(runs):
    base = runs["base"][1]
    for sc in ("upside", "downside"):
        res = runs[sc][1]
        np.testing.assert_allclose(res["closing"][..., :12], base["closing"][..., :12])
        np.testing.assert_allclose(res["revenue"][..., :12], base["revenue"][..., :12])
        assert res["k_cal"] == pytest.approx(base["k_cal"])


def test_scenarios_are_ordered(runs):
    rev = {sc: forecast_revenue(r, p) for sc, (p, r) in runs.items()}
    assert rev["upside"] > rev["base"] > rev["downside"]


@pytest.mark.parametrize("target", ["upside", "downside", "experiment", "custom"])
def test_bridge_ties_start_to_end(assumptions, params, target):
    if target in SCENARIOS:
        p_to = build_params(assumptions, target)
    elif target == "experiment":
        p_to = params | {"exp_enabled": 1, "fx_shock_dir": 1}
    else:
        p_to = params | {"churn_tail": 0.06, "count_trials_as_subs": 0, "react_rate": 0.03}
    b = bridge(params, p_to)
    assert b["start"] + sum(s["delta"] for s in b["steps"]) == pytest.approx(b["end"], abs=1.0)
    assert b["end"] == pytest.approx(forecast_revenue(run(p_to), p_to))


def test_bridge_is_empty_for_identical_inputs(params):
    b = bridge(params, dict(params))
    assert b["steps"] == [] and b["start"] == pytest.approx(b["end"])


def test_experiment_off_matches_base(params, result):
    off = run(params | {"exp_enabled": 0, "exp_conv_lift": 0.15, "exp_price_change": 0.2})
    np.testing.assert_allclose(off["revenue"], result["revenue"])


def test_experiment_changes_nothing_before_it_starts(params, result):
    on = run(params | {"exp_enabled": 1, "exp_price_change": 0.1, "exp_churn_change": 0.05})
    t0 = params["exp_start_t"]
    np.testing.assert_allclose(on["closing"][..., :t0], result["closing"][..., :t0])
    np.testing.assert_allclose(on["revenue"][..., :t0], result["revenue"][..., :t0])


def test_price_change_scales_revenue_exactly(params, result):
    on = run(params | {"exp_enabled": 1, "exp_price_change": 0.1, "exp_conv_lift": 0.0, "exp_churn_change": 0.0})
    t0 = params["exp_start_t"]
    np.testing.assert_allclose(on["closing"], result["closing"])
    np.testing.assert_allclose(on["revenue"][..., t0:], result["revenue"][..., t0:] * 1.1)


def test_churn_change_only_touches_new_cohorts(params, result):
    on = run(params | {"exp_enabled": 1, "exp_conv_lift": 0.0, "exp_price_change": 0.0, "exp_churn_change": 0.05})
    np.testing.assert_allclose(on["legacy"], result["legacy"])
    assert on["closing"][..., -1].sum() < result["closing"][..., -1].sum()


def test_experiment_cannot_start_in_history(params, result):
    early = run(params | {"exp_enabled": 1, "exp_start_t": 0, "exp_price_change": 0.1})
    np.testing.assert_allclose(early["revenue"][..., :12], result["revenue"][..., :12])


def test_sensitivity_signs_and_order(assumptions, params):
    rows = sensitivity(params, slider_specs(assumptions))
    by_key = {r["key"]: r for r in rows}
    assert by_key["churn_tail"]["rev_high"] < 0 < by_key["churn_tail"]["rev_low"]
    assert by_key["conv_multiplier"]["rev_high"] > 0 > by_key["conv_multiplier"]["rev_low"]
    swings = [r["pct_swing"] for r in rows]
    assert swings == sorted(swings, reverse=True)
