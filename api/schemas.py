from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Trips ──────────────────────────────────────────────────────────────────────

class TripCreate(BaseModel):
    goal: str
    user_id: Optional[str] = None  # M6: set from JWT auth; nullable for migration compat
    total_budget: Optional[float] = None
    org_id: Optional[str] = None
    policy_id: Optional[str] = None  # explicit override; error if inactive (INV-9)


class TripRead(BaseModel):
    id: str
    goal: str
    status: str
    total_spent: float
    user_id: Optional[str] = None
    total_budget: Optional[float] = None
    org_id: Optional[str] = None
    policy_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Approvals ──────────────────────────────────────────────────────────────────

class ApprovalRead(BaseModel):
    id: str
    trip_id: str
    domain: str
    action: str
    details: Optional[Dict[str, Any]] = None
    status: str
    policy_violations_json: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ApprovalDecide(BaseModel):
    approved: bool


class PolicyViolationOut(BaseModel):
    rule_key: str
    severity: str
    message: str
    actual_value: Dict[str, Any]
    rule_value: Dict[str, Any]


class PendingApprovalOut(BaseModel):
    """Approval detail shown to travel approvers — includes inline policy violations."""
    id: str
    trip_id: str
    domain: str
    action: str
    details: Optional[Dict[str, Any]] = None
    status: str
    requested_at: Optional[datetime] = None
    policy_violations: List[PolicyViolationOut] = []

    model_config = {"from_attributes": True}


# ── Policies ──────────────────────────────────────────────────────────────────

class PolicyRuleCreate(BaseModel):
    booking_type: str  # 'flight' | 'hotel' | 'any'
    rule_key: str
    operator: str      # 'lte' | 'gte' | 'in' | 'not_in'
    value: Dict[str, Any]
    severity: str      # 'hard' | 'soft'
    message: str
    is_enabled: bool = True


class PolicyRuleOut(BaseModel):
    id: str
    policy_id: str
    booking_type: str
    rule_key: str
    operator: str
    value: Dict[str, Any]
    severity: str
    message: str
    is_enabled: bool

    model_config = {"from_attributes": True}


class PolicyRuleUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    value: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    message: Optional[str] = None


class PolicyCreate(BaseModel):
    org_id: str
    name: str
    is_active: bool = True
    created_by: str = "system"
    rules: List[PolicyRuleCreate] = []


class PolicyOut(BaseModel):
    id: str
    org_id: str
    name: str
    is_active: bool
    created_by: str
    created_at: Optional[datetime] = None
    rules: List[PolicyRuleOut] = []

    model_config = {"from_attributes": True}


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None


# ── Policy report ─────────────────────────────────────────────────────────────

class PolicyViolationRowOut(BaseModel):
    id: str
    policy_id: str
    rule_id: str
    trip_id: str
    approval_id: Optional[str] = None
    booking_type: str
    severity: str
    actual_value: Dict[str, Any]
    rule_value: Dict[str, Any]
    outcome: str
    message: str
    recorded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PolicyReportResponse(BaseModel):
    trip_id: str
    policy_id: Optional[str] = None
    violations: List[PolicyViolationRowOut] = []
