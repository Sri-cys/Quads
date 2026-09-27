"""
CaseService: Coordinates case lifecycle, LangGraph orchestration,
and SQLite checkpoint persistence across three sequential REST calls.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone

from langgraph.checkpoint.sqlite import SqliteSaver

from app.repositories.base import BaseRepository
from app.services.audit_service import AuditService
from app.services.gemini_service import GeminiService
from app.workflow.graph import create_workflow_graph
from app.models.case import Case, CaseCreateRequest
from app.models.impact import ImpactAnalysis, AuditEvent
from app.services.recovery_service import RecoveryService
from app.models.recovery import (
    RecoveryPlanSet,
    ManagerConstraints,
    PlanModifyRequest,
    Checkpoint2Request,
    Checkpoint2Response,
)


class CaseService:
    def __init__(
        self,
        repository: BaseRepository,
        audit_service: AuditService,
        gemini_service: Optional[GeminiService] = None,
        db_path: Optional[str] = None,
    ):
        self.repository = repository
        self.audit_service = audit_service
        self.gemini_service = gemini_service or GeminiService()

        # Persistent SQLite checkpointer for LangGraph
        if db_path:
            self._db_path = Path(db_path)
        else:
            env_db = os.environ.get("DATABASE_PATH")
            if env_db:
                self._db_path = Path(env_db)
            else:
                backend_dir = Path(__file__).resolve().parents[2]
                self._db_path = backend_dir / "quads_checkpoints.db"

        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self.checkpointer = SqliteSaver(self._conn)

        # Build workflow graph
        self.workflow = create_workflow_graph(
            repository=self.repository,
            audit_service=self.audit_service,
            gemini_service=self.gemini_service,
            checkpointer=self.checkpointer,
        )

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def create_disruption_case(self, req: CaseCreateRequest) -> Tuple[Case, bool]:
        """
        Create a new disruption case and run LangGraph ingestion + case_creation.
        Returns (case, is_duplicate).
        If duplicate found, returns (existing_case, True).
        """
        # Step 1: Check duplicate
        existing = self.repository.find_duplicate_case(
            supplier_id=req.supplier_id,
            material_id=req.material_id,
            plant_id=req.plant_id,
            disruption_type=req.disruption_type,
        )
        if existing:
            return existing, True

        # Generate case_id
        temp_case = Case(
            case_id="",
            disruption_type=req.disruption_type,
            description=req.description,
            supplier_id=req.supplier_id,
            material_id=req.material_id,
            plant_id=req.plant_id,
            expected_delay_days=req.expected_delay_days,
            affected_quantity=req.affected_quantity,
            detected_at=datetime.now(timezone.utc).isoformat(),
            status="CREATED",
        )
        # Allocate ID in repository
        created_case = self.repository.create_case(temp_case)
        case_id = created_case.case_id

        # Invoke LangGraph stage 1 (ingestion + case_creation)
        config = {"configurable": {"thread_id": case_id}}
        initial_state = {
            "case_id": case_id,
            "disruption": {
                "disruption_type": req.disruption_type,
                "description": req.description,
                "supplier_id": req.supplier_id,
                "material_id": req.material_id,
                "plant_id": req.plant_id,
                "expected_delay_days": req.expected_delay_days,
                "affected_quantity": req.affected_quantity,
                "detected_at": created_case.detected_at,
            },
            "status": "CREATED",
            "errors": [],
            "audit_events": [],
        }

        self.workflow.invoke(initial_state, config=config)
        return created_case, False

    def get_case_or_from_checkpoint(self, case_id: str) -> Optional[Case]:
        """
        Fetch case from repository, and synchronize with persistent LangGraph SQLite checkpointer.
        Ensures restart persistence across both pre-seeded and dynamically created cases.
        """
        case = self.repository.get_case(case_id)

        # Attempt recovery / sync from persistent SQLite checkpointer
        config = {"configurable": {"thread_id": case_id}}
        state_snapshot = self.workflow.get_state(config)
        if state_snapshot.values and "disruption" in state_snapshot.values:
            d = state_snapshot.values["disruption"]
            snap_status = state_snapshot.values.get("status")
            snap_cp1 = state_snapshot.values.get("checkpoint1_decision")
            snap_cp2 = state_snapshot.values.get("checkpoint2_decision")

            if case:
                if snap_status:
                    status_order = [
                        "CREATED", "TRIAGED", "ANALYZED", "CHECKPOINT_APPROVED",
                        "RECOVERY_PLANNING", "AWAITING_CHECKPOINT_2", "RECOVERY_APPROVED",
                        "EXECUTION_IN_PROGRESS", "MONITORING", "RESOLVED"
                    ]
                    try:
                        curr_idx = status_order.index(case.status)
                        snap_idx = status_order.index(snap_status)
                        if snap_idx > curr_idx or snap_status == "RECOVERY_PLANNING":
                            case.status = snap_status
                    except ValueError:
                        case.status = snap_status
                if snap_cp1 and not case.checkpoint1_decision:
                    case.checkpoint1_decision = snap_cp1
                if case.status == "RECOVERY_PLANNING":
                    case.approved_plan_id = None
                    case.approved_plan_version = None
                    case.checkpoint2_decision = None
                else:
                    if snap_cp2 and not case.checkpoint2_decision:
                        case.checkpoint2_decision = snap_cp2.get("decision")
                        case.checkpoint2_timestamp = snap_cp2.get("timestamp")
                        case.approved_plan_id = snap_cp2.get("plan_id")
                        case.approved_plan_version = snap_cp2.get("version")
                self.repository.update_case(case)
            else:
                case = Case(
                    case_id=case_id,
                    disruption_type=d.get("disruption_type", "UNKNOWN"),
                    description=d.get("description", ""),
                    supplier_id=d.get("supplier_id", ""),
                    material_id=d.get("material_id", ""),
                    plant_id=d.get("plant_id", ""),
                    expected_delay_days=d.get("expected_delay_days", 5),
                    affected_quantity=d.get("affected_quantity"),
                    detected_at=d.get("detected_at", datetime.now(timezone.utc).isoformat()),
                    status=snap_status or "CREATED",
                    severity=state_snapshot.values.get("severity"),
                    checkpoint1_decision=snap_cp1,
                    checkpoint2_decision=snap_cp2.get("decision") if snap_cp2 else None,
                    checkpoint2_timestamp=snap_cp2.get("timestamp") if snap_cp2 else None,
                    approved_plan_id=snap_cp2.get("plan_id") if snap_cp2 else None,
                    approved_plan_version=snap_cp2.get("version") if snap_cp2 else None,
                )
                self.repository.create_case(case)

            if "execution_record" in state_snapshot.values and state_snapshot.values["execution_record"]:
                if not self.repository.get_execution_record(case_id):
                    from app.models.execution import ExecutionAction
                    rec = ExecutionAction(**state_snapshot.values["execution_record"])
                    self.repository.save_execution_record(rec)
            if "execution_baseline" in state_snapshot.values and state_snapshot.values["execution_baseline"]:
                if not self.repository.get_execution_baseline(case_id):
                    from app.models.execution import ExecutionBaseline
                    base = ExecutionBaseline(**state_snapshot.values["execution_baseline"])
                    self.repository.save_execution_baseline(base)
            if "tracking_events" in state_snapshot.values and state_snapshot.values["tracking_events"]:
                existing_evts = self.repository.get_tracking_events(case_id)
                if not existing_evts:
                    from app.models.execution import TrackingEvent
                    for ev in state_snapshot.values["tracking_events"]:
                        self.repository.add_tracking_event(case_id, TrackingEvent(**ev))

            if "impact_analysis" in state_snapshot.values and state_snapshot.values["impact_analysis"]:
                if not self.repository.get_impact_analysis(case_id):
                    analysis = ImpactAnalysis(**state_snapshot.values["impact_analysis"])
                    self.repository.save_impact_analysis(analysis)
            if "recovery_plan_set" in state_snapshot.values and state_snapshot.values["recovery_plan_set"]:
                if not self.repository.get_recovery_plan_set(case_id):
                    plan_set = RecoveryPlanSet(**state_snapshot.values["recovery_plan_set"])
                    self.repository.save_recovery_plan_set(plan_set)
            if snap_cp2 and case.status != "RECOVERY_PLANNING" and not self.repository.get_checkpoint2(case_id):
                try:
                    cp2 = Checkpoint2Response(**{**snap_cp2, "case_id": case_id})
                    self.repository.save_checkpoint2(case_id, cp2)
                except Exception:
                    pass
            return case

        return case

    def run_impact_analysis(self, case_id: str) -> ImpactAnalysis:
        """
        Resume LangGraph for case_id:
        Runs triage_node -> impact_analysis_node -> gemini_explanation_node.
        Halts before checkpoint1_node.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        # Conflict check: if analysis already ran or checkpoint already done
        if case.status in {"CHECKPOINT_APPROVED", "RESOLVED"}:
            raise ValueError(f"Case {case_id} is already in {case.status} state")

        config = {"configurable": {"thread_id": case_id}}
        state_snapshot = self.workflow.get_state(config)

        # If not present in graph state (e.g. mock pre-seeded cases), initialize graph state
        if not state_snapshot.values:
            initial_state = {
                "case_id": case_id,
                "disruption": {
                    "disruption_type": case.disruption_type,
                    "description": case.description,
                    "supplier_id": case.supplier_id,
                    "material_id": case.material_id,
                    "plant_id": case.plant_id,
                    "expected_delay_days": case.expected_delay_days,
                    "affected_quantity": case.affected_quantity,
                    "detected_at": case.detected_at,
                },
                "status": "CREATED",
            }
            self.workflow.invoke(initial_state, config=config)

        # Resume workflow
        self.workflow.invoke(None, config=config)

        # Retrieve saved analysis from repository
        analysis = self.repository.get_impact_analysis(case_id)
        if not analysis:
            raise RuntimeError(f"Impact analysis could not be generated for {case_id}")
        return analysis

    def submit_checkpoint1(self, case_id: str, priority: str) -> Case:
        """
        Submit Human Checkpoint 1 priority decision.
        Resumes LangGraph: runs checkpoint1_node and reaches END.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        if case.status == "CHECKPOINT_APPROVED":
            raise ValueError(f"Checkpoint 1 has already been approved for {case_id}")

        analysis = self.repository.get_impact_analysis(case_id)
        if not analysis:
            raise ValueError(f"Impact analysis must be performed before Checkpoint 1 for {case_id}")

        config = {"configurable": {"thread_id": case_id}}
        
        # Check graph state exists
        state_snapshot = self.workflow.get_state(config)
        if not state_snapshot.values:
            # Sync graph state if pre-seeded case
            self.workflow.invoke({
                "case_id": case_id,
                "disruption": {
                    "disruption_type": case.disruption_type,
                    "description": case.description,
                    "supplier_id": case.supplier_id,
                    "material_id": case.material_id,
                    "plant_id": case.plant_id,
                    "expected_delay_days": case.expected_delay_days,
                    "affected_quantity": case.affected_quantity,
                    "detected_at": case.detected_at,
                },
                "status": "AWAITING_CHECKPOINT_1",
            }, config=config)

        # Update decision in graph state
        self.workflow.update_state(config, {"checkpoint1_decision": priority})

        # Resume to complete checkpoint1_node and reach END
        self.workflow.invoke(None, config=config)

        updated_case = self.repository.get_case(case_id)
        return updated_case

    def get_recovery_plan_set(self, case_id: str) -> Optional[RecoveryPlanSet]:
        return self.repository.get_recovery_plan_set(case_id)

    def get_checkpoint2(self, case_id: str) -> Optional[Checkpoint2Response]:
        return self.repository.get_checkpoint2(case_id)

    def run_recovery_planning(
        self,
        case_id: str,
        constraints: Optional[ManagerConstraints] = None,
        force_regenerate: bool = False,
    ) -> RecoveryPlanSet:
        """
        Execute Agent 2 Recovery Planning:
        Discovers alternate suppliers, plants, inventory, and transport options.
        Evaluates hard vs soft constraints, computes deterministic scores based on Checkpoint 1 priority,
        ranks feasible alternatives, generates AI executive briefing, and pauses at Checkpoint 2.
        """
        case = self.get_case_or_from_checkpoint(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        if not case.checkpoint1_decision:
            raise ValueError(f"Checkpoint 1 must be approved before beginning recovery planning for {case_id}")

        # If already exists and not forced, return existing
        existing_set = self.repository.get_recovery_plan_set(case_id)
        if existing_set and not force_regenerate and not constraints:
            return existing_set

        impact = self.repository.get_impact_analysis(case_id)
        if not impact:
            raise ValueError(f"Impact analysis required before recovery planning for {case_id}")

        priority = case.checkpoint1_decision or "BALANCED"
        plan_set = RecoveryService.generate_plans(
            case=case,
            impact=impact,
            repository=self.repository,
            manager_constraints=constraints,
            priority_override=priority,
        )

        briefing, ai_status = self.gemini_service.generate_recovery_briefing(
            case_id=case_id,
            priority=priority,
            feasible_plans=plan_set.feasible_plans,
            infeasible_plans=plan_set.infeasible_plans,
        )
        plan_set.ai_briefing = briefing
        plan_set.ai_status = ai_status
        self.repository.save_recovery_plan_set(plan_set)

        config = {"configurable": {"thread_id": case_id}}
        try:
            self.workflow.update_state(config, {
                "recovery_plan_set": plan_set.model_dump(),
                "checkpoint1_decision": priority,
                "manager_constraints": constraints.model_dump() if constraints else {},
                "status": "AWAITING_CHECKPOINT_2",
            })
        except Exception:
            pass

        self.audit_service.log(
            case_id=case_id,
            event="RECOVERY_PLANNING_COMPLETED",
            actor="AGENT_2_RECOVERY",
            details=(
                f"Generated {len(plan_set.feasible_plans)} feasible recovery options and {len(plan_set.infeasible_plans)} rejected options. "
                f"Top recommended option: {plan_set.feasible_plans[0].plan_id if plan_set.feasible_plans else 'None'} "
                f"(Score: {plan_set.feasible_plans[0].score if plan_set.feasible_plans else 0.0})"
            ),
        )
        return plan_set

    def modify_recovery_plan(
        self,
        case_id: str,
        modify_req: PlanModifyRequest,
    ) -> RecoveryPlanSet:
        """
        Planner modifies a specific plan (e.g. quantity, transport, constraints).
        Recalculates feasibility, constraints, scores, increments version to v2, and updates ranking.
        """
        case = self.get_case_or_from_checkpoint(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        current_set = self.repository.get_recovery_plan_set(case_id)
        if not current_set:
            current_set = self.run_recovery_planning(case_id)

        updated_set = RecoveryService.modify_and_recalculate(
            case=case,
            current_set=current_set,
            modify_req=modify_req,
            repository=self.repository,
        )

        # Update graph state
        config = {"configurable": {"thread_id": case_id}}
        try:
            self.workflow.update_state(config, {"recovery_plan_set": updated_set.model_dump()})
        except Exception:
            pass

        self.audit_service.log(
            case_id=case_id,
            event="RECOVERY_PLAN_MODIFIED",
            actor="SUPPLY_CHAIN_PLANNER",
            details=f"Plan {modify_req.plan_id} modified. New version: {updated_set.current_plan_version}.",
        )
        return updated_set

    def submit_checkpoint2(
        self,
        case_id: str,
        req: Checkpoint2Request,
    ) -> Checkpoint2Response:
        """
        Submit Human Checkpoint 2 Governance Decision:
        - APPROVE: Locks exact plan version, marks case RECOVERY_APPROVED, ready for Phase 3.
        - MODIFY: Modifies parameters, creates new version, recalculates score and ranking.
        - REJECT: Rejects options, triggers audit, marks case AWAITING_CHECKPOINT_2.
        """
        case = self.get_case_or_from_checkpoint(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        if case.status == "RECOVERY_APPROVED":
            raise ValueError(f"Recovery plan has already been approved for case '{case_id}' (Plan: {case.approved_plan_id} {case.approved_plan_version})")

        plan_set = self.repository.get_recovery_plan_set(case_id)
        if not plan_set:
            plan_set = self.run_recovery_planning(case_id)

        decision_upper = req.decision.upper()
        if decision_upper not in {"APPROVE", "MODIFY", "REJECT"}:
            raise ValueError(f"Invalid Checkpoint 2 decision: '{req.decision}'. Must be APPROVE, MODIFY, or REJECT.")

        if decision_upper == "MODIFY":
            if not req.modify_params:
                raise ValueError("modify_params required when decision is MODIFY")
            updated_set = self.modify_recovery_plan(case_id, req.modify_params)
            return Checkpoint2Response(
                case_id=case_id,
                decision="MODIFY",
                plan_id=req.modify_params.plan_id,
                version=updated_set.current_plan_version,
                status="AWAITING_CHECKPOINT_2",
                message=f"Plan {req.modify_params.plan_id} recalculated to version {updated_set.current_plan_version}. Review updated ranking.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor="SUPPLY_CHAIN_PLANNER",
                approved_plan=None,
                phase3_status="Recalculated. Awaiting Checkpoint 2 decision.",
            )

        if decision_upper == "REJECT":
            resp = Checkpoint2Response(
                case_id=case_id,
                decision="REJECT",
                plan_id=req.plan_id,
                version=req.version,
                status="AWAITING_CHECKPOINT_2",
                message="Recovery alternatives rejected by manager. Regeneration available.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor="SUPPLY_CHAIN_PLANNER",
                approved_plan=None,
                phase3_status="Paused at Phase 2. Awaiting revised recovery cycle.",
            )
            self.repository.save_checkpoint2(case_id, resp)
            self.audit_service.log(
                case_id=case_id,
                event="CHECKPOINT_2_REJECTED",
                actor="SUPPLY_CHAIN_PLANNER",
                details=f"Recovery plan rejected by manager. Rationale: {req.rationale or 'Requirements not met'}",
            )
            return resp

        # APPROVE
        plan_id = req.get_effective_plan_id()
        if not plan_id:
            raise ValueError("plan_id is required to approve Checkpoint 2")

        selected_plan: Optional[Any] = None
        for p in plan_set.feasible_plans:
            if p.plan_id == plan_id:
                selected_plan = p
                break

        if not selected_plan:
            # Check if attempting to approve an infeasible plan
            for p in plan_set.infeasible_plans:
                if p.plan_id == plan_id:
                    raise ValueError(f"Cannot approve Plan {plan_id}: Plan is not feasible ({p.infeasibility_reason})")
            raise KeyError(f"Plan {plan_id} was not found in recovery alternatives for case {case_id}")

        version = req.get_effective_version() or selected_plan.version

        # Update LangGraph state and resume to checkpoint2_node
        config = {"configurable": {"thread_id": case_id}}
        state_snapshot = self.workflow.get_state(config)
        if not state_snapshot.values:
            self.run_recovery_planning(case_id)

        resp = Checkpoint2Response(
            case_id=case_id,
            decision="APPROVE",
            plan_id=selected_plan.plan_id,
            version=version,
            status="RECOVERY_APPROVED",
            message=f"Human Checkpoint 2 approved with Plan {selected_plan.plan_id} (Version: {version}). Plan locked for execution.",
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor="SUPPLY_CHAIN_PLANNER",
            approved_plan=selected_plan,
            phase3_status="Ready for Phase 3 Execution. Autonomous execution paused at Phase 2 boundary.",
        )

        self.workflow.update_state(config, {
            "checkpoint2_decision": resp.model_dump(),
            "status": "RECOVERY_APPROVED",
        })
        self.workflow.invoke(None, config=config)

        self.repository.save_checkpoint2(case_id, resp)

        case = self.repository.get_case(case_id)
        if case:
            case.status = "RECOVERY_APPROVED"
            case.checkpoint2_decision = "APPROVE"
            case.checkpoint2_timestamp = resp.timestamp
            case.approved_plan_id = selected_plan.plan_id
            case.approved_plan_version = version
            self.repository.update_case(case)

        self.audit_service.log(
            case_id=case_id,
            event="CHECKPOINT_2_APPROVED",
            actor="SUPPLY_CHAIN_PLANNER",
            details=f"Human Checkpoint 2 approved plan {selected_plan.plan_id} (Version: {version}). Plan locked for execution. Phase 2 complete.",
        )
        return resp
