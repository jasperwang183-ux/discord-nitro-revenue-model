"""FX path, shock, and the ARPU walk from list price to net revenue."""
import numpy as np
import pytest

from nitro_model.cohorts import drivers, fx_index, fx_rates, run


@pytest.fixture(scope="module")
def rates(params):
    return fx_rates(params, len(params["months"]))


def test_fy2025_priced_at_average_rates(params):
    idx = fx_index(params, len(params["months"]))
    np.testing.assert_allclose(idx[:, :12], 1.0)


def test_path_reaches_observed_spot(params, rates):
    np.testing.assert_allclose(rates[:, params["fx_spot_t"]], params["fx_spot"])


def test_forwards_follow_interest_differentials(params, rates):
    """Covered interest parity: high-rate currencies trade weaker forward, low-rate ones stronger."""
    ts, cur = params["fx_spot_t"], params["currencies"]
    assert rates[cur.index("BRL"), -1] > rates[cur.index("BRL"), ts]   # Selic far above Fed funds
    assert rates[cur.index("JPY"), -1] < rates[cur.index("JPY"), ts]   # BoJ below Fed funds
    np.testing.assert_allclose(rates[cur.index("USD")], 1.0)


def test_shock_moves_non_usd_regions_after_spot_only(params):
    T, ts = len(params["months"]), params["fx_spot_t"]
    base = fx_index(params, T)
    strong = fx_index(params | {"fx_shock_dir": 1}, T)
    np.testing.assert_allclose(strong[:, : ts + 1], base[:, : ts + 1])
    us, eu = params["regions"].index("US_CA"), params["regions"].index("EUROPE")
    np.testing.assert_allclose(strong[us], base[us])
    np.testing.assert_allclose(strong[eu, ts + 1:], base[eu, ts + 1:] / 1.10)


def test_shock_never_changes_subscribers(params, result):
    shocked = run(params | {"fx_shock_dir": 1})
    np.testing.assert_allclose(shocked["closing"], result["closing"])
    assert shocked["revenue"][..., -12:].sum() < result["revenue"][..., -12:].sum()


def test_walk_ends_at_revenue(params, result):
    d = drivers(params, result)
    sub_years = result["paying"].sum(axis=(0, 1)).reshape(-1, 12).sum(axis=1) / 12
    revenue = result["revenue"].sum(axis=(0, 1)).reshape(-1, 12).sum(axis=1)
    np.testing.assert_allclose(np.array(d["walk"]["FX"]) * sub_years, revenue, rtol=1e-9)


def test_walk_only_deducts_until_fx(params, result):
    d = drivers(params, result)
    steps = [np.array(d["walk"][s]) for s in d["walk_steps"][:-1]]
    for before, after in zip(steps, steps[1:]):
        assert (after <= before + 1e-9).all()


def test_platform_split_ties_to_revenue(params, result):
    d = drivers(params, result)
    by_pl = sum(np.array(v["revenue"]) for v in d["by_platform"].values())
    revenue = result["revenue"].sum(axis=(0, 1)).reshape(-1, 12).sum(axis=1)
    np.testing.assert_allclose(by_pl, revenue, rtol=1e-9)


def test_counted_arpu_below_paying_arpu_when_trials_counted(params):
    res = run(params | {"count_trials_as_subs": 1})
    d = drivers(params | {"count_trials_as_subs": 1}, res)
    assert all(c < p for c, p in zip(d["per_counted_sub"], d["walk"]["FX"]))
