# Phase 8 — Backend Persistence & Observability

INDUSTRIA-X Phase 8 adds a production-ready persistence and observability
foundation to the existing FastAPI/ML/RAG/Agent backend.

---

## Overview

| Component | Description |
|-----------|-------------|
| **Database Models** | `Machine`, `MachineAssessment`, `AgentAuditLog` |
| **New APIs** | Machines (CRUD), Assessment (run + history) |
| **Migrations** | Alembic migration: `001_phase8_persistence` |
| **Audit Logging** | Every agent request recorded structurally |
| **Request IDs** | UUID per request, preserved or generated |
| **Rate Limiting** | Redis-backed, fails open gracefully |
| **Error Handling** | Clean API errors, no stack trace exposure |
| **Session Foundation** | Optional `session_id` on agent requests |

---

## Database Architecture

The existing SQLAlchemy + PostgreSQL infrastructure (Phase 1) is reused
without modification.  No second database system is introduced.

### Tables

#### `machines`

Stores machine identity and metadata.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | Auto-increment |
| `machine_identifier` | String(128) | Unique business identifier |
| `type` | String(64) | Optional machine type/category |
| `created_at` | DateTime TZ | Server-default `now()` |
| `updated_at` | DateTime TZ | Server-default `now()`, updated on change |

#### `machine_assessments`

Stores the persisted output of one ML pipeline run.
Values come exclusively from `ml.assessment.assess_machine()` — no duplication.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | Auto-increment |
| `machine_id` | Integer FK → `machines.id` | CASCADE DELETE |
| `failure_probability` | Float | From Phase 3 XGBoost model |
| `anomaly_score` | Float | From Phase 4 IsolationForest |
| `risk_score` | Float | Weighted composite (0.70 × failure + 0.30 × anomaly) |
| `risk_level` | String(32) | `NORMAL` / `WARNING` / `CRITICAL` |
| `model_version` | String(64) | Artifact version tag |
| `created_at` | DateTime TZ | Assessment timestamp |

#### `agent_audit_logs`

Immutable record of each agent request and its structured outcome.

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | Auto-increment |
| `request_id` | String(64) | Unique per request |
| `session_id` | String(64) | Optional session correlation |
| `query` | String(1000) | Sanitised user query |
| `machine_id` | String(128) | Optional machine identifier |
| `tools_used` | String(512) | Comma-separated tool names |
| `status` | String(32) | `success` / `error` / `partial` |
| `response_summary` | String(1000) | Short structured metadata (NOT chain-of-thought) |
| `latency_ms` | Integer | End-to-end latency |
| `created_at` | DateTime TZ | Request timestamp |

> **Privacy rule**: The audit log never stores API keys, passwords, secrets,
> chain-of-thought reasoning, or hidden LLM outputs.

---

## Migrations

Alembic is used for all schema changes.

### Running migrations

```bash
# From the project root
alembic upgrade head
```

### Migration file

`backend/migrations/versions/001_phase8_persistence.py`

Creates all three Phase 8 tables.  The migration is reproducible from a clean
database and includes a `downgrade()` function for rollback.

---

## New API Endpoints

### Machines

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/machines` | List all machines (paginated) |
| `GET` | `/api/v1/machines/{id}` | Get machine by integer ID |
| `POST` | `/api/v1/machines` | Register a new machine |

**POST /api/v1/machines request body:**

```json
{
  "machine_identifier": "MACHINE-001",
  "type": "CNC_LATHE"
}
```

- `machine_identifier`: 1–128 chars, alphanumeric + `-`, `_`, `.` only.
- `type`: optional, max 64 chars.
- Returns `201 Created` on success.
- Returns `409 Conflict` if the identifier already exists.

### Assessments

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/machines/{id}/assess` | Run + persist an assessment |
| `GET` | `/api/v1/machines/{id}/assessments` | List assessment history (newest first) |

**POST /api/v1/machines/{id}/assess request body:**

```json
{
  "air_temperature_k": 300.1,
  "process_temperature_k": 310.2,
  "rotational_speed_rpm": 1500.0,
  "torque_nm": 45.0,
  "tool_wear_min": 120.0,
  "type": "M"
}
```

