# INDUSTRIA-X

**Agentic AI for Predictive Maintenance and Sustainable Industrial Operations**

> Primary SDG: UN Sustainable Development Goal 9 — Industry, Innovation and Infrastructure

---

## ⚠️ Important Limitations

Before using this system, read these limitations carefully:

1. **Synthetic dataset** — The AI4I 2020 dataset is a synthetic research dataset created for ML benchmarking. It does NOT represent real factory telemetry.
2. **No real industrial validation** — INDUSTRIA-X has not been validated against real industrial equipment.
3. **Energy/CO₂e are estimates** — Sustainability figures are derived from kinematic formulas, not measured electrical consumption.
4. **Simulation is not live telemetry** — The "real-time monitoring" dashboard replays the AI4I dataset sequentially; it is not connected to any physical sensors.
5. **ML predictions are probabilistic decision support** — Model outputs are not guarantees. False positives and false negatives will occur.
6. **SHAP is attribution, not causation** — SHAP values show which features influenced the model's prediction, not which factors caused the failure.
7. **Human review required** — All maintenance recommendations require review by qualified personnel before action.
8. **Not a machine-control system** — INDUSTRIA-X cannot control industrial equipment. It is a decision-support tool only.
9. **LLM integration is optional** — The agent works without an LLM using deterministic rule-based orchestration. LLM integration requires IBM watsonx.ai or OpenAI credentials.
10. **Frontend build status** — The frontend build was not executed in the CI environment used for Phase 14 (Node.js unavailable). See [Frontend Build](#frontend-build) below.

---

## Overview

INDUSTRIA-X is an AI-powered industrial decision-support platform that integrates:

- **Predictive failure detection** — calibrated ML models (Random Forest, XGBoost, Logistic Regression)
- **Anomaly detection** — Isolation Forest on sensor readings
- **Risk scoring** — composite weighted risk engine (0–100 scale)
- **SHAP explainability** — per-prediction feature attribution
- **Maintenance RAG** — semantic retrieval from an embedded knowledge base
- **Agentic AI** — LangGraph-based orchestrator with tool routing and optional LLM reasoning
- **Maintenance prioritization** — ranked work-order prioritisation across machines
- **What-if analysis** — ML-based scenario comparison for operating condition changes
- **Sustainability estimation** — mechanical power, electrical power, and CO₂e estimates
- **Simulated monitoring** — step-by-step AI4I dataset replay with live ML assessment
- **Human decision support** — structured recommendations with evidence, never autonomous action

**Dataset:** [UCI AI4I 2020 Predictive Maintenance Dataset](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset) — synthetic, CC BY 4.0

---

## Architecture

```
                    INDUSTRIA-X
                         │
              ┌──────────┴──────────┐
              │                     │
        Machine Data            Knowledge Base
              │                     │
              ▼                     ▼
       Failure Prediction          RAG
              │               (ChromaDB +
       Anomaly Detection      sentence-transformers)
              │                     │
              └──────────┬──────────┘
                         ▼
                    Risk Engine
                         │
                         ▼
                  SHAP Explainability
                         │
                         ▼
                   Agentic AI
                   (LangGraph)
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
         Maintenance   What-if   Sustainability
         Priority     Analysis    Analytics
             │
             └───────────┬───────────┘
                         ▼
                  Human Decision
                   (review required)
                         │
                         ▼
                  Industrial Dashboard
                    (React + Recharts)
                         │
                         ▼
                 Simulation / Monitoring
              (AI4I dataset replay — not live)
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| ML / Data Science | Python 3.11, scikit-learn, XGBoost, SHAP, imbalanced-learn |
| Agentic Orchestration | LangGraph + LangChain |
| LLM | IBM watsonx.ai (granite-13b-instruct-v2) / OpenAI fallback / deterministic fallback |
| RAG / Vector Store | ChromaDB + sentence-transformers/all-MiniLM-L6-v2 |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL 15 + SQLAlchemy 2 + Alembic |
| Cache / Rate Limiting | Redis 7 |
| Frontend | React 18 + TypeScript + Vite + Recharts + Tailwind CSS + Zustand + React Query |
| Containers | Docker + Docker Compose |

---

## Dataset

**Name:** AI4I 2020 Predictive Maintenance Dataset  
**Source:** UCI Machine Learning Repository  
**URL:** https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset  
**Authors:** S. Matzka  
**Licence:** CC BY 4.0  
**Nature:** ⚠️ **Synthetic** dataset — NOT real factory telemetry  
**Records:** 10,000 rows × 14 columns  
**Failures:** 339 (3.39%) — severe class imbalance, ratio 28.5:1  
**Features:** 5 numerical + 1 categorical (6 model features)  
**File location:** `data/raw/ai4i2020.csv` (not committed — download separately)

---

## API Security

Protected write/compute endpoints require an `X-API-Key` header:

```
X-API-Key: <your-api-key>
```

**Protected endpoints:**

| Endpoint | Requires Key |
|---|---|
| `POST /api/v1/machines` | ✅ |
| `POST /api/v1/machines/{id}/assess` | ✅ |
| `POST /api/v1/agent/query` | ✅ |
| `POST /api/v1/whatif/analyze` | ✅ |
| `POST /api/v1/sustainability/estimate` | ✅ |
| `POST /api/v1/simulation/start` | ✅ |
| `POST /api/v1/simulation/pause` | ✅ |
| `POST /api/v1/simulation/reset` | ✅ |
| `POST /api/v1/simulation/step` | ✅ |
| `POST /api/v1/rag/ingest` | ✅ |

**Public (no key required):**

| Endpoint | Public |
|---|---|
| `GET /api/v1/health` | ✅ |
| `GET /api/v1/health/ready` | ✅ |
| `GET /api/v1/rag/status` | ✅ |
| `GET /api/v1/sustainability/insights` | ✅ |
| `GET /api/v1/simulation/status` | ✅ |
| `GET /api/v1/machines` | ✅ |
| `GET /api/v1/machines/{id}` | ✅ |

Configure the key via the `API_KEY` environment variable.

---

## Project Structure

```
industria-x/
├── data/               # Dataset storage (raw CSV not committed)
├── ml/                 # ML training scripts and saved artifacts
├── backend/            # FastAPI application
│   ├── api/            # Route handlers
│   ├── core/           # Config, DB, Redis, security, rate limiter, middleware
│   ├── models/         # SQLAlchemy ORM models
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic services
│   ├── agent/          # LangGraph agentic orchestration
│   └── migrations/     # Alembic database migrations
├── frontend/           # React + TypeScript dashboard (Vite)
├── rag/                # ChromaDB knowledge base ingestion and retrieval
├── knowledge_base/     # Source markdown documents for RAG
├── tests/              # Full test suite (518+ tests)
└── docs/               # Phase documentation
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- Docker + Docker Compose (for PostgreSQL and Redis)
- Git
- Node.js 18+ (for frontend development; optional for backend-only)

### 1. Clone and configure

```bash
git clone <repo-url>
cd industria-x
cp .env.example .env
# Edit .env — set API_KEY, database credentials, and optionally LLM credentials
```

### 2. Start infrastructure

```bash
docker-compose up -d postgres redis
```

### 3. Python environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Start the backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Backend API docs: http://localhost:8000/docs  
Health check: http://localhost:8000/api/v1/health

### 6. Start the frontend (optional)

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

### 7. Using the API key

For protected endpoints, include the header in your requests:

```bash
curl -X POST http://localhost:8000/api/v1/agent/query \
  -H "X-API-Key: your-api-key-from-env" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the risk for machine 1?"}'
```

---

## Running with Docker Compose (full stack)

```bash
# Build and start all services
docker-compose up --build

# Backend:  http://localhost:8000
# Frontend: http://localhost:80
# Docs:     http://localhost:8000/docs
```

The backend container runs `alembic upgrade head` automatically before starting Uvicorn.

---

## Frontend Build

> **Node.js was not available in the Phase 14 CI environment.**
>
> The frontend build (`npm run build`) and frontend tests (`npm run test`) were **not executed** in this environment and cannot be reported as passing.
>
> Static inspection confirms:
> - TypeScript configuration is correct (`tsconfig.json`, strict mode enabled)
> - `vite.config.ts` configures a dev proxy for `/api` → backend, build target is correct
> - All API type definitions are consistent with backend schemas
> - `VITE_API_KEY` is documented as a **development/demo-only mechanism** — it is bundled into the JavaScript bundle and is NOT suitable for production secrets
>
> To verify the frontend build in an environment with Node.js:
> ```bash
> cd frontend
> npm install
> npm run typecheck
> npm run test
> npm run build
> ```

---

## Backend Tests

```bash
pytest tests/ -v --cov=backend --cov-report=term-missing
```

518 tests verified passing in Phase 13. Phase 14 adds targeted API key enforcement tests.

---

## Development Commands

```bash
# Lint and format
ruff check .
black .

# Type checking
mypy backend/

# Run specific test module
pytest tests/phase14/ -v
```

---

## Implementation Phases

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Repository setup, tooling, pyproject.toml |
| 1 | ✅ Complete | Project foundation — config, backend shell, frontend shell |
| 2 | ✅ Complete | Data pipeline — AI4I 2020, validation, preprocessing, EDA |
| 3 | ✅ Complete | ML model training — XGBoost/RF/LR failure prediction, calibrated threshold |
| 4 | ✅ Complete | Anomaly detection (Isolation Forest) + unified risk engine |
| 5 | ✅ Complete | SHAP explainability — per-prediction and global feature importance |
| 6 | ✅ Complete | ChromaDB RAG — knowledge base ingestion and semantic retrieval |
| 7 | ✅ Complete | Agentic AI core — LangGraph orchestrator, 5-tool registry, agent API |
| 8 | ✅ Complete | PostgreSQL persistence, audit logging, request IDs, rate limiting |
| 9 | ✅ Complete | Professional React dashboard — 5-page UI with real-time data |
| 10 | ✅ Complete | Sustainability & Energy Intelligence — power/energy/CO₂e estimates |
| 11 | ✅ Complete | What-if analysis + maintenance prioritization |
| 12 | ✅ Complete | Simulated real-time monitoring — AI4I dataset replay with ML assessment |
| 13 | ✅ Complete | Evaluation, security & integration audit — 20/20 agent eval, 2 defects fixed |
| 14 | ✅ Complete | Production hardening — API key enforcement, deployment config, final docs |

---

## Safety Statement

- INDUSTRIA-X **cannot control industrial equipment**. It is a decision-support tool.
- All maintenance recommendations require **human approval** before being treated as actionable.
- Simulated sensor data is **clearly labelled** as simulated throughout the UI and API.
- AI-generated recommendations are **labelled as AI-generated** and include evidence citations.
- The system will **never fabricate sensor readings or machine history**.
- The agent will **refuse** requests for machine control, code execution, or knowledge-base modification.

---

## Licence

MIT — see `LICENSE` for details.
