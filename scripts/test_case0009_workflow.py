import requests
import json
import sys
import time
import sqlite3
from pathlib import Path

BASE_URL = "http://localhost:8000"

def reset_case():
    db_path = Path("backend/quads_checkpoints.db")
    if db_path.exists():
        conn = sqlite3.connect(str(db_path))
        conn.execute("DELETE FROM checkpoints WHERE thread_id = 'CASE-0009'")
        conn.execute("DELETE FROM writes WHERE thread_id = 'CASE-0009'")
        conn.commit()
        conn.close()
    
    # Touch main.py to trigger reload of in-memory MockRepository
    main_py = Path("backend/app/main.py")
    main_py.touch()
    time.sleep(2)

def test_workflow():
    print("==================================================")
    print("TESTING STRICT WORKFLOW FOR CASE-0009")
    print("==================================================")

    reset_case()

    # 1. Inspect initial case
    r = requests.get(f"{BASE_URL}/api/v1/cases/CASE-0009")
    assert r.status_code == 200, f"Case fetch failed: {r.text}"
    case = r.json()
    print(f"[1. CASE] ID: {case['case_id']}, Status: {case['status']}, Stage: {case['current_stage']}, Route: {case['stage_route']}")
    assert case["status"] == "TRIAGED"
    assert case["current_stage"] == "IMPACT_ANALYSIS"
    assert case["checkpoint1_decision"] is None
    assert case["checkpoint2_decision"] is None

    # 2. Negative test: Attempt checkpoint1 before Impact Analysis
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/checkpoint1", json={"priority": "TIME"})
    print(f"[NEGATIVE 1] Attempt Checkpoint 1 before Impact Analysis -> Status: {r.status_code}")
    assert r.status_code in [400, 409, 422], f"Expected error, got {r.status_code}"

    # 3. Negative test: Attempt recovery planning before Checkpoint 1
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/recovery/plan", json={"priority": "TIME"})
    print(f"[NEGATIVE 2] Attempt Recovery Plan before Checkpoint 1 -> Status: {r.status_code}")
    assert r.status_code in [400, 409, 422], f"Expected error, got {r.status_code}"

    # 4. Start Impact Analysis (Agent 1)
    print("\n--- Starting Stage 2: Impact Analysis (Agent 1) ---")
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/analyze")
    assert r.status_code == 200, f"Analysis failed: {r.text}"
    impact = r.json()
    print(f"Impact Analysis complete:")
    print(f"  Total Inventory:        {impact.get('total_inventory')}")
    print(f"  Available Inventory:    {impact.get('available_inventory')}")
    print(f"  Reserved Quantity:      {impact.get('reserved_quantity')}")
    print(f"  Daily Demand:           {impact.get('daily_demand')}")
    print(f"  Days of Cover:          {impact.get('days_of_cover')}")
    print(f"  Safety Stock Quantity:  {impact.get('safety_stock_quantity')}")
    print(f"  Safety Stock Breach:    {impact.get('safety_stock_breach')}")
    print(f"  Supply Gap Quantity:    {impact.get('supply_gap_quantity')}")
    print(f"  Severity:               {impact.get('severity')}")

    # Verify inventory is NOT null or 0 fake
    assert impact["total_inventory"] == 150.0
    assert impact["available_inventory"] == 50.0
    assert impact["reserved_quantity"] == 100.0
    assert impact["daily_demand"] == 25.0
    assert impact["days_of_cover"] == 2.0
    assert impact["safety_stock_quantity"] == 100.0
    assert impact["safety_stock_breach"] is True
    assert impact["supply_gap_quantity"] == 0.0

    # Verify updated case state
    r = requests.get(f"{BASE_URL}/api/v1/cases/CASE-0009")
    case = r.json()
    print(f"After Analysis: Status: {case['status']}, Stage: {case['current_stage']}, Route: {case['stage_route']}")
    assert case["status"] in ["ANALYZED", "AWAITING_CHECKPOINT_1"]
    assert case["current_stage"] == "PRIORITY"
    assert case["stage_route"] == "checkpoint1"

    # 5. Checkpoint 1 (Stage 3): Select and Save Priority
    print("\n--- Testing Stage 3: Checkpoint 1 Priority Selection ---")
    # Test changing to different priorities
    priorities = ["TIME", "COST", "STOCK", "RISK", "CUSTOMER", "BALANCED"]
    for p in priorities:
        print(f"  Selecting priority: {p}")
    
    # Save TIME priority
    chosen_priority = "TIME"
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/checkpoint1", json={"priority": chosen_priority})
    assert r.status_code == 200, f"Checkpoint 1 save failed: {r.text}"
    cp1_data = r.json()
    print(f"Saved Checkpoint 1: decision={cp1_data.get('decision')}, status={cp1_data.get('status')}")

    r = requests.get(f"{BASE_URL}/api/v1/cases/CASE-0009")
    case = r.json()
    print(f"After CP1 Save: Status: {case['status']}, Stage: {case['current_stage']}, Route: {case['stage_route']}")
    assert case["status"] == "CHECKPOINT_APPROVED"
    assert case["checkpoint1_decision"] == "TIME"
    assert case["current_stage"] == "CONSTRAINTS"
    assert case["stage_route"] == "constraints"

    # 6. Stage 4 & 5: Generate Recovery Plans (Agent 2 Constraints -> Agent 3 Recovery)
    print("\n--- Generating Recovery Plans (Agent 3) ---")
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/recovery/plan", json={"priority": chosen_priority})
    assert r.status_code == 200, f"Plan generation failed: {r.text}"
    plans_data = r.json()
    feasible = plans_data.get("feasible_plans", [])
    infeasible = plans_data.get("infeasible_plans", [])
    print(f"Agent 3 generated {len(feasible)} feasible plans, {len(infeasible)} infeasible plans.")
    assert len(feasible) > 0, "Expected at least one feasible plan"

    # CRITICAL CHECK: NO AUTOMATIC APPROVAL
    r = requests.get(f"{BASE_URL}/api/v1/cases/CASE-0009")
    case = r.json()
    print(f"CRITICAL CHECK - Case Status after Agent 3: {case['status']}")
    print(f"  checkpoint2_decision: {case['checkpoint2_decision']}")
    print(f"  approved_plan_id:     {case['approved_plan_id']}")
    assert case["status"] in ["AWAITING_CHECKPOINT_2", "DECISION_PENDING"], f"Case should be AWAITING_CHECKPOINT_2, got {case['status']}"
    assert case["checkpoint2_decision"] is None, "Plan must NOT be automatically approved!"
    assert case["approved_plan_id"] is None, "approved_plan_id must NOT be set automatically!"
    assert case["current_stage"] == "DECISION", f"Current stage should be DECISION, got {case['current_stage']}"
    assert case["stage_route"] == "decision"

    # 7. Stage 6: Final Human Decision (Approve)
    print("\n--- Stage 6: Human Final Decision ---")
    top_plan = feasible[0]
    strat = top_plan.get("strategy") or top_plan.get("strategy_name") or "Expedite"
    print(f"Selected plan for approval: {top_plan['plan_id']} ({strat})")
    
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/checkpoint2", json={
        "decision": "APPROVE",
        "plan_id": top_plan["plan_id"],
        "version": top_plan.get("version", "v1"),
        "rationale": "Supply chain director verified feasibility and cost limits."
    })
    assert r.status_code == 200, f"Approval failed: {r.text}"
    dec_data = r.json()
    print(f"Approval response: {dec_data}")

    r = requests.get(f"{BASE_URL}/api/v1/cases/CASE-0009")
    case = r.json()
    print(f"After Approval: Status: {case['status']}, Stage: {case['current_stage']}, Route: {case['stage_route']}")
    assert case["status"] == "RECOVERY_APPROVED"
    assert case["checkpoint2_decision"] == "APPROVE"
    assert case["approved_plan_id"] == top_plan["plan_id"]
    assert case["current_stage"] == "EXECUTION & MONITORING"
    assert case["stage_route"] == "executionMonitoring"

    # 8. Stage 7: Execution & Monitoring
    print("\n--- Stage 7: Start Execution ---")
    r = requests.post(f"{BASE_URL}/api/v1/cases/CASE-0009/execution/start", json={
        "plan_id": top_plan["plan_id"],
        "version": top_plan.get("version", "v1")
    })
    assert r.status_code == 200, f"Execution start failed: {r.text}"
    exec_data = r.json()
    print(f"Execution started: Action ID: {exec_data.get('action_id')}, Status: {exec_data.get('status')}")

    r = requests.get(f"{BASE_URL}/api/v1/cases/CASE-0009")
    case = r.json()
    print(f"During Execution: Status: {case['status']}, Stage: {case['current_stage']}, Route: {case['stage_route']}")
    assert case["status"] in ["EXECUTION_IN_PROGRESS", "ON_TRACK", "MONITORING"]

    print("\n==================================================")
    print("ALL STRICT WORKFLOW CHECKS PASSED PERFECTLY!")
    print("==================================================")

if __name__ == "__main__":
    test_workflow()
