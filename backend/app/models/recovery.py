from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class TransportOption(BaseModel):
    mode: str = Field(..., description="Transport mode code (e.g. AIR_EXPEDITED)")
    name: str = Field(..., description="Descriptive transport name")
    transit_days: int = Field(..., ge=0, description="Transit duration in days")
    flat_cost: float = Field(default=0.0, description="Base dispatch flat fee")
    cost_per_unit: float = Field(default=0.0, description="Variable transport fee per unit")
    reliability: float = Field(default=0.90, ge=0.0, le=1.0, description="Carrier on-time reliability score")
    transit_risk_score: float = Field(default=0.10, ge=0.0, le=1.0, description="Risk penalty factor (0.0 to 1.0)")
    description: str = Field(default="", description="Detailed route & equipment description")


class HistoricalPrecedent(BaseModel):
    precedent_id: str
    disruption_type: str
    material_id: str
    material_name: str
    disrupted_supplier_id: str
    strategy_used: str
    recovery_source: str
    recovered_quantity: float
    recovery_days: int
    outcome_summary: str
    similarity_score: float = Field(default=0.85, ge=0.0, le=1.0)
    success_rate: float = Field(default=0.90, ge=0.0, le=1.0)


class ContractClause(BaseModel):
    clause_reference: str
    title: str
    terms: str
    penalty_rebate_rate: Optional[float] = None
    cost_share_rate: Optional[float] = None
    buffer_capacity: Optional[float] = None
    lead_time_days: Optional[int] = None
    price_surcharge_rate: Optional[float] = None


class ContractEvidence(BaseModel):
    contract_id: str
    supplier_id: str
    title: str
    status: str = "ACTIVE"
    clauses: list[ContractClause] = Field(default_factory=list)
    is_available: bool = True
    summary: str = ""


class ConstraintEvaluation(BaseModel):
    constraint_name: str
    constraint_type: str = Field(..., description="HARD or SOFT")
    required_value: str
    actual_value: str
    satisfied: bool
    violation_reason: Optional[str] = None


class ScoreBreakdown(BaseModel):
    time_score: float = Field(..., ge=0.0, le=100.0)
    cost_score: float = Field(..., ge=0.0, le=100.0)
    risk_score: float = Field(..., ge=0.0, le=100.0)
    fulfillment_score: float = Field(..., ge=0.0, le=100.0)
    overall_score: float = Field(..., ge=0.0, le=100.0)
    weights_applied: dict[str, float]
    explanation: str


class RecoveryPlan(BaseModel):
    plan_id: str = Field(..., description="Unique plan code (e.g. PLAN-01)")
    version: str = Field(default="v1", description="Exact plan version (e.g. v1, v2)")
    title: str = Field(..., description="Display title for the recovery option")
    strategy: str = Field(..., description="ALTERNATE_SUPPLIER, INTER_PLANT_TRANSFER, SPLIT_SOURCING, EXPEDITED_LOGISTICS")
    source_type: str = Field(..., description="SUPPLIER, PLANT, HYBRID, or EXPEDITED_PO")
    source_id: str = Field(..., description="Supplier ID or Source Plant ID")
    source_name: str
    source_location: str
    target_plant_id: str
    target_plant_name: str
    recovered_quantity: float
    fulfillment_pct: float = Field(..., ge=0.0, le=100.0)
    recovery_days: int
    expected_arrival_date: str
    total_cost: float
    cost_breakdown: dict[str, float] = Field(default_factory=dict)
    transport_mode: str
    transport_name: str
    transport_days: int
    transport_cost: float
    carrier_reliability: float
    operational_risk: str = Field(..., description="LOW, MEDIUM, or HIGH")
    operational_risk_score: float = Field(..., ge=0.0, le=100.0)
    customer_impact_remaining: str
    production_impact_remaining: str
    feasibility_status: str = Field(..., description="FEASIBLE or INFEASIBLE")
    infeasibility_reason: Optional[str] = None
    constraints: list[ConstraintEvaluation] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    score_breakdown: Optional[ScoreBreakdown] = None
    trade_offs: list[str] = Field(default_factory=list)
    historical_evidence: list[HistoricalPrecedent] = Field(default_factory=list)
    contract_evidence: Optional[ContractEvidence] = None
    split_details: Optional[dict[str, Any]] = None


