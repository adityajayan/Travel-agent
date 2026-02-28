import asyncio
import json
import logging
from typing import Callable, Optional

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from agents.activity_agent import ActivityAgent
from agents.flight_agent import FlightAgent
from agents.hotel_agent import HotelAgent
from agents.transport_agent import TransportAgent
from agents.trip_state import SubTaskResult, TripState
from core.approval_gate import ApprovalGate
from core.audit_logger import AuditLogger
from core.config import settings
from core.state import ExtractedParams
from db.models import Trip
from sqlalchemy import select

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"

DOMAIN_KEYWORDS = {
    "flight": ["fly", "flight", "plane", "airport", "airline", "airways"],
    "hotel": ["hotel", "stay", "accommodation", "lodge", "hostel", "airbnb"],
    "transport": ["transport", "taxi", "transfer", "shuttle", "car", "uber", "train"],
    "activity": ["activity", "tour", "museum", "sightseeing", "experience", "visit", "excursion"],
}


def _detect_domains(goal: str) -> list[str]:
    """Simple keyword-based domain detection."""
    goal_lower = goal.lower()
    found = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in goal_lower for kw in keywords):
            found.append(domain)
    return found or ["flight"]  # default to flight if nothing detected


def _extract_params_from_plan(plan: dict) -> ExtractedParams:
    """Populate ExtractedParams from a decomposed plan dict."""
    params = ExtractedParams()
    extracted = plan.get("extracted_params", {})

    if extracted:
        params.arrival_city = extracted.get("arrival_city")
        params.arrival_airport = extracted.get("arrival_airport")
        params.departure_city = extracted.get("departure_city")
        params.departure_airport = extracted.get("departure_airport")
        params.check_in_date = extracted.get("check_in_date")
        params.check_out_date = extracted.get("check_out_date")
        params.destination_city = extracted.get("destination_city")
        if extracted.get("travel_dates"):
            params.travel_dates = extracted["travel_dates"]
        if extracted.get("num_travelers"):
            params.num_travelers = extracted["num_travelers"]
        return params

    # Infer from task goals if no explicit extracted_params
    for task in plan.get("tasks", []):
        goal = task.get("goal", "")
        domain = task.get("domain", "")
        # Basic inference: set destination_city from flight/hotel tasks
        if domain == "flight" and not params.destination_city:
            goal_lower = goal.lower()
            for prefix in ["to ", "in "]:
                idx = goal_lower.rfind(prefix)
                if idx >= 0:
                    city = goal[idx + len(prefix):].strip().rstrip(".")
                    if city:
                        params.destination_city = city
                        params.arrival_city = city
                        break

    return params


