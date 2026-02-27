"""Corporate Travel Policy Engine — M3.

Sits upstream of ApprovalGate and enforces organisational spend rules.
HARD violations block the booking entirely (INV-7).
SOFT violations flag the approval for manager review.
"""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import CorporatePolicy, PolicyRule, PolicyViolation

logger = logging.getLogger(__name__)


class PolicyNotFoundError(Exception):
    """Raised when a policy_id is supplied but the policy is missing or inactive (INV-9)."""


@dataclass
class PolicyViolationDetail:
    rule_id: str
    rule_key: str
    severity: str  # 'hard' | 'soft'
    message: str
    actual_value: dict
    rule_value: dict


@dataclass
class PolicyEvalResult:
    compliant: bool
    hard_violations: List[PolicyViolationDetail] = field(default_factory=list)
    soft_violations: List[PolicyViolationDetail] = field(default_factory=list)

    @property
    def is_hard_blocked(self) -> bool:
        return len(self.hard_violations) > 0


class PolicyEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._policy: Optional[CorporatePolicy] = None
        self._rules: List[PolicyRule] = []

    async def load_policy(self, policy_id: str) -> CorporatePolicy:
        """Load policy + rules. Raises PolicyNotFoundError if missing or inactive (INV-9)."""
        result = await self.db.execute(
            select(CorporatePolicy).where(CorporatePolicy.id == policy_id)
        )
        policy = result.scalar_one_or_none()
        if not policy or not policy.is_active:
            raise PolicyNotFoundError(
                f"Policy '{policy_id}' not found or is inactive. Trip will be marked failed."
            )
        self._policy = policy

        rules_result = await self.db.execute(
            select(PolicyRule).where(
                PolicyRule.policy_id == policy_id,
                PolicyRule.is_enabled == True,  # noqa: E712
            )
        )
        self._rules = list(rules_result.scalars().all())
        return policy

    async def evaluate(
        self,
        booking_type: str,
        tool_input: dict,
        trip_total_spent: float = 0.0,
    ) -> PolicyEvalResult:
        """Run all enabled rules for this booking_type + 'any' rules.

        Returns violations WITHOUT writing DB rows — caller decides outcome first.
        """
        if self._policy is None:
            return PolicyEvalResult(compliant=True)

        applicable = [r for r in self._rules if r.booking_type in (booking_type, "any")]

        hard: List[PolicyViolationDetail] = []
        soft: List[PolicyViolationDetail] = []

        for rule in applicable:
            violation = self._evaluate_rule(rule, tool_input, trip_total_spent)
            if violation:
                if violation.severity == "hard":
                    hard.append(violation)
                else:
                    soft.append(violation)

        return PolicyEvalResult(
            compliant=not hard and not soft,
            hard_violations=hard,
            soft_violations=soft,
        )

    def _evaluate_rule(
        self, rule: PolicyRule, tool_input: dict, trip_total_spent: float
    ) -> Optional[PolicyViolationDetail]:
        """Evaluate one rule. Returns a violation detail if violated, None if compliant or skipped."""
        rk = rule.rule_key
        rv = rule.value

        try:
            if rk == "max_flight_cost":
                actual = tool_input.get("estimated_cost")
                if actual is None:
                    logger.warning("Rule %s skipped: 'estimated_cost' missing from tool_input", rk)
                    return None
                if actual > rv["amount"]:
                    return self._violation(rule, {"estimated_cost": actual}, rv)

            elif rk == "allowed_cabin_classes":
                default_cabin = rv.get("default", "economy")
                actual = tool_input.get("cabin_class", default_cabin)
                if actual not in rv["classes"]:
                    return self._violation(rule, {"cabin_class": actual}, rv)

            elif rk == "require_advance_booking_days":
                departure = tool_input.get("departure_date")
                if departure is None:
                    logger.warning("Rule %s skipped: 'departure_date' missing", rk)
                    return None
                if isinstance(departure, str):
                    from datetime import date as dt_date
                    dep_date = dt_date.fromisoformat(departure)
                else:
                    dep_date = departure
                days_ahead = (dep_date - datetime.now(timezone.utc).date()).days
                if days_ahead < rv["days"]:
                    return self._violation(rule, {"days_ahead": days_ahead}, rv)

            elif rk == "max_flight_duration_hours":
                minutes = tool_input.get("duration_minutes", 0)
                hours = minutes / 60.0
                if hours > rv["hours"]:
                    return self._violation(rule, {"duration_hours": round(hours, 2)}, rv)

            elif rk == "max_hotel_cost_per_night":
                actual = tool_input.get("cost_per_night")
                if actual is None:
                    logger.warning("Rule %s skipped: 'cost_per_night' missing", rk)
                    return None
                if actual > rv["amount"]:
                    return self._violation(rule, {"cost_per_night": actual}, rv)

            elif rk == "max_hotel_stay_total":
                cpn = tool_input.get("cost_per_night")
                nights = tool_input.get("nights")
                if cpn is None or nights is None:
                    logger.warning("Rule %s skipped: cost_per_night or nights missing", rk)
                    return None
                total = cpn * nights
                if total > rv["amount"]:
                    return self._violation(rule, {"stay_total": total}, rv)

            elif rk == "max_hotel_star_rating":
                default_stars = rv.get("default", 0)
                actual = tool_input.get("star_rating", default_stars)
                if actual > rv["stars"]:
                    return self._violation(rule, {"star_rating": actual}, rv)

            elif rk == "preferred_vendors_only":
                provider = tool_input.get("provider")
                if provider is None:
                    logger.warning("Rule %s skipped: 'provider' missing", rk)
                    return None
                if provider not in rv["vendors"]:
                    return self._violation(rule, {"provider": provider}, rv)

            elif rk == "max_total_trip_spend":
                estimated = tool_input.get("estimated_cost", 0.0)
                projected = trip_total_spent + estimated
                if projected > rv["amount"]:
                    return self._violation(
                        rule,
                        {"projected_total": round(projected, 2), "already_spent": round(trip_total_spent, 2)},
                        rv,
                    )

            else:
                logger.warning("Unknown rule_key '%s' — skipping", rk)

        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Rule evaluation error for '%s': %s — skipping", rk, exc)

        return None  # compliant or skipped

    @staticmethod
    def _violation(rule: PolicyRule, actual: dict, rule_val: dict) -> PolicyViolationDetail:
        return PolicyViolationDetail(
            rule_id=rule.id,
            rule_key=rule.rule_key,
            severity=rule.severity,
            message=rule.message,
            actual_value=actual,
            rule_value=rule_val,
        )

    async def record_violations(
        self,
        result: PolicyEvalResult,
        trip_id: str,
        approval_id: Optional[str],
        outcome: str,
        booking_type: str,
    ) -> List[str]:
        """Append PolicyViolation rows (INV-8: never updated). Returns list of violation IDs."""
        if self._policy is None:
            return []

        all_violations = result.hard_violations + result.soft_violations
        ids: List[str] = []
        for v in all_violations:
            row = PolicyViolation(
                id=str(uuid.uuid4()),
                policy_id=self._policy.id,
                rule_id=v.rule_id,
                trip_id=trip_id,
                approval_id=approval_id,
                booking_type=booking_type,
                severity=v.severity,
                actual_value=v.actual_value,
                rule_value=v.rule_value,
                outcome=outcome,
                message=v.message,
            )
            self.db.add(row)
            ids.append(row.id)

        await self.db.commit()
        return ids
