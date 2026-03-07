"""Tests for M8 Redis caching layer.

Tests cache hit/miss behavior, TTL, and graceful degradation when Redis is unavailable.
"""
import pytest

from providers.cache import ProviderCache


@pytest.mark.asyncio
async def test_cache_disabled_when_no_redis_url():
    """Cache is a no-op when no Redis URL is provided."""
    cache = ProviderCache()
    assert not cache.enabled


@pytest.mark.asyncio
async def test_cache_get_returns_none_when_disabled():
    """get() returns None when cache is disabled."""
    cache = ProviderCache()
    result = await cache.get("flight", "MockFlightProvider", {"origin": "JFK"})
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_noop_when_disabled():
    """set() silently does nothing when cache is disabled."""
    cache = ProviderCache()
    # Should not raise
    await cache.set("flight", "MockFlightProvider", {"origin": "JFK"}, [{"flight_id": "FL001"}])


@pytest.mark.asyncio
async def test_cache_invalidate_noop_when_disabled():
    """invalidate() silently does nothing when cache is disabled."""
    cache = ProviderCache()
    await cache.invalidate("flight", "MockFlightProvider", {"origin": "JFK"})


@pytest.mark.asyncio
async def test_cache_close_noop_when_disabled():
    """close() silently does nothing when cache is disabled."""
    cache = ProviderCache()
    await cache.close()


def test_cache_key_generation():
    """Cache keys are deterministic and namespaced."""
    cache = ProviderCache()
    key1 = cache._cache_key("flight", "Amadeus", {"origin": "JFK", "destination": "CDG"})
    key2 = cache._cache_key("flight", "Amadeus", {"origin": "JFK", "destination": "CDG"})
    key3 = cache._cache_key("flight", "Amadeus", {"origin": "LAX", "destination": "CDG"})

    assert key1 == key2  # Same params → same key
    assert key1 != key3  # Different params → different key
    assert key1.startswith("concierge:flight:Amadeus:")


def test_cache_key_different_domains():
    """Different domains produce different cache keys."""
    cache = ProviderCache()
    params = {"origin": "JFK"}
    key_flight = cache._cache_key("flight", "Provider", params)
    key_hotel = cache._cache_key("hotel", "Provider", params)
    assert key_flight != key_hotel


def test_cache_key_different_providers():
    """Different providers produce different cache keys."""
    cache = ProviderCache()
    params = {"origin": "JFK"}
    key_amadeus = cache._cache_key("flight", "Amadeus", params)
    key_duffel = cache._cache_key("flight", "Duffel", params)
    assert key_amadeus != key_duffel


@pytest.mark.asyncio
async def test_cache_graceful_degradation_on_bad_url():
    """Cache gracefully handles invalid Redis URL."""
    cache = ProviderCache(redis_url="redis://nonexistent:6379")
    # Even with a URL, operations should not crash
    result = await cache.get("flight", "test", {})
    assert result is None


def test_cache_ttl_configuration():
    """Cache respects custom TTL settings."""
    cache = ProviderCache(ttl_seconds=60)
    assert cache._ttl == 60

    default_cache = ProviderCache()
    assert default_cache._ttl == 900  # 15 minutes default
