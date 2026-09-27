from typing import TypedDict, Optional, Any


class SupplyChainState(TypedDict, total=False):
    case_id: str
    disruption: dict[str, Any]
    supplier: Optional[dict[str, Any]]
    material: Optional[dict[str, Any]]
    plant: Optional[dict[str, Any]]
    inventory: Optional[dict[str, Any]]
    demand: Optional[dict[str, Any]]
    safety_stock: Optional[dict[str, Any]]
    purchase_orders: list[dict[str, Any]]
    impact_analysis: Optional[dict[str, Any]]
    severity: Optional[str]
    status: str
    checkpoint1_decision: Optional[str]
    recovery_plan_set: Optional[dict[str, Any]]
    manager_constraints: Optional[dict[str, Any]]
    checkpoint2_decision: Optional[dict[str, Any]]
    approved_plan: Optional[dict[str, Any]]
    execution_record: Optional[dict[str, Any]]
    execution_baseline: Optional[dict[str, Any]]
    tracking_events: list[dict[str, Any]]
    failed_plans: list[dict[str, Any]]
    outcome_record: Optional[dict[str, Any]]
    errors: list[str]
    audit_events: list[dict[str, Any]]

