import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_checkpoint1_stock_priority():
    # 1. Create a disruption case
    case_payload = {
        "disruption_type": "SUPPLIER_DELAY",
        "description": "Supplier delayed shipment of microcontrollers",
        "supplier_id": "SUP-001",
        "material_id": "MAT-001",
        "plant_id": "PLANT-001",
        "expected_delay_days": 5,
        "affected_quantity": 500,
    }
    create_res = client.post("/api/v1/cases", json=case_payload)
    assert create_res.status_code == 201
    case_id = create_res.json()["case_id"]

    # 2. Run Impact Analysis
    analyze_res = client.post(f"/api/v1/cases/{case_id}/analyze")
    assert analyze_res.status_code == 200

    # 3. Checkpoint 1: Select STOCK priority
    cp_res = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": "STOCK"})
    assert cp_res.status_code == 200
    data = cp_res.json()
    assert data["priority"] == "STOCK"
    assert data["status"] == "CHECKPOINT_APPROVED"

    # 4. Generate recovery plans
    plan_res = client.post(f"/api/v1/cases/{case_id}/recovery/plan", json={"priority": "STOCK"})
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["priority"] == "STOCK"
    assert len(plan_data["feasible_plans"]) > 0

    # Top feasible plan should explain STOCK prioritization
    top_plan = plan_data["feasible_plans"][0]
    assert "inventory protection" in top_plan["score_breakdown"]["explanation"].lower()


def test_checkpoint1_customer_priority():
    # 1. Create a disruption case
    case_payload = {
        "disruption_type": "LOGISTICS_DELAY",
        "description": "Logistics carrier route delay affecting plant assembly",
        "supplier_id": "SUP-001",
        "material_id": "MAT-001",
        "plant_id": "PLANT-001",
        "expected_delay_days": 4,
        "affected_quantity": 400,
    }
    create_res = client.post("/api/v1/cases", json=case_payload)
    assert create_res.status_code == 201
    case_id = create_res.json()["case_id"]

    # 2. Run Impact Analysis
    analyze_res = client.post(f"/api/v1/cases/{case_id}/analyze")
    assert analyze_res.status_code == 200

    # 3. Checkpoint 1: Select CUSTOMER priority
    cp_res = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": "CUSTOMER"})
    assert cp_res.status_code == 200
    data = cp_res.json()
    assert data["priority"] == "CUSTOMER"
    assert data["status"] == "CHECKPOINT_APPROVED"

    # 4. Generate recovery plans
    plan_res = client.post(f"/api/v1/cases/{case_id}/recovery/plan", json={"priority": "CUSTOMER"})
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert plan_data["priority"] == "CUSTOMER"
    assert len(plan_data["feasible_plans"]) > 0

    # Top feasible plan should explain CUSTOMER prioritization
    top_plan = plan_data["feasible_plans"][0]
    assert "customer delivery commitments" in top_plan["score_breakdown"]["explanation"].lower()
