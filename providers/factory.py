"""Provider factory — returns Mock or Real providers based on USE_REAL_APIS (M5)."""
import os

from providers.base import BaseProvider


def get_provider(domain: str) -> BaseProvider:
    """Return the active provider for the given domain.

    Reads USE_REAL_APIS env var. Returns MockProvider by default.
    """
    use_real = os.environ.get("USE_REAL_APIS", "false").lower() == "true"

    if domain == "flight":
        if use_real:
            from providers.real.amadeus import AmadeusFlightProvider
            return AmadeusFlightProvider()
        from providers.mock.flight_provider import MockFlightProvider
        return MockFlightProvider()

    elif domain == "hotel":
        if use_real:
            from providers.real.bookingcom import BookingcomHotelProvider
            return BookingcomHotelProvider()
        from providers.mock.hotel_provider import MockHotelProvider
        return MockHotelProvider()

    elif domain == "transport":
        if use_real:
            from providers.real.raileurope import RailEuropeTransportProvider
            return RailEuropeTransportProvider()
        from providers.mock.transport_provider import MockTransportProvider
        return MockTransportProvider()

    elif domain == "activity":
        if use_real:
            from providers.real.viator import ViatorActivityProvider
            return ViatorActivityProvider()
        from providers.mock.activity_provider import MockActivityProvider
        return MockActivityProvider()

    else:
        raise ValueError(f"Unknown domain: {domain}")
