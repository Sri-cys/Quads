import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_repository, get_execution_service, get_case_service
from app.models.execution import (
    ExecutionProgress,
    ExecutePlanRequest,
    SimulateEventRequest,
    HistoricalOutcomeRecord,
    FailedPlanRecord,
)
from app.models.impact import ErrorResponse, AuditEvent
from app.workflow.state_machine import CaseState, normalize_state

logger = logging.getLogger("quads.api.execution")
router = APIRouter(prefix="/api/v1", tags=["Execution, Monitoring & Learning"])


@router.post(
    "/cases/{case_id}/execution/start",
    response_model=ExecutionProgress,
    responses={
        404: {"model": ErrorResponse, "description": "Case or approved plan not found"},
        409: {"model": ErrorResponse, "description": "Execution safety violation or version conflict"},
        422: {"model": ErrorResponse, "description": "Invalid execution request parameters"},
    },
)
def start_execution(
    case_id: str,
    req: ExecutePlanRequest,
    execution_service=Depends(get_execution_service),
):
    """
    Initiate execution of the exact approved recovery plan version.
    - Validates that Checkpoint 2 was approved.
    - Validates that requested plan_id and version match approved decision.
    - Locks the execution baseline.
    - Generates external order action in SAP S/4HANA & TM.
    - Updates case status to EXECUTION and creates audit event.
    """
    try:
        progress = execution_service.start_execution(case_id=case_id, req=req)
        return progress
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RESOURCE_NOT_FOUND", "message": str(ke)},
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "EXECUTION_SAFETY_CONFLICT", "message": str(ve)},
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "EXECUTION_STATE_ERROR", "message": str(re)},
        )
    except Exception as e:
        logger.error(f"Error starting execution for case {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "EXECUTION_INITIATION_FAILED", "message": str(e)},
        )


@router.get(
    "/cases/{case_id}/execution/progress",
    response_model=ExecutionProgress,
    responses={
        404: {"model": ErrorResponse, "description": "Case or execution record not found"},
    },
)
def get_execution_progress(
    case_id: str,
    execution_service=Depends(get_execution_service),
):
    """
    Fetch complete execution baseline, telemetry events, and quantified planned vs actual deviations.
    """
    try:
        return execution_service.get_execution_progress(case_id=case_id)
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "EXECUTION_NOT_FOUND", "message": str(ke)},
        )
    except Exception as e:
        logger.error(f"Error fetching execution progress for case {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "EXECUTION_PROGRESS_FAILED", "message": str(e)},
        )


@router.get(
    "/cases/{case_id}/execution",
    response_model=ExecutionProgress,
)
def get_execution_alias(
    case_id: str,
    execution_service=Depends(get_execution_service),
):
    """Alias for GET /cases/{case_id}/execution per specification Section 15."""
    return get_execution_progress(case_id=case_id, execution_service=execution_service)


@router.post(
    "/cases/{case_id}/execution/event",
    response_model=ExecutionProgress,
    responses={
        404: {"model": ErrorResponse, "description": "Case or execution not found"},
        409: {"model": ErrorResponse, "description": "Execution conflict"},
    },
)
def record_execution_event(
    case_id: str,
    req: SimulateEventRequest,
    execution_service=Depends(get_execution_service),
):
    """
    Record incoming logistics telemetry / carrier status update:
    - SUPPLIER_CONFIRMED, SHIPMENT_CREATED, SHIPMENT_DISPATCHED, IN_TRANSIT, DELAYED, DELIVERED, FAILED
    """
    try:
        progress = execution_service.record_tracking_event(case_id=case_id, req=req)
        return progress
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RESOURCE_NOT_FOUND", "message": str(ke)},
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "EXECUTION_CONFLICT", "message": str(re)},
        )
    except Exception as e:
        logger.error(f"Error recording execution event for case {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "EXECUTION_EVENT_FAILED", "message": str(e)},
        )


@router.post(
    "/cases/{case_id}/replan",
)
def replan_case_endpoint(
    case_id: str,
    payload: dict = {},
    case_service=Depends(get_case_service),
):
    """
    Initiate replanning cycle while active approved plan continues execution.
    Transitions case to REPLANNING -> AGENT2_RUNNING.
    """
    reason = payload.get("reason", "Replanning triggered due to execution deviation.")
    try:
        updated_case = case_service.replan_case(case_id, reason)
        return {
            "case_id": case_id,
            "status": updated_case.status,
            "planning_cycle": updated_case.planning_cycle,
            "message": f"Replanning initiated for cycle {updated_case.planning_cycle}.",
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "REPLAN_FAILED", "message": str(e)})


@router.post(
    "/cases/{case_id}/execution/replan",
)
def execution_replan_alias(
    case_id: str,
    payload: dict = {},
    case_service=Depends(get_case_service),
):
    """Alias for POST /cases/{case_id}/replan."""
    return replan_case_endpoint(case_id=case_id, payload=payload, case_service=case_service)


@router.get(
    "/cases/{case_id}/execution/failed-plans",
    response_model=list[FailedPlanRecord],
)
def get_failed_plans(
    case_id: str,
    repo=Depends(get_repository),
):
    """Retrieve historical failed recovery plans preserved for this case."""
    return repo.get_failed_plans(case_id=case_id)


@router.get(
    "/cases/{case_id}/execution/outcomes",
    response_model=list[HistoricalOutcomeRecord],
)
def get_case_historical_outcomes(
    case_id: str,
    repo=Depends(get_repository),
):
    """Retrieve certified post-resolution outcome records for this case."""
    return repo.get_historical_outcomes(case_id=case_id)


@router.get(
    "/cases/{case_id}/outcome",
)
def get_case_outcome_locked_check(
    case_id: str,
    repo=Depends(get_repository),
):
    """
    Specification Section 10 & 15:
    GET /cases/:id/outcome is 403/locked until case status is RESOLVED.
    """
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "CASE_NOT_FOUND", "message": f"Case {case_id} not found"})

    curr_state = normalize_state(case.status)
    if curr_state != CaseState.RESOLVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "OUTCOME_LOCKED",
                "message": f"Outcome destination is locked until case is RESOLVED. Current case status: '{curr_state.value}'.",
            },
        )

    outcomes = repo.get_historical_outcomes(case_id=case_id)
    return {
        "case_id": case_id,
        "status": "RESOLVED",
        "resolved_at": case.resolved_at,
        "outcomes": outcomes,
    }


@router.get(
    "/cases/{case_id}/audit",
    response_model=list[AuditEvent],
)
def get_audit_trail(
    case_id: str,
    repo=Depends(get_repository),
):
    """Retrieve immutable audit event trail for a case."""
    return repo.get_audit_events(case_id=case_id)
