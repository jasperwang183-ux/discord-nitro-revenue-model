import pandas as pd
import pytest

from nitro_model.assumptions import AssumptionError, Assumptions, validation_errors


@pytest.fixture(scope="module")
def a() -> Assumptions:
    return Assumptions.load()


def test_assumptions_load_and_validate(a):
    assert len(a.table) > 0


def test_every_row_has_source_and_date(a):
    t = a.table
    assert t["source_ids"].notna().all()
    assert t["as_of"].notna().all()


def test_scenario_override_beats_all_row(a):
    assert a.get("churn_tail", "MONTHLY", "downside") > a.get("churn_tail", "MONTHLY", "base")
    # list_price has only an `all` row, so every scenario falls back to it
    assert a.get("list_price", "NITRO_M", "upside") == a.get("list_price", "NITRO_M", "base")


def test_scenarios_are_ordered(a):
    """Upside should never be worse than base, nor downside better, on retention inputs."""
    for aid, seg in [("churn_m1", "MONTHLY"), ("churn_tail", "MONTHLY"), ("open_churn_tail", "MONTHLY")]:
        assert a.get(aid, seg, "upside") <= a.get(aid, seg, "base") <= a.get(aid, seg, "downside")
    for aid, seg in [("annual_renewal_first", "ANNUAL"), ("annual_renewal_later", "ANNUAL")]:
        assert a.get(aid, seg, "upside") >= a.get(aid, seg, "base") >= a.get(aid, seg, "downside")


def test_experiment_off_in_every_scenario(a):
    """Magnitudes (exp_conv_lift etc.) stay populated so the toggle is ready; only the flag gates them."""
    for sc in ("base", "upside", "downside"):
        assert a.get("exp_enabled", scenario=sc) == 0


def test_missing_key_raises(a):
    with pytest.raises(AssumptionError):
        a.get("does_not_exist")


def _row(**kw):
    base = dict(id="x", group="g", segment="all", scenario="all", value=1.0, unit="u",
                low=None, high=None, status="design", source_ids="P01", as_of="2026-10-27", notes="")
    base.update(kw)
    return base


@pytest.mark.parametrize("bad, fragment", [
    (_row(source_ids=None), "missing source_ids"),
    (_row(as_of=None), "missing as_of"),
    (_row(source_ids="S999"), "unknown source"),
    (_row(source_ids="A01", status="verified"), "analyst-only source"),
    (_row(value=5.0, low=0.0, high=1.0), "above high"),
    (_row(status="guess"), "unknown status"),
])
def test_validator_catches_bad_rows(a, bad, fragment):
    errs = validation_errors(pd.DataFrame([bad]), a.sources)
    assert any(fragment in e for e in errs), errs


def test_validator_catches_shares_not_summing(a):
    rows = pd.DataFrame([_row(id="plan_mix", segment="A", value=0.6), _row(id="plan_mix", segment="B", value=0.6)])
    assert any("shares sum" in e for e in validation_errors(rows, a.sources))
