import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.dependencies import get_repository, get_case_service, get_audit_service
from app.models.case import Case, CaseCreateRequest, CaseListResponse
from app.models.impact import AuditEvent, ErrorResponse

logger = logging.getLogger("quads.api.cases")
router = APIRouter(prefix="/api/v1", tags=["Case Management"])


class ReopenRequest(BaseModel):
    reason: str


@router.post(
    "/cases",
    response_model=Case,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Duplicate open case already exists"},
        422: {"model": ErrorResponse, "description": "Invalid input data"},
    },
)
def create_case(
    req: CaseCreateRequest,
    case_service=Depends(get_case_service),
    repo=Depends(get_repository),
):
    """
    Create a disruption case and execute initial LangGraph ingestion and case registration.
    """
    # Verify foreign key existence (supplier, material, plant)
    if not repo.get_supplier(req.supplier_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "INVALID_SUPPLIER", "message": f"Supplier {req.supplier_id} does not exist in master data"},
        )
    if not repo.get_material(req.material_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "INVALID_MATERIAL", "message": f"Material {req.material_id} does not exist in master data"},
        )
    if not repo.get_plant(req.plant_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "INVALID_PLANT", "message": f"Plant {req.plant_id} does not exist in master data"},
        )

    try:
        created_case, is_duplicate = case_service.create_disruption_case(req)
        if is_duplicate:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": "DUPLICATE_CASE",
                    "message": f"An active case ({created_case.case_id}) already exists for Supplier {req.supplier_id}, Material {req.material_id}, Plant {req.plant_id}, and Type {req.disruption_type}",
                },
            )
        return created_case
    except Exception as e:
        logger.error(f"Error creating case: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INTERNAL_ERROR", "message": "Failed to register disruption case"},
        )


@router.get("/cases", response_model=CaseListResponse)
def list_cases(
    limit: int = Query(default=25, ge=1, le=100, description="Page limit"),
    offset: int = Query(default=0, ge=0, description="Page offset"),
    repo=Depends(get_repository),
):
    """
    List disruption cases with pagination.
    """
    total, items = repo.list_cases(limit=limit, offset=offset)
    return CaseListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get(
    "/cases/{case_id}",
    response_model=Case,
    responses={404: {"model": ErrorResponse, "description": "Case not found"}},
)
def get_case(
    case_id: str,
    case_service=Depends(get_case_service),
):
    """
    Fetch a single disruption case by case_id.
    """
    case = case_service.get_case_or_from_checkpoint(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )
    return case


@router.get("/cases/{case_id}/audit", response_model=list[AuditEvent])
def get_case_audit_history(
    case_id: str,
    audit_service=Depends(get_audit_service),
    case_service=Depends(get_case_service),
):
    """
    Get audit history log for a case.
    """
    case = case_service.get_case_or_from_checkpoint(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case with ID '{case_id}' was not found"},
        )
    return audit_service.get_events(case_id=case_id)


# Master data endpoints for UI dropdowns
@router.get("/suppliers")
def list_suppliers(repo=Depends(get_repository)):
    return repo.list_suppliers()


@router.get("/materials")
def list_materials(repo=Depends(get_repository)):
    return repo.list_materials()


@router.get("/plants")
def list_plants(repo=Depends(get_repository)):
    return repo.list_plants()


@router.post("/cases/{case_id}/reopen", response_model=Case)
def reopen_case(
    case_id: str,
    body: "ReopenRequest",
    repo=Depends(get_repository),
    audit_service=Depends(get_audit_service),
):
    """
    Reset a case back to IMPACT_ANALYSIS_COMPLETED for a fresh planning cycle.
    Clears: checkpoint1/2 decisions, approved plan, execution records, recovery plans.
    Preserves: impact analysis results (disruption facts don't change).
    Called when the planner marks recovery as 'Not Completed'.
    """
    case = repo.get_case(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "CASE_NOT_FOUND", "message": f"Case {case_id} not found"},
        )

    # Reset case fields
    case.checkpoint1_decision = None
    case.checkpoint1_timestamp = None
    case.checkpoint2_decision = None
    case.checkpoint2_timestamp = None
    case.approved_plan_id = None
    case.approved_plan_version = None
    case.execution_action_id = None
    case.execution_status = None
    case.resolved_at = None
    case.status = "IMPACT_ANALYSIS_COMPLETED"
    case.last_error = None

    # Increment planning cycle counter
    case.planning_cycle = (getattr(case, "planning_cycle", 1) or 1) + 1

    # Clear recovery plans and execution records from repo
    repo._recovery_plan_sets.pop(case_id, None)
    repo._checkpoint2_decisions.pop(case_id, None)
    repo._execution_records.pop(case_id, None)
    repo._execution_baselines.pop(case_id, None)
    repo._tracking_events.pop(case_id, None)

    repo.update_case(case)

    audit_service.log(
        case_id=case_id,
        event="CASE_REOPENED",
        actor="SUPPLY_CHAIN_PLANNER",
        details=f"Case reopened for planning cycle {case.planning_cycle}. Reason: {body.reason}",
    )
    logger.info(f"Case {case_id} reopened for cycle {case.planning_cycle}. Reason: {body.reason}")
    return case

