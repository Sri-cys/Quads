from pydantic import BaseModel, Field


class Supplier(BaseModel):
    supplier_id: str = Field(..., description="Unique supplier identifier (SUP-###)")
    name: str = Field(..., description="Supplier company name")
    location: str = Field(..., description="Supplier headquarters or primary facility location")
    reliability_score: float = Field(..., ge=0.0, le=1.0, description="Reliability score between 0.0 and 1.0")
    materials_supplied: list[str] = Field(default_factory=list, description="List of material IDs this supplier is qualified to deliver")
    available_capacity: float = Field(default=500.0, description="Available uncommitted production/shipment capacity in units")
    standard_lead_time_days: int = Field(default=7, description="Standard procurement and shipment lead time in days")
    expedited_lead_time_days: int = Field(default=3, description="Expedited rush lead time in days")
    unit_cost_modifier: float = Field(default=1.0, description="Price multiplier relative to base material cost")


class Plant(BaseModel):
    plant_id: str = Field(..., description="Unique plant identifier (PLANT-###)")
    name: str = Field(..., description="Plant facility name")
    location: str = Field(..., description="Plant geographic location")


class Material(BaseModel):
    material_id: str = Field(..., description="Unique material identifier (MAT-###)")
    name: str = Field(..., description="Material name")
    category: str = Field(..., description="Material category")
    unit_cost: float = Field(..., ge=0.0, description="Unit cost in standard currency")
