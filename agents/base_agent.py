import logging
from typing import Optional

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.approval_gate import ApprovalGate, ApprovalRequiredError, ApprovalRejectedError, PriceChangedError
from core.audit_logger import AuditLogger
from core.config import settings
from db.models import Trip
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"

# System prompt guiding specialist agents toward cost-optimized, value-aware
# decisions when the customer hasn't expressed a strong preference.
AGENT_SYSTEM_PROMPT = (
    "You are a specialist travel booking agent. Your job is to search for options "
    "and book the best one for the customer.\n\n"
    "## Step 1 — Check what you know\n"
    "Your goal text may contain a [System defaults applied: ...] block. These are "
    "smart defaults inferred from the customer's request. Each default includes a "
    "reason and confidence level. Treat USER_STATED values as hard constraints. "
    "Treat INFERRED values as reasonable starting points — use them, but feel free "
    "to adjust if you find better options.\n\n"
    "## Step 2 — Search and score\n"
    "OPTIMIZATION GUIDELINES — apply these whenever the customer has NOT expressed "
    "a strong preference for a particular option:\n"
    "- COST: Default to the cheapest option that still meets quality standards. "
    "Prefer economy class flights, well-rated budget-friendly hotels, "
    "and free or low-cost activities.\n"
    "- DEALS & SPECIALS: Look for promotional rates, off-peak discounts, "
    "package deals, and early-bird pricing. Mention any savings you find.\n"
    "- SEASONAL TIMING: If dates are flexible or unspecified, recommend travel "
    "during shoulder season or off-peak periods when prices are lower and crowds "
    "are smaller. Note the best time of year for the destination's key activities "
    "(e.g. cherry blossoms in Japan in spring, Northern Lights in Scandinavia in "
    "winter, Mediterranean in shoulder months of May/September).\n"
    "- VALUE RATIO: When comparing similar options, choose the one with the best "
    "value — not just lowest price, but best experience-per-dollar.\n"
    "- SCORING: rank options by value_score = (quality × 0.4) + ((1 - normalized_price) × 0.6). "
    "Pick the highest scorer unless the customer stated a preference.\n\n"
    "If the customer HAS specified preferences (e.g. business class, 5-star hotel, "
    "specific airline, exact dates), respect those exactly. Only optimize on "
    "dimensions they left open.\n\n"
    "## Step 3 — Output\n"
    "Always include an 'Assumptions' section listing any inferred defaults you "
    "relied on (e.g. 'Assumed economy class — not specified'). This keeps the "
    "customer informed about what can be changed.\n\n"
    "Always explain your reasoning briefly when selecting an option."
)

# Tools that require human approval — PolicyEngine check fires for these (INV-7)
APPROVAL_REQUIRED_TOOLS = {
    "book_flight", "cancel_flight",
    "book_hotel", "cancel_hotel",
    "book_transport", "cancel_transport",
    "book_activity", "cancel_activity",
}

BOOKING_TYPE_MAP = {
    "book_flight": "flight", "cancel_flight": "flight",
    "book_hotel": "hotel", "cancel_hotel": "hotel",
    "book_transport": "transport", "cancel_transport": "transport",
    "book_activity": "activity", "cancel_activity": "activity",
}


