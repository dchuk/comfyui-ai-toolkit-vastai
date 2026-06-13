import pytest

from conftest import offer_raw

from vastctl import offers
from vastctl.errors import NoOffersError
from vastctl.models import Offer


def test_pick_cheapest():
    items = [Offer.from_raw(offer_raw(1, 0.50)), Offer.from_raw(offer_raw(2, 0.30)),
             Offer.from_raw(offer_raw(3, 0.40))]
    assert offers.pick(items, max_dph=None).id == 2


def test_pick_tie_break_reliability():
    items = [
        Offer.from_raw(offer_raw(1, 0.30, reliability=0.95)),
        Offer.from_raw(offer_raw(2, 0.30, reliability=0.99)),
    ]
    assert offers.pick(items, max_dph=None).id == 2


def test_pick_respects_max_dph():
    items = [Offer.from_raw(offer_raw(1, 0.80)), Offer.from_raw(offer_raw(2, 0.20))]
    assert offers.pick(items, max_dph=0.50).id == 2


def test_pick_over_budget_raises_with_cheapest_hint():
    items = [Offer.from_raw(offer_raw(1, 0.80)), Offer.from_raw(offer_raw(2, 0.70))]
    with pytest.raises(NoOffersError) as exc:
        offers.pick(items, max_dph=0.50)
    assert "0.70" in str(exc.value)


def test_pick_empty_raises():
    with pytest.raises(NoOffersError):
        offers.pick([], max_dph=None)


def test_pick_fastest_by_download_speed():
    items = [
        Offer.from_raw(offer_raw(1, 0.30, inet_down=500.0)),
        Offer.from_raw(offer_raw(2, 0.50, inet_down=3000.0)),
        Offer.from_raw(offer_raw(3, 0.40, inet_down=1500.0)),
    ]
    # cheapest would be id 1, but fastest download is id 2
    assert offers.pick(items, max_dph=None, fastest=True).id == 2


def test_pick_fastest_respects_max_dph():
    items = [
        Offer.from_raw(offer_raw(1, 0.80, inet_down=9000.0)),  # fastest but over budget
        Offer.from_raw(offer_raw(2, 0.40, inet_down=2000.0)),
    ]
    assert offers.pick(items, max_dph=0.50, fastest=True).id == 2


def test_search_parses_offers(fake_runner, flux_profile):
    fake_runner.responses = {("search", "offers"): [offer_raw(7, 0.33)]}
    result = offers.search(flux_profile, runner=fake_runner)
    assert len(result) == 1
    assert result[0].id == 7
    assert result[0].gpu_ram_gb == 24.0  # 24576 MB -> GB
