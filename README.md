# Travel & Logistics Agentic Platform

Multi-agent travel booking system powered by Claude. Accepts natural language
travel goals, decomposes them into sub-tasks, runs specialist AI agents, requires
human approval before any booking, and logs everything to a database.

---

## Repository Layout

```
travel-agent/            ← repo root
├── README.md            ← you are here
├── agents/
├── tools/
├── core/
├── db/
├── api/
├── providers/
├── tests/
├── requirements.txt
└── pytest.ini
```

> **Note:** This repo contains the full runnable codebase only. Milestone
> snapshots and delta folders (`milestones/m1/`, `milestones/m2/` etc.) are
> maintained separately in the build chat and are not committed here. The
> repo always reflects the latest complete state — every milestone is applied
> on top of the previous one before pushing.

---

## Adding a New Milestone

1. Build the milestone delta in the build chat (new + modified files only).
2. Overlay those files onto this repo (new files added, modified files overwrite).
3. Update the milestone status table below and push.
4. Commit with message: `feat: milestone 3 — <one-line description>`.
5. Tag: `git tag v0.3.0-m3 && git push origin v0.3.0-m3`.

---

## Architecture

```
POST /trips  →  Agent runs async in background  →  Claude calls tools  →
ApprovalGate intercepts book_*/cancel_* calls  →  Human approves via
POST /approvals/{id}/decide  →  Booking persisted, Trip marked complete
```

### Agent routing (as of M2)

| Goal domains detected       | Agent used          |
|-----------------------------|---------------------|
| 1 domain (flight only)      | FlightAgent         |
| 1 domain (hotel only)       | HotelAgent          |
| 1 domain (transport only)   | TransportAgent      |
| 1 domain (activity only)    | ActivityAgent       |
| 2+ domains                  | OrchestratorAgent   |

### OrchestratorAgent flow (M2)

1. `_decompose()` — one Claude call, no tools → structured TripPlan JSON
2. Fan-out to sub-agents sequentially, sharing TripState
   - Each failure retried once, then skipped (optional) or aborts (required)
3. `_synthesize()` — one Claude call → unified narrative trip summary

---

## Milestone Status

| Milestone | Status    | Description                                              |
|-----------|-----------|----------------------------------------------------------|
| M1        | ✅ Complete | FlightAgent, HotelAgent, ApprovalGate, AuditLogger, API  |
| M2        | ✅ Complete | OrchestratorAgent, TransportAgent, ActivityAgent, providers layer |
| M3        | 🔲 Planned | Parallel sub-task execution, typed ExtractedParams, real API providers, integration tests |

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

### Environment variables

```
ANTHROPIC_API_KEY=           # required
DATABASE_URL=                # defaults to sqlite+aiosqlite:///./travel_agent.db
USE_REAL_APIS=false          # mock mode (default)
APPROVAL_TIMEOUT_MINUTES=30
MAX_AGENT_ITERATIONS=10
LOG_LEVEL=INFO
```

---

## Key Invariants — Never Break These

1. `book_*` and `cancel_*` tools are **never** called without an approved
   `HumanApproval` DB record. Enforced two-layer: `ApprovalGate.check()` +
   `ApprovalGate.verify_approved()`.
2. Each agent gets a **scoped** `ToolRegistry` — agents never see tools
   outside their domain.
3. `log_booking()` is called after every successful `book_*` call. It persists
   the `Booking` row and atomically increments `Trip.total_spent`.
4. No real payment data. `payment_token` is always a dummy string in mock mode.
5. `_run_agent_task` never silently fails — top-level try/except marks
   the Trip as `"failed"`.
6. Audit logs are append-only — `ToolCall` and `Booking` rows are never updated.
