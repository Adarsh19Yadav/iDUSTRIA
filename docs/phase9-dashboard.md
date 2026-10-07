# Phase 9 — Professional Industrial AI Dashboard

## Overview

Phase 9 transforms the INDUSTRIA-X frontend shell (Phase 1) into a fully functional professional
predictive maintenance dashboard. All data is sourced from the real Phase 7/8 backend APIs. No fake
or hardcoded statistics are used in the production UI.

---

## Routes Implemented

| Route | Page | Description |
|-------|------|-------------|
| `/` | Redirect → `/dashboard` | |
| `/dashboard` | Executive Overview | KPIs, risk distribution, recent assessments, attention-required |
| `/machines` | Machine Monitoring | Searchable/filterable/sortable machine table |
| `/machines/:id` | Machine Details | Identity, risk, history, RAG guidance, assess action |
| `/maintenance` | Maintenance Center | Machines grouped by risk priority |
| `/ai` | AI Operations Center | Natural-language queries to the agentic AI |
| `/sustainability` | Coming Soon | Phase 10 placeholder |
| `/whatif` | Coming Soon | Phase 11 placeholder |
| `/settings` | Coming Soon | Future placeholder |

---

## Dashboard Architecture

### Component Structure

```
src/
├── api/
│   ├── client.ts        — Shared Axios instance (baseURL, interceptors)
│   ├── machines.ts      — machinesApi (list, get, create, assess, listAssessments)
│   └── agent.ts         — agentApi, ragApi
├── components/
│   ├── AssessmentForm.tsx       — Six-input sensor form with SYNTHETIC data warning
│   ├── EmptyState.tsx           — Empty state with optional action
│   ├── ErrorMessage.tsx         — Error with optional retry; InlineError variant
│   ├── KpiCard.tsx              — KPI metric card with variant colours
│   ├── LoadingSpinner.tsx       — Spinner + SkeletonCard
│   ├── PageHeader.tsx           — Title, subtitle, badge, actions
│   ├── RegisterMachineModal.tsx — Machine registration modal
│   └── RiskBadge.tsx            — Accessible NORMAL/WARNING/CRITICAL badge
├── pages/
│   ├── AIOperationsPage.tsx     — Agent query UI
│   ├── ComingSoonPage.tsx       — Placeholder for future phases
│   ├── DashboardPage.tsx        — Executive overview
│   ├── MachineDetailPage.tsx    — Per-machine detail
│   ├── MachinesPage.tsx         — Machine monitoring table
│   ├── MaintenancePage.tsx      — Maintenance priority view
│   ├── NotFoundPage.tsx         — 404
│   └── OverviewPage.tsx         — Legacy Phase 1 health check (preserved)
├── types/
│   ├── health.ts    — HealthStatus, ReadinessStatus
│   ├── machines.ts  — Machine, Assessment, AssessmentRequest, MachineCreate
│   └── agent.ts     — AgentQuery, AgentResponse, RAGSource, ToolEvidence
└── utils/
    └── risk.ts      — Risk level utilities (colors, labels, sorting, formatting)
```

---

## API Dependencies

### Machine & Assessment APIs
- `GET  /api/v1/machines`                         — List machines
- `GET  /api/v1/machines/{id}`                    — Get machine by ID
- `POST /api/v1/machines`                         — Register machine
- `POST /api/v1/machines/{id}/assess`             — Run assessment
- `GET  /api/v1/machines/{id}/assessments`        — Assessment history

### Agent API
- `POST /api/v1/agent/query`                      — Natural-language agentic query

### RAG API
- `POST /api/v1/rag/query`                        — Retrieve maintenance guidance
- `GET  /api/v1/rag/status`                       — Knowledge base readiness

### Health APIs (preserved from Phase 1)
- `GET  /api/v1/health`
- `GET  /api/v1/health/ready`

---

## UI Data Flow

