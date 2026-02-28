import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import dataclasses

from core.state import ExtractedParams


@dataclass
class SubTaskResult:
    domain: str
    goal: str
    status: str  # success | failed | skipped
    output: str = ""
    error: str = ""


@dataclass
class BookingRecord:
    domain: str
    provider: str
    details: dict
    amount: float


@dataclass
class TripState:
    """Shared state passed between OrchestratorAgent and its sub-agents."""

    trip_id: str
    original_goal: str
    sub_results: List[SubTaskResult] = field(default_factory=list)
    bookings: List[BookingRecord] = field(default_factory=list)
    total_spent: float = 0.0
    # M3: policy resolution fields (populated at trip creation, before agent loop)
    policy_id: Optional[str] = None
    org_id: Optional[str] = None
    # Cached CorporatePolicy object — avoids repeated DB round-trips (not serialised)
    _policy: Any = field(default=None, repr=False, compare=False)
    # M4: Typed extracted parameters for cross-agent data passing
    extracted_params: ExtractedParams = field(default_factory=ExtractedParams)
    # M4: Lock for thread-safe parallel state updates
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def add_result(self, result: SubTaskResult) -> None:
        self.sub_results.append(result)

    async def safe_add_booking(self, record: BookingRecord) -> None:
        """Thread-safe booking append for parallel execution (M4)."""
        async with self._lock:
            self.bookings.append(record)
            self.total_spent += record.amount

    def successful_domains(self) -> List[str]:
        return [r.domain for r in self.sub_results if r.status == "success"]

    def failed_domains(self) -> List[str]:
        return [r.domain for r in self.sub_results if r.status == "failed"]

    def to_context_dict(self) -> Dict[str, Any]:
        """Serialize state including ExtractedParams as a flat dict."""
        result = self.summary_dict()
        result["extracted_params"] = dataclasses.asdict(self.extracted_params)
        return result

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "trip_id": self.trip_id,
            "goal": self.original_goal,
            "sub_results": [
                {
                    "domain": r.domain,
                    "status": r.status,
                    "output": r.output,
                    "error": r.error,
                }
                for r in self.sub_results
            ],
        }
