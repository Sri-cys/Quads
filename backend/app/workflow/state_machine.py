"""
QUADS State Machine & Transition Engine (v2)
Centralized source of truth for all case workflow states, transitions, guards,
and audit hooks according to Specification Section 3.
"""

from enum import Enum
from typing import Optional, Any, Callable
from datetime import datetime, timezone
import logging

logger = logging.getLogger("quads.workflow.state_machine")


class CaseState(str, Enum):
    CASE_CREATED = "CASE_CREATED"
    CASE_OVERVIEW = "CASE_OVERVIEW"
    IMPACT_ANALYSIS_PENDING = "IMPACT_ANALYSIS_PENDING"
    IMPACT_ANALYSIS_RUNNING = "IMPACT_ANALYSIS_RUNNING"
    IMPACT_ANALYSIS_COMPLETED = "IMPACT_ANALYSIS_COMPLETED"
    IMPACT_ANALYSIS_FAILED = "IMPACT_ANALYSIS_FAILED"
    PRIORITY_PENDING = "PRIORITY_PENDING"
    PRIORITY_SAVED = "PRIORITY_SAVED"
    AGENT2_RUNNING = "AGENT2_RUNNING"
    AGENT2_COMPLETED = "AGENT2_COMPLETED"
    AGENT2_FAILED = "AGENT2_FAILED"
    AGENT3_RUNNING = "AGENT3_RUNNING"
    AGENT3_COMPLETED = "AGENT3_COMPLETED"
    AGENT3_FAILED = "AGENT3_FAILED"
    DECISION_PENDING = "DECISION_PENDING"
    PLAN_APPROVED = "RECOVERY_APPROVED"
    PLAN_MODIFIED = "PLAN_MODIFIED"
    PLAN_REJECTED = "PLAN_REJECTED"
    EXECUTION = "EXECUTION"
    AT_RISK = "AT_RISK"
    REPLANNING = "REPLANNING"
    RESOLVED = "RESOLVED"


LEGACY_STATE_MAPPING: dict[str, CaseState] = {
    "CREATED": CaseState.CASE_OVERVIEW,
    "TRIAGED": CaseState.CASE_OVERVIEW,
    "ANALYZED": CaseState.IMPACT_ANALYSIS_COMPLETED,
    "AWAITING_CHECKPOINT_1": CaseState.IMPACT_ANALYSIS_COMPLETED,
    "CHECKPOINT_APPROVED": CaseState.PRIORITY_SAVED,
    "RECOVERY_PLANNING": CaseState.DECISION_PENDING,
    "AWAITING_CHECKPOINT_2": CaseState.DECISION_PENDING,
    "RECOVERY_APPROVED": CaseState.PLAN_APPROVED,
    "PLAN_APPROVED": CaseState.PLAN_APPROVED,
    "EXECUTION_IN_PROGRESS": CaseState.EXECUTION,
    "MONITORING": CaseState.EXECUTION,
    "ON_TRACK": CaseState.EXECUTION,
    "ACTION_REQUIRED": CaseState.AT_RISK,
    "DELIVERED": CaseState.RESOLVED,
    "RESOLVED": CaseState.RESOLVED,
}


def normalize_state(raw_state: Optional[str]) -> CaseState:
    """Normalize any raw or legacy state string to a valid CaseState."""
    if not raw_state:
        return CaseState.CASE_OVERVIEW
    upper = raw_state.upper()
    try:
        return CaseState(upper)
    except ValueError:
        return LEGACY_STATE_MAPPING.get(upper, CaseState.CASE_OVERVIEW)


