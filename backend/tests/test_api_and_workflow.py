import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import reset_services, get_repository, get_case_service
from app.models.case import CaseCreateRequest
from app.models.disruption import Disruption
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock
from app.services.impact_service import ImpactService
from app.services.gemini_service import GeminiService
from app.agents.impact_agent import ImpactAgent


@pytest.fixture(autouse=True)
def setup_teardown(monkeypatch, tmp_path):
    test_db = tmp_path / "test_checkpoints.db"
    monkeypatch.setenv("DATABASE_PATH", str(test_db))
    reset_services()
    yield
    reset_services()


client = TestClient(app)


# Scenario 1: Normal Disruption Creation
def test_create_disruption_case():
    payload = {
        "disruption_type": "PORT_STRIKE",
        "description": "Dockworkers strike at regional logistics terminal.",
        "supplier_id": "SUP-001",
        "material_id": "MAT-001",
        "plant_id": "PLANT-001",
        "expected_delay_days": 4,
        "affected_quantity": 250,
    }
    response = client.post("/api/v1/cases", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"].startswith("CASE-")
    assert data["status"] == "CREATED"


# Scenario 2: Critical Disruption
def test_critical_disruption_analysis():
    # CASE-0001 has doc = 2.0 (<= 3.0) -> CRITICAL
    response = client.post("/api/v1/cases/CASE-0001/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "CRITICAL"
    assert data["days_of_cover"] == 2.0
    assert data["stockout_date"] is not None


# Scenario 3: High Disruption
def test_high_disruption_analysis():
    # CASE-0003 has doc = 5.0 (<= 7.0) -> HIGH
    response = client.post("/api/v1/cases/CASE-0003/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "HIGH"
    assert data["days_of_cover"] == 5.0
    assert data["safety_stock_breach"] is True


# Scenario 4: Medium Disruption
def test_medium_disruption_analysis():
    # CASE-0005 has doc = 10.0 (<= 14.0) -> MEDIUM
    response = client.post("/api/v1/cases/CASE-0005/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "MEDIUM"
    assert data["days_of_cover"] == 10.0


# Scenario 5: Low Disruption
def test_low_disruption_analysis():
    # CASE-0007 has doc = 30.0 (> 14.0) -> LOW
    response = client.post("/api/v1/cases/CASE-0007/analyze")
    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "LOW"
    assert data["days_of_cover"] == 30.0


# Scenario 6: Missing Inventory
def test_missing_inventory_handling():
    disruption = Disruption(
        disruption_type="CUSTOMS_HOLD",
        description="Missing inventory scenario",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        expected_delay_days=5,
    )
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=10.0)
    analysis = ImpactService.analyze(
        case_id="TEST-001",
        disruption=disruption,
        supplier=None,
        material=None,
        plant=None,
        inventory=None,  # Missing inventory
        demand=demand,
        safety_stock=None,
        purchase_orders=[],
    )
    assert analysis.available_inventory == 0.0
    assert analysis.days_of_cover == 0.0
    assert analysis.severity == "CRITICAL"


# Scenario 7: Missing Demand
def test_missing_demand_handling():
    disruption = Disruption(
        disruption_type="SUPPLIER_DELAY",
        description="Missing demand scenario",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        expected_delay_days=5,
    )
    inv = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0, reserved_quantity=0.0)
    analysis = ImpactService.analyze(
        case_id="TEST-002",
        disruption=disruption,
        supplier=None,
        material=None,
        plant=None,
        inventory=inv,
        demand=None,  # Missing demand
        safety_stock=None,
        purchase_orders=[],
    )
    assert analysis.days_of_cover is None
    assert analysis.demand_status == "DATA_UNAVAILABLE"
    assert analysis.stockout_date is None


# Scenario 8: Zero Demand
def test_zero_demand_handling():
    disruption = Disruption(
        disruption_type="SUPPLIER_DELAY",
        description="Zero demand scenario",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        expected_delay_days=5,
    )
    inv = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0, reserved_quantity=0.0)
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=0.0)
    analysis = ImpactService.analyze(
        case_id="TEST-003",
        disruption=disruption,
        supplier=None,
        material=None,
        plant=None,
        inventory=inv,
        demand=demand,  # Zero demand
        safety_stock=None,
        purchase_orders=[],
    )
    assert analysis.days_of_cover is None
    assert analysis.demand_status == "ZERO_DEMAND"
    assert analysis.stockout_date is None


