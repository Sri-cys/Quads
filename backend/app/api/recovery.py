import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_case_service, get_repository
from app.models.impact import ErrorResponse
from app.models.recovery import (
    RecoveryPlanSet,
    ManagerConstraints,
    PlanModifyRequest,
    Checkpoint2Request,
    Checkpoint2Response,
)

logger = logging.getLogger("quads.api.recovery")
router = APIRouter(prefix="/api/v1", tags=["Recovery Planning & Optimization (Phase 2)"])


@router.post(
    "/cases/{case_id}/recovery/plan",
    response_model=RecoveryPlanSet,
    responses={
        404: {"model": ErrorResponse, "description": "Case not found"},
        409: {"model": ErrorResponse, "description": "Checkpoint 1 not yet approved or workflow conflict"},
        500: {"model": ErrorResponse, "description": "Recovery planning calculation error"},
    },
)
def generate_recovery_plans(
    case_id: str,
    constraints: Optional[ManagerConstraints] = None,
    force_regenerate: bool = Query(default=False, description="Force re-running recovery planning discovery"),
    case_service=Depends(get_case_service),
    repo=Depends(get_repository),
):
    """
    Agent 2: Recovery Planning & Optimization.
    Ingests Phase 1 disruption impact, Checkpoint 1 priority (TIME/COST/RISK/BALANCED),
    and manager constraints. Discovers real supply alternatives, checks hard constraints,
    computes deterministic scores, and outputs ranked feasible & rejected options.
    """
    case = case_service.get_case_or_from_checkpoint(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )

    if not case.checkpoint1_decision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "CHECKPOINT_1_REQUIRED",
                "message": f"Human Checkpoint 1 must be approved before Phase 2 Recovery Planning can begin for case '{case_id}'",
            },
        )

    try:
        plan_set = case_service.run_recovery_planning(
            case_id=case_id,
            constraints=constraints,
            force_regenerate=force_regenerate,
        )
        return plan_set
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
        logger.error(f"Error during recovery planning for case {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "RECOVERY_PLANNING_FAILED", "message": f"Failed to generate recovery options: {str(e)}"},
        )


@router.get(
    "/cases/{case_id}/recovery/plan",
    response_model=RecoveryPlanSet,
    responses={
        404: {"model": ErrorResponse, "description": "Case or recovery plan not found"},
    },
)
def get_recovery_plans(
    case_id: str,
    repo=Depends(get_repository),
    case_service=Depends(get_case_service),
):
    """
    Fetch the currently active recovery plan set for a case.
    """
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )

    plan_set = repo.get_recovery_plan_set(case_id)
    if not plan_set:
        # If Checkpoint 1 is approved, generate plans on demand
        if case.checkpoint1_decision:
            return case_service.run_recovery_planning(case_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "RECOVERY_PLANS_NOT_FOUND",
                "message": f"Recovery planning has not been executed yet for case '{case_id}'. Please run POST /recovery/plan first.",
            },
        )
    return plan_set


@router.post(
    "/cases/{case_id}/recovery/modify",
    response_model=RecoveryPlanSet,
    responses={
        404: {"model": ErrorResponse, "description": "Case or plan not found"},
        422: {"model": ErrorResponse, "description": "Invalid modification parameters"},
    },
)
def modify_recovery_plan(
    case_id: str,
    modify_req: PlanModifyRequest,
    case_service=Depends(get_case_service),
):
    """
    Modify parameters of an existing recovery plan (e.g. quantity, transport mode, source).
    Recalculates feasibility, constraints, scores, increments version to v2/v3, and re-ranks.
    """
    try:
        updated_set = case_service.modify_recovery_plan(case_id, modify_req)
        return updated_set
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RESOURCE_NOT_FOUND", "message": str(ke)},
        )
    except Exception as e:
        logger.error(f"Error modifying plan for case {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "PLAN_MODIFICATION_FAILED", "message": str(e)},
        )


@router.post(
    "/cases/{case_id}/checkpoint2",
    response_model=Checkpoint2Response,
    responses={
        404: {"model": ErrorResponse, "description": "Case or plan not found"},
        409: {"model": ErrorResponse, "description": "Workflow conflict or already approved"},
        422: {"model": ErrorResponse, "description": "Invalid decision or infeasible plan"},
    },
)
def submit_checkpoint_2(
    case_id: str,
    req: Checkpoint2Request,
    case_service=Depends(get_case_service),
):
    """
    Human Checkpoint 2 Decision (APPROVE, MODIFY, REJECT).
    - APPROVE: Locks the exact plan version (e.g. PLAN-01 v1). Case status becomes RECOVERY_APPROVED.
               Ready for Phase 3 Execution. Autonomous execution pauses here.
    - MODIFY:  Recalculates plan with modified parameters, creates new version (v2).
    - REJECT:  Rejects options, records rationale, initiates new planning cycle.
    """
    try:
        resp = case_service.submit_checkpoint2(case_id, req)
        return resp
    except KeyError as ke:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "RESOURCE_NOT_FOUND", "message": str(ke)},
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CHECKPOINT_CONFLICT", "message": str(ve)},
        )
    except Exception as e:
        logger.error(f"Error submitting checkpoint 2 for case {case_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CHECKPOINT_FAILED", "message": str(e)},
        )


@router.get(
    "/cases/{case_id}/checkpoint2",
    response_model=Checkpoint2Response,
    responses={
        404: {"model": ErrorResponse, "description": "Checkpoint 2 decision not found"},
    },
)
def get_checkpoint_2(
    case_id: str,
    repo=Depends(get_repository),
):
    """
    Fetch the Checkpoint 2 governance decision for a case.
    """
    decision = repo.get_checkpoint2(case_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "CHECKPOINT_2_NOT_FOUND",
                "message": f"Checkpoint 2 decision has not been submitted yet for case '{case_id}'",
            },
        )
    return decision