```
User opens /dashboard
  → machinesApi.list()                   — All machines
  → fetchLatestForMachines()             — Latest assessment per machine (parallel)
  → KPI cards, risk distribution chart, attention list, recent assessments table

User opens /machines/:id
  → machinesApi.get(id)                  — Machine identity
  → machinesApi.listAssessments(id)      — History (newest first)
  → [button] Assess Machine              — Opens AssessmentForm
    → machinesApi.assess(id, sensorData) — POST /assess → result shown, cache invalidated
  → [button] Get Guidance                — ragApi.query(question)
    → Results rendered with source, relevance score, content excerpt

User opens /ai
  → machinesApi.list()                   — Machine selector
  → [submit] agentApi.query(body)        — POST /agent/query
    → Answer, tools_used, evidence, sources rendered
    → Chain-of-thought NOT shown
    → Internal errors NOT exposed

User opens /maintenance
  → machinesApi.list() + listAssessments — All machines with latest assessments
  → Grouped by CRITICAL / WARNING / NORMAL / Unassessed
  → "Recommended for maintenance review" wording (not "will fail")
```

---

## Synthetic Data Labeling

All pages that may show data derived from the UCI AI4I 2020 dataset include:
- A `SYNTHETIC DATASET` badge in the page header
- Safety disclaimers explaining the data source
- The AssessmentForm includes an explicit `SIMULATED / SYNTHETIC DEMO DATA` notice
- AI responses include a "decision-support only" notice

The synthetic data warning is **never hidden** and is visible before any data is shown.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + TypeScript |
| Build | Vite 5 |
| Routing | React Router v6 |
| Data Fetching | TanStack Query v5 (React Query) |
| HTTP Client | Axios |
| Styling | Tailwind CSS v3 |
| Charts | Recharts |
| Icons | Lucide React |
| Notifications | React Hot Toast |
| Testing | Vitest + Testing Library |

---

## Error and Empty States

Every API-driven page implements:

| State | Behaviour |
|-------|-----------|
| Loading | `<LoadingSpinner>` with descriptive message |
| Empty (no machines) | `<EmptyState>` with CTA to register machine |
| API unavailable | `<ErrorMessage>` with Retry button |
| 404 machine | Specific "Machine not found" message |
| Assessment failure | Toast error + form retry |
| RAG unavailable | Warning banner; no fabricated guidance |
| Agent failure | Clean error; no stack trace exposed |

---

## Accessibility

- All interactive elements have `aria-label`, `aria-pressed`, `aria-expanded`, or `aria-sort` as appropriate
- Loading states use `role="status"` with `aria-live="polite"`
- Error states use `role="alert"` with `aria-live="assertive"`
- Tables use `aria-label` and `aria-sort` on sortable headers
- Risk status uses both colour AND text labels (never colour-only)
- Form inputs have associated `<label>` elements with `htmlFor`
- Keyboard navigation: tables support Enter key for row navigation

---

## Security

- No secrets, API keys, or credentials in frontend code
- API key read from `VITE_API_KEY` environment variable (not hard-coded)
- Machine identifiers validated client-side before submission (pattern validation)
- Agent responses displayed as text — no `dangerouslySetInnerHTML`
- Internal stack traces never displayed to users
- Query input is length-limited (1000 chars) before submission

---

## Known Limitations

1. **No authentication** — Phase 9 does not add auth (per spec). All endpoints are open.
2. **No real-time streaming** — Assessment results polled; no WebSocket streaming.
3. **No SHAP visualisation** — SHAP explanation data is not currently returned by the assessments API. The RAG guidance is used as a proxy for maintenance rationale.
4. **Sensor data is manual** — The UI requires manual sensor input. No live sensor feed in Phase 9.
5. **Rate limiting** — The backend rate-limits assessments. The UI shows a toast on 429.
6. **Machine type field** — Optional; shows "Unknown type" when not set.
7. **Assessment history chart** — Limited to last 20 assessments for performance.

---

## Frontend Test Coverage

Tests are located in `frontend/src/test/` and cover:

- `utils/risk.test.ts` — All risk utility functions
- `components/RiskBadge.test.tsx`
- `components/KpiCard.test.tsx`
- `components/EmptyState.test.tsx`
- `components/LoadingSpinner.test.tsx`
- `components/ErrorMessage.test.tsx`
- `pages/ComingSoonPage.test.tsx`
- `pages/DashboardPage.test.tsx` — KPI calculation, empty state, API error, with-data
- `pages/MachinesPage.test.tsx` — List, filtering, search, empty state, error
- `pages/MachineDetailPage.test.tsx` — Machine render, history, risk, missing data, 404
- `pages/AIOperationsPage.test.tsx` — Query submission, tools, evidence, sources, error
- `pages/MaintenancePage.test.tsx` — Risk grouping, correct wording, no fabricated claims
- `pages/Navigation.test.tsx` — All routes render correct components
