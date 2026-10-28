"""Cohort totals tie to the aggregate subscriber line every month."""
import numpy as np
import pytest

from nitro_model.arpu import PLATFORMS, net_price
from nitro_model.cohorts import cohort_triangle, net_prices
from nitro_model.params import REGIONS


def test_cohort_triangle_ties_to_paid_active(params, result):
    tri = cohort_triangle(params, result)  # built cohort by cohort, independent of the convolution
    np.testing.assert_allclose(tri.sum(axis=2), result["paid_active"], rtol=0, atol=1e-3)


def test_segments_tie_to_total(result):
    closing = result["closing"]
    total = closing.sum(axis=(0, 1))
    by_region = closing.sum(axis=1).sum(axis=0)
    by_plan = closing.sum(axis=0).sum(axis=0)
    np.testing.assert_allclose(by_region, total)
    np.testing.assert_allclose(by_plan, total)


def test_closing_is_sum_of_layers(result):
    layers = result["legacy"] + result["paid_active"] + result["react_active"] + result["trial_active"]
    np.testing.assert_allclose(result["closing"], layers)


def test_hand_rebuilt_cohort(params, result):
    """US/CA Nitro monthly, Jan 2025 cohort: rebuild survival by hand from the hazards."""
    starts = result["paid_starts"][0, 0, 0]
    tri = cohort_triangle(params, result)[0, 0, 0]
    h = [0, params["churn_m1"], params["churn_m2"], params["churn_m3"]] + [params["churn_tail"]] * 8
    expected = starts
    for age in range(12):
        expected *= 1 - h[age]
        assert tri[age] == pytest.approx(expected)


def test_engine_prices_match_arpu_module(assumptions, params):
    """The numpy engine re-implements arpu.net_price for the browser; both must agree."""
    y1, later = net_prices(params)
    for i, region in enumerate(REGIONS):
        for j, plan in enumerate(params["plans"]):
            mix = [assumptions.get("platform_mix", f"{region}|{pl}") for pl in PLATFORMS]
            ref_y1 = sum(w * net_price(assumptions, plan, region, pl, True).net for w, pl in zip(mix, PLATFORMS))
            ref_later = sum(w * net_price(assumptions, plan, region, pl, False).net for w, pl in zip(mix, PLATFORMS))
            assert y1[i, j] == pytest.approx(ref_y1)
            assert later[i, j] == pytest.approx(ref_later)
