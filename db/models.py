import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, JSON, String
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ── M6: User model ──────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    auth_provider_id = Column(String, nullable=False)  # external ID from Supabase/Auth0
    preferences_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trips = relationship("Trip", back_populates="user", lazy="select")


class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    goal = Column(String, nullable=False)
    # pending | running | awaiting_approval | complete | failed
    status = Column(String, default="pending", nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)
    # M3/M6 additions
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    total_budget = Column(Float, nullable=True)
    org_id = Column(String, nullable=True)
    policy_id = Column(String, ForeignKey("corporate_policies.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="trips", lazy="select")
    bookings = relationship("Booking", back_populates="trip", lazy="select")
    tool_calls = relationship("ToolCall", back_populates="trip", lazy="select")
    approvals = relationship("HumanApproval", back_populates="trip", lazy="select")
    policy_violations = relationship("PolicyViolation", back_populates="trip", lazy="select")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    # flight | hotel | transport | activity
    domain = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    details = Column(JSON, nullable=False)
    amount = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trip = relationship("Trip", back_populates="bookings")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    agent_name = Column(String, nullable=False)
    tool_name = Column(String, nullable=False)
    input = Column(JSON)
    output = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    trip = relationship("Trip", back_populates="tool_calls")


class HumanApproval(Base):
    __tablename__ = "human_approvals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    domain = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSON)
    # pending | approved | rejected
    status = Column(String, default="pending", nullable=False)
    # M3: denormalised snapshot of SOFT policy violations at approval creation time
    policy_violations_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    decided_at = Column(DateTime(timezone=True))

    trip = relationship("Trip", back_populates="approvals")


# ── M3: Corporate Policy Engine ───────────────────────────────────────────────

class CorporatePolicy(Base):
    __tablename__ = "corporate_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String, nullable=False, default="system")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    rules = relationship("PolicyRule", back_populates="policy", lazy="select",
                         cascade="all, delete-orphan")
    violations = relationship("PolicyViolation", back_populates="policy", lazy="select")


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id = Column(String, ForeignKey("corporate_policies.id"), nullable=False)
    # 'flight' | 'hotel' | 'any'
    booking_type = Column(String, nullable=False)
    rule_key = Column(String, nullable=False)
    # 'lte' | 'gte' | 'in' | 'not_in'
    operator = Column(String, nullable=False)
    value = Column(JSON, nullable=False)
    # 'hard' | 'soft'
    severity = Column(String, nullable=False)
    message = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)

    policy = relationship("CorporatePolicy", back_populates="rules")


class PolicyViolation(Base):
    """Append-only audit record of every policy evaluation that produced a violation (INV-8)."""

    __tablename__ = "policy_violations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    policy_id = Column(String, ForeignKey("corporate_policies.id"), nullable=False)
    rule_id = Column(String, ForeignKey("policy_rules.id"), nullable=False)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    approval_id = Column(String, ForeignKey("human_approvals.id"), nullable=True)
    booking_type = Column(String, nullable=False)
    # 'hard' | 'soft'
    severity = Column(String, nullable=False)
    actual_value = Column(JSON, nullable=False)
    rule_value = Column(JSON, nullable=False)
    # 'blocked' | 'flagged_pending' | 'flagged_approved' | 'flagged_rejected'
    outcome = Column(String, nullable=False)
    message = Column(String, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    policy = relationship("CorporatePolicy", back_populates="violations")
    trip = relationship("Trip", back_populates="policy_violations")


# Indices for common query patterns
Index("ix_policies_org_active", CorporatePolicy.org_id, CorporatePolicy.is_active)
Index("ix_violations_trip", PolicyViolation.trip_id)
