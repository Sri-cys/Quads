from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class DisruptionCreate(BaseModel):
    disruption_type: str = Field(..., min_length=2, description="Type of disruption (e.g. SUPPLIER_DELAY, PORT_CONGESTION)")
    description: str = Field(..., min_length=5, description="Detailed natural language disruption description")
    supplier_id: str = Field(..., description="Affected supplier identifier (SUP-###)")
    material_id: str = Field(..., description="Affected material identifier (MAT-###)")
    plant_id: str = Field(..., description="Affected plant identifier (PLANT-###)")
    expected_delay_days: int = Field(default=5, ge=0, description="Estimated delay in days")
    affected_quantity: Optional[float] = Field(default=None, ge=0.0, description="Affected shipment quantity")


class Disruption(BaseModel):
    disruption_type: str = Field(...)
    description: str = Field(...)
    supplier_id: str = Field(...)
    material_id: str = Field(...)
    plant_id: str = Field(...)
    expected_delay_days: int = Field(default=5, ge=0)
    affected_quantity: Optional[float] = Field(default=None)
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
