"""Subscribers roll forward: opening + new + reactivated - churned = closing, every segment, every month."""
import numpy as np
import pytest

from nitro_model.cohorts import run


def _gap(res):
    return res["opening"] + res["new"] + res["reactivated"] - res["churned"] - res["closing"]


def test_rollforward_every_segment_every_month(result):
    assert np.abs(_gap(result)).max() < 1e-3  # persons


def test_opening_equals_prior_closing(result):
    np.testing.assert_allclose(result["opening"][..., 1:], result["closing"][..., :-1])


@pytest.mark.parametrize("count_trials", [0, 1])
@pytest.mark.parametrize("trial_months", [1, 3])
def test_rollforward_holds_under_both_trial_definitions(params, count_trials, trial_months):
    p = params | {"count_trials_as_subs": count_trials, "trial_months": trial_months}
    assert np.abs(_gap(run(p))).max() < 1e-3


def test_no_negative_flows(result):
    for k in ("new", "reactivated", "churned", "closing", "revenue"):
        assert result[k].min() >= -1e-6, k


def test_trialists_only_counted_when_flag_on(params):
    on = run(params | {"count_trials_as_subs": 1}, k_cal=1.0)
    off = run(params | {"count_trials_as_subs": 0}, k_cal=1.0)
    np.testing.assert_allclose(on["closing"] - off["closing"], on["trial_active"])
    np.testing.assert_allclose(on["revenue"], off["revenue"])  # trialists never pay


def test_annual_cohort_keeps_everyone_until_first_renewal(result):
    s = result["survival"][1]  # NITRO_A
    assert (s[:12] == 1).all()
    assert s[12] == pytest.approx(0.45) and s[24] == pytest.approx(0.45 * 0.65)
