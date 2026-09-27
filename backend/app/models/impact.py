from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field


class DownstreamImpact(BaseModel):
    affected_material_id: str
    affected_material_name: str
    affected_plant_id: str
    affected_plant_name: str
    affected_supplier_id: str
    affected_supplier_name: str
    affected_purchase_orders: list[str] = Field(default_factory=list)
    demand_exposure_units: float = Field(default=0.0)
    inventory_exposure_units: float = Field(default=0.0)
    financial_exposure: float = Field(default=0.0)
    production_risk_indicators: list[str] = Field(default_factory=list)


class ImpactAnalysis(BaseModel):
    case_id: str
    severity: str
    available_inventory: float
    reserved_quantity: float
    total_inventory: float
    daily_demand: Optional[float] = None
    demand_status: str = Field(default="AVAILABLE", description="AVAILABLE, ZERO_DEMAND, or DATA_UNAVAILABLE")
    days_of_cover: Optional[float] = None
    stockout_date: Optional[str] = None
    safety_stock_quantity: float = 0.0
    safety_stock_breach: bool = False
    supply_gap_quantity: float = 0.0
    downstream_impact: DownstreamImpact
    calculated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ai_explanation: Optional[str] = None
    ai_status: str = Field(default="UNAVAILABLE", description="AVAILABLE, UNAVAILABLE, or FAILED")


class AuditEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    case_id: str
    event: str
    actor: str
    details: str


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Short machine-readable error code")
    message: str = Field(..., description="Human-readable error explanation")
