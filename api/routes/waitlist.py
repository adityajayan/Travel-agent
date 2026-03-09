"""Waitlist and invite-code routes for controlled rollout."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.database import get_db
from db.models import User, WaitlistEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


class WaitlistRequest(BaseModel):
    email: str


class InviteCodeRequest(BaseModel):
    code: str
    user_id: str


@router.post("")
async def join_waitlist(body: WaitlistRequest, db: AsyncSession = Depends(get_db)):
    """Add an email to the waitlist. Public endpoint — no auth required."""
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")

    # Check if already on waitlist
    result = await db.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        return {"status": "already_registered", "email": email}

    entry = WaitlistEntry(id=str(uuid.uuid4()), email=email)
    db.add(entry)
    await db.commit()

    return {"status": "joined", "email": email}


@router.post("/validate-invite")
async def validate_invite(body: InviteCodeRequest, db: AsyncSession = Depends(get_db)):
    """Validate an invite code and approve the user."""
    if not settings.invite_codes:
        raise HTTPException(status_code=503, detail="Invite codes not configured")

    valid_codes = {c.strip() for c in settings.invite_codes.split(",") if c.strip()}

    if body.code.strip() not in valid_codes:
        raise HTTPException(status_code=403, detail="Invalid invite code")

    # Find and approve the user
    result = await db.execute(select(User).where(User.id == body.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_approved = True
    await db.commit()
    await db.refresh(user)

    # Issue a new JWT with updated is_approved claim
    secret = settings.jwt_secret or settings.auth_secret
    if not secret:
        raise HTTPException(status_code=500, detail="Auth not configured")

    token = jwt.encode(
        {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture_url or "",
            "is_approved": True,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
        },
        secret,
        algorithm="HS256",
    )

    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"status": "approved", "user_id": user.id})
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.jwt_expiry_hours * 3600,
        path="/",
    )
    return response
