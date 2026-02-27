"""CRUD routes for CorporatePolicy, PolicyRule, and the policy-report endpoint."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.schemas import PolicyCreate, PolicyOut, PolicyRuleOut, PolicyRuleUpdate, PolicyUpdate
from db.database import get_db
from db.models import CorporatePolicy, PolicyRule

router = APIRouter(prefix="/policies", tags=["policies"])


async def _get_policy_with_rules(policy_id: str, db: AsyncSession) -> Optional[CorporatePolicy]:
    """Fetch a CorporatePolicy with its rules eagerly loaded."""
    result = await db.execute(
        select(CorporatePolicy)
        .options(selectinload(CorporatePolicy.rules))
        .where(CorporatePolicy.id == policy_id)
    )
    return result.scalar_one_or_none()


# ── Policy CRUD ───────────────────────────────────────────────────────────────

@router.post("", response_model=PolicyOut, status_code=201)
async def create_policy(body: PolicyCreate, db: AsyncSession = Depends(get_db)):
    # Enforce: only one active policy per org (409 if violated)
    if body.is_active:
        existing = await db.execute(
            select(CorporatePolicy).where(
                CorporatePolicy.org_id == body.org_id,
                CorporatePolicy.is_active == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"An active policy already exists for org '{body.org_id}'. "
                       "Deactivate it first or set is_active=false.",
            )

    policy = CorporatePolicy(
        id=str(uuid.uuid4()),
        org_id=body.org_id,
        name=body.name,
        is_active=body.is_active,
        created_by=body.created_by,
    )
    db.add(policy)
    await db.flush()  # get policy.id before adding rules

    for rule_data in body.rules:
        rule = PolicyRule(
            id=str(uuid.uuid4()),
            policy_id=policy.id,
            booking_type=rule_data.booking_type,
            rule_key=rule_data.rule_key,
            operator=rule_data.operator,
            value=rule_data.value,
            severity=rule_data.severity,
            message=rule_data.message,
            is_enabled=rule_data.is_enabled,
        )
        db.add(rule)

    await db.commit()
    # Re-fetch with rules eagerly loaded (avoids greenlet lazy-load error)
    return await _get_policy_with_rules(policy.id, db)


@router.get("", response_model=list[PolicyOut])
async def list_policies(org_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = (
        select(CorporatePolicy)
        .options(selectinload(CorporatePolicy.rules))
        .order_by(CorporatePolicy.created_at.desc())
    )
    if org_id:
        query = query.where(CorporatePolicy.org_id == org_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{policy_id}", response_model=PolicyOut)
async def get_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    policy = await _get_policy_with_rules(policy_id, db)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.patch("/{policy_id}", response_model=PolicyOut)
async def update_policy(
    policy_id: str, body: PolicyUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CorporatePolicy).where(CorporatePolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    # Enforce one-active-per-org if activating
    if body.is_active is True and not policy.is_active:
        existing = await db.execute(
            select(CorporatePolicy).where(
                CorporatePolicy.org_id == policy.org_id,
                CorporatePolicy.is_active == True,  # noqa: E712
                CorporatePolicy.id != policy_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Another active policy exists for org '{policy.org_id}'.",
            )

    if body.name is not None:
        policy.name = body.name
    if body.is_active is not None:
        policy.is_active = body.is_active

    await db.commit()
    # Re-fetch with rules eagerly loaded
    return await _get_policy_with_rules(policy_id, db)


@router.delete("/{policy_id}", status_code=204)
async def delete_policy(policy_id: str, db: AsyncSession = Depends(get_db)):
    """Soft delete — sets is_active=False. Existing trips referencing the policy are unaffected."""
    result = await db.execute(
        select(CorporatePolicy).where(CorporatePolicy.id == policy_id)
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.is_active = False
    await db.commit()


# ── Rule PATCH ────────────────────────────────────────────────────────────────

@router.patch("/{policy_id}/rules/{rule_id}", response_model=PolicyRuleOut)
async def update_rule(
    policy_id: str,
    rule_id: str,
    body: PolicyRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PolicyRule).where(
            PolicyRule.id == rule_id, PolicyRule.policy_id == policy_id
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if body.is_enabled is not None:
        rule.is_enabled = body.is_enabled
    if body.value is not None:
        rule.value = body.value
    if body.severity is not None:
        rule.severity = body.severity
    if body.message is not None:
        rule.message = body.message

    await db.commit()
    await db.refresh(rule)
    return rule
