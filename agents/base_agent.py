import logging
from typing import Optional

from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.approval_gate import ApprovalGate, ApprovalRequiredError, ApprovalRejectedError
from core.audit_logger import AuditLogger
from core.config import settings
from db.models import Trip
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-6"

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
