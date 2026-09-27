import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.dependencies import get_repository, get_case_service, get_audit_service
from app.models.case import Case, CaseCreateRequest, CaseListResponse
from app.models.impact import AuditEvent, ErrorResponse

logger = logging.getLogger("quads.api.cases")
router = APIRouter(prefix="/api/v1", tags=["Case Management"])


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
