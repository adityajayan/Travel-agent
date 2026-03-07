import collections
import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import approvals, policies, push, streaming, trips
from core.config import settings
from db.database import init_db

logger = logging.getLogger(__name__)

app = FastAPI(title="Travel & Logistics Agentic Platform", version="0.7.0")

# ── CORS — restrict to specific origins, methods, and headers ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Security headers middleware ──────────────────────────────────────────────
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.auth_secret:
        # Only add HSTS when auth is configured (implies production-like environment)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ── Simple in-memory rate limiter ────────────────────────────────────────────
_rate_limit_window = 60  # seconds
_rate_limit_max = 60  # requests per window per IP
_rate_counters: dict[str, list[float]] = collections.defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Basic per-IP rate limiting to prevent abuse."""
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Prune old entries
    _rate_counters[client_ip] = [
        ts for ts in _rate_counters[client_ip] if now - ts < _rate_limit_window
    ]

    if len(_rate_counters[client_ip]) >= _rate_limit_max:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
            headers={"Retry-After": str(_rate_limit_window)},
        )

    _rate_counters[client_ip].append(now)
    return await call_next(request)


# M6: Health check (exempt from auth — INV-12)
@app.get("/health")
async def health():
    return {"status": "ok"}


# ── VAPID public key endpoint (exempt from auth for client bootstrap) ────────
@app.get("/push/vapid-key")
async def vapid_key():
    """Return the VAPID public key for push notification subscription."""
    return {"vapid_public_key": settings.vapid_public_key or ""}


# M6: Auth middleware — only active when AUTH_SECRET is configured
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Reject unauthenticated requests when auth is configured (INV-12)."""
    # Skip auth if not configured (dev/test mode)
    if not settings.auth_secret:
        return await call_next(request)

    # Exempt paths
    exempt = {"/health", "/docs", "/openapi.json", "/redoc", "/push/vapid-key"}
    if request.url.path in exempt:
        return await call_next(request)

    # Exempt WebSocket paths (WebSocket has its own auth via token)
    if request.url.path.endswith("/stream"):
        return await call_next(request)

    # Check for JWT
    auth_header = request.headers.get("authorization", "")
    cookie_token = request.cookies.get("auth_token")

    if not auth_header.startswith("Bearer ") and not cookie_token:
        return JSONResponse(status_code=401, content={"detail": "Authentication required"})

    token = auth_header[7:] if auth_header.startswith("Bearer ") else cookie_token

    try:
        import jwt
        payload = jwt.decode(token, settings.auth_secret, algorithms=["HS256"])
        # Inject user info into request state (never log the token — INV-12)
        request.state.user_id = payload.get("sub", "")
        request.state.user_email = payload.get("email", "")
        request.state.user_name = payload.get("name", "")
    except Exception:
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token"})

    return await call_next(request)


app.include_router(trips.router)
app.include_router(approvals.router)
app.include_router(policies.router)
app.include_router(streaming.router)
app.include_router(push.router)


@app.on_event("startup")
async def on_startup():
    await init_db()
    if not settings.auth_secret:
        logger.warning(
            "AUTH_SECRET is not configured — authentication is DISABLED. "
            "Set AUTH_SECRET in .env to enable JWT authentication."
        )
