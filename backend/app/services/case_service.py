"""
CaseService: Coordinates case lifecycle, centralized state transitions,
Agent 1 background runs, Agent 2 plan generation, Agent 3 deterministic evaluation,
and Human Checkpoint 2 decision governance.
"""

import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, Tuple, Any
from datetime import datetime, timezone

from app.repositories.base import BaseRepository
from app.services.audit_service import AuditService
from app.services.gemini_service import GeminiService
from app.services.impact_service import ImpactService
from app.agents.agent2_generator import Agent2PlanGenerator
from app.agents.agent3_evaluator import Agent3Evaluator
from app.models.case import Case, CaseCreateRequest
from app.models.disruption import Disruption
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.impact import ImpactAnalysis, AuditEvent
from app.models.recovery import (
    RecoveryPlanSet,
    CandidatePlanSet,
    CandidatePlan,
    RecoveryPlan,
    ExecutionSnapshot,
    ManagerConstraints,
    PlanModifyRequest,
    Checkpoint2Request,
    Checkpoint2Response,
)
from app.workflow.state_machine import (
    CaseState,
    validate_and_transition,
    normalize_state,
    InvalidStateTransitionError,
)
import logging

logger = logging.getLogger("quads.case_service")


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
        self._lock = threading.Lock()

    def close(self):
        """Clean up services on teardown."""
        pass

    def get_case(self, case_id: str) -> Optional[Case]:
        case = self.repository.get_case(case_id)
        if case:
            case.status = normalize_state(case.status).value
        return case

    def get_case_or_from_checkpoint(self, case_id: str) -> Optional[Case]:
        return self.get_case(case_id)

    def create_disruption_case(self, req: CaseCreateRequest) -> Tuple[Case, bool]:
        """
        Create a new disruption case and initialize in CASE_OVERVIEW.
        """
        existing = self.repository.find_duplicate_case(
            supplier_id=req.supplier_id,
            material_id=req.material_id,
            plant_id=req.plant_id,
            disruption_type=req.disruption_type,
        )
        if existing:
            return existing, True

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
            planning_cycle=1,
            active_plan_version="v1",
        )
        created_case = self.repository.create_case(temp_case)

        self.audit_service.log(
            case_id=created_case.case_id,
            event="DISRUPTION_RECEIVED",
            actor="SYSTEM_WORKFLOW",
            details=f"Disruption case {created_case.case_id} registered and persisted",
        )
        self.audit_service.log(
            case_id=created_case.case_id,
            event="CASE_CREATED",
            actor="SYSTEM_WORKFLOW",
            details=f"Disruption case {created_case.case_id} initialized",
        )
        return created_case, False

    def start_impact_analysis(self, case_id: str) -> Case:
        """
        One-click entry to Agent 1 Impact Analysis.
        Validates transition, marks case IMPACT_ANALYSIS_RUNNING, and executes in background worker.
        Idempotent: if already running, returns current run.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        curr_state = normalize_state(case.status)
        if curr_state == CaseState.IMPACT_ANALYSIS_RUNNING:
            logger.info(f"Analysis already running for {case_id} (idempotent)")
            return case

        # Transition validation
        target_state = validate_and_transition(
            case=case,
            event="start_impact_analysis",
            actor="HUMAN_USER",
            audit_service=self.audit_service,
        )

        with self._lock:
            case.status = target_state.value
            case.last_error = None
            case.active_step = "disruption"
            case.steps_progress = {
                "disruption": "COMPLETED",
                "inventory": "RUNNING",
                "supplier": "PENDING",
                "logistics": "PENDING",
                "production": "PENDING",
                "customer": "PENDING",
                "financial": "PENDING",
                "overall": "PENDING",
            }
            case.run_id = f"RUN-A1-{case_id}-{int(datetime.now(timezone.utc).timestamp())}"
            self.repository.update_case(case)

        # Launch background worker thread for real processing
        worker_thread = threading.Thread(
            target=self._run_impact_analysis_worker,
            args=(case_id, case.run_id),
            daemon=True,
        )
        worker_thread.start()

        self.audit_service.log(
            case_id=case_id,
            event="IMPACT_ANALYSIS_STARTED",
            actor="SYSTEM_ORCHESTRATOR",
            details=f"Impact analysis started for {case_id}",
        )

        return case

    def _run_impact_analysis_worker(self, case_id: str, run_id: str):
        """Background execution worker for Agent 1."""
        try:
            case = self.repository.get_case(case_id)
            if not case or case.run_id != run_id:
                return

            disruption = Disruption(
                disruption_type=case.disruption_type,
                description=case.description,
                supplier_id=case.supplier_id,
                material_id=case.material_id,
                plant_id=case.plant_id,
                expected_delay_days=case.expected_delay_days,
                affected_quantity=case.affected_quantity,
                detected_at=case.detected_at,
            )

            # Master data lookups
            supplier = self.repository.get_supplier(case.supplier_id)
            material = self.repository.get_material(case.material_id)
            plant = self.repository.get_plant(case.plant_id)
            inventory = self.repository.get_inventory(case.material_id, case.plant_id)
            demand = self.repository.get_demand(case.material_id, case.plant_id)
            safety_stock = self.repository.get_safety_stock(case.material_id, case.plant_id)
            pos = self.repository.get_purchase_orders(
                supplier_id=case.supplier_id,
                material_id=case.material_id,
                plant_id=case.plant_id,
            )

            # Simulate real step progress transitions
            steps = ["inventory", "supplier", "logistics", "production", "customer", "financial", "overall"]
            for step in steps:
                time.sleep(0.04)  # Micro-delay for realistic telemetry
                with self._lock:
                    case.active_step = step
                    case.steps_progress[step] = "RUNNING"
                    self.repository.update_case(case)
                time.sleep(0.03)
                with self._lock:
                    case.steps_progress[step] = "COMPLETED"
                    self.repository.update_case(case)

            # Deterministic Python impact calculation
            impact = ImpactService.analyze(
                case_id=case_id,
                disruption=disruption,
                supplier=supplier,
                material=material,
                plant=plant,
                inventory=inventory,
                demand=demand,
                safety_stock=safety_stock,
                purchase_orders=pos,
            )

            # AI Executive Explanation
            explanation, ai_status = self.gemini_service.generate_explanation(
                disruption=disruption,
                impact=impact,
            )
            impact.ai_explanation = explanation
            impact.ai_status = ai_status

            # Mark COMPLETED
            with self._lock:
                target_state = validate_and_transition(
                    case=case,
                    event="agent1_success",
                    actor="AGENT_1_IMPACT",
                    audit_service=self.audit_service,
                )
                case.status = target_state.value
                case.severity = impact.severity
                case.active_step = None
                self.repository.update_case(case)

            # Persist analysis
            self.repository.save_impact_analysis(impact)

            self.audit_service.log(
                case_id=case_id,
                event="TRIAGE_COMPLETED",
                actor="AGENT_1_IMPACT",
                details=f"Agent 1 triage completed. Severity: {impact.severity}",
            )
            self.audit_service.log(
                case_id=case_id,
                event="IMPACT_ANALYSIS_COMPLETED",
                actor="AGENT_1_IMPACT",
                details=f"Agent 1 analysis persisted. Days of cover: {impact.days_of_cover}",
            )

            logger.info(f"Agent 1 analysis completed successfully for case {case_id}")

        except Exception as e:
            logger.error(f"Error in Agent 1 worker for case {case_id}: {e}", exc_info=True)
            with self._lock:
                case = self.repository.get_case(case_id)
                if case:
                    case.status = CaseState.IMPACT_ANALYSIS_FAILED.value
                    case.last_error = str(e)
                    self.repository.update_case(case)
            self.audit_service.log(
                case_id=case_id,
                event="IMPACT_ANALYSIS_FAILED",
                actor="AGENT_1_IMPACT",
                details=f"Agent 1 execution failed: {str(e)}",
            )

    def retry_impact_analysis(self, case_id: str) -> Case:
        """Retry Agent 1 after failure."""
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")
        validate_and_transition(
            case=case,
            event="retry_impact_analysis",
            actor="HUMAN_USER",
            audit_service=self.audit_service,
        )
        return self.start_impact_analysis(case_id)

    def proceed_to_priority(self, case_id: str) -> Case:
        """Human planner completes impact review and advances to Checkpoint 1 priority selection."""
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        target_state = validate_and_transition(
            case=case,
            event="proceed_to_priority",
            actor="HUMAN_PLANNER",
            audit_service=self.audit_service,
        )
        case.status = target_state.value
        self.repository.update_case(case)
        return case

    def submit_checkpoint1(
        self,
        case_id: str,
        priority: str,
        constraints: Optional[ManagerConstraints] = None,
        force: bool = False,
    ) -> Case:
        """
        Human Checkpoint 1: Saves priority and immediately launches Agent 2 in background.
        Single transaction: PRIORITY_SAVED -> AGENT2_RUNNING.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        curr_state = normalize_state(case.status)
        if not force and curr_state in (CaseState.AGENT2_RUNNING, CaseState.AGENT3_RUNNING, CaseState.DECISION_PENDING):
            logger.info(f"Agent pipeline already active in state {curr_state.value} for {case_id} (idempotent)")
            return case

        if curr_state not in (CaseState.AGENT2_RUNNING, CaseState.AGENT3_RUNNING, CaseState.DECISION_PENDING):
            target_state = validate_and_transition(
                case=case,
                event="confirm_priority",
                actor="HUMAN_PLANNER",
                payload={"priority": priority},
                audit_service=self.audit_service,
            )
            target_status = target_state.value
        else:
            target_status = CaseState.AGENT2_RUNNING.value

        with self._lock:
            case.checkpoint1_decision = priority.upper()
            case.checkpoint1_timestamp = datetime.now(timezone.utc).isoformat()
            case.status = target_status  # AGENT2_RUNNING
            case.active_step = "generating_candidates"
            case.steps_progress = {
                "discovering_suppliers": "RUNNING",
                "evaluating_interplant": "PENDING",
                "evaluating_logistics": "PENDING",
                "generating_candidates": "PENDING",
            }
            case.run_id = f"RUN-A23-{case_id}-{int(datetime.now(timezone.utc).timestamp())}"
            self.repository.update_case(case)

        # Kick off background pipeline for Agent 2 -> auto-chain Agent 3
        worker = threading.Thread(
            target=self._run_agent2_and_3_pipeline,
            args=(case_id, priority.upper(), case.run_id, constraints),
            daemon=True,
        )
        worker.start()

        self.audit_service.log(
            case_id=case_id,
            event="CHECKPOINT_1_APPROVED",
            actor="HUMAN_PLANNER",
            details=f"Checkpoint 1 priority {priority.upper()} confirmed and Agent 2 launched",
        )

        return case

    def _run_agent2_and_3_pipeline(
        self,
        case_id: str,
        priority: str,
        run_id: str,
        constraints: Optional[ManagerConstraints] = None,
        rejected_strategies: Optional[list[str]] = None,
    ):
        """
        Background worker pipeline:
        Runs Agent 2 (generates candidate plans) -> auto-chains Agent 3 (evaluates candidates).
        """
        try:
            case = self.repository.get_case(case_id)
            if not case or case.run_id != run_id:
                return

            impact = self.repository.get_impact_analysis(case_id)
            if not impact:
                raise ValueError(f"Impact analysis required for case {case_id}")

            # ------------------------------------------------------------------
            # AGENT 2: Candidate Recovery Plan Generation
            # ------------------------------------------------------------------
            logger.info(f"Agent 2 generating candidate recovery options for {case_id} with priority {priority}...")
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["discovering_suppliers"] = "COMPLETED"
                case.steps_progress["evaluating_interplant"] = "RUNNING"
                self.repository.update_case(case)
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["evaluating_interplant"] = "COMPLETED"
                case.steps_progress["evaluating_logistics"] = "RUNNING"
                self.repository.update_case(case)
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["evaluating_logistics"] = "COMPLETED"
                case.steps_progress["generating_candidates"] = "RUNNING"
                self.repository.update_case(case)

            candidates = Agent2PlanGenerator.generate_candidates(
                case=case,
                impact=impact,
                repository=self.repository,
                priority=priority,
                rejected_strategies=rejected_strategies,
            )

            if not candidates:
                raise ValueError("Agent 2 failed to generate candidate recovery plans from available network data.")

            cand_set = CandidatePlanSet(
                case_id=case_id,
                planning_cycle=case.planning_cycle,
                priority=priority,
                candidates=candidates,
            )
            self.repository.save_candidate_plan_set(cand_set)

            with self._lock:
                fresh_case = self.repository.get_case(case_id)
                if not fresh_case or fresh_case.run_id != run_id:
                    logger.info(f"Agent 2 run {run_id} superseded. Aborting.")
                    return
                case = fresh_case
                case.steps_progress["generating_candidates"] = "COMPLETED"
                # Transition: AGENT2_RUNNING -> AGENT2_COMPLETED -> AGENT3_RUNNING
                target_a2 = validate_and_transition(case, "agent2_success", "AGENT_2_PLANNER", audit_service=self.audit_service)
                case.status = target_a2.value
                target_a3 = validate_and_transition(case, "auto_chain_agent3", "SYSTEM_ORCHESTRATOR", audit_service=self.audit_service)
                case.status = target_a3.value  # AGENT3_RUNNING
                case.active_step = "evaluating_plans"
                case.steps_progress = {
                    "validating_candidates": "RUNNING",
                    "calculating_costs": "PENDING",
                    "evaluating_risks": "PENDING",
                    "evaluating_contracts": "PENDING",
                    "checking_constraints": "PENDING",
                    "priority_scoring": "PENDING",
                }
                self.repository.update_case(case)

            # ------------------------------------------------------------------
            # AGENT 3: Evaluation, Cost, Risk, Contracts & Feasibility
            # ------------------------------------------------------------------
            logger.info(f"Agent 3 evaluating {len(candidates)} candidate plans for {case_id}...")
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["validating_candidates"] = "COMPLETED"
                case.steps_progress["calculating_costs"] = "RUNNING"
                self.repository.update_case(case)
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["calculating_costs"] = "COMPLETED"
                case.steps_progress["evaluating_risks"] = "RUNNING"
                self.repository.update_case(case)
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["evaluating_risks"] = "COMPLETED"
                case.steps_progress["evaluating_contracts"] = "RUNNING"
                self.repository.update_case(case)
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["evaluating_contracts"] = "COMPLETED"
                case.steps_progress["checking_constraints"] = "RUNNING"
                self.repository.update_case(case)
            time.sleep(0.04)
            with self._lock:
                case.steps_progress["checking_constraints"] = "COMPLETED"
                case.steps_progress["priority_scoring"] = "RUNNING"
                self.repository.update_case(case)

            plan_set = Agent3Evaluator.evaluate_candidate_plans(
                case=case,
                impact=impact,
                candidates=candidates,
                repository=self.repository,
                priority=priority,
                manager_constraints=constraints,
            )

            # Executive AI recovery briefing
            briefing, ai_status = self.gemini_service.generate_recovery_briefing(
                case_id=case_id,
                priority=priority,
                feasible_plans=plan_set.feasible_plans,
                infeasible_plans=plan_set.infeasible_plans,
            )
            plan_set.ai_briefing = briefing
            plan_set.ai_status = ai_status

            with self._lock:
                fresh_case = self.repository.get_case(case_id)
                if not fresh_case or fresh_case.run_id != run_id:
                    logger.info(f"Agent 3 run {run_id} superseded. Aborting.")
                    return
                case = fresh_case
                case.steps_progress["priority_scoring"] = "COMPLETED"
                target_state = validate_and_transition(
                    case=case,
                    event="agent3_success",
                    actor="AGENT_3_EVALUATOR",
                    audit_service=self.audit_service,
                )
                case.status = target_state.value  # DECISION_PENDING
                case.active_step = None
                self.repository.update_case(case)

            self.repository.save_recovery_plan_set(plan_set)

            logger.info(f"Agent 3 completed evaluation. Case {case_id} is in {case.status}.")

        except Exception as e:
            logger.error(f"Error in Agent 2/3 pipeline for case {case_id}: {e}", exc_info=True)
            with self._lock:
                case = self.repository.get_case(case_id)
                if case:
                    case.status = CaseState.AGENT3_FAILED.value
                    case.last_error = str(e)
                    self.repository.update_case(case)
            self.audit_service.log(
                case_id=case_id,
                event="AGENT3_FAILED",
                actor="SYSTEM_ORCHESTRATOR",
                details=f"Agent 2/3 execution failed: {str(e)}",
            )

    def submit_decision(self, case_id: str, req: Checkpoint2Request) -> tuple[Case, Checkpoint2Response]:
        """
        Human Checkpoint 2 Final Decision:
        APPROVE / MODIFY / REJECT
        Only human approvers can act. No AI may approve.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        curr_state = normalize_state(case.status)
        if curr_state != CaseState.DECISION_PENDING:
            raise InvalidStateTransitionError(
                curr_state.value, "submit_decision", f"Case is not awaiting human decision. Current: {curr_state.value}"
            )

        plan_set = self.repository.get_recovery_plan_set(case_id)
        if not plan_set:
            raise ValueError(f"Recovery plan set not found for case {case_id}")

        decision_upper = req.decision.upper()

        if decision_upper == "APPROVE":
            plan_id = req.get_effective_plan_id()
            comment = req.get_effective_comment() or "Approved by supply chain planner."

            # Find target plan in feasible plans
            target_plan = next((p for p in plan_set.feasible_plans if p.plan_id == plan_id), None)
            if not target_plan:
                # Check if it was in infeasible plans
                infeasible_target = next((p for p in plan_set.infeasible_plans if p.plan_id == plan_id), None)
                if infeasible_target:
                    raise ValueError(f"Cannot approve plan {plan_id}: Plan was evaluated as NOT FEASIBLE ({infeasible_target.infeasibility_reason}).")
                raise KeyError(f"Plan {plan_id} not found in evaluated recovery options.")

            # Validate transition
            validate_and_transition(
                case=case,
                event="approve_plan",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                payload={"plan_id": plan_id, "comment": comment, "is_feasible": True},
                audit_service=self.audit_service,
            )

            # Create immutable execution snapshot
            import hashlib
            snapshot_content = {
                "case_id": case_id,
                "plan": target_plan.model_dump(),
                "priority": case.checkpoint1_decision or "BALANCED",
                "planning_cycle": case.planning_cycle,
                "version": target_plan.version,
            }
            content_hash = hashlib.sha256(str(snapshot_content).encode()).hexdigest()

            snapshot = ExecutionSnapshot(
                case_id=case_id,
                plan_id=target_plan.plan_id,
                plan_version=target_plan.version,
                planning_cycle=case.planning_cycle,
                priority=case.checkpoint1_decision or "BALANCED",
                approved_by=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                approval_comment=comment,
                plan=target_plan.model_dump(),
                evaluation=target_plan.model_dump(),
                content_hash=content_hash,
                is_active=True,
            )
            self.repository.save_snapshot(snapshot)

            # Update case state
            with self._lock:
                case.status = "RECOVERY_APPROVED"
                case.checkpoint2_decision = "APPROVE"
                case.checkpoint2_timestamp = datetime.now(timezone.utc).isoformat()
                case.approved_plan_id = target_plan.plan_id
                case.approved_plan_version = target_plan.version
                self.repository.update_case(case)

            self.audit_service.log(
                case_id=case_id,
                event="CHECKPOINT_2_APPROVED",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                details=f"Checkpoint 2 approved for plan {target_plan.plan_id} ({target_plan.version}). Comment: {comment}",
            )
            self.audit_service.log(
                case_id=case_id,
                event="PLAN_APPROVED",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                details=f"Plan {target_plan.plan_id} ({target_plan.version}) marked as approved.",
            )

            resp = Checkpoint2Response(
                case_id=case_id,
                decision="APPROVE",
                plan_id=target_plan.plan_id,
                version=target_plan.version,
                status="RECOVERY_APPROVED",
                message=f"Recovery plan {target_plan.plan_id} ({target_plan.version}) approved for execution.",
                phase3_status="Recovery plan approved. Ready for Phase 3 Execution.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                approved_plan=target_plan,
                snapshot_id=snapshot.snapshot_id,
            )
            self.repository.save_checkpoint2(case_id, resp)
            return case, resp

        elif decision_upper == "MODIFY":
            plan_id = req.get_effective_plan_id()
            target_plan = next((p for p in (plan_set.feasible_plans + plan_set.infeasible_plans) if p.plan_id == plan_id), None)
            if not target_plan:
                raise KeyError(f"Plan {plan_id} not found")

            # Create new version vN+1
            new_version = f"v{case.planning_cycle + 1}"
            modified_plan = target_plan.model_copy(deep=True)
            modified_plan.version = new_version

            if req.modify_params:
                if req.modify_params.allocated_quantity:
                    modified_plan.recovered_quantity = req.modify_params.allocated_quantity
                if req.modify_params.transport_mode:
                    modified_plan.transport_mode = req.modify_params.transport_mode
                if req.modify_params.source_id:
                    modified_plan.source_id = req.modify_params.source_id

            # Add to plan set as unapproved new version
            plan_set.feasible_plans.insert(0, modified_plan)
            plan_set.current_plan_version = new_version
            self.repository.save_recovery_plan_set(plan_set)

            self.audit_service.log(
                case_id=case_id,
                event="RECOVERY_PLAN_MODIFIED",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                details=f"Created modified plan {plan_id} version {new_version}. Awaiting human re-evaluation and approval.",
            )
            self.audit_service.log(
                case_id=case_id,
                event="PLAN_MODIFIED",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                details=f"Created modified plan {plan_id} version {new_version}. Awaiting human re-evaluation and approval.",
            )

            resp = Checkpoint2Response(
                case_id=case_id,
                decision="MODIFY",
                plan_id=plan_id,
                version=new_version,
                status="AWAITING_CHECKPOINT_2",
                message=f"Plan {plan_id} modified to new version {new_version}.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                approved_plan=modified_plan,
            )
            return case, resp

        elif decision_upper == "REJECT":
            reason = req.get_effective_comment() or "Cost surcharges are unacceptable under current quarterly OPEX cap."

            validate_and_transition(
                case=case,
                event="reject_plan",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                payload={"reason": reason},
                audit_service=self.audit_service,
            )

            with self._lock:
                case.planning_cycle += 1
                case.status = CaseState.AGENT2_RUNNING.value
                case.run_id = f"RUN-A23-{case_id}-{int(datetime.now(timezone.utc).timestamp())}"
                self.repository.update_case(case)

            # Start new planning cycle in background
            worker = threading.Thread(
                target=self._run_agent2_and_3_pipeline,
                args=(case_id, case.checkpoint1_decision or "BALANCED", case.run_id, None, [req.plan_id]),
                daemon=True,
            )
            worker.start()

            self.audit_service.log(
                case_id=case_id,
                event="CHECKPOINT_2_REJECTED",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                details=f"Plans rejected: {reason}",
            )
            self.audit_service.log(
                case_id=case_id,
                event="PLAN_REJECTED",
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
                details=f"Plans rejected: {reason}",
            )

            resp = Checkpoint2Response(
                case_id=case_id,
                decision="REJECT",
                plan_id=req.plan_id,
                version=f"v{case.planning_cycle - 1}",
                status="AWAITING_CHECKPOINT_2",
                message=f"Plans rejected. Starting planning cycle {case.planning_cycle}.",
                timestamp=datetime.now(timezone.utc).isoformat(),
                actor=req.manager_id or "SUPPLY_CHAIN_PLANNER",
            )
            return case, resp

        else:
            raise ValueError(f"Unknown decision '{req.decision}'. Must be APPROVE, MODIFY, or REJECT.")

    def replan_case(self, case_id: str, reason: str) -> Case:
        """
        Triggered when an execution deviation or disruption requires replanning.
        The current approved plan keeps executing until the new version is approved.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        validate_and_transition(
            case=case,
            event="replan",
            actor="HUMAN_PLANNER",
            audit_service=self.audit_service,
        )

        with self._lock:
            case.planning_cycle += 1
            case.status = CaseState.AGENT2_RUNNING.value
            case.run_id = f"RUN-REPLAN-{case_id}-{int(datetime.now(timezone.utc).timestamp())}"
            self.repository.update_case(case)

        worker = threading.Thread(
            target=self._run_agent2_and_3_pipeline,
            args=(case_id, case.checkpoint1_decision or "BALANCED", case.run_id),
            daemon=True,
        )
        worker.start()

        return case

    def get_recovery_plan_set(self, case_id: str) -> Optional[RecoveryPlanSet]:
        return self.repository.get_recovery_plan_set(case_id)

    def get_checkpoint2(self, case_id: str) -> Optional[Checkpoint2Response]:
        return self.repository.get_checkpoint2(case_id)

    def get_snapshots(self, case_id: str) -> list[ExecutionSnapshot]:
        return self.repository.get_snapshots(case_id)

    def get_active_snapshot(self, case_id: str) -> Optional[ExecutionSnapshot]:
        return self.repository.get_active_snapshot(case_id)