# Scenario 9: Safety Stock Breach
def test_safety_stock_breach_detection():
    disruption = Disruption(
        disruption_type="DELAY",
        description="Safety stock breach scenario",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        expected_delay_days=5,
    )
    inv = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=80.0, reserved_quantity=0.0)
    ss = SafetyStock(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0)
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=8.0)
    analysis = ImpactService.analyze(
        case_id="TEST-004",
        disruption=disruption,
        supplier=None,
        material=None,
        plant=None,
        inventory=inv,
        demand=demand,
        safety_stock=ss,
        purchase_orders=[],
    )
    assert analysis.safety_stock_breach is True
    assert analysis.severity == "HIGH"


# Scenario 10: Supply Gap Calculation
def test_supply_gap_calculation():
    ss = SafetyStock(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0)
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=20.0)
    # Required = 100 + (20 * 5) = 200. Available = 40. Open PO = 0. Gap = 160.
    gap = ImpactService.calculate_supply_gap(
        available_inventory=40.0,
        safety_stock=ss,
        demand=demand,
        delay_days=5,
        purchase_orders=[],
    )
    assert gap == 160.0


# Scenario 11: Stockout Calculation
def test_stockout_calculation():
    doc = 4.5
    date_str = ImpactService.calculate_stockout_date(doc)
    assert date_str is not None
    assert "T" in date_str


# Scenario 12: Gemini Unavailable Handling
def test_gemini_unavailable():
    gemini_svc = GeminiService(api_key="")
    assert gemini_svc.is_configured is False
    agent = ImpactAgent(gemini_service=gemini_svc)
    disruption = Disruption(
        disruption_type="DELAY",
        description="Gemini unavailable test",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        expected_delay_days=5,
    )
    inv = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=10.0, reserved_quantity=0.0)
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=20.0)
    impact = agent.run(
        case_id="TEST-GEMINI",
        disruption=disruption,
        supplier=None,
        material=None,
        plant=None,
        inventory=inv,
        demand=demand,
        safety_stock=None,
        purchase_orders=[],
    )
    assert impact.ai_status == "UNAVAILABLE"
    assert impact.ai_explanation is None
    # Numerical calculation still succeeded and reflects inventory/demand
    assert impact.severity == "CRITICAL"
    assert impact.days_of_cover == 0.5


# Scenario 13: Gemini Failure Handling
def test_gemini_failure_handling(monkeypatch):
    gemini_svc = GeminiService(api_key="fake-dummy-key-for-test")
    
    class MockClient:
        class models:
            @staticmethod
            def generate_content(*args, **kwargs):
                raise Exception("Simulated Gemini API 500 error")

    monkeypatch.setattr(gemini_svc, "_client", MockClient())
    monkeypatch.setattr(gemini_svc, "_is_configured", True)

    disruption = Disruption(
        disruption_type="DELAY",
        description="Gemini failure test",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        expected_delay_days=5,
    )
    inv = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=10.0, reserved_quantity=0.0)
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=20.0)
    agent = ImpactAgent(gemini_service=gemini_svc)
    impact = agent.run(
        case_id="TEST-GEMINI-FAIL",
        disruption=disruption,
        supplier=None,
        material=None,
        plant=None,
        inventory=inv,
        demand=demand,
        safety_stock=None,
        purchase_orders=[],
    )
    assert impact.ai_status == "FAILED"
    assert impact.ai_explanation is None
    assert impact.severity == "CRITICAL"


# Scenario 14: Repository Failure / Error Handling
def test_repository_error_handling(monkeypatch):
    repo = get_repository()
    # Query non-existent case
    resp = client.get("/api/v1/cases/CASE-9999")
    assert resp.status_code == 404
    assert resp.json()["error"] == "CASE_NOT_FOUND"


