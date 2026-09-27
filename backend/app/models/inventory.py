from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Inventory(BaseModel):
    material_id: str = Field(..., description="Unique material identifier")
    plant_id: str = Field(..., description="Unique plant identifier")
    quantity: float = Field(..., ge=0.0, description="Total physical inventory quantity on hand")
    reserved_quantity: float = Field(default=0.0, ge=0.0, description="Reserved or allocated inventory quantity")

    @property
    def available_quantity(self) -> float:
        return max(0.0, self.quantity - self.reserved_quantity)


class Demand(BaseModel):
    material_id: str = Field(..., description="Unique material identifier")
    plant_id: str = Field(..., description="Unique plant identifier")
    daily_demand: float = Field(..., ge=0.0, description="Average daily consumption/demand quantity")


class SafetyStock(BaseModel):
    material_id: str = Field(..., description="Unique material identifier")
    plant_id: str = Field(..., description="Unique plant identifier")
    quantity: float = Field(..., ge=0.0, description="Required buffer/safety stock quantity")


class PurchaseOrder(BaseModel):
    po_id: str = Field(..., description="Unique purchase order identifier (PO-###)")
    supplier_id: str = Field(..., description="Supplier ID")
    material_id: str = Field(..., description="Material ID")
    plant_id: str = Field(..., description="Plant ID")
    quantity: float = Field(..., gt=0.0, description="Order quantity")
    expected_delivery_date: str = Field(..., description="Expected delivery date in UTC ISO 8601")
    status: str = Field(default="OPEN", description="PO status (OPEN, IN_TRANSIT, DELIVERED, CANCELLED)")