# Valid Transitions Table: (from_state, event) -> (to_state, guard_fn)
# guard_fn receives (case, payload) -> (bool, error_message)
TRANSITIONS: dict[tuple[CaseState, str], CaseState] = {
    # Case Creation & Overview
    (CaseState.CASE_CREATED, "case_opened"): CaseState.CASE_OVERVIEW,
    (CaseState.CASE_CREATED, "start_impact_analysis"): CaseState.IMPACT_ANALYSIS_RUNNING,
    (CaseState.CASE_OVERVIEW, "start_impact_analysis"): CaseState.IMPACT_ANALYSIS_RUNNING,
    (CaseState.IMPACT_ANALYSIS_PENDING, "start_impact_analysis"): CaseState.IMPACT_ANALYSIS_RUNNING,
    
    # Impact Analysis (Agent 1)
    (CaseState.IMPACT_ANALYSIS_RUNNING, "agent1_success"): CaseState.IMPACT_ANALYSIS_COMPLETED,
    (CaseState.IMPACT_ANALYSIS_RUNNING, "agent1_error"): CaseState.IMPACT_ANALYSIS_FAILED,
    (CaseState.IMPACT_ANALYSIS_RUNNING, "agent1_timeout"): CaseState.IMPACT_ANALYSIS_FAILED,
    (CaseState.IMPACT_ANALYSIS_FAILED, "retry_impact_analysis"): CaseState.IMPACT_ANALYSIS_RUNNING,
    (CaseState.IMPACT_ANALYSIS_COMPLETED, "proceed_to_priority"): CaseState.PRIORITY_PENDING,

    # Priority Checkpoint 1
    (CaseState.PRIORITY_PENDING, "confirm_priority"): CaseState.AGENT2_RUNNING,
    (CaseState.IMPACT_ANALYSIS_COMPLETED, "confirm_priority"): CaseState.AGENT2_RUNNING,  # direct one-transaction transition
    (CaseState.PRIORITY_SAVED, "confirm_priority"): CaseState.AGENT2_RUNNING,
    (CaseState.AGENT2_RUNNING, "confirm_priority"): CaseState.AGENT2_RUNNING,
    (CaseState.AGENT3_RUNNING, "confirm_priority"): CaseState.AGENT2_RUNNING,
    (CaseState.AGENT3_COMPLETED, "confirm_priority"): CaseState.AGENT2_RUNNING,
    (CaseState.AGENT3_FAILED, "confirm_priority"): CaseState.AGENT2_RUNNING,
    (CaseState.DECISION_PENDING, "confirm_priority"): CaseState.AGENT2_RUNNING,

    # Agent 2 (Recovery Plan Generation)
    (CaseState.AGENT2_RUNNING, "agent2_success"): CaseState.AGENT2_COMPLETED,
    (CaseState.AGENT3_RUNNING, "agent2_success"): CaseState.AGENT3_RUNNING,
    (CaseState.DECISION_PENDING, "agent2_success"): CaseState.DECISION_PENDING,
    (CaseState.AGENT2_RUNNING, "agent2_error"): CaseState.AGENT2_FAILED,
    (CaseState.AGENT2_RUNNING, "agent2_timeout"): CaseState.AGENT2_FAILED,
    (CaseState.AGENT2_FAILED, "retry_agent2"): CaseState.AGENT2_RUNNING,
    (CaseState.AGENT2_RUNNING, "auto_chain_agent3"): CaseState.AGENT3_RUNNING,
    (CaseState.AGENT2_COMPLETED, "auto_chain_agent3"): CaseState.AGENT3_RUNNING,
    (CaseState.AGENT3_RUNNING, "auto_chain_agent3"): CaseState.AGENT3_RUNNING,
    (CaseState.DECISION_PENDING, "auto_chain_agent3"): CaseState.AGENT3_RUNNING,

    # Agent 3 (Evaluation, Cost, Risk, Feasibility)
    (CaseState.AGENT3_RUNNING, "agent3_success"): CaseState.DECISION_PENDING,  # auto-chains to DECISION_PENDING
    (CaseState.DECISION_PENDING, "agent3_success"): CaseState.DECISION_PENDING,
    (CaseState.AGENT3_RUNNING, "agent3_error"): CaseState.AGENT3_FAILED,
    (CaseState.AGENT3_RUNNING, "agent3_timeout"): CaseState.AGENT3_FAILED,
    (CaseState.AGENT3_FAILED, "retry_agent3"): CaseState.AGENT3_RUNNING,
    (CaseState.AGENT3_COMPLETED, "proceed_to_decision"): CaseState.DECISION_PENDING,

    # Checkpoint 2 (Human Final Decision)
    (CaseState.DECISION_PENDING, "approve_plan"): CaseState.PLAN_APPROVED,
    (CaseState.DECISION_PENDING, "modify_plan"): CaseState.AGENT3_RUNNING,
    (CaseState.DECISION_PENDING, "modify_plan_structural"): CaseState.AGENT2_RUNNING,
    (CaseState.DECISION_PENDING, "reject_plan"): CaseState.AGENT2_RUNNING,

    # Execution & Monitoring
    (CaseState.PLAN_APPROVED, "start_execution"): CaseState.EXECUTION,
    (CaseState.EXECUTION, "deviation_detected"): CaseState.AT_RISK,
    (CaseState.AT_RISK, "action_resolved"): CaseState.EXECUTION,
    (CaseState.AT_RISK, "replan"): CaseState.AGENT2_RUNNING,
    (CaseState.EXECUTION, "replan"): CaseState.AGENT2_RUNNING,
    (CaseState.EXECUTION, "delivered_and_closed"): CaseState.RESOLVED,
    (CaseState.AT_RISK, "delivered_and_closed"): CaseState.RESOLVED,
}


