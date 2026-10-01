from app.repositories.sqlite_repository import SQLiteRepository
from app.workflow.state_machine import CaseState

repo = SQLiteRepository("quads_checkpoints.db")
cases = repo.get_all_cases()
for c in cases:
    # If the case has progressed past IMPACT (e.g. DECISION_PENDING, etc.)
    if c.status in ["DECISION_PENDING", "RECOVERY_APPROVED", "AWAITING_CHECKPOINT_2", "CONSTRAINTS_ANALYZED", "CHECKPOINT_APPROVED", "EXECUTION_IN_PROGRESS", "MONITORING", "RESOLVED"]:
        if not c.checkpoint1_decision:
            c.checkpoint1_decision = "TIME"
            print(f"Set priority TIME for {c.case_id}")
        
        # Ensure completed_stages is fully populated up to the correct stage
        # E.g. for Stage 4 (DECISION_PENDING), stages CASE, IMPACT, PRIORITY must be completed.
        required_stages = ["CASE_OVERVIEW", "IMPACT_ANALYSIS", "PRIORITY"]
        for stage in required_stages:
            if stage not in c.completed_stages:
                c.completed_stages.append(stage)
                print(f"Added {stage} to completed_stages for {c.case_id}")
                
        repo.update_case(c)
print("Done")