# Scenario 15: Invalid Checkpoint (Out-of-order call returns 409)
def test_invalid_checkpoint_out_of_order():
    # Create new case without running analyze
    payload = {
        "disruption_type": "FLOOD",
        "description": "Factory flooded, awaiting review.",
        "supplier_id": "SUP-001",
        "material_id": "MAT-001",
        "plant_id": "PLANT-001",
        "expected_delay_days": 7,
    }
    create_resp = client.post("/api/v1/cases", json=payload)
    case_id = create_resp.json()["case_id"]

    # Calling checkpoint1 before analyze should return 409 Conflict
    cp_resp = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": "TIME"})
    assert cp_resp.status_code == 409
    assert cp_resp.json()["error"] == "ANALYSIS_REQUIRED"


# Scenario 16: Checkpoint Approval
def test_checkpoint_approval_all_priorities():
    priorities = ["TIME", "COST", "RISK", "BALANCED"]
    for idx, p in enumerate(priorities, start=1):
        case_id = f"CASE-000{idx}"
        # Analyze first
        an_resp = client.post(f"/api/v1/cases/{case_id}/analyze")
        assert an_resp.status_code == 200

        # Submit checkpoint
        cp_resp = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": p})
        assert cp_resp.status_code == 200
        data = cp_resp.json()
        assert data["priority"] == p
        assert data["message"] == "Checkpoint 1 approved."
        assert data["phase2_status"] == "Recovery Planning is ready for Phase 2."

        # Re-submitting same checkpoint returns 409
        cp_repeat = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": p})
        assert cp_repeat.status_code == 409
        assert cp_repeat.json()["error"] == "CHECKPOINT_ALREADY_APPROVED"


# Scenario 17: Audit Logging
def test_audit_logging():
    # Run a case through creation, analyze, and checkpoint
    payload = {
        "disruption_type": "PORT_CONGESTION",
        "description": "Port backlog audit test.",
        "supplier_id": "SUP-002",
        "material_id": "MAT-002",
        "plant_id": "PLANT-002",
        "expected_delay_days": 3,
    }
    c_resp = client.post("/api/v1/cases", json=payload)
    case_id = c_resp.json()["case_id"]

    client.post(f"/api/v1/cases/{case_id}/analyze")
    client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": "BALANCED"})

    # Check audit logs
    audit_resp = client.get(f"/api/v1/cases/{case_id}/audit")
    assert audit_resp.status_code == 200
    events = [item["event"] for item in audit_resp.json()]
    assert "DISRUPTION_RECEIVED" in events
    assert "CASE_CREATED" in events
    assert "TRIAGE_COMPLETED" in events
    assert "IMPACT_ANALYSIS_STARTED" in events
    assert "IMPACT_ANALYSIS_COMPLETED" in events
    assert "CHECKPOINT_1_APPROVED" in events


