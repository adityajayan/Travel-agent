# Travel & Logistics Agentic Platform

Multi-agent travel booking system powered by Claude. Accepts natural language
travel goals, decomposes them into sub-tasks, runs specialist AI agents, requires
human approval before any booking, logs everything to a database, and enforces
corporate travel policies.

---

## Repository Layout

```
travel-agent/            ← repo root
├── README.md            ← you are here
├── agents/
│   ├── base_agent.py       ← policy pre-check (INV-7) + tool dispatch
│   ├── orchestrator_agent.py
│   ├── flight_agent.py
│   ├── hotel_agent.py
│   ├── transport_agent.py
│   ├── activity_agent.py
│   └── trip_state.py
├── core/
│   ├── policy_engine.py    ← M3: 9-rule evaluator + violation recorder
│   ├── approval_gate.py    ← two-layer booking guard + soft-violation context
│   ├── audit_logger.py     ← append-only ToolCall/Booking/Policy logs
│   └── config.py
├── db/
│   ├── models.py           ← Trip, HumanApproval, CorporatePolicy, PolicyRule, PolicyViolation
│   └── database.py
├── api/
│   ├── main.py
│   ├── schemas.py
│   └── routes/
│       ├── trips.py        ← includes policy resolution + policy-report endpoint
│       ├── policies.py     ← M3: CRUD for policies and rules
│       └── approvals.py
├── providers/
├── tools/
├── tests/
├── requirements.txt
└── pytest.ini
```

> **Note:** The repo always reflects the latest complete state — every milestone
> is applied on top of the previous one before pushing.

---

## Architecture

```
POST /trips  →  Agent runs async in background
  └─ _resolve_policy()  →  PolicyEngine.load_policy() (INV-9)
  └─ Agent selected by domain
       └─ BaseAgent._dispatch_tool()
            └─ PolicyEngine.evaluate()  →  HARD block returns POLICY_BLOCKED (INV-7)
                                         →  SOFT violations attached to HumanApproval
            └─ ApprovalGate.check()  →  HumanApproval row created
            └─ ApprovalGate.verify_approved()  →  second-layer check
            └─ Provider books  →  AuditLogger.log_booking()
POST /approvals/{id}/decide  →  Human approves/rejects
GET  /trips/{id}/policy-report  →  All PolicyViolation rows for audit
```

### Agent routing

| Goal domains detected       | Agent used          |
|-----------------------------|---------------------|
| 1 domain (flight only)      | FlightAgent         |
| 1 domain (hotel only)       | HotelAgent          |
| 1 domain (transport only)   | TransportAgent      |
| 1 domain (activity only)    | ActivityAgent       |
| 2+ domains                  | OrchestratorAgent   |

### OrchestratorAgent flow

1. `_decompose()` — one Claude call, no tools → structured TripPlan JSON
2. Fan-out to sub-agents sequentially, sharing TripState
   - Each failure retried once, then skipped (optional) or aborts (required)
3. `_synthesize()` — one Claude call → unified narrative trip summary

### Policy Engine (M3)

The `PolicyEngine` supports 9 rule keys:

| Rule Key                      | Applies To | Checks                                      |
|-------------------------------|------------|---------------------------------------------|
| `max_flight_cost`             | flight     | estimated_cost ≤ value.amount               |
| `allowed_cabin_classes`       | flight     | cabin_class in value.classes                |
| `require_advance_booking_days`| flight     | days_until_departure ≥ value.days           |
| `max_flight_duration_hours`   | flight     | duration_hours ≤ value.hours                |
| `max_hotel_cost_per_night`    | hotel      | cost_per_night ≤ value.amount               |
| `max_hotel_stay_total`        | hotel      | total_cost ≤ value.amount                   |
| `max_hotel_star_rating`       | hotel      | star_rating ≤ value.stars                   |
| `preferred_vendors_only`      | any        | vendor_id in value.vendors                  |
| `max_total_trip_spend`        | any        | trip_total_spent + new_cost ≤ value.amount  |

Rules with `severity=hard` block the booking before it reaches `ApprovalGate`.
Rules with `severity=soft` attach violation context to the `HumanApproval` record
for human review.

---

## Milestone Status

| Milestone | Status       | Description                                                       |
|-----------|--------------|-------------------------------------------------------------------|
| M1        | ✅ Complete  | FlightAgent, HotelAgent, ApprovalGate, AuditLogger, API           |
| M2        | ✅ Complete  | OrchestratorAgent, TransportAgent, ActivityAgent, providers layer |
| M3        | ✅ Complete  | Corporate Policy Engine, 9 rule keys, CRUD API, E2E tests         |

---

## API Reference

### Trips
| Method | Path                          | Description                                 |
|--------|-------------------------------|---------------------------------------------|
| POST   | `/trips`                      | Create trip (accepts `org_id`, `policy_id`) |
| GET    | `/trips/{id}`                 | Get trip status                             |
| GET    | `/trips`                      | List all trips                              |
| GET    | `/trips/{id}/policy-report`   | Audit report: all policy violations         |

### Approvals
| Method | Path                          | Description                   |
|--------|-------------------------------|-------------------------------|
| GET    | `/approvals/{id}`             | Get approval request          |
| GET    | `/approvals`                  | List approvals (by trip)      |
| POST   | `/approvals/{id}/decide`      | Approve or reject             |

### Policies (M3)
| Method | Path                                   | Description                           |
|--------|----------------------------------------|---------------------------------------|
| POST   | `/policies`                            | Create policy + rules (201)           |
| GET    | `/policies?org_id=`                    | List policies for an org              |
| GET    | `/policies/{id}`                       | Get policy                            |
| PATCH  | `/policies/{id}`                       | Update name / is_active (409 on dup)  |
| DELETE | `/policies/{id}`                       | Soft delete (sets is_active=False)    |
| PATCH  | `/policies/{id}/rules/{rule_id}`       | Toggle is_enabled, update value/sev   |

---

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Expected: **70+ tests, all passing**.

### Environment variables

```
ANTHROPIC_API_KEY=           # required for real API; set to any value for tests
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
7. **[M3] HARD policy violations never reach `ApprovalGate`** — `PolicyEngine.evaluate()`
   runs upstream of all booking tools; a hard block returns `POLICY_BLOCKED` immediately.
8. **[M3] `PolicyViolation` rows are append-only** — each state transition (blocked,
   flagged_pending, flagged_approved) writes a new row; existing rows are never updated.
9. **[M3] Policy loaded and validated before agent loop** — if an explicit `policy_id`
   is inactive or missing, `_run_agent_task` marks the Trip `"failed"` immediately.
