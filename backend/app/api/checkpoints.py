import logging
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_repository, get_case_service
from app.models.case import CheckpointRequest, CheckpointResponse
from app.models.impact import ErrorResponse

logger = logging.getLogger("quads.api.checkpoints")
router = APIRouter(prefix="/api/v1", tags=["Human Checkpoints"])


@router.post(
    "/cases/{case_id}/checkpoint1",
    response_model=CheckpointResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        409: {"model": ErrorResponse, "description": "Out-of-order execution or duplicate checkpoint"},
        422: {"model": ErrorResponse, "description": "Invalid recovery priority"},
    },
)
def submit_checkpoint_1(
    case_id: str,
    req: CheckpointRequest,
    case_service=Depends(get_case_service),
    repo=Depends(get_repository),
):
    """
    Submit Human Checkpoint 1 Priority Decision (TIME, COST, RISK, BALANCED).
    Persists decision, records audit event, and halts workflow at Phase 1 boundary.
    Agent 2 (Recovery Planning) is NOT executed.
    """
    case = case_service.get_case_or_from_checkpoint(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )

    # 409 if checkpoint already submitted
    if case.status == "CHECKPOINT_APPROVED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "CHECKPOINT_ALREADY_APPROVED",
                "message": f"Checkpoint 1 has already been approved for case '{case_id}' with decision '{case.checkpoint1_decision}'",
            },
        )

    # 409 if analysis has not run yet
    analysis = repo.get_impact_analysis(case_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "ANALYSIS_REQUIRED",
                "message": f"Impact analysis must be executed before submitting Checkpoint 1 for case '{case_id}'",
            },
        )

    try:
        updated_case = case_service.submit_checkpoint1(case_id, req.priority)
        return CheckpointResponse(
            case_id=case_id,
            status=updated_case.status,
            priority=req.priority,
            message="Checkpoint 1 approved.",
            phase2_status="Recovery Planning is ready for Phase 2.",
        )
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
        logger.error(f"Error submitting checkpoint 1: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CHECKPOINT_FAILED", "message": "Failed to process Checkpoint 1 approval"},
        )