The endpoint calls the existing `ml.assessment.assess_machine()` function —
no ML logic is duplicated.  The result is persisted to `machine_assessments`.

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404` | Machine not found |
| `422` | Validation error |
| `429` | Rate limit exceeded |
| `503` | ML artifact missing |
| `500` | Unexpected pipeline error |

### Agent (Phase 7 — extended)

The existing `POST /api/v1/agent/query` endpoint is unchanged except for:

- Optional `session_id` field (max 64 chars) for session correlation.
- Optional `machine_id` field (max 128 chars) for audit traceability.
- Every request is now logged to `agent_audit_logs`.
- `X-Request-ID` header returned on every response.
- Rate limiting applied (see below).

---

## Audit Logging

Every call to `POST /api/v1/agent/query` results in one `AgentAuditLog` record:

- `request_id` — unique identifier for the request.
- `query` — the user's sanitised query text.
- `status` — `success`, `error`, or `partial`.
- `tools_used` — comma-separated list of tool names (no argument values).
- `response_summary` — short structured metadata string (≤ 1000 chars).
- `latency_ms` — end-to-end latency in milliseconds.
- `session_id` — if provided by the caller.
- `machine_id` — if provided by the caller.

**What is NOT stored:**

- API keys or secrets.
- LLM chain-of-thought or hidden reasoning.
- Full response text.
- Internal filesystem paths.
- Personal information.

Audit log write failures are caught and logged as warnings — they never
interrupt the response path.

---

## Request ID System

Every API request is assigned a unique `X-Request-ID`:

1. If the client sends `X-Request-ID` header with a safe value (8–64 chars,
   alphanumeric + hyphens/underscores), it is preserved.
2. Otherwise a UUID4 is generated.
3. The ID is echoed back in the `X-Request-ID` response header.
4. The ID appears in all structured log lines for that request.

Structured access log format:

```
request_id=<id> method=<METHOD> path=<path> status=<HTTP_STATUS> latency_ms=<ms>
```

---

## Rate Limiting

Redis-backed sliding-window rate limiting protects two expensive endpoints:

| Endpoint | Default Limit | Window |
|----------|--------------|--------|
| `POST /api/v1/agent/query` | 30 req/min per IP | 60 s |
| `POST /api/v1/machines/{id}/assess` | 60 req/min per IP | 60 s |

**Configuration** (via `.env`):

```dotenv
RATE_LIMIT_AGENT_PER_MINUTE=30
RATE_LIMIT_ASSESS_PER_MINUTE=60
RATE_LIMIT_WINDOW_SECONDS=60
```

**Graceful degradation**: if Redis is unavailable, rate limiting is bypassed
and a warning is logged.  The application remains fully usable.

**429 response:**

```json
{"detail": "Rate limit exceeded. Maximum 30 requests per 60 seconds."}
```

With `Retry-After` header set to the window in seconds.

---

## Security

### Input validation

- All inputs validated with Pydantic before any DB or ML call.
- `machine_identifier` restricted to `[A-Za-z0-9_\-\.]{1,128}` — prevents
  path traversal and log injection.
- Query strings have `min_length=3`, `max_length=1000`.
- Pagination `limit` capped at 500 (machines) / 200 (assessments).

### SQL injection prevention

- All database access goes through SQLAlchemy ORM — no raw SQL queries.
- Foreign keys are integer primary keys — no string-based lookups for relations.

### Error handling

- Stack traces are never returned to API consumers.
- Internal filesystem paths are never exposed in error messages.
- The global exception handler catches unexpected errors and returns `500`
  with a generic message.

### Audit log injection prevention

- The audit service strips Unicode control characters (category `C`) from
  stored query text before writing.
- `tools_used` stores only tool names, never argument values.

### Agent safety

- Phase 7 safety rules are unchanged.
- Rate limiting is applied on top — it does not replace safety checks.
- `session_id` and `machine_id` fields are optional metadata; they do not
  affect orchestration logic.

---

## Configuration Reference

All new settings have safe defaults for local development.

```dotenv
# Rate limiting
RATE_LIMIT_AGENT_PER_MINUTE=30
RATE_LIMIT_ASSESS_PER_MINUTE=60
RATE_LIMIT_WINDOW_SECONDS=60
```

Existing settings are unchanged.

---

## Limitations

1. **Authentication**: the new machine/assessment endpoints have no
   authentication.  The existing `X-API-Key` pattern from Phase 1 is available
   but not applied globally.  Production deployments should add auth middleware.

2. **Rate limiting is per-IP**: suitable for development and light production
   load.  In a load-balanced multi-instance deployment, Redis-based limits are
   shared across instances, but per-IP limits may not be sufficient if all
   traffic arrives via a single proxy IP.

3. **Assessment history is unbounded** (except by `limit`): no automatic
   pruning or archiving is implemented.

4. **No agent session memory**: `session_id` is stored for correlation only.
   There is no multi-turn conversational memory in Phase 8.

5. **No dashboard**: the frontend dashboard is a Phase 9 concern.

---

## Recommended Phase 9

Based on the Phase 8 foundation, Phase 9 should implement:

1. **Dashboard API**: `/api/v1/dashboard/summary` returning fleet-level KPIs
   (machine counts, risk distribution, recent assessments).
2. **Alerts**: threshold-based alerts written to a new `alert` table when
   assessments exceed critical thresholds.
3. **Authentication middleware**: JWT or OAuth2 protecting the machine and
   assessment APIs.
4. **Assessment pruning**: background job to archive old assessments.
5. **Frontend wiring**: connect the React/Vite shell to the Phase 8 APIs.
6. **Agent session memory foundation**: store recent tool outputs per
   `session_id` for lightweight multi-turn context.
