"""Google OAuth authentication routes.

Issues JWTs as httpOnly cookies after Google sign-in.
Tokens are never logged (INV-12).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from authlib.integrations.httpx_client import AsyncOAuth2Client
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.database import get_db
from db.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _effective_secret() -> str:
    """Return the signing secret, preferring jwt_secret over legacy auth_secret."""
    return settings.jwt_secret or settings.auth_secret


def _sign_jwt(user_id: str, email: str, name: str, picture_url: str | None = None, is_approved: bool = False) -> str:
    """Create a signed JWT for the given user. Never log the token (INV-12)."""
    secret = _effective_secret()
    if not secret:
        raise ValueError("jwt_secret (or auth_secret) must be configured to issue tokens")
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "picture": picture_url or "",
        "is_approved": is_approved,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _build_oauth_client() -> AsyncOAuth2Client:
    return AsyncOAuth2Client(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
        scope="openid email profile",
    )


@router.get("/google")
async def google_login():
    """Return the Google OAuth authorization URL."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth not configured")

    client = _build_oauth_client()
    uri, _state = client.create_authorization_url(GOOGLE_AUTHORIZE_URL)
    return {"url": uri}


@router.get("/callback/google")
async def google_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback: exchange code, upsert user, set cookie, redirect."""
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Exchange code for tokens
    client = _build_oauth_client()
    try:
        token_resp = await client.fetch_token(
            GOOGLE_TOKEN_URL,
            code=code,
            grant_type="authorization_code",
        )
    except Exception as exc:
        logger.error("Google token exchange failed: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    # Fetch user profile from Google
    try:
        resp = await client.get(GOOGLE_USERINFO_URL)
        resp.raise_for_status()
        userinfo = resp.json()
    except Exception as exc:
        logger.error("Google userinfo fetch failed: %s", exc)
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

    google_sub = userinfo.get("sub", "")
    email = userinfo.get("email", "")
    name = userinfo.get("name", email)
    picture = userinfo.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    # Upsert user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # Update profile info on each login
        user.name = name
        user.auth_provider_id = google_sub
        if picture:
            user.picture_url = picture
    else:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            auth_provider_id=google_sub,
            auth_provider="google",
            picture_url=picture,
            is_approved=False,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)

    # Issue JWT and set as httpOnly cookie
    token = _sign_jwt(user.id, user.email, user.name, user.picture_url, user.is_approved)

    redirect_url = settings.frontend_url
    if not user.is_approved:
        redirect_url += "?waitlisted=true"

    response = RedirectResponse(url=redirect_url, status_code=302)
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


@router.post("/logout")
async def logout():
    """Clear the auth cookie."""
    response = JSONResponse(content={"status": "logged_out"})
    response.delete_cookie(key="auth_token", path="/")
    return response


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    """Return current user info from JWT cookie or Bearer token."""
    secret = _effective_secret()
    if not secret:
        return {"user": None, "auth_configured": False}

    # Extract token from cookie or header
    token = request.cookies.get("auth_token")
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        return {"user": None, "auth_configured": True}

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        response = JSONResponse(content={"user": None, "auth_configured": True, "expired": True})
        response.delete_cookie(key="auth_token", path="/")
        return response
    except jwt.InvalidTokenError:
        return {"user": None, "auth_configured": True}

    # Refresh approval status from DB in case it changed since token was issued
    user_id = payload.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {"user": None, "auth_configured": True}

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture_url": user.picture_url,
            "is_approved": user.is_approved,
        },
        "auth_configured": True,
    }
