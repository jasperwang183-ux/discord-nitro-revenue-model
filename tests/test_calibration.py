"""Calibration: only conversion is solved; revenue is checked against the public band, never tuned to it."""
import pytest

from nitro_model.cohorts import calibrate, run


def test_subscribers_hit_anchor_in_calibration_month(params, result):
    i = params["cal_month_index"] - 1
    assert result["closing"][..., i].sum() == pytest.approx(params["cal_target_subs"], rel=1e-9)


def test_calibration_is_exact_when_churn_changes(params):
    """The solve is closed-form (subscribers are affine in the scalar), so it stays exact for any churn input."""
    p = params | {"churn_tail": 0.08}
    i = p["cal_month_index"] - 1
    assert run(p)["closing"][..., i].sum() == pytest.approx(p["cal_target_subs"], rel=1e-9)
    assert calibrate(p) > calibrate(params)  # more churn needs more conversion to hold the anchor


def test_fy2025_revenue_inside_public_band(params, result):
    fy25 = result["revenue"][..., :12].sum()
    assert params["cal_rev_low"] <= fy25 <= params["cal_rev_high"]
