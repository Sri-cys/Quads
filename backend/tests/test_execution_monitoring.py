import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import reset_services, get_repository, get_case_service, get_execution_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_teardown(monkeypatch, tmp_path):
    test_db = tmp_path / "test_phase3_checkpoints.db"
    monkeypatch.setenv("DATABASE_PATH", str(test_db))
    reset_services()
    yield
    reset_services()


def _advance_case_to_approved(case_id: str = "CASE-0001", priority: str = "TIME", plan_id: str = "PLAN-02") -> tuple[str, str]:
    """Helper to take a case through Phase 1 and Phase 2 approval."""
    # Phase 1: Analyze
    client.post(f"/api/v1/cases/{case_id}/analyze")
    # Phase 1: Checkpoint 1
    client.post(f"/api/v1/cases/{case_id}/checkpoint1", json={"priority": priority})
    # Phase 2: Recovery Planning
    plan_res = client.post(f"/api/v1/cases/{case_id}/recovery/plan", json={"priority": priority})
    feasible = plan_res.json()["feasible_plans"]
    target_plan = next((p for p in feasible if p["plan_id"] == plan_id), feasible[0])
    p_id = target_plan["plan_id"]
    p_ver = target_plan["version"]

    # Phase 2: Checkpoint 2 Approval
    cp2_res = client.post(
        f"/api/v1/cases/{case_id}/checkpoint2",
        json={
            "decision": "APPROVE",
            "selected_plan_id": p_id,
            "selected_plan_version": p_ver,
            "rationale": f"Approved under {priority} objective for automated testing.",
        },
    )
    assert cp2_res.status_code == 200
    assert cp2_res.json()["status"] == "RECOVERY_APPROVED"
    return p_id, p_ver


def test_execution_safety_no_approval():
    """Verify execution is refused if case has not reached Checkpoint 2 approval."""
    # CASE-0002 is only TRIAGED
    res = client.post(
        "/api/v1/cases/CASE-0002/execution/start",
        json={"plan_id": "PLAN-01", "version": "v1"},
    )
    assert res.status_code == 409
    assert res.json()["error"] == "EXECUTION_SAFETY_CONFLICT"


def test_execution_safety_wrong_plan_or_version():
    """Verify execution is refused if requested plan_id or version does not match approved decision."""
    p_id, p_ver = _advance_case_to_approved("CASE-0001", "TIME", "PLAN-02")

    # Wrong plan ID
    res_wrong_plan = client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": "PLAN-99", "version": p_ver},
    )
    assert res_wrong_plan.status_code == 409
    assert "Version conflict" in res_wrong_plan.json()["message"]

    # Wrong version
    res_wrong_ver = client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": p_id, "version": "v99"},
    )
    assert res_wrong_ver.status_code == 409
    assert "Version conflict" in res_wrong_ver.json()["message"]


def test_start_execution_success():
    """Verify successful execution startup, baseline locking, and SAP order creation."""
    p_id, p_ver = _advance_case_to_approved("CASE-0001", "TIME", "PLAN-02")

    start_res = client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": p_id, "version": p_ver},
    )
    assert start_res.status_code == 200
    data = start_res.json()

    # Step 4: Baseline preserved
    assert data["baseline"]["plan_id"] == p_id
    assert data["baseline"]["plan_version"] == p_ver
    assert data["baseline"]["planned_quantity"] == 500.0
    assert data["baseline"]["planned_arrival_date"] is not None
    assert data["baseline"]["planned_total_cost"] > 0

    # Step 1: Execution Action created via SAP adapter
    assert data["action"]["action_id"].startswith("ACT-CASE-0001-")
    assert data["action"]["status"] == "ACCEPTED"
    assert "SAP" in data["action"]["external_system"]
    assert data["action"]["external_reference"].startswith("SAP-")
    assert data["action"]["carrier_name"] is not None

    # Step 2: Audit and Case State
    case_res = client.get("/api/v1/cases/CASE-0001")
    assert case_res.json()["status"] == "EXECUTION_IN_PROGRESS"
    assert case_res.json()["execution_action_id"] == data["action"]["action_id"]

    audit_res = client.get("/api/v1/cases/CASE-0001/audit")
    event_names = [e["event"] for e in audit_res.json()]
    assert "EXECUTION_STARTED" in event_names
    assert "EXECUTION_ACTION_CREATED" in event_names


def test_tracking_telematics_updates_and_baseline_preservation():
    """Verify telematics updates, deviation calculation, and that baseline is never overwritten."""
    p_id, p_ver = _advance_case_to_approved("CASE-0001", "TIME", "PLAN-02")
    start_res = client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": p_id, "version": p_ver},
    )
    original_planned_eta = start_res.json()["baseline"]["planned_arrival_date"]
    original_planned_qty = start_res.json()["baseline"]["planned_quantity"]

    # 1. Supplier Confirmed
    res_conf = client.post(
        "/api/v1/cases/CASE-0001/execution/event",
        json={"status": "SUPPLIER_CONFIRMED", "confirmed_quantity": 500.0},
    )
    assert res_conf.status_code == 200
    assert res_conf.json()["execution_status"] == "SUPPLIER_CONFIRMED"

    # 2. Shipment Dispatched
    res_disp = client.post(
        "/api/v1/cases/CASE-0001/execution/event",
        json={"status": "SHIPMENT_DISPATCHED", "location": "Pune Logistics Hub"},
    )
    assert res_disp.status_code == 200
    assert res_disp.json()["execution_status"] == "SHIPMENT_DISPATCHED"

    # Verify baseline is unchanged
    assert res_disp.json()["baseline"]["planned_arrival_date"] == original_planned_eta
    assert res_disp.json()["baseline"]["planned_quantity"] == original_planned_qty

    # Verify case status transitioned to MONITORING
    case_res = client.get("/api/v1/cases/CASE-0001")
    assert case_res.json()["status"] == "MONITORING"


