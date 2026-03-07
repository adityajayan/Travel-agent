"""Provider factory — returns FallbackProvider chains with caching (M5, M8).

Returns Mock providers wrapped in FallbackProvider when USE_REAL_APIS=false.
Returns real provider chains (primary + fallback) when USE_REAL_APIS=true.
"""
import os

from providers.cache import ProviderCache
from providers.fallback import FallbackProvider

# Module-level cache instance — shared across all providers
_cache: ProviderCache | None = None


def _get_cache() -> ProviderCache:
    global _cache
    if _cache is None:
        redis_url = os.environ.get("REDIS_URL", "")
        _cache = ProviderCache(redis_url=redis_url or None)
    return _cache


def get_provider(domain: str) -> FallbackProvider:
    """Return a FallbackProvider with primary + fallback for the domain.

    Reads USE_REAL_APIS env var. Returns MockProvider chain by default.
    """
    use_real = os.environ.get("USE_REAL_APIS", "false").lower() == "true"
    cache = _get_cache()

    if domain == "flight":
        if use_real:
            from providers.real.duffel import DuffelFlightProvider
            from providers.real.amadeus import AmadeusFlightProvider
            providers = [DuffelFlightProvider(), AmadeusFlightProvider()]
        else:
            from providers.mock.flight_provider import MockFlightProvider
            providers = [MockFlightProvider()]

    elif domain == "hotel":
        if use_real:
            from providers.real.duffel_hotels import DuffelHotelProvider
            from providers.real.bookingcom import BookingcomHotelProvider
            providers = [DuffelHotelProvider(), BookingcomHotelProvider()]
        else:
            from providers.mock.hotel_provider import MockHotelProvider
            providers = [MockHotelProvider()]

    elif domain == "transport":
        if use_real:
            from providers.real.raileurope import RailEuropeTransportProvider
            providers = [RailEuropeTransportProvider()]
        else:
            from providers.mock.transport_provider import MockTransportProvider
            providers = [MockTransportProvider()]

    elif domain == "activity":
        if use_real:
            from providers.real.viator import ViatorActivityProvider
            from providers.real.getyourguide import GetYourGuideActivityProvider
            providers = [ViatorActivityProvider(), GetYourGuideActivityProvider()]
        else:
            from providers.mock.activity_provider import MockActivityProvider
            providers = [MockActivityProvider()]

    else:
        raise ValueError(f"Unknown domain: {domain}")

    return FallbackProvider(providers=providers, cache=cache, domain=domain)
