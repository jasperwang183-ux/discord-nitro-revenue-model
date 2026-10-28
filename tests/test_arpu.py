import pytest

from nitro_model.arpu import PLANS, PLATFORMS, book_arpu_walk, fx_index, monthly_list_usd, net_price, region_currencies
from nitro_model.assumptions import Assumptions


@pytest.fixture(scope="module")
def a() -> Assumptions:
    return Assumptions.load()


@pytest.fixture(scope="module")
def regions(a):
    return a.segments("price_index")


@pytest.fixture(scope="module")
def ref_rates(a):
    return {ccy: a.get("fx_avg_2025", ccy) for ccy in a.segments("fx_avg_2025")}


def test_fx_applied_once_at_reference_rates(a, regions, ref_rates):
    """At the reference rates the FX index is 1, so USD price = list x price_index with no second conversion."""
    for region in regions:
        assert fx_index(a, region, ref_rates) == pytest.approx(1.0)
        for plan, months in PLANS.items():
            expected = a.get("list_price", plan) / months * a.get("price_index", region)
            assert monthly_list_usd(a, plan, region, ref_rates) == pytest.approx(expected)


def test_fx_direction_local_weakness_lowers_usd(a, regions, ref_rates):
    """Rates are local per USD: a 10% higher rate (weaker local currency) cuts USD value to 1/1.1."""
    weak = {ccy: r if ccy == "USD" else r * 1.10 for ccy, r in ref_rates.items()}
    for region in regions:
        expected = sum(w if ccy == "USD" else w / 1.10 for ccy, w in region_currencies(a, region).items())
        assert fx_index(a, region, weak) == pytest.approx(expected)
    assert fx_index(a, "US_CA", weak) == 1.0
    assert fx_index(a, "EUROPE", weak) == pytest.approx(1 / 1.10)


def test_every_region_has_a_full_currency_basket(a, regions):
    for region in regions:
        assert sum(region_currencies(a, region).values()) == pytest.approx(1.0)


def test_vat_only_in_vat_inclusive_regions(a):
    assert a.get("indirect_tax", "US_CA") == 0.0
    s = net_price(a, "NITRO_M", "US_CA", "WEB", first_year=False)
    assert s.after_tax == pytest.approx(s.after_discount)


def test_store_fee_charged_on_net_of_vat_price(a, regions):
    for region in regions:
        for platform in PLATFORMS:
            for first_year in (True, False):
                s = net_price(a, "NITRO_M", region, platform, first_year)
                fee = s.after_tax - s.net
                rate = a.get("store_fee", ("IOS_Y1" if first_year else "IOS_LATER") if platform == "IOS" else platform)
                assert fee == pytest.approx(s.after_tax * rate)
                assert s.list_usd >= s.after_discount >= s.after_tax >= s.net


def test_store_fee_rates_match_published_terms(a):
    assert a.get("store_fee", "IOS_Y1") == 0.30
    assert a.get("store_fee", "IOS_LATER") == 0.15
    assert a.get("store_fee", "ANDROID") == 0.15


def test_paid_arpu_inside_range_implied_by_public_estimates(a):
    """Band, not a point: $280M-$450M on 7.3M subs. Tuning to either end would bake in one source's definition."""
    lo, hi = a.bounds("cal_nitro_rev_2025")
    subs = a.get("cal_subs_mid2025")
    arpu_yr = book_arpu_walk(a)[-1][1] * 12
    assert lo / subs <= arpu_yr <= hi / subs
