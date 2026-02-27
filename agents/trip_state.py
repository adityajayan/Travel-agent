from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubTaskResult:
    domain: str
    goal: str
    status: str  # success | failed | skipped
    output: str = ""
    error: str = ""


@dataclass
class TripState:
    """Shared state passed between OrchestratorAgent and its sub-agents."""

    trip_id: str
    original_goal: str
    sub_results: List[SubTaskResult] = field(default_factory=list)
    # M3: policy resolution fields (populated at trip creation, before agent loop)
    policy_id: Optional[str] = None
    org_id: Optional[str] = None
    # Cached CorporatePolicy object — avoids repeated DB round-trips (not serialised)
    _policy: Any = field(default=None, repr=False, compare=False)

    def add_result(self, result: SubTaskResult) -> None:
        self.sub_results.append(result)

    def successful_domains(self) -> List[str]:
        return [r.domain for r in self.sub_results if r.status == "success"]

    def failed_domains(self) -> List[str]:
        return [r.domain for r in self.sub_results if r.status == "failed"]

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
