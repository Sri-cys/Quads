import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import reset_services, get_repository, get_case_service
from app.models.recovery import (
    RecoveryPlanSet,
    ManagerConstraints,
    PlanModifyRequest,
    Checkpoint2Request,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_teardown(monkeypatch, tmp_path):
    test_db = tmp_path / "test_checkpoints_p2.db"
    monkeypatch.setenv("DATABASE_PATH", str(test_db))
    # Disable real external Gemini API calls in unit tests for speed and determinism
    monkeypatch.setenv("GEMINI_API_KEY", "")
    reset_services()
    yield
    reset_services()


def _ensure_case_at_checkpoint1(case_id: str = "CASE-0001", priority: str = "TIME"):
    """Helper to take a case through Phase 1: create/triage -> analyze -> submit checkpoint 1."""
    # Analyze
    an_res = client.post(f"/api/v1/cases/{case_id}/analyze")
    assert an_res.status_code in {200, 409}

    # Submit Checkpoint 1
    cp1_res = client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": priority})
    assert cp1_res.status_code in {200, 409}

    case_res = client.get(f"/api/v1/cases/{case_id}")
    assert case_res.status_code == 200
    case_data = case_res.json()
    assert case_data["checkpoint1_decision"] == priority
    return case_data


# 1. Test Recovery Discovery and Generation
def test_recovery_discovery_and_generation():
    _ensure_case_at_checkpoint1("CASE-0001", "TIME")

    res = client.post("/api/v1/cases/CASE-0001/recovery/plan")
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == "CASE-0001"
    assert data["priority"] == "TIME"
    assert len(data["feasible_plans"]) >= 2
    assert len(data["infeasible_plans"]) >= 1

    # Feasible plans must contain essential recovery strategies
    strategies = {p["strategy"] for p in data["feasible_plans"]}
    assert "ALTERNATE_SUPPLIER" in strategies
    assert "SPLIT_SOURCING" in strategies or "INTER_PLANT_TRANSFER" in strategies

    # Check that feasible plans have valid numbers
    for p in data["feasible_plans"]:
        assert p["feasibility_status"] == "FEASIBLE"
        assert p["score"] > 0.0
        assert p["recovery_days"] > 0
        assert p["total_cost"] > 0.0
        assert p["score_breakdown"] is not None
        assert p["score_breakdown"]["explanation"] != ""

    # Verify that infeasible plans have explicit failure reasons
    for p in data["infeasible_plans"]:
        assert p["feasibility_status"] == "INFEASIBLE"
        assert p["infeasibility_reason"] is not None
        assert len(p["infeasibility_reason"]) > 5


# 2. Test Plant C Safety Stock Rejection (Hard Requirement)
def test_interplant_safety_stock_hard_constraint():
    _ensure_case_at_checkpoint1("CASE-0001", "BALANCED")

    res = client.post("/api/v1/cases/CASE-0001/recovery/plan")
    assert res.status_code == 200
    data = res.json()

    # Find the Curitiba (Plant-003) transfer plan
    curitiba_plan = next(
        (p for p in data["infeasible_plans"] if "curitiba" in p["source_name"].lower() or p["source_id"] == "PLANT-003"),
        None,
    )
    assert curitiba_plan is not None, "Curitiba transfer should be rejected and present in infeasible_plans"
    assert curitiba_plan["feasibility_status"] == "INFEASIBLE"
    assert "safety stock" in curitiba_plan["infeasibility_reason"].lower()


# 3. Test Priority Influence on Scoring (TIME vs COST vs RISK vs BALANCED)
def test_priority_influences_scoring():
    # Test TIME priority
    _ensure_case_at_checkpoint1("CASE-0001", "TIME")
    res_time = client.post("/api/v1/cases/CASE-0001/recovery/plan?force_regenerate=true")
    assert res_time.status_code == 200
    time_plans = res_time.json()["feasible_plans"]
    top_time_plan = time_plans[0]

    # Verify score breakdown uses 50% time weight
    assert top_time_plan["score_breakdown"]["weights_applied"]["time"] == 0.50

    # Test COST priority
    # Change checkpoint1 decision to COST
    repo = get_repository()
    case = repo.get_case("CASE-0001")
    case.checkpoint1_decision = "COST"
    repo.update_case(case)

    res_cost = client.post("/api/v1/cases/CASE-0001/recovery/plan?force_regenerate=true")
    assert res_cost.status_code == 200
    cost_plans = res_cost.json()["feasible_plans"]
    top_cost_plan = cost_plans[0]

    # Verify score breakdown uses 50% cost weight
    assert top_cost_plan["score_breakdown"]["weights_applied"]["cost"] == 0.50

    # The top plan for COST should prioritize lower cost
    assert top_cost_plan["score_breakdown"]["cost_score"] >= 70.0


# 4. Test Manager Constraints Hard Rejection (Max Recovery Time)
def test_manager_max_recovery_time_constraint():
    _ensure_case_at_checkpoint1("CASE-0001", "TIME")

    # Manager specifies max 2 days recovery
    payload = {"max_recovery_days": 2}
    res = client.post("/api/v1/cases/CASE-0001/recovery/plan?force_regenerate=true", json=payload)
    assert res.status_code == 200
    data = res.json()

    # All feasible plans must satisfy <= 2 days
    for p in data["feasible_plans"]:
        assert p["recovery_days"] <= 2

    # Any plan taking > 2 days must be in infeasible plans and fail MAX_RECOVERY_TIME constraint
    over_time_plans = [p for p in data["infeasible_plans"] if p["recovery_days"] > 2]
    assert len(over_time_plans) > 0
    for p in over_time_plans:
        time_eval = next((c for c in p["constraints"] if c["constraint_name"] == "MAX_RECOVERY_TIME"), None)
        assert time_eval is not None and not time_eval["satisfied"]


# 5. Test Historical and Contract Evidence
def test_historical_and_contract_evidence_retrieval():
    _ensure_case_at_checkpoint1("CASE-0001", "TIME")

    res = client.get("/api/v1/cases/CASE-0001/recovery/plan")
    assert res.status_code == 200
    data = res.json()

    # Find a supplier plan with contract
    contracted_plan = next((p for p in data["feasible_plans"] if p["contract_evidence"] is not None), None)
    assert contracted_plan is not None
    assert contracted_plan["contract_evidence"]["contract_id"] != ""
    assert len(contracted_plan["contract_evidence"]["clauses"]) > 0

    # Find a plan with historical precedent
    precedent_plan = next((p for p in data["feasible_plans"] if len(p["historical_evidence"]) > 0), None)
    assert precedent_plan is not None
    assert precedent_plan["historical_evidence"][0]["precedent_id"].startswith("HIST-")


# 6. Test Human Checkpoint 2: APPROVE (Locks Version & Halts Phase 2)
def test_checkpoint2_approve():
    _ensure_case_at_checkpoint1("CASE-0001", "TIME")

    plans_res = client.get("/api/v1/cases/CASE-0001/recovery/plan")
    feasible = plans_res.json()["feasible_plans"]
    target_plan = feasible[0]
    target_plan_id = target_plan["plan_id"]
    target_version = target_plan["version"]

    approve_payload = {
        "decision": "APPROVE",
        "plan_id": target_plan_id,
        "version": target_version,
        "rationale": "Fastest recovery window protects Munich line from critical stockout.",
    }
    cp2_res = client.post("/api/v1/cases/CASE-0001/checkpoint2", json=approve_payload)
    assert cp2_res.status_code == 200
    cp2_data = cp2_res.json()

    assert cp2_data["decision"] == "APPROVE"
    assert cp2_data["plan_id"] == target_plan_id
    assert cp2_data["version"] == target_version
    assert cp2_data["status"] == "RECOVERY_APPROVED"
    assert "Phase 3 Execution" in cp2_data["phase3_status"]

    # Verify case state is updated and locked
    case_res = client.get("/api/v1/cases/CASE-0001")
    assert case_res.status_code == 200
    case_data = case_res.json()
    assert case_data["status"] == "RECOVERY_APPROVED"
    assert case_data["approved_plan_id"] == target_plan_id
    assert case_data["approved_plan_version"] == target_version

    # Verify audit event logged
    audit_res = client.get("/api/v1/cases/CASE-0001/audit")
    assert audit_res.status_code == 200
    events = [e["event"] for e in audit_res.json()]
    assert "CHECKPOINT_2_APPROVED" in events


# 7. Test Human Checkpoint 2: MODIFY (Recalculates, Creates v2)
def test_checkpoint2_modify():
    _ensure_case_at_checkpoint1("CASE-0002", "BALANCED")

    plans_res = client.post("/api/v1/cases/CASE-0002/recovery/plan")
    assert plans_res.status_code == 200
    feasible = plans_res.json()["feasible_plans"]
    target_plan_id = feasible[0]["plan_id"]

    modify_payload = {
        "decision": "MODIFY",
        "modify_params": {
            "plan_id": target_plan_id,
            "allocated_quantity": 250.0,
            "transport_mode": "AIR_EXPEDITED",
        },
    }
    mod_res = client.post("/api/v1/cases/CASE-0002/checkpoint2", json=modify_payload)
    assert mod_res.status_code == 200
    mod_data = mod_res.json()

    assert mod_data["decision"] == "MODIFY"
    assert mod_data["version"] == "v2"
    assert mod_data["status"] == "AWAITING_CHECKPOINT_2"

    # Verify audit event logged
    audit_res = client.get("/api/v1/cases/CASE-0002/audit")
    assert audit_res.status_code == 200
    events = [e["event"] for e in audit_res.json()]
    assert "RECOVERY_PLAN_MODIFIED" in events


# 8. Test Human Checkpoint 2: REJECT
def test_checkpoint2_reject():
    _ensure_case_at_checkpoint1("CASE-0003", "RISK")

    client.post("/api/v1/cases/CASE-0003/recovery/plan")

    reject_payload = {
        "decision": "REJECT",
        "rationale": "Cost surcharges are unacceptable under current quarterly OPEX cap.",
    }
    rej_res = client.post("/api/v1/cases/CASE-0003/checkpoint2", json=reject_payload)
    assert rej_res.status_code == 200
    rej_data = rej_res.json()

    assert rej_data["decision"] == "REJECT"
    assert rej_data["status"] == "AWAITING_CHECKPOINT_2"

    # Verify audit event logged
    audit_res = client.get("/api/v1/cases/CASE-0003/audit")
    assert audit_res.status_code == 200
    events = [e["event"] for e in audit_res.json()]
    assert "CHECKPOINT_2_REJECTED" in events


# 9. Test Persistence Across Backend Restart
def test_persistence_across_backend_restart():
    _ensure_case_at_checkpoint1("CASE-0004", "TIME")

    plans_res = client.post("/api/v1/cases/CASE-0004/recovery/plan")
    assert plans_res.status_code == 200
    top_plan_id = plans_res.json()["feasible_plans"][0]["plan_id"]

    # Approve Checkpoint 2
    app_res = client.post(
        "/api/v1/cases/CASE-0004/checkpoint2",
        json={"decision": "APPROVE", "plan_id": top_plan_id, "version": "v1"},
    )
    assert app_res.status_code == 200

    # Simulate backend restart: reset memory singletons
    reset_services()

    # Re-fetch case and checkpoint 2 from persistent checkpointer / database
    case_res = client.get("/api/v1/cases/CASE-0004")
    assert case_res.status_code == 200
    case_data = case_res.json()
    assert case_data["status"] == "RECOVERY_APPROVED"
    assert case_data["approved_plan_id"] == top_plan_id
    assert case_data["approved_plan_version"] == "v1"

    # Verify Checkpoint 2 decision is persisted
    cp2_res = client.get("/api/v1/cases/CASE-0004/checkpoint2")
    assert cp2_res.status_code == 200
    assert cp2_res.json()["plan_id"] == top_plan_id
    assert cp2_res.json()["status"] == "RECOVERY_APPROVED"
