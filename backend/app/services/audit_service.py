from datetime import datetime, timezone
from typing import Optional
from app.repositories.base import BaseRepository
from app.models.impact import AuditEvent


class AuditService:
    def __init__(self, repository: BaseRepository):
        self.repository = repository

    def log(
        self,
        case_id: str,
        event: str,
        actor: str,
        details: str,
    ) -> AuditEvent:
        """
        Record an immutable audit event in UTC ISO 8601.
        """
        audit_event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            case_id=case_id,
            event=event,
            actor=actor,
            details=details,
        )
        return self.repository.save_audit_event(audit_event)

    def get_events(self, case_id: Optional[str] = None) -> list[AuditEvent]:
        return self.repository.get_audit_events(case_id=case_id)
