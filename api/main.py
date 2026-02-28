from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import approvals, policies, push, streaming, trips
from core.config import settings
from db.database import init_db

app = FastAPI(title="Travel & Logistics Agentic Platform", version="0.6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# M6: Health check (exempt from auth — INV-12)
@app.get("/health")
async def health():
    return {"status": "ok"}


# M6: Auth middleware — only active when AUTH_SECRET is configured
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Reject unauthenticated requests when auth is configured (INV-12)."""
    # Skip auth if not configured (dev/test mode)
    if not settings.auth_secret:
        return await call_next(request)

    # Exempt paths
    exempt = {"/health", "/docs", "/openapi.json", "/redoc"}
    if request.url.path in exempt:
        return await call_next(request)

    # Exempt push subscription and WebSocket paths (WebSocket has its own auth)
    if request.url.path.startswith("/push/") or request.url.path.endswith("/stream"):
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
