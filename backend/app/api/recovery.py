import logging
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_case_service, get_repository
from app.workflow.state_machine import normalize_state, CaseState
from app.models.impact import ErrorResponse
from app.models.recovery import (
    RecoveryPlanSet,
    CandidatePlanSet,
    ManagerConstraints,
    PlanModifyRequest,
    Checkpoint2Request,
    Checkpoint2Response,
    ExecutionSnapshot,
)

logger = logging.getLogger("quads.api.recovery")
router = APIRouter(prefix="/api/v1", tags=["Recovery Planning & Decision (Agents 2 & 3)"])


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
        # If Checkpoint 1 priority exists, generate or wait
        if case.checkpoint1_decision:
            cand_set = repo.get_candidate_plan_set(case_id)
            if not cand_set:
                case_service.submit_checkpoint1(case_id, case.checkpoint1_decision)
                import time
                for _ in range(40):
                    time.sleep(0.2)
                    p = repo.get_recovery_plan_set(case_id)
                    if p:
                        return p
            plan_set = repo.get_recovery_plan_set(case_id)
            if plan_set:
                return plan_set

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "RECOVERY_PLANS_NOT_FOUND",
                "message": f"Recovery planning has not completed yet for case '{case_id}'.",
            },
        )
    return plan_set


@router.get(
    "/cases/{case_id}/plans",
    response_model=RecoveryPlanSet,
)
def get_plans_alias(
    case_id: str,
    repo=Depends(get_repository),
    case_service=Depends(get_case_service),
):
    """Alias for GET /cases/{case_id}/plans per specification Section 15."""
    return get_recovery_plans(case_id=case_id, repo=repo, case_service=case_service)


@router.post(
    "/cases/{case_id}/recovery/plan",
    response_model=RecoveryPlanSet,
)
def trigger_recovery_plans(
    case_id: str,
    constraints: Optional[ManagerConstraints] = None,
    force_regenerate: bool = Query(False),
    case_service=Depends(get_case_service),
    repo=Depends(get_repository),
):
    """Generate or retrieve recovery plans."""
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "CASE_NOT_FOUND", "message": f"Case {case_id} not found"})
    
    if not case.checkpoint1_decision:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "CHECKPOINT_1_REQUIRED", "message": "Checkpoint 1 priority must be set first."})

    if not force_regenerate and not constraints:
        existing = repo.get_recovery_plan_set(case_id)
        if existing:
            return existing
        curr_s = normalize_state(case.status)
        if curr_s in (CaseState.AGENT2_RUNNING, CaseState.AGENT3_RUNNING):
            import time
            for _ in range(70):
                time.sleep(0.1)
                p = repo.get_recovery_plan_set(case_id)
                c = repo.get_case(case_id)
                if p and c and normalize_state(c.status) == CaseState.DECISION_PENDING:
                    return p
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TIMEOUT", "message": "Timed out waiting for plans."})

    if hasattr(repo, "_recovery_plan_sets"):
        repo._recovery_plan_sets.pop(case_id, None)

    case_service.submit_checkpoint1(
        case_id,
        case.checkpoint1_decision or "BALANCED",
        constraints=constraints,
        force=True,
    )

    import time
    for _ in range(70):
        time.sleep(0.1)
        p = repo.get_recovery_plan_set(case_id)
        c = repo.get_case(case_id)
        if p and c and normalize_state(c.status) == CaseState.DECISION_PENDING:
            return p
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "TIMEOUT", "message": "Timed out generating plans."})


@router.get(
    "/cases/{case_id}/candidates",
)
def get_candidates(
    case_id: str,
    repo=Depends(get_repository),
):
    """Fetch Agent 2 raw candidate plans prior to final evaluation."""
    cand_set = repo.get_candidate_plan_set(case_id)
    if not cand_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "CANDIDATES_NOT_FOUND", "message": "No candidates generated yet."})
    return cand_set


@router.get(
    "/cases/{case_id}/evaluation",
    response_model=RecoveryPlanSet,
)
def get_evaluation(
    case_id: str,
    repo=Depends(get_repository),
    case_service=Depends(get_case_service),
):
    """Fetch Agent 3 evaluation output."""
    return get_recovery_plans(case_id=case_id, repo=repo, case_service=case_service)


@router.get(
    "/cases/{case_id}/checkpoint2",
    response_model=Checkpoint2Response,
)
def get_checkpoint_2(
    case_id: str,
    case_service=Depends(get_case_service),
):
    """Retrieve saved Checkpoint 2 decision."""
    cp2 = case_service.get_checkpoint2(case_id)
    if not cp2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": f"Checkpoint 2 decision not found for case {case_id}"},
        )
    return cp2


@router.post(
    "/cases/{case_id}/checkpoint2",
    response_model=Checkpoint2Response,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid decision payload or missing reason/comment"},
        404: {"model": ErrorResponse, "description": "Case or plan not found"},
        409: {"model": ErrorResponse, "description": "Workflow conflict or infeasible plan approval attempt"},
    },
)
def submit_checkpoint_2(
    case_id: str,
    req: Checkpoint2Request,
    case_service=Depends(get_case_service),
):
    """
    Human Checkpoint 2: Final Decision.
    APPROVE, MODIFY, or REJECT.
    Only human actors can approve; immutable execution snapshot is created on approval.
    """
    try:
        updated_case, resp = case_service.submit_decision(case_id, req)
        return resp
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": str(ke)})
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"error": "DECISION_REJECTED", "message": str(ve)})
    except Exception as e:
        logger.error(f"Error in checkpoint2 for {case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"error": "CHECKPOINT2_FAILED", "message": str(e)})


@router.post("/cases/{case_id}/decision/approve", response_model=Checkpoint2Response)
def approve_plan_alias(case_id: str, req: Checkpoint2Request, case_service=Depends(get_case_service)):
    req.decision = "APPROVE"
    return submit_checkpoint_2(case_id=case_id, req=req, case_service=case_service)


@router.post("/cases/{case_id}/decision/modify", response_model=Checkpoint2Response)
def modify_plan_alias(case_id: str, req: Checkpoint2Request, case_service=Depends(get_case_service)):
    req.decision = "MODIFY"
    return submit_checkpoint_2(case_id=case_id, req=req, case_service=case_service)


@router.post("/cases/{case_id}/decision/reject", response_model=Checkpoint2Response)
def reject_plan_alias(case_id: str, req: Checkpoint2Request, case_service=Depends(get_case_service)):
    req.decision = "REJECT"
    return submit_checkpoint_2(case_id=case_id, req=req, case_service=case_service)


@router.post("/cases/{case_id}/recovery/modify", response_model=Checkpoint2Response)
def recovery_modify_compat(case_id: str, req: PlanModifyRequest, case_service=Depends(get_case_service)):
    cp_req = Checkpoint2Request(
        decision="MODIFY",
        plan_id=req.plan_id,
        modify_params=req,
    )
    return submit_checkpoint_2(case_id=case_id, req=cp_req, case_service=case_service)


@router.get(
    "/cases/{case_id}/snapshots",
    response_model=list[ExecutionSnapshot],
)
def get_snapshots(
    case_id: str,
    case_service=Depends(get_case_service),
):
    """Fetch immutable approved plan snapshots for a case."""
    return case_service.get_snapshots(case_id)