class OrchestratorAgent:
    """Decomposes a multi-domain travel goal into sub-tasks and fans out to specialist agents."""

    def __init__(
        self,
        trip_id: str,
        db: AsyncSession,
        audit_logger: AuditLogger,
        approval_gate: ApprovalGate,
        session_factory: Optional[Callable] = None,
    ):
        self.trip_id = trip_id
        self.db = db
        self.audit_logger = audit_logger
        self.approval_gate = approval_gate
        self.session_factory = session_factory
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._state: Optional[TripState] = None

    async def run(self, goal: str) -> str:
        """Main entry point. Returns a narrative trip summary."""
        state = TripState(trip_id=self.trip_id, original_goal=goal)
        self._state = state

        try:
            plan = await self._decompose(goal)
            tasks = plan.get("tasks", [])
            required_domains = set(plan.get("required", []))

            # M4: Populate ExtractedParams from plan
            state.extracted_params = _extract_params_from_plan(plan)

            # M4: Split tasks into sequential (flight) and parallel (rest)
            flight_tasks = [t for t in tasks if t.get("domain") == "flight"]
            parallel_tasks = [t for t in tasks if t.get("domain") != "flight"]

            # Phase 1: Run flight tasks sequentially (other domains may depend on arrival data)
            for task in flight_tasks:
                domain = task.get("domain", "")
                sub_goal = task.get("goal", goal)
                is_required = domain in required_domains
                await self._run_task_with_retry(state, domain, sub_goal, is_required)

            # Check if a required flight task failed — if so, skip parallel phase
            if any(r.domain == "flight" and r.status == "failed" for r in state.sub_results):
                summary = await self._synthesize(state)
                return summary

            # Phase 2: Run hotel + transport + activity in parallel
            if parallel_tasks:
                async def _run_parallel_task(task: dict):
                    domain = task.get("domain", "")
                    sub_goal = task.get("goal", goal)
                    is_required = domain in required_domains
                    try:
                        await self._run_task_with_retry(state, domain, sub_goal, is_required)
                    except Exception as exc:
                        # Return exception instead of raising — let gather continue
                        return exc
                    return None

                results = await asyncio.gather(
                    *[_run_parallel_task(t) for t in parallel_tasks],
                    return_exceptions=True,
                )

                # After gather completes, check if any required tasks failed
                for task, result in zip(parallel_tasks, results):
                    if isinstance(result, Exception):
                        domain = task.get("domain", "")
                        if domain in required_domains:
                            await self._mark_trip_failed()
                            raise result

            summary = await self._synthesize(state)
            return summary
        except Exception:
            await self._mark_trip_failed()
            raise

    async def _run_task_with_retry(
        self, state: TripState, domain: str, sub_goal: str, is_required: bool
    ) -> None:
        """Run a sub-agent task with retry logic (2 attempts)."""
        try:
            output = await self._run_sub_agent(domain, sub_goal)
            async with state._lock:
                state.add_result(SubTaskResult(domain=domain, goal=sub_goal, status="success", output=output))
        except Exception as exc:
            logger.warning("Sub-agent %s failed: %s – retrying once", domain, exc)
            try:
                output = await self._run_sub_agent(domain, sub_goal)
                async with state._lock:
                    state.add_result(SubTaskResult(domain=domain, goal=sub_goal, status="success", output=output))
            except Exception as exc2:
                if is_required:
                    async with state._lock:
                        state.add_result(SubTaskResult(domain=domain, goal=sub_goal, status="failed", error=str(exc2)))
                    await self._mark_trip_failed()
                    raise
                async with state._lock:
                    state.add_result(SubTaskResult(domain=domain, goal=sub_goal, status="skipped", error=str(exc2)))

    async def _decompose(self, goal: str) -> dict:
        """One Claude call (no tools) → structured TripPlan JSON."""
        prompt = (
            "You are a travel planning assistant. "
            "Analyse the following travel goal and return a JSON object with this exact schema:\n"
            '{"tasks": [{"domain": "<flight|hotel|transport|activity>", "goal": "<sub-goal string>"}], '
            '"required": ["<domain>", ...], "optional": ["<domain>", ...]}\n\n'
            f"Travel goal: {goal}\n\n"
            "Return ONLY the JSON object, no markdown fences."
        )
        response = await self._client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
                break

        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: use keyword detection
            domains = _detect_domains(goal)
            return {
                "tasks": [{"domain": d, "goal": goal} for d in domains],
                "required": domains,
                "optional": [],
            }

    async def _synthesize(self, state: TripState) -> str:
        """One Claude call → unified narrative trip summary."""
        summary_data = json.dumps(state.to_context_dict(), indent=2)
        prompt = (
            "You are a travel assistant. Based on the following trip planning results, "
            "write a friendly, concise narrative summary for the traveller.\n\n"
            f"Trip results:\n{summary_data}"
        )
        response = await self._client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return "Trip planning complete."

    async def _run_sub_agent(self, domain: str, sub_goal: str) -> str:
        """Instantiate and run the appropriate specialist agent."""
        # Re-use the same DB session for simplicity
        db = self.db
        agent_map = {
            "flight": FlightAgent,
            "hotel": HotelAgent,
            "transport": TransportAgent,
            "activity": ActivityAgent,
        }
        agent_cls = agent_map.get(domain)
        if not agent_cls:
            raise ValueError(f"Unknown domain: {domain}")

        agent = agent_cls(
            trip_id=self.trip_id,
            db=db,
            audit_logger=self.audit_logger,
            approval_gate=self.approval_gate,
        )
        return await agent.run(sub_goal)

    async def _mark_trip_failed(self) -> None:
        result = await self.db.execute(select(Trip).where(Trip.id == self.trip_id))
        trip = result.scalar_one_or_none()
        if trip:
            trip.status = "failed"
            await self.db.commit()
