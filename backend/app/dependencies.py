"""
Application dependencies and service singletons for FastAPI dependency injection.
"""

import os
from typing import Optional
from app.repositories.mock_repository import MockRepository
from app.services.audit_service import AuditService
from app.services.gemini_service import GeminiService
from app.services.case_service import CaseService
from app.adapters.sap.mock_sap import MockSAPAdapter
from app.services.execution_service import ExecutionService

# Global singletons
_repo: Optional[MockRepository] = None
_audit_service: Optional[AuditService] = None
_gemini_service: Optional[GeminiService] = None
_case_service: Optional[CaseService] = None
_sap_adapter: Optional[MockSAPAdapter] = None
_execution_service: Optional[ExecutionService] = None


def get_repository() -> MockRepository:
    global _repo
    if _repo is None:
        data_dir = os.environ.get("DATA_DIR")
        _repo = MockRepository(data_dir=data_dir)
    return _repo


def get_audit_service() -> AuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService(repository=get_repository())
    return _audit_service


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


def get_case_service() -> CaseService:
    global _case_service
    if _case_service is None:
        _case_service = CaseService(
            repository=get_repository(),
            audit_service=get_audit_service(),
            gemini_service=get_gemini_service(),
        )
    return _case_service


def get_sap_adapter() -> MockSAPAdapter:
    global _sap_adapter
    if _sap_adapter is None:
        _sap_adapter = MockSAPAdapter()
    return _sap_adapter


def get_execution_service() -> ExecutionService:
    global _execution_service
    if _execution_service is None:
        _execution_service = ExecutionService(
            repository=get_repository(),
            sap_adapter=get_sap_adapter(),
            audit_service=get_audit_service(),
            gemini_service=get_gemini_service(),
            case_service=get_case_service(),
        )
    return _execution_service


def reset_services():
    """Helper for testing or resetting repository state."""
    global _repo, _audit_service, _gemini_service, _case_service, _sap_adapter, _execution_service
    if _case_service:
        _case_service.close()
    _repo = None
    _audit_service = None
    _gemini_service = None
    _case_service = None
    _sap_adapter = None
    _execution_service = None

