"""Authentication middleware for JWT validation (M6 Item 1).

Validates JWT on every request, injects current_user dependency.
Auth tokens never logged or stored in DB (INV-12).
"""
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.database import get_db
from db.models import User

logger = logging.getLogger(__name__)

# Paths exempt from authentication
AUTH_EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class CurrentUser:
    """Represents the authenticated user from JWT."""
    def __init__(self, user_id: str, email: str, name: str):
        self.user_id = user_id
        self.email = email
        self.name = name


def _decode_jwt(token: str) -> dict:
    """Decode and validate a JWT token. Never log the token (INV-12)."""
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret,
            algorithms=["HS256"],
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _extract_token(request: Request) -> Optional[str]:
    """Extract JWT from Authorization header or cookie. Never log the token (INV-12)."""
    # Check Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    # Check httpOnly cookie
    token = request.cookies.get("auth_token")
    if token:
        return token

    return None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """FastAPI dependency that validates JWT and returns the current user.

    Raises 401 if no valid token is present.
    """
    # Skip auth for exempt paths
    if request.url.path in AUTH_EXEMPT_PATHS:
        return CurrentUser(user_id="anonymous", email="", name="Anonymous")

    # Skip auth if auth is not configured (dev/test mode)
    if not settings.auth_secret:
        return CurrentUser(user_id="anonymous", email="", name="Anonymous")

    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = _decode_jwt(token)

    user_id = payload.get("sub", "")
    email = payload.get("email", "")
    name = payload.get("name", "")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")

    return CurrentUser(user_id=user_id, email=email, name=name)


async def get_optional_user(request: Request) -> Optional[CurrentUser]:
    """Non-strict version: returns None if no auth is configured or no token present."""
    if not settings.auth_secret:
        return None

    token = _extract_token(request)
    if not token:
        return None

    try:
        payload = _decode_jwt(token)
        return CurrentUser(
            user_id=payload.get("sub", ""),
            email=payload.get("email", ""),
            name=payload.get("name", ""),
        )
    except HTTPException:
        return None
