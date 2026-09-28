import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.dependencies import get_repository, get_case_service
from app.models.impact import ImpactAnalysis, ErrorResponse
from app.models.case import Case

logger = logging.getLogger("quads.api.analysis")
router = APIRouter(prefix="/api/v1", tags=["Impact Analysis"])


@router.post(
    "/cases/{case_id}/impact/start",
    response_model=Case,
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        409: {"model": ErrorResponse, "description": "Conflict in case workflow state"},
    },
)
def start_impact_analysis(
    case_id: str,
    case_service=Depends(get_case_service),
):
    """
    One-click entry to start Agent 1 (Impact Analysis).
    Transitions state to IMPACT_ANALYSIS_RUNNING and launches background processing.
    Idempotent: double-clicking or re-calling returns the active run.
    """
    try:
        updated_case = case_service.start_impact_analysis(case_id)
        return updated_case
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": str(ke)},
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "INVALID_STATE_TRANSITION", "message": str(ve)},
        )
    except Exception as e:
        logger.error(f"Error starting impact analysis for {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "ANALYSIS_FAILED", "message": f"Failed to start analysis: {str(e)}"},
        )


@router.post(
    "/cases/{case_id}/analyze",
    response_model=ImpactAnalysis,
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        409: {"model": ErrorResponse, "description": "Conflict in case workflow state"},
        503: {"model": ErrorResponse, "description": "Repository or storage unavailable"},
    },
)
def run_impact_analysis_compat(
    case_id: str,
    case_service=Depends(get_case_service),
    repo=Depends(get_repository),
):
    """
    Backward-compatible synchronous wrapper for Agent 1.
    Starts analysis if not started, waits for completion, and returns the analysis.
    """
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )

    # Check if analysis already exists
    existing = repo.get_impact_analysis(case_id)
    if existing:
        return existing

    try:
        case_service.start_impact_analysis(case_id)
        # Wait up to 16 seconds for completion
        from app.workflow.state_machine import normalize_state, CaseState
        for _ in range(160):
            time.sleep(0.1)
            res = repo.get_impact_analysis(case_id)
            c = repo.get_case(case_id)
            if res and c and normalize_state(c.status) == CaseState.IMPACT_ANALYSIS_COMPLETED:
                return res
            if c and "FAILED" in c.status:
                raise RuntimeError(c.last_error or "Analysis failed during execution")
        
        res = repo.get_impact_analysis(case_id)
        if res:
            return res
        raise TimeoutError("Analysis timed out waiting for completion")
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case '{case_id}' was not found"},
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "INVALID_STATE_TRANSITION", "message": str(ve)},
        )
    except Exception as e:
        logger.error(f"Error during impact analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "ANALYSIS_FAILED", "message": str(e)},
        )


@router.post(
    "/cases/{case_id}/impact/retry",
    response_model=Case,
)
def retry_impact_analysis(
    case_id: str,
    case_service=Depends(get_case_service),
):
    """Retry Agent 1 after a failure."""
    try:
        return case_service.retry_impact_analysis(case_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "RETRY_FAILED", "message": str(e)})


@router.post(
    "/cases/{case_id}/impact/proceed",
    response_model=Case,
)
def proceed_to_priority(
    case_id: str,
    case_service=Depends(get_case_service),
):
    """Advance case from IMPACT_ANALYSIS_COMPLETED to PRIORITY_PENDING."""
    try:
        return case_service.proceed_to_priority(case_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "TRANSITION_FAILED", "message": str(e)})


@router.get(
    "/cases/{case_id}/impact/status",
)
def get_impact_status(
    case_id: str,
    repo=Depends(get_repository),
):
    """Pollable endpoint for Agent 1 real progress telemetry."""
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )
    return {
        "case_id": case_id,
        "status": case.status,
        "active_step": case.active_step,
        "steps_progress": case.steps_progress,
        "last_error": case.last_error,
        "current_stage": case.current_stage,
    }


@router.get(
    "/cases/{case_id}/impact",
    response_model=ImpactAnalysis,
    responses={
        404: {"model": ErrorResponse, "description": "Case or analysis not found"},
    },
)
def get_impact_analysis(
    case_id: str,
    repo=Depends(get_repository),
):
    """
    Fetch the completed impact analysis result for a case.
    """
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )

    analysis = repo.get_impact_analysis(case_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ANALYSIS_NOT_FOUND",
                "message": f"Impact analysis has not been executed yet for case '{case_id}'. Please run /impact/start first.",
            },
        )
    return analysis
