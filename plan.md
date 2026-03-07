# Plan: Make Duffel the Primary Provider for Flights and Hotels

## Current State

| Domain  | Primary      | Fallback       |
|---------|-------------|----------------|
| Flight  | Amadeus     | Duffel         |
| Hotel   | Booking.com | Amadeus Hotels |

## Target State

| Domain  | Primary | Fallback       |
|---------|---------|----------------|
| Flight  | Duffel  | Amadeus        |
| Hotel   | Duffel  | Booking.com    |

---

## Step 1: Swap Duffel to primary for flights in the factory

**File:** `providers/factory.py` (lines 31-38)

Change the flight provider order from `[AmadeusFlightProvider(), DuffelFlightProvider()]` to `[DuffelFlightProvider(), AmadeusFlightProvider()]`. Amadeus becomes the fallback.

This is a one-line swap — the `FallbackProvider` already treats index 0 as primary and tries subsequent providers on failure.

---

## Step 2: Create `DuffelHotelProvider`

**New file:** `providers/real/duffel_hotels.py`

Duffel offers a Stays API (`/stays/search`, `/stays/bookings`, etc.). Create a new provider class `DuffelHotelProvider` extending `BaseHotelProvider` with:

- **`__init__`**: Reuse the same `DUFFEL_API_TOKEN` env var (shared credential with `DuffelFlightProvider`)
- **`_request()`**: Reuse the same authenticated HTTP helper pattern (Bearer token, `Duffel-Version: v2`, retry on 429) — can be copied from `duffel.py`
- **`search_hotels(destination, check_in, check_out, guests)`**:
  - POST to `/stays/search` with location, check-in/check-out dates, guest count
  - Parse response into `NormalizedHotelResult` objects (hotel_id, name, cost_per_night, total_price, star_rating, rating_score, provider="Duffel")
- **`book_hotel(hotel_id, guest_details, payment_token)`**:
  - POST to `/stays/bookings` with rate ID and guest details
  - Return `NormalizedBookingConfirmation` with SANDBOX- prefix when in sandbox mode
- **`cancel_hotel(booking_reference)`**:
  - POST cancellation request to Duffel stays cancellation endpoint
  - Return standard cancellation dict
- **`verify_price()`**: Stub returning unchanged price (same pattern as existing Duffel flight provider)
- **`get_cancellation_policy()`**: Return generic Duffel policy text (same pattern)

The provider follows the exact same patterns as `DuffelFlightProvider` and `BookingcomHotelProvider`:
- Bearer token auth via `DUFFEL_API_TOKEN`
- Sandbox detection via `duffel_test_` prefix
- SANDBOX- booking reference prefix (INV-11)
- Retry on 429 with exponential backoff
- Returns normalized Pydantic schemas (INV-14)

---

## Step 3: Update the factory to use Duffel as primary for hotels

**File:** `providers/factory.py` (lines 40-47)

Change the hotel provider chain from:
```python
providers = [BookingcomHotelProvider(), AmadeusHotelProvider()]
```
to:
```python
providers = [DuffelHotelProvider(), BookingcomHotelProvider()]
```

Import `DuffelHotelProvider` from `providers.real.duffel_hotels`. Amadeus Hotels is removed from the fallback chain (replaced by Booking.com as fallback).

---

## Step 4: Update configuration and documentation

**File:** `core/config.py` — No changes needed. `duffel_api_token` already exists (line 41) and is used by both flight and hotel Duffel providers via `os.environ.get("DUFFEL_API_TOKEN")`.

**File:** `.env.example` — Move `DUFFEL_API_TOKEN` from the "M8: Fallback Providers" section up to the "Real API Providers" section, since it is now a primary provider credential. Add a comment indicating it's used for both flights and hotels.

---

## Step 5: Update tests

### 5a. Update `test_real_providers.py`
- Add `test_duffel_flight_search()` — verify Duffel flight search returns normalized results with expected fields
- Add `test_duffel_hotel_search()` — verify Duffel hotel search returns normalized results with expected fields
- Update `test_factory_returns_mock_by_default()` — this test uses `isinstance` checks against mock providers, which still work since mock providers are unchanged when `USE_REAL_APIS=false`

### 5b. Update `test_fallback.py`
- Existing tests are provider-agnostic (they use mock providers), so no changes needed. The fallback logic itself hasn't changed.

### 5c. Add `test_duffel_hotels.py` (new)
- Unit test `DuffelHotelProvider.search_hotels()` with mocked HTTP responses
- Unit test `DuffelHotelProvider.book_hotel()` with mocked HTTP responses
- Unit test `DuffelHotelProvider.cancel_hotel()`
- Verify sandbox prefix (INV-11)
- Verify normalized schema fields match `NormalizedHotelResult`

### 5d. Update `test_cache.py`
- Add a cache key test for `DuffelHotelProvider` (similar to existing Duffel flight cache key test on line 73)

---

## Step 6: Optional — Extract shared Duffel HTTP client

Both `DuffelFlightProvider` and `DuffelHotelProvider` share identical `_request()` logic (auth header, retry on 429, base URL). Consider extracting a shared `DuffelClient` mixin or utility class in `providers/real/duffel_base.py` to avoid duplication. Both providers would inherit from it or compose it.

This is optional and can be deferred — the duplication is small (~25 lines) and both providers work independently.

---

## Files Changed Summary

| File | Action | Description |
|------|--------|-------------|
| `providers/factory.py` | Edit | Swap flight order; change hotel chain to Duffel + Booking.com |
| `providers/real/duffel_hotels.py` | **Create** | New `DuffelHotelProvider` class (~180 lines) |
| `.env.example` | Edit | Move `DUFFEL_API_TOKEN` to primary section |
| `tests/test_duffel_hotels.py` | **Create** | Unit tests for new hotel provider |
| `tests/test_real_providers.py` | Edit | Add Duffel integration tests |
| `tests/test_cache.py` | Edit | Add Duffel hotel cache key test |

No changes to: `core/config.py`, `providers/base.py`, `providers/schemas.py`, `providers/fallback.py`, agents, approval gate, policy engine, or frontend.

---

## Risks and Considerations

1. **Duffel Stays API availability** — Duffel's Stays API may have different availability/coverage than Booking.com. The fallback chain (Duffel → Booking.com) mitigates this.
2. **Booking operations use primary only** — `FallbackProvider.book()` always delegates to primary (no fallback). If Duffel booking fails, the user gets an error rather than an automatic fallback to Booking.com. This is the existing design choice to prevent double-bookings.
3. **Shared credentials** — Both Duffel flight and hotel providers use the same `DUFFEL_API_TOKEN`. No additional env vars needed.
4. **Sandbox detection** — Duffel sandbox detection (`duffel_test_` prefix) applies identically to both flights and hotels.
5. **Cache keys** — Cache keys include provider class name, so `DuffelHotelProvider` and `DuffelFlightProvider` will have distinct cache keys automatically.
