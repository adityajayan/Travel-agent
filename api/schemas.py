from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Trips ──────────────────────────────────────────────────────────────────────

class TripCreate(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = Field(None, max_length=255)
    total_budget: Optional[float] = Field(None, ge=0, le=1_000_000)
    org_id: Optional[str] = Field(None, max_length=255)
    policy_id: Optional[str] = Field(None, max_length=255)
    parsed_params: Optional["ParsedTripParams"] = None


class ClarificationResponse(BaseModel):
    request_id: str = Field(..., max_length=255)
    answers: Dict[str, str]  # values are user-supplied text


class BookingOut(BaseModel):
    domain: str
    provider: str
    details: Dict[str, Any]
    amount: float

    model_config = {"from_attributes": True}


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
    summary_text: Optional[str] = None
    bookings: List[BookingOut] = []

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
    booking_type: str = Field(..., max_length=50)
    rule_key: str = Field(..., max_length=100)
    operator: str = Field(..., max_length=20)
    value: Dict[str, Any]
    severity: str = Field(..., max_length=10)
    message: str = Field(..., max_length=500)
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
    severity: Optional[str] = Field(None, max_length=10)
    message: Optional[str] = Field(None, max_length=500)


class PolicyCreate(BaseModel):
    org_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    created_by: str = Field("system", max_length=255)
    rules: List[PolicyRuleCreate] = Field(default=[], max_length=50)


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
    name: Optional[str] = Field(None, max_length=255)
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


# ── Parse (freeform NLU) ─────────────────────────────────────────────────────

class ParseTripRequest(BaseModel):
    text: str = Field(..., min_length=5, max_length=2000, description="Raw natural language trip request")


class TravelerCount(BaseModel):
    adults: int = 1
    children: int = 0


class FlightPreferences(BaseModel):
    cabin_class: Optional[str] = None
    airline: Optional[str] = None
    nonstop: Optional[bool] = None
    seat_preference: Optional[str] = None


class HotelPreferences(BaseModel):
    type: Optional[str] = None
    star_rating: Optional[int] = None
    amenities: List[str] = Field(default_factory=list)
    location_notes: Optional[str] = None
    budget_per_night: Optional[float] = None


class ParsedTripParams(BaseModel):
    destinations: List[str] = Field(default_factory=list)
    origin: Optional[str] = None
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    duration_days: Optional[int] = None
    budget_total: Optional[float] = None
    budget_currency: str = "USD"
    travelers: TravelerCount = Field(default_factory=TravelerCount)
    domains: List[str] = Field(default_factory=list)
    flight_preferences: FlightPreferences = Field(default_factory=FlightPreferences)
    hotel_preferences: HotelPreferences = Field(default_factory=HotelPreferences)
    activity_preferences: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ParseTripResponse(BaseModel):
    parsed: ParsedTripParams
    goal_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    clarification_needed: List[str] = Field(default_factory=list)
    raw_input: str


# Resolve forward reference in TripCreate
TripCreate.model_rebuild()