class InvalidStateTransitionError(ValueError):
    def __init__(self, current_state: str, event: str, reason: str):
        super().__init__(f"Illegal transition from '{current_state}' via event '{event}': {reason}")
        self.current_state = current_state
        self.event = event
        self.reason = reason


def validate_and_transition(
    case: Any,
    event: str,
    actor: str,
    payload: Optional[dict[str, Any]] = None,
    audit_service: Optional[Any] = None,
) -> CaseState:
    """
    Centralized state transition validation engine.
    Checks state transition table and specific guards.
    Returns target CaseState.
    Raises InvalidStateTransitionError on violation (triggers HTTP 409).
    """
    payload = payload or {}
    current_state = normalize_state(getattr(case, "status", None))
    key = (current_state, event)

    if key not in TRANSITIONS:
        msg = f"Transition not permitted from status '{current_state.value}' on event '{event}'."
        if audit_service:
            case_id = getattr(case, "case_id", "UNKNOWN")
            audit_service.log(
                case_id=case_id,
                event="ILLEGAL_TRANSITION_BLOCKED",
                actor=actor,
                details=f"Blocked transition from '{current_state.value}' via '{event}'. Reason: Not in transition table.",
            )
        raise InvalidStateTransitionError(current_state.value, event, msg)

    target_state = TRANSITIONS[key]

    # Specific Guards
    if event == "confirm_priority":
        priority = payload.get("priority", "").upper()
        from app.config.severity_rules import VALID_CHECKPOINT_PRIORITIES
        if priority not in VALID_CHECKPOINT_PRIORITIES:
            raise InvalidStateTransitionError(
                current_state.value, event, f"Priority '{priority}' not in {VALID_CHECKPOINT_PRIORITIES}"
            )

    elif event == "approve_plan":
        plan_id = payload.get("plan_id")
        comment = payload.get("comment", "").strip()
        is_feasible = payload.get("is_feasible", True)
        if not plan_id:
            raise InvalidStateTransitionError(current_state.value, event, "plan_id is required for approval.")
        if not comment:
            raise InvalidStateTransitionError(current_state.value, event, "Mandatory approval comment is required.")
        if not is_feasible:
            raise InvalidStateTransitionError(current_state.value, event, "Cannot approve an infeasible recovery plan.")

    elif event == "reject_plan":
        reason = payload.get("reason", "").strip()
        if not reason:
            raise InvalidStateTransitionError(current_state.value, event, "Mandatory rejection reason is required.")

    # Record successful transition in audit if service provided
    if audit_service:
        case_id = getattr(case, "case_id", "UNKNOWN")
        audit_service.log(
            case_id=case_id,
            event=f"STATE_TRANSITION_{event.upper()}",
            actor=actor,
            details=f"State transitioned from {current_state.value} -> {target_state.value}",
        )

    # Mutate case.status if object allows it
    if hasattr(case, "status"):
        case.status = target_state.value

    return target_state
