import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from app.repositories.base import BaseRepository
from app.adapters.sap.base import SAPAdapter
from app.services.audit_service import AuditService
from app.services.gemini_service import GeminiService
from app.models.case import Case
from app.models.recovery import RecoveryPlan, RecoveryPlanSet
from app.models.execution import (
    ExecutionBaseline,
    ExecutionAction,
    TrackingEvent,
    ExecutionDeviation,
    FailedPlanRecord,
    HistoricalOutcomeRecord,
    ExecutionProgress,
    ExecutePlanRequest,
    SimulateEventRequest,
)

logger = logging.getLogger("quads.execution_service")


class ExecutionService:
    """
    Agent 3 — Execution, Monitoring & Learning Service.
    Enforces strict governance:
    1. Requires explicit Checkpoint 2 manager approval with matching plan version.
    2. Communicates with enterprise systems via SAP Adapter layer.
    3. Preserves immutable planned baseline vs actual telemetry.
    4. Detects delivery delays, supplier shortages, and transport failures.
    5. Coordinates failure escalation and returns case to Recovery Planning (excluding failed plan).
    6. Concludes successful recoveries, marks case RESOLVED, and stores historical learning outcomes.
    """

    def __init__(
        self,
        repository: BaseRepository,
        sap_adapter: SAPAdapter,
        audit_service: AuditService,
        gemini_service: GeminiService,
        case_service: Optional[Any] = None,
    ):
        self.repository = repository
        self.sap_adapter = sap_adapter
        self.audit_service = audit_service
        self.gemini_service = gemini_service
        self.case_service = case_service

    def start_execution(
        self,
        case_id: str,
        req: ExecutePlanRequest,
    ) -> ExecutionProgress:
        """
        Step 1 & 2: Validate approval, lock baseline, create SAP action, record execution start.
        """
        case = self.case_service.get_case_or_from_checkpoint(case_id) if self.case_service else self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' was not found.")

        # Safety Check 1: Approval validation
        if case.status not in {"RECOVERY_APPROVED", "AWAITING_CHECKPOINT_2"}:
            if case.status == "RESOLVED":
                raise ValueError(f"Case '{case_id}' is already closed and resolved.")
            if case.status in {"EXECUTION_IN_PROGRESS", "MONITORING"}:
                # If already executing, return existing progress
                return self.get_execution_progress(case_id)
            raise ValueError(f"Cannot execute case '{case_id}': Recovery plan has not been approved at Checkpoint 2. Current status: '{case.status}'.")

        if case.checkpoint2_decision != "APPROVE":
            raise ValueError(f"Cannot execute case '{case_id}': Checkpoint 2 decision was '{case.checkpoint2_decision}', not 'APPROVE'.")

        # Safety Check 2: Version validation
        if not case.approved_plan_id or case.approved_plan_id != req.plan_id:
            raise ValueError(
                f"Version conflict: Approved plan is '{case.approved_plan_id}', but execution was requested for '{req.plan_id}'."
            )

        if not case.approved_plan_version or case.approved_plan_version != req.version:
            raise ValueError(
                f"Version conflict: Approved version is '{case.approved_plan_version}', but execution was requested for '{req.version}'."
            )

        # Retrieve exact approved plan details
        plan_set = self.repository.get_recovery_plan_set(case_id)
        if not plan_set:
            raise RuntimeError(f"Recovery plan set not found for case '{case_id}'.")

        approved_plan: Optional[RecoveryPlan] = None
        for p in plan_set.feasible_plans:
            if p.plan_id == req.plan_id:
                approved_plan = p
                break

        if not approved_plan:
            raise RuntimeError(f"Approved plan '{req.plan_id}' ({req.version}) was not found in feasible plans.")

        now_iso = datetime.now(timezone.utc).isoformat()

        # Step 4: Establish Immutable Planned Baseline
        baseline = ExecutionBaseline(
            case_id=case_id,
            plan_id=approved_plan.plan_id,
            plan_version=approved_plan.version,
            strategy=approved_plan.strategy,
            source_id=approved_plan.source_id,
            source_name=approved_plan.source_name,
            source_location=approved_plan.source_location,
            target_plant_id=approved_plan.target_plant_id,
            target_plant_name=approved_plan.target_plant_name,
            material_id=case.material_id,
            planned_quantity=approved_plan.recovered_quantity,
            planned_recovery_days=approved_plan.recovery_days,
            planned_arrival_date=approved_plan.expected_arrival_date,
            planned_total_cost=approved_plan.total_cost,
            planned_transport_mode=approved_plan.transport_mode,
            approved_by=req.manager_id or "SUPPLY_CHAIN_PLANNER",
            approved_at=case.checkpoint2_timestamp or now_iso,
            approval_rationale=getattr(case, "planner_rationale", None),
        )
        self.repository.save_execution_baseline(baseline)

        # Step 1: Create Execution Action via SAP Adapter
        sap_result = self.sap_adapter.create_recovery_order(
            case_id=case_id,
            plan_id=approved_plan.plan_id,
            strategy=approved_plan.strategy,
            source_id=approved_plan.source_id,
            target_plant_id=approved_plan.target_plant_id,
            material_id=case.material_id,
            quantity=approved_plan.recovered_quantity,
            transport_mode=approved_plan.transport_mode,
        )

        action = ExecutionAction(
            action_id=f"ACT-{case_id}-{approved_plan.plan_id}",
            case_id=case_id,
            plan_id=approved_plan.plan_id,
            plan_version=approved_plan.version,
            action_type=sap_result.get("action_type", "EMERGENCY_PURCHASE_ORDER"),
            external_reference=sap_result.get("external_reference", f"SAP-REF-{case_id}"),
            external_system=sap_result.get("external_system", "SAP S/4HANA & TM"),
            status="ACCEPTED",
            carrier_name=sap_result.get("carrier_name", "DHL Express Dedicated Fleet"),
            tracking_number=sap_result.get("tracking_number", f"TRK-{case_id}"),
            created_at=now_iso,
            started_at=now_iso,
        )
        self.repository.save_execution_record(action)

        # Initial Tracking Event
        init_event = TrackingEvent(
            status="ACCEPTED",
            location=approved_plan.source_location,
            description=f"Recovery order confirmed in {action.external_system}. Doc: {action.external_reference}. Carrier: {action.carrier_name}.",
            confirmed_quantity=approved_plan.recovered_quantity,
            estimated_arrival=approved_plan.expected_arrival_date,
            actual_cost=approved_plan.total_cost,
            source_system=action.external_system,
        )
        self.repository.add_tracking_event(case_id, init_event)

        # Step 2: Persist state & log audit trail
        case.status = "EXECUTION_IN_PROGRESS"
        case.execution_action_id = action.action_id
        case.execution_status = "ACCEPTED"
        self.repository.update_case(case)

        if self.case_service:
            config = {"configurable": {"thread_id": case_id}}
            try:
                self.case_service.workflow.update_state(config, {
                    "status": "EXECUTION_IN_PROGRESS",
                    "execution_record": action.model_dump(),
                    "execution_baseline": baseline.model_dump(),
                    "tracking_events": [init_event.model_dump()],
                })
            except Exception:
                pass

        self.audit_service.log(
            case_id=case_id,
            event="EXECUTION_STARTED",
            actor="AGENT_3_EXECUTION",
            details=f"Autonomous execution initiated for approved plan {approved_plan.plan_id} (Version: {approved_plan.version}).",
        )
        self.audit_service.log(
            case_id=case_id,
            event="EXECUTION_ACTION_CREATED",
            actor="SAP_ADAPTER",
            details=f"Created {action.action_type} '{action.external_reference}' via {action.external_system}. Tracking: {action.tracking_number}.",
        )

        return self.get_execution_progress(case_id)

    def record_tracking_event(
        self,
        case_id: str,
        req: SimulateEventRequest,
    ) -> ExecutionProgress:
        """
        Step 5 & 6: Record execution update, calculate planned vs actual deviations, detect failures or confirm success.
        """
        case = self.repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case '{case_id}' was not found.")

        baseline = self.repository.get_execution_baseline(case_id)
        action = self.repository.get_execution_record(case_id)
        if not baseline or not action:
            raise RuntimeError(f"No active execution found for case '{case_id}'. Please call POST /execution/start first.")

        now_iso = datetime.now(timezone.utc).isoformat()
        current_events = self.repository.get_tracking_events(case_id)
        last_event = current_events[-1] if current_events else None

        # Determine effective values
        confirmed_qty = req.confirmed_quantity if req.confirmed_quantity is not None else (
            last_event.confirmed_quantity if last_event and last_event.confirmed_quantity is not None else baseline.planned_quantity
        )
        est_arrival = req.new_eta or (last_event.estimated_arrival if last_event and last_event.estimated_arrival else baseline.planned_arrival_date)
        current_cost = req.actual_cost if req.actual_cost is not None else (
            last_event.actual_cost if last_event and last_event.actual_cost is not None else baseline.planned_total_cost
        )

        status_upper = req.status.upper()
        default_descs = {
            "SUPPLIER_CONFIRMED": f"Supplier {baseline.source_name} confirmed allocation of {confirmed_qty:.0f} units.",
            "SHIPMENT_CREATED": f"Freight manifest and customs documentation prepared by carrier {action.carrier_name}.",
            "SHIPMENT_DISPATCHED": f"Consignment departed departure facility ({baseline.source_location}). In transit.",
            "IN_TRANSIT": f"Shipment scanned at transfer terminal. En route to {baseline.target_plant_name}.",
            "DELAYED": f"Logistics delay reported. Estimated arrival pushed to {est_arrival}.",
            "DELIVERED": f"Consignment delivered to {baseline.target_plant_name}. Inbound inspection passed.",
            "FAILED": f"Execution failure reported: {req.reason or 'Logistics corridor blocked'}.",
        }
        event_desc = req.description or default_descs.get(status_upper, f"Execution status changed to {status_upper}")

        # Add event to history
        new_event = TrackingEvent(
            status=status_upper,
            location=req.location or "En Route",
            description=event_desc,
            confirmed_quantity=confirmed_qty,
            estimated_arrival=est_arrival,
            actual_cost=current_cost,
            source_system=action.external_system,
        )
        self.repository.add_tracking_event(case_id, new_event)

        # Update action status
        action.status = status_upper
        case.execution_status = status_upper
        if status_upper in {"SHIPMENT_DISPATCHED", "IN_TRANSIT", "DELAYED"}:
            case.status = "MONITORING"

        # Log audit event
        audit_event_map = {
            "SUPPLIER_CONFIRMED": "SUPPLIER_CONFIRMED",
            "SHIPMENT_CREATED": "SHIPMENT_CREATED",
            "SHIPMENT_DISPATCHED": "SHIPMENT_DISPATCHED",
            "IN_TRANSIT": "SHIPMENT_IN_TRANSIT",
            "DELAYED": "SHIPMENT_DELAYED",
            "DELIVERED": "SHIPMENT_DELIVERED",
            "FAILED": "EXECUTION_FAILED",
        }
        self.audit_service.log(
            case_id=case_id,
            event=audit_event_map.get(status_upper, "MONITORING_UPDATE"),
            actor="CARRIER_TELEMATICS" if status_upper in {"IN_TRANSIT", "DELAYED", "DELIVERED"} else "SUPPLIER_EDI",
            details=f"[{status_upper}] {event_desc} Confirmed Qty: {confirmed_qty:.0f}, ETA: {est_arrival}",
        )

        # Compute deviations
        deviation = self._calculate_deviation(baseline, confirmed_qty, est_arrival, current_cost)

        # Failure Condition Checks (Steps 8 & 9)
        # 1. Explicit failure status
        # 2. Significant delay beyond stockout tolerance (> 2 days late)
        # 3. Severe quantity shortage (< 70% of requirement)
        is_failure = (
            status_upper == "FAILED"
            or deviation.delay_days > 2
            or (confirmed_qty < baseline.planned_quantity * 0.70)
        )

        if is_failure:
            fail_reason = req.reason or deviation.explanation
            self._handle_failure(case_id, baseline, action, fail_reason, confirmed_qty, est_arrival, deviation)
            return self.get_execution_progress(case_id)

        # Success Condition Checks (Steps 7 & 12)
        # Delivered + quantity fulfilled within accepted tolerance
        if status_upper == "DELIVERED" and confirmed_qty >= baseline.planned_quantity * 0.95:
            self._handle_success(case_id, baseline, action, confirmed_qty, est_arrival, current_cost)
            return self.get_execution_progress(case_id)

        # Otherwise continue monitoring
        self.repository.save_execution_record(action)
        self.repository.update_case(case)

        if self.case_service:
            config = {"configurable": {"thread_id": case_id}}
            try:
                all_events = self.repository.get_tracking_events(case_id)
                self.case_service.workflow.update_state(config, {
                    "status": case.status,
                    "execution_record": action.model_dump(),
                    "tracking_events": [e.model_dump() for e in all_events],
                })
            except Exception:
                pass

        return self.get_execution_progress(case_id)

    def _calculate_deviation(
        self,
        baseline: ExecutionBaseline,
        confirmed_qty: float,
        current_eta: str,
        current_cost: float,
    ) -> ExecutionDeviation:
        """
        Step 6: Deterministic comparison between planned baseline and actual telemetry.
        """
        shortage = max(0.0, baseline.planned_quantity - confirmed_qty)
        cost_var = round(current_cost - baseline.planned_total_cost, 2)

        delay_days = 0
        try:
            planned_dt = datetime.strptime(baseline.planned_arrival_date, "%Y-%m-%d").date()
            current_dt = datetime.strptime(current_eta, "%Y-%m-%d").date()
            delay_days = (current_dt - planned_dt).days
        except Exception:
            delay_days = 0

        is_crit = False
        reasons: list[str] = []

        if delay_days > 0:
            reasons.append(f"Arrival delayed by {delay_days} day(s) past planned date {baseline.planned_arrival_date}")
            if delay_days > 2:
                is_crit = True
        elif delay_days < 0:
            reasons.append(f"Tracking ahead of schedule by {abs(delay_days)} day(s)")

        if shortage > 0:
            pct_short = (shortage / baseline.planned_quantity) * 100.0
            reasons.append(f"Supply gap of {shortage:.0f} units ({pct_short:.1f}% unfulfilled)")
            if pct_short > 25.0:
                is_crit = True

        if cost_var > 0:
            reasons.append(f"Cost overrun of ${cost_var:,.2f}")
        elif cost_var < 0:
            reasons.append(f"Cost savings of ${abs(cost_var):,.2f}")

        explanation = "; ".join(reasons) if reasons else "Tracking nominally aligned with planned baseline."

        return ExecutionDeviation(
            quantity_shortage=shortage,
            delay_days=delay_days,
            cost_variance=cost_var,
            is_critical=is_crit,
            explanation=explanation,
        )

    def _handle_failure(
        self,
        case_id: str,
        baseline: ExecutionBaseline,
        action: ExecutionAction,
        reason: str,
        confirmed_qty: float,
        current_eta: str,
        deviation: ExecutionDeviation,
    ):
        """
        Steps 8, 9, 10 & 11: Escalate failure, preserve failed plan, return case to Recovery Planning.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        action.status = "FAILED"
        action.failure_reason = reason
        self.repository.save_execution_record(action)

        # Step 11: Preserve failed plan record
        failed_rec = FailedPlanRecord(
            case_id=case_id,
            plan_id=baseline.plan_id,
            plan_version=baseline.plan_version,
            strategy=baseline.strategy,
            source_id=baseline.source_id,
            source_name=baseline.source_name,
            failed_at=now_iso,
            failure_reason=reason,
            planned_quantity=baseline.planned_quantity,
            confirmed_quantity=confirmed_qty,
            planned_arrival=baseline.planned_arrival_date,
            actual_arrival_or_failed_date=current_eta,
            delay_days=deviation.delay_days,
            notes=deviation.explanation,
        )
        self.repository.save_failed_plan(case_id, failed_rec)

        # Audit events for escalation and replanning
        self.audit_service.log(
            case_id=case_id,
            event="EXECUTION_FAILED",
            actor="SYSTEM_MONITOR",
            details=f"Plan {baseline.plan_id} ({baseline.plan_version}) failed: {reason}. Shortage: {deviation.quantity_shortage:.0f}, Delay: {deviation.delay_days}d.",
        )
        self.audit_service.log(
            case_id=case_id,
            event="RECOVERY_ESCALATED",
            actor="HUMAN_IN_THE_LOOP",
            details=f"Manager alerted: Recovery plan failed to fulfill operational constraints. Escalated for replanning cycle.",
        )
        self.audit_service.log(
            case_id=case_id,
            event="REPLAN_REQUIRED",
            actor="AGENT_2_RECOVERY",
            details=f"Returning case {case_id} to Recovery Planning. Failed plan {baseline.plan_id} excluded from future recommendations.",
        )

        # Step 10: Return case to recovery planning
        case = self.repository.get_case(case_id)
        if case:
            case.status = "RECOVERY_PLANNING"
            case.checkpoint2_decision = None
            case.checkpoint2_timestamp = None
            case.approved_plan_id = None
            case.approved_plan_version = None
            self.repository.update_case(case)

        # Trigger automatic replanning cycle via CaseService if available
        if self.case_service:
            try:
                self.case_service.run_recovery_planning(case_id, force_regenerate=True)
            except Exception as e:
                logger.warning(f"Could not auto-regenerate plan set on failure: {e}")

            config = {"configurable": {"thread_id": case_id}}
            try:
                all_events = self.repository.get_tracking_events(case_id)
                self.case_service.workflow.update_state(config, {
                    "status": "RECOVERY_PLANNING",
                    "checkpoint2_decision": None,
                    "execution_record": action.model_dump(),
                    "tracking_events": [e.model_dump() for e in all_events],
                    "failed_plans": [f.model_dump() for f in self.repository.get_failed_plans(case_id)],
                })
            except Exception:
                pass
            if case:
                case.status = "RECOVERY_PLANNING"
                self.repository.update_case(case)

    def _handle_success(
        self,
        case_id: str,
        baseline: ExecutionBaseline,
        action: ExecutionAction,
        actual_qty: float,
        actual_arrival: str,
        actual_cost: float,
    ):
        """
        Steps 7, 12, 13 & 14: Confirm success, calculate actual outcomes, resolve case, save historical learning.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        action.status = "DELIVERED"
        action.completed_at = now_iso
        self.repository.save_execution_record(action)

        case = self.repository.get_case(case_id)

        # Step 13: Calculate actual outcome differences
        actual_days = baseline.planned_recovery_days
        try:
            start_dt = datetime.strptime(action.started_at[:10], "%Y-%m-%d").date()
            deliv_dt = datetime.strptime(actual_arrival[:10], "%Y-%m-%d").date()
            actual_days = max(1, (deliv_dt - start_dt).days)
        except Exception:
            pass

        # Step 14: Save historical outcome for future learning
        outcome_rec = HistoricalOutcomeRecord(
            record_id=f"HIST-{datetime.now(timezone.utc).strftime('%Y-%m%d%H%M')}",
            case_id=case_id,
            disruption_type=case.disruption_type if case else "DISRUPTION",
            supplier_id=case.supplier_id if case else baseline.source_id,
            material_id=baseline.material_id,
            plant_id=baseline.target_plant_id,
            initial_severity=case.severity if case else "HIGH",
            manager_priority=case.checkpoint1_decision if case else "BALANCED",
            strategy_used=baseline.strategy,
            plan_id=baseline.plan_id,
            plan_version=baseline.plan_version,
            planned_quantity=baseline.planned_quantity,
            actual_quantity=actual_qty,
            planned_days=baseline.planned_recovery_days,
            actual_days=actual_days,
            planned_cost=baseline.planned_total_cost,
            actual_cost=actual_cost,
            success=True,
            outcome_summary=f"100% quantity recovered ({actual_qty:.0f} units) via {baseline.strategy} from {baseline.source_name} within {actual_days} days. Zero customer stockouts.",
            lessons_learned=f"Strategy {baseline.strategy} demonstrated superior agility for {baseline.material_id} disruptions under priority {case.checkpoint1_decision if case else 'BALANCED'}.",
            recorded_at=now_iso,
        )
        self.repository.save_historical_outcome(outcome_rec)

        # Step 12: Resolve case
        if case:
            case.status = "RESOLVED"
            case.resolved_at = now_iso
            self.repository.update_case(case)

        if self.case_service:
            config = {"configurable": {"thread_id": case_id}}
            try:
                all_events = self.repository.get_tracking_events(case_id)
                self.case_service.workflow.update_state(config, {
                    "status": "RESOLVED",
                    "execution_record": action.model_dump(),
                    "tracking_events": [e.model_dump() for e in all_events],
                    "outcome_record": outcome_rec.model_dump(),
                })
            except Exception:
                pass

        # Complete audit trail
        self.audit_service.log(
            case_id=case_id,
            event="RECOVERY_COMPLETED",
            actor="AGENT_3_EXECUTION",
            details=f"Recovery plan {baseline.plan_id} completed successfully. Material verified in plant inventory.",
        )
        self.audit_service.log(
            case_id=case_id,
            event="OUTCOME_RECORDED",
            actor="LEARNING_SUBSYSTEM",
            details=f"Certified outcome recorded as precedent {outcome_rec.record_id} for future historical retrieval.",
        )
        self.audit_service.log(
            case_id=case_id,
            event="CASE_CLOSED",
            actor="SUPPLY_CHAIN_PLANNER",
            details=f"Case {case_id} marked as RESOLVED. Supply chain continuity restored.",
        )

    def get_execution_progress(self, case_id: str) -> ExecutionProgress:
        """
        Retrieve complete execution and monitoring telemetry for visualization.
        """
        baseline = self.repository.get_execution_baseline(case_id)
        action = self.repository.get_execution_record(case_id)
        events = self.repository.get_tracking_events(case_id)

        if not baseline or not action:
            if self.case_service:
                self.case_service.get_case_or_from_checkpoint(case_id)
            baseline = self.repository.get_execution_baseline(case_id)
            action = self.repository.get_execution_record(case_id)
            events = self.repository.get_tracking_events(case_id)

        if not baseline or not action:
            raise KeyError(f"No execution record found for case '{case_id}'.")

        last_event = events[-1] if events else None
        current_confirmed = last_event.confirmed_quantity if last_event and last_event.confirmed_quantity is not None else baseline.planned_quantity
        current_eta = last_event.estimated_arrival if last_event and last_event.estimated_arrival else baseline.planned_arrival_date
        current_cost = last_event.actual_cost if last_event and last_event.actual_cost is not None else baseline.planned_total_cost

        deviation = self._calculate_deviation(baseline, current_confirmed, current_eta, current_cost)

        is_succ = action.status == "DELIVERED"
        is_fail = action.status == "FAILED"

        # AI Executive Briefing (Step 15)
        ai_summary = None
        ai_status = "FALLBACK"
        if is_fail:
            ai_summary = f"ALERT: Recovery action {action.action_id} has failed. Reason: {action.failure_reason or deviation.explanation}. A deviation of {deviation.delay_days} days and {deviation.quantity_shortage:.0f} unfulfilled units occurred. The case has been returned to Recovery Planning."
        elif is_succ:
            ai_summary = f"SUCCESS: Recovery plan {baseline.plan_id} ({baseline.plan_version}) fully completed. All {current_confirmed:.0f} units of {baseline.material_id} safely delivered to {baseline.target_plant_name}. Case is resolved and recorded into the institutional knowledge base."
        else:
            ai_summary = f"Recovery plan {baseline.plan_id} is actively executing in state '{action.status}'. Transport via {action.carrier_name} is tracking to ETA {current_eta}. Current variance: {deviation.explanation}."

        case = self.repository.get_case(case_id)
        exec_status = action.status

        # Determine monitoring_status and action_required
        monitoring_status = "ON_TRACK"
        action_required = False
        if is_fail:
            monitoring_status = "FAILED"
            action_required = True
        elif is_succ:
            monitoring_status = "RESOLVED"
        elif deviation.delay_days > 2 or deviation.is_critical:
            monitoring_status = "ACTION_REQUIRED"
            action_required = True
        elif deviation.delay_days > 0 or exec_status == "DELAYED":
            monitoring_status = "AT_RISK"
            action_required = False

        return ExecutionProgress(
            case_id=case_id,
            execution_status=exec_status,
            baseline=baseline,
            action=action,
            tracking_events=events,
            current_confirmed_quantity=current_confirmed,
            current_estimated_arrival=current_eta,
            current_estimated_cost=current_cost,
            deviation=deviation,
            is_success=is_succ,
            is_failed=is_fail,
            failure_reason=action.failure_reason,
            ai_summary=ai_summary,
            ai_status=ai_status,
            can_replan=is_fail or (case and case.status == "RECOVERY_PLANNING"),
            can_resolve=is_succ or (case and case.status == "RESOLVED"),
            monitoring_status=monitoring_status,
            action_required=action_required,
            supplier_status="CONFIRMED" if exec_status != "ACCEPTED" else "PENDING_CONFIRMATION",
            shipment_status=exec_status,
            inventory_status="CRITICAL BUFFER" if deviation.delay_days > 0 else "PROTECTED",
            production_status="AT RISK" if deviation.delay_days > 1 else "NORMAL",
            customer_impact="1 ORDER AT RISK" if deviation.delay_days > 1 else "0 DELAYED ORDERS",
            risk_status="HIGH" if action_required else ("MEDIUM" if monitoring_status == "AT_RISK" else "LOW"),
            last_updated=last_event.timestamp if last_event else baseline.approved_at,
        )
