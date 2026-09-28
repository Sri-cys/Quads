from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
import hashlib
import json


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
    time_score: float = Field(default=0.0, ge=0.0, le=100.0)
    cost_score: float = Field(default=0.0, ge=0.0, le=100.0)
    stock_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_score: float = Field(default=0.0, ge=0.0, le=100.0)
    customer_score: float = Field(default=0.0, ge=0.0, le=100.0)
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    weights_applied: dict[str, float] = Field(default_factory=dict)
    explanation: str = ""


class CandidatePlan(BaseModel):
    """
    Agent 2 Output: Pure candidate recovery option.
    Does NOT contain final evaluation, scoring, ranking, or feasibility determination.
    """
    plan_id: str = Field(..., description="Unique plan code (e.g. PLAN-001)")
    plan_version: str = Field(default="v1", description="Exact plan version (e.g. v1, v2)")
    strategy: str = Field(..., description="Recovery strategy name")
    source: str = Field(..., description="Source location or entity name")
    destination: str = Field(..., description="Destination plant location")
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    plant_id: str
    plant_name: str
    quantity: float
    transport_mode: str
    carrier: str
    est_dispatch: str
    est_arrival: str
    recovery_time_est: int = Field(..., description="Estimated recovery days (pre-evaluation)")
    recovery_cost_est: float = Field(default=0.0, description="Estimated total cost (pre-evaluation)")
    required_resources: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    expected_customer_impact: str = "Pending evaluation"
    content_hash: str = ""

    def compute_hash(self) -> str:
        data = {
            "id": self.plan_id,
            "version": self.plan_version,
            "strategy": self.strategy,
            "source": self.source,
            "dest": self.destination,
            "supplier": self.supplier_id,
            "plant": self.plant_id,
            "qty": self.quantity,
            "mode": self.transport_mode,
            "carrier": self.carrier,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


class CandidatePlanSet(BaseModel):
    case_id: str
    planning_cycle: int = 1
    priority: str
    candidates: list[CandidatePlan] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RecoveryPlan(BaseModel):
    """
    Evaluated Recovery Plan (Agent 3 output).
    Includes deterministic plan-specific cost, risk, constraints, and scoring.
    """
    plan_id: str = Field(..., description="Unique plan code (e.g. PLAN-001)")
    version: str = Field(default="v1", description="Exact plan version (e.g. v1, v2)")
    title: str = Field(..., description="Display title for the recovery option")
    strategy: str = Field(..., description="ALTERNATE_SUPPLIER, INTER_PLANT_TRANSFER, SPLIT_SOURCING, EXPEDITED_LOGISTICS, etc.")
    source_type: str = Field(default="SUPPLIER", description="SUPPLIER, PLANT, HYBRID, or EXPEDITED_PO")
    source_id: str = Field(default="", description="Supplier ID or Source Plant ID")
    source_name: str = ""
    source_location: str = ""
    target_plant_id: str = ""
    target_plant_name: str = ""
    recovered_quantity: float = 0.0
    fulfillment_pct: float = Field(default=100.0, ge=0.0, le=100.0)
    recovery_days: int = 0
    expected_arrival_date: str = ""
    
    # Cost (Agent 3 Plan-Specific)
    total_cost: float = 0.0
    cost_breakdown: dict[str, Any] = Field(default_factory=dict)
    cost_status: str = Field(default="COMPLETE", description="COMPLETE or INCOMPLETE")
    missing_cost_data: list[str] = Field(default_factory=list)

    # Transport details
    transport_mode: str = ""
    transport_name: str = ""
    transport_days: int = 0
    transport_cost: float = 0.0
    carrier_reliability: float = 0.90
    carrier: str = ""

    # Risk (Agent 3 Plan-Specific)
    operational_risk: str = Field(default="LOW", description="LOW, MEDIUM, or HIGH")
    operational_risk_score: float = Field(default=15.0, ge=0.0, le=100.0)
    risk_breakdown: dict[str, Any] = Field(default_factory=dict)

    # Customer & Production Impact
    customer_delay_days: int = 0
    customer_impact_remaining: str = "None"
    production_impact_remaining: str = "None"

    # Feasibility (Hard Constraints)
    is_feasible: bool = True
    feasibility_status: str = Field(default="FEASIBLE", description="FEASIBLE or INFEASIBLE")
    infeasibility_reasons: list[str] = Field(default_factory=list)
    infeasibility_reason: Optional[str] = None
    constraints: list[ConstraintEvaluation] = Field(default_factory=list)

    # Scoring (Weighted by Checkpoint 1 Priority)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    score_breakdown: Optional[ScoreBreakdown] = None
    trade_offs: list[str] = Field(default_factory=list)

    # Evidence & Contract Citations
    historical_evidence: list[HistoricalPrecedent] = Field(default_factory=list)
    contract_evidence: Optional[ContractEvidence] = None
    contract_findings: list[str] = Field(default_factory=list)
    candidate_hash: str = ""


class ManagerConstraints(BaseModel):
    max_recovery_days: Optional[int] = Field(default=None, ge=1, description="Upper bound on acceptable recovery lead time")
    max_budget: Optional[float] = Field(default=None, ge=0.0, description="Upper bound on total recovery cost")
    min_quantity: Optional[float] = Field(default=None, ge=0.0, description="Minimum acceptable quantity recovered")
    preferred_strategy: Optional[str] = Field(default=None, description="Preferred recovery strategy filter")
    max_customer_delay: Optional[int] = Field(default=10, description="Max acceptable customer delay days")
    min_safety_stock: Optional[float] = Field(default=50.0, description="Minimum safety stock threshold")


class RecoveryPlanSet(BaseModel):
    case_id: str
    priority: str = Field(..., description="Checkpoint 1 priority: TIME, COST, STOCK, RISK, CUSTOMER, or BALANCED")
    planning_cycle: int = 1
    manager_constraints: ManagerConstraints = Field(default_factory=ManagerConstraints)
    feasible_plans: list[RecoveryPlan] = Field(default_factory=list)
    infeasible_plans: list[RecoveryPlan] = Field(default_factory=list)
    candidates: list[CandidatePlan] = Field(default_factory=list)
    total_evaluated: int = 0
    no_feasible_plans: bool = False
    ai_briefing: Optional[str] = None
    ai_status: str = Field(default="UNAVAILABLE", description="AVAILABLE, UNAVAILABLE, or FAILED")
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    current_plan_version: str = "v1"
    checkpoint2_status: str = Field(default="AWAITING_CHECKPOINT_2", description="AWAITING_CHECKPOINT_2, APPROVED, REJECTED, MODIFIED")
    checkpoint2_decision: Optional[dict[str, Any]] = None


class ExecutionSnapshot(BaseModel):
    """
    Immutable Execution Snapshot created upon human approval at Checkpoint 2.
    Append-only; no update or delete path.
    """
    snapshot_id: str = Field(default_factory=lambda: f"SNAP-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')[:18]}")
    case_id: str
    plan_id: str
    plan_version: str
    planning_cycle: int = 1
    priority: str
    approved_by: str = "SUPPLY_CHAIN_PLANNER"
    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approval_comment: str
    plan: dict[str, Any]
    evaluation: dict[str, Any]
    constraints: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    content_hash: str
    is_active: bool = True
    is_superseded: bool = False


class PlanModifyRequest(BaseModel):
    plan_id: str = Field(..., description="Target plan ID to modify")
    allocated_quantity: Optional[float] = Field(default=None, ge=1.0, description="Adjusted recovery quantity")
    transport_mode: Optional[str] = Field(default=None, description="Adjusted transport mode")
    source_id: Optional[str] = Field(default=None, description="Adjusted source supplier or plant ID")
    max_recovery_days: Optional[int] = Field(default=None, ge=1, description="Updated maximum acceptable recovery days")
    max_budget: Optional[float] = Field(default=None, ge=0.0, description="Updated maximum allowable recovery budget")


class Checkpoint2Request(BaseModel):
    decision: str = Field(..., description="APPROVE, MODIFY, or REJECT")
    plan_id: Optional[str] = Field(default=None, description="Plan ID being approved, modified, or rejected")
    selected_plan_id: Optional[str] = Field(default=None, description="Selected plan ID alias")
    version: Optional[str] = Field(default=None, description="Exact version being approved")
    selected_plan_version: Optional[str] = Field(default=None, description="Selected version alias")
    rationale: Optional[str] = Field(default=None, description="Mandatory reason for rejection or approval justification")
    comment: Optional[str] = Field(default=None, description="Mandatory confirmation comment for approval")
    manager_id: Optional[str] = Field(default="SUPPLY_CHAIN_PLANNER")
    user_role: Optional[str] = Field(default="APPROVER", description="Role of the actor: APPROVER, VIEWER, PLANNER")
    modify_params: Optional[PlanModifyRequest] = Field(default=None, description="Modification parameters when decision is MODIFY")

    def get_effective_plan_id(self) -> Optional[str]:
        if self.plan_id:
            return self.plan_id
        if self.selected_plan_id:
            return self.selected_plan_id
        if self.modify_params and getattr(self.modify_params, "plan_id", None):
            return self.modify_params.plan_id
        return None

    def get_effective_version(self) -> Optional[str]:
        return self.version or self.selected_plan_version or "v1"

    def get_effective_comment(self) -> str:
        return (self.comment or self.rationale or "").strip()


class Checkpoint2Response(BaseModel):
    case_id: str = Field(default="", description="Case identifier")
    decision: str = Field(default="APPROVE", description="APPROVE, MODIFY, or REJECT")
    plan_id: Optional[str] = None
    version: Optional[str] = None
    status: str = Field(default="RECOVERY_APPROVED", description="RECOVERY_APPROVED, AWAITING_CHECKPOINT_2, PLAN_APPROVED, PLAN_MODIFIED, PLAN_REJECTED")
    message: str = Field(default="Checkpoint 2 processed.", description="Summary message")
    phase3_status: Optional[str] = Field(default="Recovery plan approved. Ready for Phase 3 Execution.", description="Phase 3 execution status")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str = "SUPPLY_CHAIN_PLANNER"
    approved_plan: Optional[RecoveryPlan] = None
    snapshot_id: Optional[str] = None