def test_successful_recovery_and_case_resolution():
    """Complete success path: delivery confirmed within tolerance -> outcome recorded -> case resolved."""
    p_id, p_ver = _advance_case_to_approved("CASE-0001", "TIME", "PLAN-02")
    client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": p_id, "version": p_ver},
    )
    client.post(
        "/api/v1/cases/CASE-0001/execution/event",
        json={"status": "SHIPMENT_DISPATCHED"},
    )

    # Deliver material
    deliv_res = client.post(
        "/api/v1/cases/CASE-0001/execution/event",
        json={
            "status": "DELIVERED",
            "confirmed_quantity": 500.0,
            "location": "Munich Assembly Plant Inbound Bay 3",
            "description": "500 units safely received and quality inspected.",
        },
    )
    assert deliv_res.status_code == 200
    data = deliv_res.json()
    assert data["is_success"] is True
    assert data["execution_status"] == "DELIVERED"

    # Step 12: Case is RESOLVED
    case_res = client.get("/api/v1/cases/CASE-0001")
    assert case_res.json()["status"] == "RESOLVED"
    assert case_res.json()["resolved_at"] is not None

    # Step 14: Historical Outcome Record created and queryable
    outcomes_res = client.get("/api/v1/cases/CASE-0001/execution/outcomes")
    assert outcomes_res.status_code == 200
    outcomes = outcomes_res.json()
    assert len(outcomes) > 0
    assert outcomes[0]["success"] is True
    assert outcomes[0]["actual_quantity"] == 500.0
    assert outcomes[0]["strategy_used"] == "ALTERNATE_SUPPLIER"

    # Verify complete audit sequence
    audit_res = client.get("/api/v1/cases/CASE-0001/audit")
    event_names = [e["event"] for e in audit_res.json()]
    assert "SHIPMENT_DELIVERED" in event_names
    assert "RECOVERY_COMPLETED" in event_names
    assert "OUTCOME_RECORDED" in event_names
    assert "CASE_CLOSED" in event_names


def test_failure_detection_and_escalation_loop():
    """Complete failure path: delay/shortage exceeds tolerance -> failure detected -> replan triggered -> failed plan excluded."""
    p_id, p_ver = _advance_case_to_approved("CASE-0001", "TIME", "PLAN-02")
    client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": p_id, "version": p_ver},
    )

    # Simulate carrier failure / excessive delay
    fail_res = client.post(
        "/api/v1/cases/CASE-0001/execution/event",
        json={
            "status": "FAILED",
            "confirmed_quantity": 100.0,
            "reason": "Air transport cargo hold canceled due to airspace restriction; 400 units missing.",
        },
    )
    assert fail_res.status_code == 200
    data = fail_res.json()
    assert data["is_failed"] is True
    assert data["execution_status"] == "FAILED"
    assert "Air transport cargo hold canceled" in data["failure_reason"]

    # Step 9 & 10: Case escalated and returned to RECOVERY_PLANNING
    case_res = client.get("/api/v1/cases/CASE-0001")
    assert case_res.json()["status"] == "RECOVERY_PLANNING"
    # Approval revoked for the failed plan
    assert case_res.json()["approved_plan_id"] is None

    # Step 11: Failed plan preserved
    failed_plans_res = client.get("/api/v1/cases/CASE-0001/execution/failed-plans")
    assert failed_plans_res.status_code == 200
    failed_list = failed_plans_res.json()
    assert len(failed_list) == 1
    assert failed_list[0]["plan_id"] == p_id
    assert failed_list[0]["strategy"] == "ALTERNATE_SUPPLIER"

    # Step 10: Fresh recovery planning cycle excludes the failed plan
    new_plans_res = client.post(
        "/api/v1/cases/CASE-0001/recovery/plan?force_regenerate=true",
        json={"priority": "TIME"},
    )
    assert new_plans_res.status_code == 200
    plan_set = new_plans_res.json()

    # Verify that the failed source is now in infeasible_plans
    infeasible_sources = [p["source_id"] for p in plan_set["infeasible_plans"]]
    assert "SUP-003" in infeasible_sources
    failed_p = next(p for p in plan_set["infeasible_plans"] if p["source_id"] == "SUP-003")
    assert "Previously failed in execution" in failed_p["infeasibility_reason"]

    # Audit history contains failure and replan events
    audit_res = client.get("/api/v1/cases/CASE-0001/audit")
    event_names = [e["event"] for e in audit_res.json()]
    assert "EXECUTION_FAILED" in event_names
    assert "RECOVERY_ESCALATED" in event_names
    assert "REPLAN_REQUIRED" in event_names


def test_persistence_across_backend_restart():
    """Verify that execution record and progress survive a backend restart."""
    p_id, p_ver = _advance_case_to_approved("CASE-0001", "TIME", "PLAN-02")
    client.post(
        "/api/v1/cases/CASE-0001/execution/start",
        json={"plan_id": p_id, "version": p_ver},
    )
    client.post(
        "/api/v1/cases/CASE-0001/execution/event",
        json={"status": "IN_TRANSIT", "location": "Frankfurt Airport Hub"},
    )

    # Simulate backend crash/restart
    reset_services()

    # Read execution progress after restart
    prog_res = client.get("/api/v1/cases/CASE-0001/execution/progress")
    assert prog_res.status_code == 200
    prog = prog_res.json()
    assert prog["action"]["action_id"].startswith("ACT-CASE-0001-")
    assert prog["baseline"]["plan_id"] == p_id
    assert len(prog["tracking_events"]) >= 2
    assert prog["tracking_events"][-1]["status"] == "IN_TRANSIT"
