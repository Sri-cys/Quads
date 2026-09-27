# Quads REST API Specification (v1)

Base URL: `http://localhost:8000/api/v1`  
Infrastructure URL: `http://localhost:8000/api`  
Interactive Swagger Docs: `http://localhost:8000/docs`

---

## Standard Error Format
All 4xx and 5xx responses consistently return:
```json
{
  "error": "MACHINE_READABLE_CODE",
  "message": "Human readable description of the error"
}
```

---

## 1. System Health
### `GET /api/health`
Unversioned infrastructure endpoint returning status of all subsystems.

**Response (200 OK):**
```json
{
  "status": "ONLINE",
  "backend": "ONLINE",
  "gemini": "CONFIGURED",
  "mock_repository": "ONLINE",
  "sap_integration": "MOCK_MODE",
  "hana_cloud": "NOT_CONNECTED_PHASE_1",
  "btp": "LOCAL_DEVELOPMENT_MODE",
  "timestamp": "2026-09-27T06:00:00Z",
  "cases_count": 8
}
```

---

## 2. Case Management
### `POST /api/v1/cases`
Creates a new disruption case. Initiates LangGraph Stage 1 (`ingestion_node` -> `case_creation_node`), then interrupts before triage.

**Request Body:**
```json
{
  "disruption_type": "SUPPLIER_DELAY",
  "description": "Supplier shipment delayed by 5 days.",
  "supplier_id": "SUP-001",
  "material_id": "MAT-001",
  "plant_id": "PLANT-001",
  "expected_delay_days": 5,
  "affected_quantity": 500
}
```

**Status Codes:**
- `201 Created`: Case successfully registered.
- `409 Conflict`: Duplicate open case exists for this supplier, material, plant, and disruption type within 5 minutes.
- `422 Unprocessable Entity`: Validation failure or invalid master data reference.

### `GET /api/v1/cases`
List disruption cases with pagination.

**Query Parameters:**
- `limit` (default: 25, max: 100)
- `offset` (default: 0)

**Response (200 OK):**
```json
{
  "total": 8,
  "limit": 25,
  "offset": 0,
  "items": [
    {
      "case_id": "CASE-0001",
      "disruption_type": "PACKAGING_BOTTLENECK",
      "description": "Supplier shipment delayed by 5 days due to packaging bottleneck.",
      "supplier_id": "SUP-001",
      "material_id": "MAT-001",
      "plant_id": "PLANT-001",
      "expected_delay_days": 5,
      "affected_quantity": 500,
      "detected_at": "2026-09-27T06:00:00Z",
      "status": "TRIAGED",
      "severity": null
    }
  ]
}
```

### `GET /api/v1/cases/{case_id}`
Retrieve a single case. Returns `404 Not Found` if the case ID does not exist.

---

## 3. Impact Analysis (Agent 1)
### `POST /api/v1/cases/{case_id}/analyze`
Resumes LangGraph Stage 2: executes `triage_node` -> `impact_analysis_node` -> `gemini_explanation_node`, and interrupts before `checkpoint1_node`.

**Status Codes:**
- `200 OK`: Analysis successfully executed and persisted.
- `404 Not Found`: Case does not exist.
- `409 Conflict`: Case is already approved at Checkpoint 1.
- `503 Service Unavailable`: Repository failure.

**Response (200 OK):**
```json
{
  "case_id": "CASE-0001",
  "severity": "CRITICAL",
  "available_inventory": 50.0,
  "reserved_quantity": 100.0,
  "total_inventory": 150.0,
  "daily_demand": 25.0,
  "demand_status": "AVAILABLE",
  "days_of_cover": 2.0,
  "stockout_date": "2026-09-29T06:00:00Z",
  "safety_stock_quantity": 100.0,
  "safety_stock_breach": true,
  "supply_gap_quantity": 0.0,
  "downstream_impact": {
    "affected_material_id": "MAT-001",
    "affected_material_name": "Semiconductor Microcontroller MCU-32",
    "affected_plant_id": "PLANT-001",
    "affected_plant_name": "Munich Manufacturing Hub",
    "affected_supplier_id": "SUP-001",
    "affected_supplier_name": "Global Chips Ltd",
    "affected_purchase_orders": ["PO-001"],
    "demand_exposure_units": 125.0,
    "inventory_exposure_units": 50.0,
    "financial_exposure": 5625.0,
    "production_risk_indicators": [
      "Immediate stockout hazard within 2.0 days",
      "Safety buffer depleted below mandatory operational threshold"
    ]
  },
  "calculated_at": "2026-09-27T06:05:00Z",
  "ai_explanation": "Executive summary of disruption...",
  "ai_status": "AVAILABLE"
}
```

### `GET /api/v1/cases/{case_id}/impact`
Fetch existing analysis results. Returns `404 Not Found` if analysis has not yet been executed.

---

## 4. Human Checkpoint 1
### `POST /api/v1/cases/{case_id}/checkpoint1`
Submits human prioritization decision. Resumes LangGraph Stage 3: executes `checkpoint1_node` and transitions to `END`.

**Request Body:**
```json
{
  "priority": "TIME"
}
```
*Valid values:* `TIME`, `COST`, `RISK`, `BALANCED`

**Status Codes:**
- `200 OK`: Decision persisted, workflow reaches Phase 1 stopping point.
- `404 Not Found`: Case does not exist.
- `409 Conflict`: Impact analysis has not been executed yet, or Checkpoint 1 was already approved.
- `422 Unprocessable Entity`: Invalid priority value.

**Response (200 OK):**
```json
{
  "case_id": "CASE-0001",
  "status": "CHECKPOINT_APPROVED",
  "priority": "TIME",
  "message": "Checkpoint 1 approved.",
  "phase2_status": "Recovery Planning is ready for Phase 2."
}
```

---

## 5. Audit Logging
### `GET /api/v1/cases/{case_id}/audit`
Retrieves chronological audit trail for a case.

**Response (200 OK):**
```json
[
  {
    "timestamp": "2026-09-27T06:00:00Z",
    "case_id": "CASE-0001",
    "event": "CASE_CREATED",
    "actor": "SYSTEM_WORKFLOW",
    "details": "Disruption case CASE-0001 registered and persisted"
  },
  {
    "timestamp": "2026-09-27T06:01:00Z",
    "case_id": "CASE-0001",
    "event": "CHECKPOINT_1_APPROVED",
    "actor": "SUPPLY_CHAIN_PLANNER",
    "details": "Human Checkpoint 1 approved with recovery priority: TIME. Phase 1 complete."
  }
]
```
