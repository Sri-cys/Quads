# Quads Architecture Specification (Phase 1)
**Control Tower for Supply Chain Disruption Detection & Impact Analysis**  
*Team QuadS | PSGITECH220 | SAP Hackfest 2026*

---

## 1. Overview & Architectural Principles

QUADS is designed as an enterprise-grade, SAP-oriented, agentic supply chain disruption control tower. Phase 1 establishes the complete foundation for disruption ingestion, triage, deterministic impact calculation, and executive explanation, terminating at **Human Checkpoint 1**.

The system strictly adheres to a **Mock-First Architecture**:
- Zero hard dependencies on SAP BTP, SAP HANA Cloud, or live SAP cloud tenants during local development.
- Clean repository and adapter abstractions ensuring production SAP systems plug directly into defined interfaces in subsequent phases.
- Zero direct coupling between the frontend and external AI or ERP services:
  - Frontend **never** calls SAP APIs directly.
  - Frontend **never** calls Gemini directly.
  - Agents **never** contain hardcoded endpoints or credentials.

---

## 2. Phase 1 Layered Architecture

```
+-------------------------------------------------------------+
|                SAPUI5 Frontend (SAP Fiori)                 |
|             com.quads.supplychain (Port 8080)              |
+-------------------------------------------------------------+
                              |
                     REST (CORS Whitelisted)
                              v
+-------------------------------------------------------------+
|                  FastAPI Backend (Port 8000)                |
|  /api/v1/cases | /api/v1/analyze | /api/v1/checkpoint1     |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                        Service Layer                        |
|   CaseService   |   ImpactService   |   AuditService        |
+-------------------------------------------------------------+
          |                   |                     |
          v                   v                     v
+------------------+ +------------------+ +-------------------+
|  LangGraph Core  | |  GeminiService   | |  BaseRepository   |
| 6-Node Workflow  | | (Explanation Only| | (Data Abstraction)|
+------------------+ +------------------+ +-------------------+
          |                                         |
          v                                         v
+---------------------+                   +-------------------+
| SqliteSaver Checkpt |                   |  MockRepository   |
| quads_checkpoints.db|                   |  data/mock/*.json |
+---------------------+                   +-------------------+
```

---

## 3. LangGraph Workflow Across Three REST Calls (§10.1)

A core requirement of Quads is reconciling a continuous LangGraph `StateGraph` with three sequential, user-driven REST interactions:

1. `POST /api/v1/cases`
2. `POST /api/v1/cases/{case_id}/analyze`
3. `POST /api/v1/cases/{case_id}/checkpoint1`

### Graph Topology & Nodes
```
START
  |
[ingestion_node]
  |
[case_creation_node]
  | (INTERRUPT 1: interrupt_before=["triage_node"])
[triage_node]
  |
[impact_analysis_node] (Deterministic Agent 1 calculations)
  |
[gemini_explanation_node] (Executive narrative generation)
  | (INTERRUPT 2: interrupt_before=["checkpoint1_node"])
[checkpoint1_node] (Human priority approval: TIME/COST/RISK/BALANCED)
  |
 END (Phase 1 Final Stopping Point)
```

### Checkpoint Persistence Mechanism
- **Thread ID Mapping:** Each case is tracked using `thread_id = case_id`.
- **Persistent Storage:** The graph checkpointer is backed by SQLite (`SqliteSaver` pointing to `quads_checkpoints.db`). If the backend server restarts between `/analyze` and `/checkpoint1`, the thread state, variables, and progress are fully preserved and recoverable.
- **Out-of-Order Call Prevention:** Calling `/checkpoint1` before analysis has completed, or calling `/analyze` on an already approved case, returns an explicit `409 Conflict`.

---

## 4. Separation of Deterministic Math vs Generative AI

To ensure operational accuracy and eliminate hallucinations:
- **Numerical Calculations:** All quantitative metrics (Available Inventory, Days of Cover, Stockout Date, Safety Stock Breach, Supply Gap) are computed in Python via `ImpactService`.
- **Configurable Severity Rules:** Thresholds are centrally declared in `app/config/severity_rules.py` as named constants:
  - `CRITICAL`: Days of Cover &le; 3.0 OR (Supply Gap &gt; 0 and Available Inventory &le; 0).
  - `HIGH`: Safety Stock Breach == True OR Days of Cover &le; 7.0.
  - `MEDIUM`: Days of Cover &le; 14.0 OR Supply Gap &gt; 0.
  - `LOW`: Baseline buffer nominal.
- **Gemini Responsibility:** Gemini receives the structured calculations as read-only inputs and produces executive summaries and operational context. It cannot alter or fabricate numbers.
- **Graceful Fallback:** If `GEMINI_API_KEY` is omitted or Gemini encounters a timeout/rate-limit, the system automatically falls back to an `UNAVAILABLE` status. Deterministic calculations and Checkpoint 1 proceed uninterrupted.

---

## 5. Future SAP Integration Architecture

When deploying to SAP BTP in subsequent phases:

```
[SAPUI5 Frontend]
       |
[SAP BTP Cloud Foundry / Kyma Runtime]
       |
[Application Services (FastAPI / CAP / Node.js)]
  |-- SAP BTP Destination Service
  |-- SAP XSUAA (Authorization and Trust Management)
       |
  +----+------------------------+------------------------+
  |                             |                        |
  v                             v                        v
[SAP HANA Cloud]         [SAP S/4HANA / IBP]       [SAP TM / Ariba]
(HDI Containers via       (OData / REST APIs       (Logistics & Network
HANACloudRepository)      via RealSAPAdapter)       Collaboration)
```
