"""GPU offer search and cheapest-match selection.

Price filtering happens here in Python (against each offer's `dph_total`) rather
than in the search query, so we don't depend on the exact query field name and
we get deterministic cheapest-first selection.
"""

from __future__ import annotations

from . import vastai
from .errors import NoOffersError
from .models import Offer, Profile


def search(profile: Profile, runner=None) -> list[Offer]:
    runner = runner or vastai.run
    data = runner(["search", "offers", profile.search]) or []
    return [Offer.from_raw(d) for d in data]


def pick(offers: list[Offer], max_dph: float | None) -> Offer:
    """Cheapest offer within budget; ties broken by higher reliability."""
    candidates = [o for o in offers if max_dph is None or o.dph <= max_dph]
    if not candidates:
        if offers and max_dph is not None:
            cheapest = min(offers, key=lambda o: o.dph)
            raise NoOffersError(
                f"no offer at/under ${max_dph:.2f}/hr (cheapest match is "
                f"${cheapest.dph:.2f}/hr on {cheapest.gpu_name}). "
                "Raise --max-dph or use --force."
            )
        raise NoOffersError(
            "no rentable offers matched the search. Loosen the profile/--gpu-ram filters."
        )
    return min(candidates, key=lambda o: (o.dph, -o.reliability))