class BaseAgent:
    """Common agentic loop: send goal to Claude, dispatch tool calls, repeat."""

    def __init__(
        self,
        name: str,
        trip_id: str,
        db: AsyncSession,
        tool_registry: ToolRegistry,
        audit_logger: AuditLogger,
        approval_gate: ApprovalGate,
        policy_engine: Optional[object] = None,  # core.policy_engine.PolicyEngine
    ):
        self.name = name
        self.trip_id = trip_id
        self.db = db
        self.tool_registry = tool_registry
        self.audit_logger = audit_logger
        self.approval_gate = approval_gate
        self.policy_engine = policy_engine
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._pending_approval_id: Optional[str] = None

    async def run(self, goal: str) -> str:
        """Run the agent loop. Returns final text output."""
        messages = [{"role": "user", "content": goal}]
        tools = self.tool_registry.get_tools()

        for iteration in range(settings.max_agent_iterations):
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=AGENT_SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            logger.debug("%s iteration %d stop_reason=%s", self.name, iteration, response.stop_reason)

            if response.stop_reason == "end_turn":
                return self._extract_text(response)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result_content = await self._dispatch_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_content,
                            }
                        )

                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            break  # unexpected stop reason

        return self._extract_text(response) if "response" in dir() else "Agent completed."

    async def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:
        """Dispatch a tool call, applying the policy pre-check before any booking tool."""
        pending_soft: list = []
        booking_type: Optional[str] = None

        try:
            # ── M3: Policy pre-check (INV-7: HARD violations never reach ApprovalGate) ────
            if tool_name in APPROVAL_REQUIRED_TOOLS and self.policy_engine is not None:
                booking_type = BOOKING_TYPE_MAP[tool_name]
                trip_spent = await self._get_trip_total_spent()
                eval_result = await self.policy_engine.evaluate(
                    booking_type=booking_type,
                    tool_input=tool_input,
                    trip_total_spent=trip_spent,
                )

                if self.policy_engine._policy:
                    await self.audit_logger.log_policy_evaluation(
                        self.trip_id,
                        self.policy_engine._policy.id,
                        booking_type,
                        eval_result,
                    )

                if eval_result.is_hard_blocked:
                    # Record violation and return fail immediately — DO NOT call ApprovalGate
                    await self.policy_engine.record_violations(
                        eval_result, self.trip_id, None, "blocked", booking_type
                    )
                    msg = eval_result.hard_violations[0].message
                    await self.audit_logger.log_tool_call(
                        self.trip_id, self.name, tool_name, tool_input,
                        {"status": "policy_blocked", "message": msg},
                    )
                    return f"POLICY_BLOCKED:{msg}"

                if eval_result.soft_violations:
                    pending_soft = eval_result.soft_violations
                    # Attach to approval_gate so the new HumanApproval row gets the context
                    self.approval_gate._pending_soft_violations = [
                        {
                            "rule_key": v.rule_key,
                            "severity": v.severity,
                            "message": v.message,
                            "actual_value": v.actual_value,
                            "rule_value": v.rule_value,
                        }
                        for v in pending_soft
                    ]
            # ── Normal tool dispatch ─────────────────────────────────────────────────────
            result = await self.tool_registry.dispatch(tool_name, tool_input)
            await self.audit_logger.log_tool_call(
                self.trip_id,
                self.name,
                tool_name,
                tool_input,
                result if isinstance(result, dict) else {"result": str(result)},
            )

            # Soft violation: booking went through without needing approval — record as approved
            if pending_soft and self.policy_engine is not None and booking_type:
                from core.policy_engine import PolicyEvalResult
                soft_result = PolicyEvalResult(
                    compliant=False, hard_violations=[], soft_violations=pending_soft
                )
                await self.policy_engine.record_violations(
                    soft_result, self.trip_id, None, "flagged_approved", booking_type
                )

            return str(result)

        except ApprovalRequiredError as exc:
            self._pending_approval_id = exc.approval_id

            # Soft violation: record as flagged_pending with the new approval_id
            if pending_soft and self.policy_engine is not None and booking_type:
                from core.policy_engine import PolicyEvalResult
                soft_result = PolicyEvalResult(
                    compliant=False, hard_violations=[], soft_violations=pending_soft
                )
                await self.policy_engine.record_violations(
                    soft_result, self.trip_id, exc.approval_id, "flagged_pending", booking_type
                )

            await self.audit_logger.log_tool_call(
                self.trip_id, self.name, tool_name, tool_input,
                {"status": "pending_approval", "approval_id": exc.approval_id},
            )
            return f"PENDING_APPROVAL:{exc.approval_id}"

        except PriceChangedError as exc:
            await self.audit_logger.log_tool_call(
                self.trip_id, self.name, tool_name, tool_input,
                {
                    "status": "price_changed",
                    "approval_id": exc.approval_id,
                    "original_price": exc.original_price,
                    "current_price": exc.current_price,
                    "pct_change": exc.pct_change,
                },
            )
            return f"PRICE_CHANGED:{exc}"

        except ApprovalRejectedError as exc:
            await self.audit_logger.log_tool_call(
                self.trip_id, self.name, tool_name, tool_input, {"status": "rejected"}
            )
            return f"REJECTED:{exc}"

        except Exception as exc:
            logger.error("%s tool %s error: %s", self.name, tool_name, exc)
            return f"ERROR:{exc}"

    async def _get_trip_total_spent(self) -> float:
        result = await self.db.execute(select(Trip).where(Trip.id == self.trip_id))
        trip = result.scalar_one_or_none()
        return trip.total_spent if trip else 0.0

    @staticmethod
    def _extract_text(response) -> str:
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""