class ManagerConstraints(BaseModel):
    max_recovery_days: Optional[int] = Field(default=None, ge=1, description="Upper bound on acceptable recovery lead time")
    max_budget: Optional[float] = Field(default=None, ge=0.0, description="Upper bound on total recovery cost")
    min_quantity: Optional[float] = Field(default=None, ge=0.0, description="Minimum acceptable quantity recovered")
    preferred_strategy: Optional[str] = Field(default=None, description="Preferred recovery strategy filter")


class RecoveryPlanSet(BaseModel):
    case_id: str
    priority: str = Field(..., description="Checkpoint 1 priority: TIME, COST, RISK, or BALANCED")
    manager_constraints: ManagerConstraints = Field(default_factory=ManagerConstraints)
    feasible_plans: list[RecoveryPlan] = Field(default_factory=list)
    infeasible_plans: list[RecoveryPlan] = Field(default_factory=list)
    total_evaluated: int = 0
    ai_briefing: Optional[str] = None
    ai_status: str = Field(default="UNAVAILABLE", description="AVAILABLE, UNAVAILABLE, or FAILED")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_plan_version: str = "v1"
    checkpoint2_status: str = Field(default="AWAITING_CHECKPOINT_2", description="AWAITING_CHECKPOINT_2, APPROVED, REJECTED")
    checkpoint2_decision: Optional[dict[str, Any]] = None


class PlanModifyRequest(BaseModel):
    plan_id: str = Field(..., description="Target plan ID to modify")
    allocated_quantity: Optional[float] = Field(default=None, ge=1.0, description="Adjusted recovery quantity")
    transport_mode: Optional[str] = Field(default=None, description="Adjusted transport mode")
    source_id: Optional[str] = Field(default=None, description="Adjusted source supplier or plant ID")
    max_recovery_days: Optional[int] = Field(default=None, ge=1, description="Updated maximum acceptable recovery days")
    max_budget: Optional[float] = Field(default=None, ge=0.0, description="Updated maximum allowable recovery budget")


class Checkpoint2Request(BaseModel):
    decision: str = Field(..., description="APPROVE, MODIFY, or REJECT")
    plan_id: Optional[str] = Field(default=None, description="Plan ID being approved or modified")
    selected_plan_id: Optional[str] = Field(default=None, description="Alternative field name for plan_id")
    version: Optional[str] = Field(default=None, description="Exact version being approved")
    selected_plan_version: Optional[str] = Field(default=None, description="Alternative field name for version")
    rationale: Optional[str] = Field(default=None, description="Planner rationale or decision justification")
    manager_id: Optional[str] = Field(default="SUPPLY_CHAIN_PLANNER")
    modify_params: Optional[PlanModifyRequest] = Field(default=None, description="Modification parameters when decision is MODIFY")

    def get_effective_plan_id(self) -> Optional[str]:
        return self.plan_id or self.selected_plan_id

    def get_effective_version(self) -> Optional[str]:
        return self.version or self.selected_plan_version


class Checkpoint2Response(BaseModel):
    case_id: str = Field(default="", description="Case identifier")
    decision: str = Field(default="APPROVE", description="APPROVE, MODIFY, or REJECT")
    plan_id: Optional[str] = None
    version: Optional[str] = None
    status: str = Field(default="RECOVERY_APPROVED", description="RECOVERY_APPROVED or AWAITING_CHECKPOINT_2")
    message: str = Field(default="Checkpoint 2 processed.", description="Summary message")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str = "SUPPLY_CHAIN_PLANNER"
    approved_plan: Optional[RecoveryPlan] = None
    phase3_status: str = "Ready for Phase 3 Execution. Autonomous execution paused at Phase 2 boundary."
