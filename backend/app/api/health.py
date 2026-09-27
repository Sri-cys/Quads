from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from app.dependencies import get_repository, get_gemini_service

router = APIRouter(tags=["Health & Status"])


@router.get("/api/health")
def get_system_health(
    repo=Depends(get_repository),
    gemini=Depends(get_gemini_service),
):
    """
    Backend system health check and component status.
    Exposes no secrets.
    """
    gemini_status = "CONFIGURED" if gemini.is_configured else "NOT_CONFIGURED"

    return {
        "status": "ONLINE",
        "backend": "ONLINE",
        "gemini": gemini_status,
        "mock_repository": "ONLINE",
        "sap_integration": "MOCK_MODE",
        "hana_cloud": "NOT_CONNECTED_PHASE_1",
        "btp": "LOCAL_DEVELOPMENT_MODE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cases_count": repo.list_cases(limit=1, offset=0)[0],
    }
