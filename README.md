# QUADS: Agentic Supply Chain Control Tower
**Disruption Detection, Impact Analysis & Recovery Orchestration**  
*Team: QuadS | PSGITECH220 | SAP Hackfest 2026*  
*Phase 1 Implementation*

---

## 1. Project Overview
**QUADS** is an enterprise-grade, SAP-oriented, agentic supply chain control tower designed to autonomously detect disruptions, quantify multi-echelon business impact, and coordinate governed recovery plans.

This repository implements **PHASE 1**:
- Ingestion of supply chain disruption signals.
- Disruption Case registration and automated triage.
- **Agent 1 (Impact Analysis)** executing pure deterministic calculations for Days of Cover, Stockout Dates, Safety Stock Breaches, and Supply Gaps.
- Executive briefing generation via Google Gemini, grounded strictly in calculated metrics.
- **Human Checkpoint 1**: Mandatory governance decision point where supply chain planners select recovery trade-off priorities (`TIME`, `COST`, `RISK`, or `BALANCED`).
- **Explicit Phase 1 Stopping Boundary**: Autonomous execution ceases at Checkpoint 1; Agent 2 (Recovery Planning) and Agent 3 (Execution) are strictly reserved for subsequent phases.

---

## 2. Architecture
QUADS uses a **Mock-First Layered Architecture** ready for enterprise SAP BTP deployment:

```
[ SAPUI5 Frontend ] (SAP Fiori, Port 8080)
         |
    REST / CORS
         v
[ FastAPI Backend ] (Port 8000)
         |
  Service Layer (CaseService, ImpactService, AuditService)
         |
    +----+---------------------------+
    |                                |
    v                                v
[ LangGraph StateGraph ]      [ GeminiService ] (Explanation Only)
(6 Nodes, SQLite Checkpoint)         |
    |                                v
    v                     [ BaseRepository Interface ]
[ quads_checkpoints.db ]             |
                                     v
                           [ MockRepository ]
                           (data/mock/*.json)
```

---

## 3. Technology Stack
- **Frontend:** SAPUI5 (v1.120), SAP Fiori design principles (Horizon theme), UI5 Tooling (`@ui5/cli`).
- **Backend:** Python 3.11+ / 3.14, FastAPI, Pydantic v2, Uvicorn.
- **Orchestration:** LangGraph, StateGraph, SQLite Checkpointer (`SqliteSaver`).
- **AI Integration:** Google Gemini (`google-genai`), backend-only, resilient with retries and graceful offline degradation.
- **Persistence (Phase 1):** Local structured mock JSON data with thread-safe `BaseRepository` abstraction.
- **Persistence (Future):** SAP HANA Cloud (`HANACloudRepository`).
- **Testing:** `pytest`, `pytest-asyncio`, `httpx` TestClient, `coverage.py` (100% coverage on core calculation engine).

---

## 4. Prerequisites
- **Node.js:** v18+ or v20+ (`node -v`, `npm -v`)
- **Python:** v3.11+ (`python3 --version`)
- **UI5 Tooling:** `@ui5/cli` (installed locally in `frontend/node_modules`)
- Modern web browser (Chrome, Edge, Firefox, Safari)

---

## 5. Installation

### Clone repository:
```bash
git clone <repo_url> quads
cd quads
```

### Backend Virtual Environment:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend Dependencies:
```bash
cd ../frontend
npm install
```

---

## 6. Environment Configuration
Create `backend/.env` from the provided template:
```bash
cp backend/.env.example backend/.env
```

Contents of `backend/.env`:
```ini
# Optional: Provide Gemini API Key for executive narrative explanations
# If empty, deterministic impact calculations will still execute 100% nominally.
GEMINI_API_KEY=

# Local CORS Whitelist
CORS_ALLOWED_ORIGINS=http://localhost:8080

# Environment Mode
APP_ENV=development
DATA_DIR=../data/mock
```
> **Security Note:** `GEMINI_API_KEY` is never printed, logged, or transmitted to the frontend.

---

## 7. Running the Application (Single Integrated URL)
QUADS Phase 1 runs as **one integrated application** served directly from FastAPI:

### Step 1: Build the SAPUI5 Frontend
```bash
cd frontend
npm run build
```

