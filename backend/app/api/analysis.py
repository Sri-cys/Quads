import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.dependencies import get_repository, get_case_service
from app.models.impact import ImpactAnalysis, ErrorResponse

logger = logging.getLogger("quads.api.analysis")
router = APIRouter(prefix="/api/v1", tags=["Impact Analysis"])


@router.post(
    "/cases/{case_id}/analyze",
    response_model=ImpactAnalysis,
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        409: {"model": ErrorResponse, "description": "Conflict in case workflow state"},
        503: {"model": ErrorResponse, "description": "Repository or storage unavailable"},
    },
)
def run_impact_analysis(
    case_id: str,
    case_service=Depends(get_case_service),
    repo=Depends(get_repository),
):
    """
    Run Agent 1 (Impact Analysis).
    Executes triage -> deterministic calculations -> Gemini executive explanation.
    Halts immediately before Human Checkpoint 1.
    """
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )

    # 409 if case already submitted Checkpoint 1
    if case.status in {"CHECKPOINT_APPROVED", "RESOLVED"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "WORKFLOW_STATE_CONFLICT",
                "message": f"Case '{case_id}' has already been approved at Checkpoint 1 and cannot be re-analyzed",
            },
        )

    try:
        analysis = case_service.run_impact_analysis(case_id)
        return analysis
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
    except RuntimeError as re:
        logger.error(f"Runtime error during impact analysis: {re}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "ANALYSIS_FAILED", "message": "Failed to complete impact calculation"},
        )
    except Exception as e:
        logger.critical(f"Critical error during analysis: {e}", exc_info=True)
        # If repo failure
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "REPOSITORY_UNAVAILABLE", "message": "Master data repository is currently unavailable"},
        )


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
                "message": f"Impact analysis has not been executed yet for case '{case_id}'. Please run /analyze first.",
            },
        )
    return analysis
