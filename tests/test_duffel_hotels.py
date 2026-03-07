"""Tests for DuffelHotelProvider — unit tests with mocked HTTP responses."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from providers.real.duffel_hotels import DuffelHotelProvider


@pytest.fixture
def provider():
    with patch.dict("os.environ", {"DUFFEL_API_TOKEN": "duffel_test_abc123"}):
        return DuffelHotelProvider()


@pytest.fixture
def live_provider():
    with patch.dict("os.environ", {"DUFFEL_API_TOKEN": "duffel_live_abc123"}):
        return DuffelHotelProvider()


def test_sandbox_detection_test_token(provider):
    """Sandbox mode detected for test tokens."""
    assert provider._is_sandbox is True


def test_sandbox_detection_live_token(live_provider):
    """Live mode detected for production tokens."""
    assert live_provider._is_sandbox is False


def test_sandbox_detection_empty_token():
    """Sandbox mode when no token is set."""
    with patch.dict("os.environ", {"DUFFEL_API_TOKEN": ""}):
        p = DuffelHotelProvider()
        assert p._is_sandbox is True


MOCK_SEARCH_RESPONSE = {
    "data": {
        "results": [
            {
                "id": "acc_001",
                "cheapest_rate_total_amount": "450.00",
                "cheapest_rate_currency": "USD",
                "accommodation": {
                    "name": "Grand Hotel London",
                    "star_rating": 4,
                    "review_score": 8.5,
                },
            },
            {
                "id": "acc_002",
                "cheapest_rate_total_amount": "300.00",
                "cheapest_rate_currency": "USD",
                "accommodation": {
                    "name": "Budget Inn London",
                    "star_rating": 3,
                    "review_score": 7.2,
                },
            },
        ]
    }
}


@pytest.mark.asyncio
async def test_search_hotels(provider):
    """Search returns normalized hotel results."""
    with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = MOCK_SEARCH_RESPONSE

        results = await provider.search_hotels("London", "2026-06-15", "2026-06-18")

        mock_req.assert_called_once()
        assert len(results) == 2

        first = results[0]
        assert first["hotel_id"] == "acc_001"
        assert first["name"] == "Grand Hotel London"
        assert first["destination"] == "London"
        assert first["check_in"] == "2026-06-15"
        assert first["check_out"] == "2026-06-18"
        assert first["total_price"] == 450.00
        assert first["cost_per_night"] == 150.00  # 450 / 3 nights
        assert first["star_rating"] == 4.0
        assert first["rating_score"] == 8.5
        assert first["provider"] == "Duffel"
        assert first["raw_provider_id"] == "acc_001"


@pytest.mark.asyncio
async def test_search_hotels_empty_results(provider):
    """Search handles empty results gracefully."""
    with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"data": {"results": []}}
        results = await provider.search_hotels("Nowhere", "2026-06-15", "2026-06-18")
        assert results == []


MOCK_BOOKING_RESPONSE = {
    "data": {
        "booking_reference": "HTLBKG123",
        "total_amount": "450.00",
    }
}


@pytest.mark.asyncio
async def test_book_hotel_sandbox_prefix(provider):
    """Sandbox bookings get SANDBOX- prefix (INV-11)."""
    with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = MOCK_BOOKING_RESPONSE

        result = await provider.book_hotel(
            "acc_001", {"name": "Alice Smith", "email": "alice@test.com"}, "tok_123"
        )

        assert result["booking_reference"] == "SANDBOX-HTLBKG123"
        assert result["domain"] == "hotel"
        assert result["provider"] == "Duffel"
        assert result["status"] == "confirmed"
        assert result["is_sandbox"] is True
        assert result["amount"] == 450.00


@pytest.mark.asyncio
async def test_book_hotel_live_no_prefix(live_provider):
    """Live bookings do not get SANDBOX- prefix."""
    with patch.object(live_provider, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = MOCK_BOOKING_RESPONSE

        result = await live_provider.book_hotel(
            "acc_001", {"name": "Alice Smith"}, "tok_123"
        )

        assert result["booking_reference"] == "HTLBKG123"
        assert result["is_sandbox"] is False


@pytest.mark.asyncio
async def test_cancel_hotel(provider):
    """Cancel returns standard cancellation dict."""
    with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"data": {"status": "cancelled"}}

        result = await provider.cancel_hotel("SANDBOX-HTLBKG123")

        assert result["booking_reference"] == "SANDBOX-HTLBKG123"
        assert result["status"] == "cancelled"
        # Verify the API call strips SANDBOX- prefix
        call_args = mock_req.call_args
        assert "SANDBOX-" not in str(call_args[1]["json"]["data"]["booking_id"])


@pytest.mark.asyncio
async def test_cancel_hotel_api_error_handled(provider):
    """Cancel gracefully handles API errors."""
    with patch.object(provider, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = RuntimeError("API error")

        result = await provider.cancel_hotel("SANDBOX-HTLBKG123")

        assert result["status"] == "cancelled"


@pytest.mark.asyncio
async def test_verify_price(provider):
    """verify_price returns unchanged price stub."""
    result = await provider.verify_price("acc_001", 450.00)
    assert result.price_changed is False
    assert result.current_price == 450.00
    assert result.original_price == 450.00


@pytest.mark.asyncio
async def test_get_cancellation_policy(provider):
    """get_cancellation_policy returns Duffel policy."""
    result = await provider.get_cancellation_policy("HTLBKG123")
    assert result.refundable is True
    assert result.provider == "Duffel"
    assert "Duffel" in result.policy_text
