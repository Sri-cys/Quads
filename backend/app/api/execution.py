import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_repository, get_execution_service
from app.models.execution import (
    ExecutionProgress,
    ExecutePlanRequest,
    SimulateEventRequest,
    HistoricalOutcomeRecord,
    FailedPlanRecord,
)
from app.models.impact import ErrorResponse

logger = logging.getLogger("quads.api.execution")
router = APIRouter(prefix="/api/v1", tags=["Phase 3: Execution, Monitoring & Learning"])


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
    - Updates case status to EXECUTION_IN_PROGRESS and creates audit event.
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
    - SUPPLIER_CONFIRMED
    - SHIPMENT_CREATED
    - SHIPMENT_DISPATCHED
    - IN_TRANSIT
    - DELAYED
    - DELIVERED
    - FAILED

    Determines if tolerance has been breached (triggering failure and replanning loop)
    or if material has arrived within tolerance (triggering success, outcome recording, and case resolution).
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


@router.get(
    "/cases/{case_id}/execution/failed-plans",
    response_model=list[FailedPlanRecord],
)
def get_failed_plans(
    case_id: str,
    repo=Depends(get_repository),
):
    """
    Retrieve historical failed recovery plans preserved for this case.
    """
    return repo.get_failed_plans(case_id=case_id)


@router.get(
    "/cases/{case_id}/execution/outcomes",
    response_model=list[HistoricalOutcomeRecord],
)
def get_case_historical_outcomes(
    case_id: str,
    repo=Depends(get_repository),
):
    """
    Retrieve certified post-resolution outcome records for this case.
    """
    return repo.get_historical_outcomes(case_id=case_id)