# Scenario 18: End-to-End Phase 1 Flow (§29)
def test_exact_end_to_end_phase1_flow():
    """
    Scenario from §29:
    Supplier: SUP-001
    Material: MAT-001
    Plant: PLANT-001
    Description: 'Supplier shipment delayed by 5 days.'
    Workflow:
    1. Create case
    2. Start LangGraph (ingestion + case creation)
    3. Run triage + Agent 1 (deterministic impact + Gemini)
    4. Verify Impact Analysis result
    5. Reach Checkpoint 1
    6. Select TIME
    7. Persist decision
    8. Create audit event
    9. Verify Checkpoint 1 approved message
    10. STOP (Agent 2 does not execute)
    """
    # Step 1 & 2: Ingest & Create Case
    payload = {
        "disruption_type": "SUPPLIER_DELAY",
        "description": "Supplier shipment delayed by 5 days.",
        "supplier_id": "SUP-001",
        "material_id": "MAT-001",
        "plant_id": "PLANT-001",
        "expected_delay_days": 5,
        "affected_quantity": 500,
    }
    create_res = client.post("/api/v1/cases", json=payload)
    assert create_res.status_code == 201
    case_data = create_res.json()
    case_id = case_data["case_id"]
    assert case_data["status"] == "CREATED"

    # Step 3 & 4: Analyze
    analyze_res = client.post(f"/api/v1/cases/{case_id}/analyze")
    assert analyze_res.status_code == 200
    impact_data = analyze_res.json()
    assert impact_data["case_id"] == case_id
    assert impact_data["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    assert impact_data["days_of_cover"] is not None

    # Verify impact can be fetched via GET /impact
    get_impact_res = client.get(f"/api/v1/cases/{case_id}/impact")
    assert get_impact_res.status_code == 200
    assert get_impact_res.json()["case_id"] == case_id

    # Step 5 & 6: Submit Checkpoint 1 with 'TIME'
    cp_res = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": "TIME"})
    assert cp_res.status_code == 200
    cp_data = cp_res.json()
    assert cp_data["priority"] == "TIME"
    assert cp_data["message"] == "Checkpoint 1 approved."
    assert cp_data["phase2_status"] == "Recovery Planning is ready for Phase 2."

    # Verify case state is in valid Checkpoint 1 states
    case_res = client.get(f"/api/v1/cases/{case_id}")
    assert case_res.status_code == 200
    assert case_res.json()["status"] in ("CHECKPOINT_APPROVED", "PRIORITY_SAVED", "AGENT2_RUNNING")
    assert case_res.json()["checkpoint1_decision"] == "TIME"


# Duplicate prevention test (409)
def test_duplicate_case_prevention():
    payload = {
        "disruption_type": "DUPLICATE_TEST_EVENT",
        "description": "First unique event.",
        "supplier_id": "SUP-003",
        "material_id": "MAT-003",
        "plant_id": "PLANT-001",
        "expected_delay_days": 3,
    }
    res1 = client.post("/api/v1/cases", json=payload)
    assert res1.status_code == 201

    # Second identical call should return 409
    res2 = client.post("/api/v1/cases", json=payload)
    assert res2.status_code == 409
    assert res2.json()["error"] == "DUPLICATE_CASE"


# Health Check Test
def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ONLINE"
    assert data["backend"] == "ONLINE"
    assert data["mock_repository"] == "ONLINE"
    assert data["sap_integration"] == "MOCK_MODE"
    assert data["hana_cloud"] == "NOT_CONNECTED_PHASE_1"
    assert data["btp"] == "LOCAL_DEVELOPMENT_MODE"


# Scenario 19: Checkpointer Persistence Across Backend Restart (§10.1 & §37)
def test_checkpointer_persistence_across_backend_restart():
    payload = {
        "disruption_type": "POWER_OUTAGE",
        "description": "Grid power loss at assembly node.",
        "supplier_id": "SUP-005",
        "material_id": "MAT-005",
        "plant_id": "PLANT-002",
        "expected_delay_days": 4,
    }
    create_res = client.post("/api/v1/cases", json=payload)
    assert create_res.status_code == 201
    case_id = create_res.json()["case_id"]

    # Step 2: Analyze
    an_res = client.post(f"/api/v1/cases/{case_id}/analyze")
    assert an_res.status_code == 200

    # Simulate backend crash / restart: reset in-memory singletons
    # but DO NOT delete the SQLite db file!
    reset_services()

    # Step 3: Call checkpoint1 after restart
    cp_res = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": "BALANCED"})
    assert cp_res.status_code == 200
    assert cp_res.json()["message"] == "Checkpoint 1 approved."
    assert cp_res.json()["priority"] == "BALANCED"

    # Confirm case was updated
    case_res = client.get(f"/api/v1/cases/{case_id}")
    assert case_res.status_code == 200
    assert case_res.json()["status"] in ("CHECKPOINT_APPROVED", "PRIORITY_SAVED", "AGENT2_RUNNING")
    assert case_res.json()["checkpoint1_decision"] == "BALANCED"
