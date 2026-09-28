from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator, computed_field
from app.config.severity_rules import VALID_CHECKPOINT_PRIORITIES
from app.models.impact import ImpactAnalysis


class Case(BaseModel):
    case_id: str
    disruption_type: str
    description: str
    supplier_id: str
    material_id: str
    plant_id: str
    expected_delay_days: int = 5
    affected_quantity: Optional[float] = None
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = Field(default="CREATED", description="CREATED, TRIAGED, ANALYZED, CHECKPOINT_APPROVED, RECOVERY_PLANNING, AWAITING_CHECKPOINT_2, RECOVERY_APPROVED, EXECUTION_IN_PROGRESS, MONITORING, RESOLVED")
    severity: Optional[str] = None
    checkpoint1_decision: Optional[str] = None
    checkpoint1_timestamp: Optional[str] = None
    checkpoint2_decision: Optional[str] = None
    checkpoint2_timestamp: Optional[str] = None
    approved_plan_id: Optional[str] = None
    approved_plan_version: Optional[str] = None
    execution_action_id: Optional[str] = None
    execution_status: Optional[str] = None
    resolved_at: Optional[str] = None

    @computed_field
    @property
    def current_stage(self) -> str:
        s = (self.status or "CREATED").upper()
        if s in {"NEW", "CREATED", "CASE_CREATED", "CASE_OVERVIEW"}:
            return "CASE"
        elif s in {"TRIAGED", "IMPACT_ANALYSIS_PENDING", "IMPACT_ANALYSIS_RUNNING", "IMPACT_ANALYSIS_FAILED"}:
            return "IMPACT_ANALYSIS"
        elif s in {"ANALYZED", "IMPACT_ANALYSIS_COMPLETED", "PRIORITY_PENDING", "AWAITING_CHECKPOINT_1"}:
            return "PRIORITY"
        elif s in {"PRIORITY_SAVED", "CHECKPOINT_APPROVED", "AGENT2_RUNNING", "AGENT2_COMPLETED", "AGENT2_FAILED"}:
            return "CONSTRAINTS"
        elif s in {"RECOVERY_PLANNING", "AGENT3_RUNNING", "AGENT3_COMPLETED", "AGENT3_FAILED"}:
            return "RECOVERY_PLANNING"
        elif s in {"AWAITING_CHECKPOINT_2", "DECISION_PENDING", "PLAN_MODIFIED", "PLAN_REJECTED"}:
            return "DECISION"
        elif s in {"PLAN_APPROVED", "RECOVERY_APPROVED", "EXECUTION", "EXECUTION_IN_PROGRESS", "MONITORING", "ON_TRACK", "AT_RISK", "ACTION_REQUIRED", "REPLANNING", "DELIVERED"}:
            return "EXECUTION & MONITORING"
        elif s == "RESOLVED":
            return "OUTCOME"
        return "CASE"

    @computed_field
    @property
    def stage_route(self) -> str:
        s = (self.status or "CREATED").upper()
        if s in {"NEW", "CREATED", "CASE_CREATED", "CASE_OVERVIEW"}:
            return "caseOverview"
        elif s in {"TRIAGED", "IMPACT_ANALYSIS_PENDING", "IMPACT_ANALYSIS_RUNNING", "IMPACT_ANALYSIS_FAILED"}:
            return "impactAnalysis"
        elif s in {"ANALYZED", "IMPACT_ANALYSIS_COMPLETED", "PRIORITY_PENDING", "AWAITING_CHECKPOINT_1"}:
            return "checkpoint1"
        elif s in {"PRIORITY_SAVED", "CHECKPOINT_APPROVED", "AGENT2_RUNNING", "AGENT2_COMPLETED", "AGENT2_FAILED"}:
            return "constraints"
        elif s in {"RECOVERY_PLANNING", "AGENT3_RUNNING", "AGENT3_COMPLETED", "AGENT3_FAILED"}:
            return "recoveryPlanning"
        elif s in {"AWAITING_CHECKPOINT_2", "DECISION_PENDING", "PLAN_MODIFIED", "PLAN_REJECTED"}:
            return "decision"
        elif s in {"PLAN_APPROVED", "RECOVERY_APPROVED", "EXECUTION", "EXECUTION_IN_PROGRESS", "MONITORING", "ON_TRACK", "AT_RISK", "ACTION_REQUIRED", "REPLANNING", "DELIVERED"}:
            return "executionMonitoring"
        elif s == "RESOLVED":
            return "outcome"
        return "caseOverview"


class CaseCreateRequest(BaseModel):
    disruption_type: str = Field(..., min_length=2, description="Type of disruption")
    description: str = Field(..., min_length=5, description="Description of the disruption event")
    supplier_id: str = Field(..., description="Affected supplier identifier (e.g. SUP-001)")
    material_id: str = Field(..., description="Affected material identifier (e.g. MAT-001)")
    plant_id: str = Field(..., description="Affected plant identifier (e.g. PLANT-001)")
    expected_delay_days: int = Field(default=5, ge=0, description="Expected shipment or lead time delay in days")
    affected_quantity: Optional[float] = Field(default=None, ge=0.0, description="Affected shipment quantity")


class CaseListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Case]


class CheckpointRequest(BaseModel):
    priority: str = Field(..., description="Recovery priority: TIME, COST, RISK, or BALANCED")

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        upper = v.upper()
        if upper not in VALID_CHECKPOINT_PRIORITIES:
            raise ValueError(f"Priority must be one of {sorted(VALID_CHECKPOINT_PRIORITIES)}")
        return upper


class CheckpointResponse(BaseModel):
    case_id: str
    status: str
    priority: str
    message: str
    phase2_status: str
