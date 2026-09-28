from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field
from app.models.recovery import RecoveryPlan


class ExecutionBaseline(BaseModel):
    """
    Immutable planned recovery baseline established at Checkpoint 2 approval.
    Preserves what was planned so it can be compared with actuals.
    """
    case_id: str
    plan_id: str
    plan_version: str
    strategy: str
    source_id: str
    source_name: str
    source_location: str
    target_plant_id: str
    target_plant_name: str
    material_id: str
    planned_quantity: float
    planned_recovery_days: int
    planned_arrival_date: str
    planned_total_cost: float
    planned_transport_mode: str
    approved_by: str = "SUPPLY_CHAIN_PLANNER"
    approved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approval_rationale: Optional[str] = None


class TrackingEvent(BaseModel):
    """
    Point-in-time progress telemetry event emitted during logistics / supplier execution.
    """
    event_id: str = Field(default_factory=lambda: f"EVT-{datetime.now(timezone.utc).strftime('%H%M%S%f')[:10]}")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = Field(..., description="ACCEPTED, SUPPLIER_CONFIRMED, SHIPMENT_CREATED, SHIPMENT_DISPATCHED, IN_TRANSIT, DELAYED, DELIVERED, FAILED")
    location: str = Field(default="In Transit")
    description: str
    confirmed_quantity: Optional[float] = None
    estimated_arrival: Optional[str] = None
    actual_cost: Optional[float] = None
    source_system: str = "SAP Transportation Management (Mock)"


class ExecutionAction(BaseModel):
    """
    Enterprise recovery order / action registered via the SAP adapter layer.
    """
    action_id: str
    case_id: str
    plan_id: str
    plan_version: str
    action_type: str = Field(..., description="EMERGENCY_PURCHASE_ORDER, STOCK_TRANSPORT_ORDER, SPLIT_SOURCING_ORDER, EXPEDITED_FREIGHT_BOOKING")
    external_reference: str = Field(..., description="SAP PO / STO / Freight Order Document Number")
    external_system: str = "SAP S/4HANA & TM"
    status: str = Field(default="ACCEPTED", description="ACCEPTED, SUPPLIER_CONFIRMED, SHIPMENT_CREATED, SHIPMENT_DISPATCHED, IN_TRANSIT, DELAYED, DELIVERED, FAILED")
    carrier_name: Optional[str] = None
    tracking_number: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None


class ExecutionDeviation(BaseModel):
    """
    Quantified comparison between original planned baseline and actual execution progress.
    """
    quantity_shortage: float = 0.0
    delay_days: int = 0
    cost_variance: float = 0.0
    is_critical: bool = False
    explanation: str = "Execution is tracking nominally within planned boundaries."


class FailedPlanRecord(BaseModel):
    """
    Preserved record of an attempted recovery plan that failed during execution.
    Used to prevent repeating the failed strategy in subsequent replanning loops.
    """
    case_id: str
    plan_id: str
    plan_version: str
    strategy: str
    source_id: str
    source_name: str
    failed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    failure_reason: str
    planned_quantity: float
    confirmed_quantity: float
    planned_arrival: str
    actual_arrival_or_failed_date: str
    delay_days: int
    notes: Optional[str] = None


class HistoricalOutcomeRecord(BaseModel):
    """
    Certified post-resolution outcome stored to empower future historical retrieval and learning.
    """
    record_id: str = Field(default_factory=lambda: f"HIST-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}")
    case_id: str
    disruption_type: str
    supplier_id: str
    material_id: str
    plant_id: str
    initial_severity: str
    manager_priority: str
    strategy_used: str
    plan_id: str
    plan_version: str
    planned_quantity: float
    actual_quantity: float
    planned_days: int
    actual_days: int
    planned_cost: float
    actual_cost: float
    success: bool
    outcome_summary: str
    lessons_learned: str
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ExecutionProgress(BaseModel):
    """
    Aggregated execution state for real-time monitoring and frontend visualization.
    """
    case_id: str
    execution_status: str
    baseline: ExecutionBaseline
    action: ExecutionAction
    tracking_events: list[TrackingEvent] = []
    current_confirmed_quantity: float
    current_estimated_arrival: str
    current_estimated_cost: float
    deviation: ExecutionDeviation
    is_success: bool = False
    is_failed: bool = False
    failure_reason: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_status: str = "FALLBACK"
    can_replan: bool = False
    can_resolve: bool = False
    monitoring_status: str = "ON_TRACK"
    action_required: bool = False
    supplier_status: str = "CONFIRMED"
    shipment_status: str = "IN_TRANSIT"
    inventory_status: str = "PROTECTED"
    production_status: str = "NORMAL"
    customer_impact: str = "0 DELAYED ORDERS"
    risk_status: str = "LOW"
    last_updated: Optional[str] = None


class ExecutePlanRequest(BaseModel):
    plan_id: str
    version: str
    manager_id: Optional[str] = "SUPPLY_CHAIN_PLANNER"


class SimulateEventRequest(BaseModel):
    status: str = Field(..., description="SUPPLIER_CONFIRMED, SHIPMENT_CREATED, SHIPMENT_DISPATCHED, IN_TRANSIT, DELAYED, DELIVERED, FAILED")
    location: Optional[str] = "Regional Distribution Node"
    description: Optional[str] = None
    confirmed_quantity: Optional[float] = None
    new_eta: Optional[str] = None
    actual_cost: Optional[float] = None
    reason: Optional[str] = None
