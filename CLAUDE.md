# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent travel booking platform powered by Claude. Accepts natural language travel goals, decomposes into sub-tasks, runs specialist AI agents (flight, hotel, transport, activity), enforces corporate policies, requires human approval before bookings, and logs everything.

**Backend:** Python/FastAPI (async) with SQLAlchemy + SQLite (aiosqlite)
**Frontend:** TypeScript/React 18 + Next.js 14 (App Router) PWA with Tailwind CSS 4

## Commands

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Run all tests
pytest tests/ -v

# Run a single test file
pytest tests/test_policy_engine.py -v

# Run a specific test
pytest tests/test_policy_engine.py::test_hard_violation_blocks -v
```

### Frontend
```bash
cd client
npm install
npm run dev          # Dev server on port 3000
npm run build        # Production build
npm run lint         # ESLint
npm test             # Jest tests (--passWithNoTests)
```

### Environment
Copy `.env.example` to `.env`. Only `ANTHROPIC_API_KEY` is required. `USE_REAL_APIS=false` (default) uses mock providers. Leave `AUTH_SECRET` empty to disable JWT auth.

## Architecture

### Request Flow
```
POST /trips (natural language goal)
  → _resolve_policy() loads corporate policy
  → Domain detection → route to agent (single-domain agent or OrchestratorAgent for 2+)
  → Agent loop:
      PolicyEngine.evaluate() → hard block = POLICY_BLOCKED
      ApprovalGate.check() → creates HumanApproval row
      Human approves/rejects via POST /approvals/{id}/decide
      ApprovalGate.verify_approved() → second-layer check
      Provider books → AuditLogger.log_booking()
      EventBus.emit() → real-time events to client via WebSocket/SSE
  → Trip transitions to complete/failed
```

### Agent Routing
- Single domain → domain-specific agent (FlightAgent, HotelAgent, TransportAgent, ActivityAgent)
- Multiple domains → OrchestratorAgent (decomposes, parallel fan-out via asyncio.gather, synthesizes)

### Key Directories
- `agents/` — AI agents: `base_agent.py` (policy pre-check + tool dispatch), `orchestrator_agent.py` (parallel sub-tasks), domain agents, `trip_state.py` (shared state + asyncio.Lock)
- `api/` — FastAPI app (`main.py`) and route modules (trips, approvals, policies, streaming, push)
- `core/` — Policy engine, approval gate, audit logger, config (Pydantic BaseSettings from `.env`), event bus, auth
- `db/` — SQLAlchemy models (Trip, Booking, HumanApproval, CorporatePolicy, PolicyRule, PolicyViolation, ToolCall, User) and async session
- `providers/` — BaseProvider ABC, factory (`get_provider()`), `mock/` and `real/` implementations
- `tools/` — Scoped tool registries per agent
- `client/src/app/` — Next.js App Router pages, `trips/[id]/page.tsx` for trip detail
- `client/src/components/` — TripForm, TripTimeline, TripList, VoiceInputButton, Toast, AuthGate
- `client/src/hooks/` — useWebSocket (reconnection + SSE fallback), usePushNotifications
- `client/src/lib/` — API client singleton, airport data

### Frontend Path Alias
`@/*` maps to `./src/*` (tsconfig.json)

### API Proxy
Next.js rewrites `/api/*` to the backend URL (`BACKEND_URL` env, defaults to `http://localhost:8000`).

### Real-Time
WebSocket at `/trips/{id}/stream`, SSE fallback at `/trips/{id}/events`. Client auto-reconnects with exponential backoff.

### Policy Engine
9 rule keys (max_flight_cost, allowed_cabin_classes, max_hotel_cost_per_night, etc.). Hard violations block before ApprovalGate; soft violations attach to HumanApproval for human review.

### Database
SQLite with async SQLAlchemy. Tables auto-created on startup via `init_db()`. Audit logs (ToolCall, Booking, PolicyViolation) are append-only.

## Design System

The UI follows the **Bold Editorial** design system defined in `docs/DESIGN_SYSTEM.md`. This is the single source of truth for all visual decisions. Key rules:

- **Colors:** Cream background (#f8f5ef), Navy text (#1a1a1a), Vermillion accent (#c0392b, use sparingly)
- **Fonts:** Playfair Display (headlines), Syne (UI/buttons/labels), DM Sans (body), Lora (quotes only)
- **Border radius: 0 everywhere** — no rounded corners on any element, no exceptions
- **Borders:** 2px solid #1a1a1a for structural, 1px #e0dbd3 for internal dividers
- **No gradients, no drop shadows** — use hard offset shadow (8px 8px 0 #1a1a1a) for emphasis
- Re-read `docs/DESIGN_SYSTEM.md` before any visual change

## Key Invariants

1. `book_*`/`cancel_*` tools never execute without an approved HumanApproval record (two-layer: check + verify_approved)
2. Agents get scoped ToolRegistries — never see tools outside their domain
3. Audit logs are append-only — ToolCall, Booking, PolicyViolation rows are never updated
4. Hard policy violations block upstream of ApprovalGate
5. Credentials come from env vars only (`core/config.py`) — never hardcoded or logged
6. Real provider bookings are prefixed "SANDBOX-"
7. Auth tokens are never persisted to DB or logs

## Test Configuration

pytest uses `asyncio_mode = auto` (pytest.ini). Backend tests are in `tests/`. Frontend tests use Jest with React Testing Library.
