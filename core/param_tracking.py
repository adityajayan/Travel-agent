"""Provenance tracking for trip parameters.

Every extracted/inferred parameter carries its source and a human-readable
reason so the UI and agents can transparently communicate assumptions.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ParamSource(str, Enum):
    USER_STATED = "user_stated"        # explicitly in the goal text
    INFERRED_DEFAULT = "inferred"      # smart default applied by the system
    AGENT_REFINED = "agent_refined"    # agent adjusted after search results
    USER_HISTORY = "user_history"      # from past trip preferences (future)


@dataclass
class TrackedParam:
    value: Any
    source: ParamSource
    confidence: float = 1.0            # 0–1, lower for guesses
    reason: str = ""                   # human-readable explanation

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "source": self.source.value,
            "confidence": self.confidence,
            "reason": self.reason,
        }


@dataclass
class TrackedParams:
    """Mirrors ExtractedParams fields but wraps each in TrackedParam | None."""

    destination_city: Optional[TrackedParam] = None
    departure_city: Optional[TrackedParam] = None
    arrival_airport: Optional[TrackedParam] = None
    departure_airport: Optional[TrackedParam] = None
    check_in_date: Optional[TrackedParam] = None
    check_out_date: Optional[TrackedParam] = None
    duration_nights: Optional[TrackedParam] = None
    num_travelers: Optional[TrackedParam] = None
    cabin_class: Optional[TrackedParam] = None
    total_budget: Optional[TrackedParam] = None
    trip_purpose: Optional[TrackedParam] = None

    # Budget breakdown (when total_budget is known)
    flight_budget: Optional[TrackedParam] = None
    hotel_budget: Optional[TrackedParam] = None

    def _all_fields(self) -> Dict[str, Optional[TrackedParam]]:
        return {
            "destination_city": self.destination_city,
            "departure_city": self.departure_city,
            "arrival_airport": self.arrival_airport,
            "departure_airport": self.departure_airport,
            "check_in_date": self.check_in_date,
            "check_out_date": self.check_out_date,
            "duration_nights": self.duration_nights,
            "num_travelers": self.num_travelers,
            "cabin_class": self.cabin_class,
            "total_budget": self.total_budget,
            "trip_purpose": self.trip_purpose,
            "flight_budget": self.flight_budget,
            "hotel_budget": self.hotel_budget,
        }

    def stated_params(self) -> Dict[str, Any]:
        """Only user-stated values."""
        return {
            k: tp.value
            for k, tp in self._all_fields().items()
            if tp is not None and tp.source == ParamSource.USER_STATED
        }

    def inferred_params(self) -> Dict[str, dict]:
        """Only system-inferred values with reasons."""
        return {
            k: {"value": tp.value, "reason": tp.reason, "confidence": tp.confidence}
            for k, tp in self._all_fields().items()
            if tp is not None and tp.source == ParamSource.INFERRED_DEFAULT
        }

    def missing_params(self) -> List[str]:
        """Fields still None after extraction."""
        return [k for k, tp in self._all_fields().items() if tp is None]

    def to_context_dict(self) -> Dict[str, Any]:
        """Serialize for agent context — three sections."""
        return {
            "user_stated": self.stated_params(),
            "system_inferred": self.inferred_params(),
            "missing_params": self.missing_params(),
        }

    def to_flat_dict(self) -> Dict[str, Any]:
        """Flat dict of all resolved values (regardless of source)."""
        return {
            k: tp.value
            for k, tp in self._all_fields().items()
            if tp is not None
        }
