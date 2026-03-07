"""Multi-provider fallback wrapper (M8).

Wraps an ordered list of providers and tries them in sequence.
On failure (HTTP 5xx, timeout, rate limit), logs a fallback event and tries the next.
Integrates with ProviderCache for search result caching.
Logs fallback events to AuditLogger (INV-15).
"""
import logging
from typing import Optional

from providers.base import BaseProvider
from providers.cache import ProviderCache

logger = logging.getLogger(__name__)


class AllProvidersFailedError(Exception):
    """Raised when all providers in the fallback chain have failed."""

    def __init__(self, domain: str, errors: list[tuple[str, str]]):
        self.domain = domain
        self.errors = errors
        details = "; ".join(f"{name}: {err}" for name, err in errors)
        super().__init__(f"All {domain} providers failed: {details}")


class FallbackProvider:
    """Wraps multiple providers with automatic failover and caching."""

    def __init__(
        self,
        providers: list[BaseProvider],
        cache: ProviderCache,
        domain: str,
        audit_logger=None,
        event_bus_factory=None,
    ):
        self._providers = providers
        self._cache = cache
        self._domain = domain
        self._audit = audit_logger
        self._event_bus_factory = event_bus_factory

    @property
    def primary(self) -> BaseProvider:
        """Return the primary (first) provider for direct method access."""
        return self._providers[0]

    async def search(self, **params) -> list[dict]:
        """Search with cache check + fallback across providers."""
        # 1. Check cache
        cache_provider = self._provider_name(self._providers[0])
        cached = await self._cache.get(self._domain, cache_provider, params)
        if cached is not None:
            logger.debug("Cache hit for %s search", self._domain)
            await self._log_audit("cache_hit", {"domain": self._domain, "provider": cache_provider})
            return cached

        # 2. Try each provider
        errors: list[tuple[str, str]] = []
        for i, provider in enumerate(self._providers):
            provider_name = self._provider_name(provider)
            try:
                results = await provider.search(**params)
                # Cache successful results
                await self._cache.set(self._domain, provider_name, params, results)
                if i > 0:
                    # Log fallback event (INV-15)
                    await self._log_audit("provider_fallback", {
                        "domain": self._domain,
                        "failed_providers": [e[0] for e in errors],
                        "succeeded_provider": provider_name,
                    })
                    await self._emit_event("provider_fallback", {
                        "domain": self._domain,
                        "provider": provider_name,
                        "message": f"Switched to {provider_name} after {i} provider(s) failed",
                    })
                else:
                    await self._log_audit("cache_miss", {
                        "domain": self._domain,
                        "provider": provider_name,
                    })
                return results
            except Exception as exc:
                error_msg = type(exc).__name__
                errors.append((provider_name, error_msg))
                logger.warning(
                    "%s provider %s failed: %s — trying next",
                    self._domain, provider_name, error_msg,
                )

        # 3. All providers failed
        await self._log_audit("all_providers_failed", {
            "domain": self._domain,
            "errors": [{"provider": n, "error": e} for n, e in errors],
        })
        raise AllProvidersFailedError(self._domain, errors)

    async def book(self, item_id: str, details: dict, payment_token: str) -> dict:
        """Book using the primary provider (no fallback for bookings)."""
        return await self.primary.book(item_id, details, payment_token)

    async def cancel(self, booking_reference: str) -> dict:
        """Cancel using the primary provider."""
        return await self.primary.cancel(booking_reference)

    async def get_details(self, item_id: str) -> dict:
        """Get details from the primary provider."""
        return await self.primary.get_details(item_id)

    async def hold_fare(self, item_id: str):
        """Hold fare using the primary provider."""
        return await self.primary.hold_fare(item_id)

    async def verify_price(self, item_id: str, original_price: float):
        """Verify price using the primary provider."""
        return await self.primary.verify_price(item_id, original_price)

    async def get_cancellation_policy(self, booking_reference: str):
        """Get cancellation policy from the primary provider."""
        return await self.primary.get_cancellation_policy(booking_reference)

    # Domain-specific convenience methods — delegate to primary
    def __getattr__(self, name: str):
        """Delegate any domain-specific methods to the primary provider."""
        return getattr(self.primary, name)

    @staticmethod
    def _provider_name(provider: BaseProvider) -> str:
        return type(provider).__name__

    async def _log_audit(self, event_type: str, data: dict) -> None:
        if self._audit:
            try:
                await self._audit.log_tool_call(
                    trip_id="system",
                    agent_name="FallbackProvider",
                    tool_name=event_type,
                    input_data=data,
                    output_data={"status": "logged"},
                )
            except Exception:
                pass

    async def _emit_event(self, event_type: str, data: dict) -> None:
        if self._event_bus_factory:
            try:
                bus = self._event_bus_factory()
                await bus.emit({"type": event_type, **data})
            except Exception:
                pass