### Step 2: Start the Integrated Application Server
```bash
cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Application URLs:
- **Integrated Quads Control Tower Web App:** `http://localhost:8000/`
- **Interactive Swagger Documentation:** `http://localhost:8000/docs`
- **Health Check & Telemetry:** `http://localhost:8000/api/health`

---

## 8. Standalone Frontend Development (Optional)
If you wish to run the standalone UI5 development server with live reloads during frontend design:
```bash
cd frontend
npm start
```
- Standalone UI5 Dev Server: `http://localhost:8080/index.html`
*(Note: The primary demo and integrated run mode is `http://localhost:8000/`)*

---

## 9. API Documentation Summary
Full API specification available in [docs/api.md](file:///Users/srisaran/Quads/docs/api.md):
- `GET /api/health` — Infrastructure health and status
- `POST /api/v1/cases` — Ingest disruption and register case (201 Created, 409 Conflict on duplicate)
- `GET /api/v1/cases` — Paginated case list (`?limit=25&offset=0`)
- `GET /api/v1/cases/{case_id}` — Case details
- `POST /api/v1/cases/{case_id}/analyze` — Run Agent 1 deterministic impact + AI explanation
- `GET /api/v1/cases/{case_id}/impact` — Retrieve impact assessment
- `POST /api/v1/cases/{case_id}/checkpoint1` — Submit Human Checkpoint 1 priority (`TIME`, `COST`, `RISK`, `BALANCED`)
- `GET /api/v1/cases/{case_id}/audit` — Immutable audit history

---

## 10. Phase 1 Workflow
```
DISRUPTION -> INGESTION -> CASE CREATION -> TRIAGE -> AGENT 1 (IMPACT ANALYSIS) ->
DETERMINISTIC BUSINESS CALCULATIONS -> GEMINI EXPLANATION ->
HUMAN CHECKPOINT 1 [ TIME / COST / RISK / BALANCED ] -> STOP
```

---

## 11. Gemini AI Configuration & Resilience
- **Strict Role:** Gemini acts as an executive communication analyst. It explains results without inventing numbers.
- **Timeout & Retry:** Gemini calls timeout after 10 seconds and retry once with exponential backoff.
- **Graceful Degradation:** If Gemini is unconfigured or unavailable, the Impact view displays:
  > *"AI explanation currently unavailable. Deterministic impact analysis is still available."*

---

## 12. Mock Data Architecture
Mock data is stored in `data/mock/` with interconnected entities:
- `suppliers.json` (SUP-001 through SUP-006)
- `materials.json` (MAT-001 through MAT-008)
- `plants.json` (PLANT-001 through PLANT-003)
- `inventory.json` (Physical stock & reserved quantities)
- `demand.json` (Daily consumption rates)
- `safety_stock.json` (Buffer thresholds)
- `purchase_orders.json` (In-flight purchase orders)
- `cases.json` (8 pre-seeded cases covering CRITICAL, HIGH, MEDIUM, and LOW tiers)

---

## 13. Automated Testing
Run automated unit, integration, and coverage tests:
```bash
cd backend
source .venv/bin/activate
pytest --cov=app.services.impact_service --cov=app.agents.impact_agent --cov-report=term-missing
```
**Coverage:** 100% coverage on Agent 1 and ImpactService. All 33 test scenarios pass, including duplicate protection, out-of-order 409 handling, and checkpointer persistence across backend restarts.

---

## 14. SAP BTP Future Integration
Read [docs/future-sap-integration.md](file:///Users/srisaran/Quads/docs/future-sap-integration.md) for details on BTP Kyma deployment, XSUAA security, and Cloud Connector configurations.

---

## 15. SAP HANA Cloud Future Integration
The `HANACloudRepository` abstraction is prepared for SAP HANA HDI containers and in-memory tables.

---

## 16. Phase 2 Roadmap
- **Agent 2:** Autonomous Recovery Planning & Multi-Criteria Optimization.
- Candidate recovery generation (air freight, alternate sourcing, plant reallocation).
- Real-time transport validation via SAP TM.
- Multi-criteria scoring aligned to Checkpoint 1 priority decision.
- **Human Checkpoint 2:** Recovery plan selection and executive sign-off.

---

## 17. Phase 3 Roadmap
- **Agent 3:** Execution, Monitoring & Learning.
- Automated ERP modifications (SAP S/4HANA Purchase Order updates).
- Real-time telematics tracking and dynamic re-routing.
- Outcome reconciliation and reinforcement learning policy updates.
