from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator, computed_field
from app.config.severity_rules import VALID_CHECKPOINT_PRIORITIES
from app.models.impact import ImpactAnalysis
from app.workflow.state_machine import CaseState, normalize_state


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
    status: str = Field(default="CASE_OVERVIEW")
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
    
    # Redesign v2 fields
    planning_cycle: int = Field(default=1, description="Planning cycle incremented on rejection or replan")
    active_plan_version: str = Field(default="v1", description="Active plan version being considered or executed")
    legacy: bool = Field(default=False, description="True if case was created under older workflow")
    last_error: Optional[str] = Field(default=None, description="Detailed error message if agent or step failed")
    active_step: Optional[str] = Field(default=None, description="Active fine-grained step within the current stage")
    steps_progress: dict[str, Any] = Field(default_factory=dict, description="Fine-grained step completion statuses")
    run_id: Optional[str] = Field(default=None, description="Unique run identifier for concurrency/idempotency")
    completed_stages: list[str] = Field(default_factory=list, description="List of completed stage names")

    @computed_field
    @property
    def normalized_status(self) -> str:
        return normalize_state(self.status).value

    @computed_field
    @property
    def current_stage(self) -> str:
        s = normalize_state(self.status)
        if s in {CaseState.CASE_CREATED, CaseState.CASE_OVERVIEW}:
            return "CASE"
        elif s in {
            CaseState.IMPACT_ANALYSIS_PENDING,
            CaseState.IMPACT_ANALYSIS_RUNNING,
            CaseState.IMPACT_ANALYSIS_FAILED,
            CaseState.IMPACT_ANALYSIS_COMPLETED,
        }:
            return "IMPACT"
        elif s == CaseState.PRIORITY_PENDING:
            return "PRIORITY"
        elif s in {
            CaseState.PRIORITY_SAVED,
            CaseState.AGENT2_RUNNING,
            CaseState.AGENT2_COMPLETED,
            CaseState.AGENT2_FAILED,
        }:
            return "RECOVERY PLANS"
        elif s in {
            CaseState.AGENT3_RUNNING,
            CaseState.AGENT3_COMPLETED,
            CaseState.AGENT3_FAILED,
        }:
            return "EVALUATION"
        elif s in {
            CaseState.DECISION_PENDING,
            CaseState.PLAN_MODIFIED,
            CaseState.PLAN_REJECTED,
        }:
            return "DECISION"
        elif s in {
            CaseState.PLAN_APPROVED,
            CaseState.EXECUTION,
            CaseState.AT_RISK,
            CaseState.REPLANNING,
        }:
            return "EXECUTION & MONITORING"
        elif s == CaseState.RESOLVED:
            return "OUTCOME"
        return "CASE"

    @computed_field
    @property
    def stage_route(self) -> str:
        s = normalize_state(self.status)
        if s in {CaseState.CASE_CREATED, CaseState.CASE_OVERVIEW}:
            return "caseOverview"
        elif s in {
            CaseState.IMPACT_ANALYSIS_PENDING,
            CaseState.IMPACT_ANALYSIS_RUNNING,
            CaseState.IMPACT_ANALYSIS_FAILED,
            CaseState.IMPACT_ANALYSIS_COMPLETED,
        }:
            return "impactAnalysis"
        elif s == CaseState.PRIORITY_PENDING:
            return "checkpoint1"
        elif s in {
            CaseState.PRIORITY_SAVED,
            CaseState.AGENT2_RUNNING,
            CaseState.AGENT2_COMPLETED,
            CaseState.AGENT2_FAILED,
            CaseState.AGENT3_RUNNING,
            CaseState.AGENT3_COMPLETED,
            CaseState.AGENT3_FAILED,
        }:
            return "recoveryPlanning"
        elif s in {
            CaseState.DECISION_PENDING,
            CaseState.PLAN_MODIFIED,
            CaseState.PLAN_REJECTED,
        }:
            return "decision"
        elif s in {
            CaseState.PLAN_APPROVED,
            CaseState.EXECUTION,
            CaseState.AT_RISK,
            CaseState.REPLANNING,
        }:
            return "executionMonitoring"
        elif s == CaseState.RESOLVED:
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
    priority: str = Field(..., description="Recovery priority: TIME, COST, STOCK, RISK, CUSTOMER, or BALANCED")

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
    planning_cycle: int = 1
