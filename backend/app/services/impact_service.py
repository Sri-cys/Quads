"""
Deterministic Business Impact Calculation Service for Quads Phase 1.
Implements pure deterministic business logic for Agent 1.
Zero GenAI involvement in numerical calculations.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import math

from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.disruption import Disruption
from app.models.impact import DownstreamImpact, ImpactAnalysis
from app.config import severity_rules


class ImpactService:
    """
    Computes exact, deterministic supply chain metrics for a disruption:
    - Available Inventory
    - Days of Cover
    - Stockout Date
    - Safety Stock Breach
    - Supply Gap
    - Severity Tiering
    - Downstream Impact
    """

    @staticmethod
    def calculate_available_inventory(inventory: Optional[Inventory]) -> float:
        """
        Formula: available_inventory = max(0.0, inventory_quantity - reserved_quantity)
        """
        if not inventory:
            return 0.0
        return max(0.0, inventory.quantity - inventory.reserved_quantity)

    @staticmethod
    def calculate_days_of_cover(
        available_inventory: float,
        demand: Optional[Demand],
    ) -> tuple[Optional[float], str]:
        """
        Formula: days_of_cover = available_inventory / daily_demand
        Returns (days_of_cover, demand_status).
        Handles:
        - None demand -> (None, "DATA_UNAVAILABLE")
        - Zero demand -> (None, "ZERO_DEMAND")
        - Valid demand -> (round(available_inventory / daily_demand, 2), "AVAILABLE")
        """
        if demand is None:
            return None, "DATA_UNAVAILABLE"
        if demand.daily_demand <= 0.0:
            return None, "ZERO_DEMAND"
        
        doc = available_inventory / demand.daily_demand
        return round(doc, 2), "AVAILABLE"

    @staticmethod
    def calculate_stockout_date(
        days_of_cover: Optional[float],
        base_date: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Formula: stockout_date = base_date (UTC) + days_of_cover
        Returns ISO 8601 UTC timestamp string, or None if days_of_cover is None.
        """
        if days_of_cover is None:
            return None
        
        now = base_date or datetime.now(timezone.utc)
        stockout_dt = now + timedelta(days=days_of_cover)
        return stockout_dt.isoformat()

    @staticmethod
    def calculate_safety_stock_breach(
        available_inventory: float,
        safety_stock: Optional[SafetyStock],
    ) -> bool:
        """
        Formula: available_inventory < safety_stock_quantity
        """
        if not safety_stock:
            return False
        return available_inventory < safety_stock.quantity

    @staticmethod
    def calculate_supply_gap(
        available_inventory: float,
        safety_stock: Optional[SafetyStock],
        demand: Optional[Demand],
        delay_days: int,
        purchase_orders: list[PurchaseOrder],
    ) -> float:
        """
        Deterministic Supply Gap Formula:
        target_requirement = safety_stock_quantity + (daily_demand * delay_days)
        inbound_open_supply = sum(PO.quantity for PO in purchase_orders if PO.status == 'OPEN')
        total_supply = available_inventory + inbound_open_supply
        supply_gap = max(0.0, target_requirement - total_supply)
        """
        ss_qty = safety_stock.quantity if safety_stock else 0.0
        daily_d = demand.daily_demand if demand and demand.daily_demand > 0.0 else 0.0
        demand_during_delay = daily_d * max(0, delay_days)
        
        target_requirement = ss_qty + demand_during_delay
        
        # Consider open PO quantity that has not yet been delayed indefinitely
        open_po_supply = sum(
            po.quantity for po in purchase_orders if po.status in {"OPEN", "IN_TRANSIT"}
        )
        
        total_available = available_inventory + open_po_supply
        gap = target_requirement - total_available
        return round(max(0.0, gap), 2)

    @staticmethod
    def evaluate_severity(
        days_of_cover: Optional[float],
        supply_gap_quantity: float,
        available_inventory: float,
        safety_stock_breach: bool,
    ) -> str:
        """
        Deterministic severity rules configured in app.config.severity_rules:
        CRITICAL:
          days_of_cover is not null AND days_of_cover <= CRITICAL_DAYS_OF_COVER_THRESHOLD
          OR supply_gap_quantity > 0 AND available_inventory <= CRITICAL_INVENTORY_ZERO_THRESHOLD
        HIGH:
          safety_stock_breach is true
          OR (days_of_cover is not null AND days_of_cover <= HIGH_DAYS_OF_COVER_THRESHOLD)
        MEDIUM:
          (days_of_cover is not null AND days_of_cover <= MEDIUM_DAYS_OF_COVER_THRESHOLD)
          OR supply_gap_quantity > 0
        LOW:
          None of the above conditions hold
        """
        # CRITICAL check
        is_critical_doc = (
            days_of_cover is not None
            and days_of_cover <= severity_rules.CRITICAL_DAYS_OF_COVER_THRESHOLD
        )
        is_critical_gap_zero_inv = (
            supply_gap_quantity > 0.0
            and available_inventory <= severity_rules.CRITICAL_INVENTORY_ZERO_THRESHOLD
        )
        if is_critical_doc or is_critical_gap_zero_inv:
            return severity_rules.SEVERITY_CRITICAL

        # HIGH check
        is_high_doc = (
            days_of_cover is not None
            and days_of_cover <= severity_rules.HIGH_DAYS_OF_COVER_THRESHOLD
        )
        if safety_stock_breach or is_high_doc:
            return severity_rules.SEVERITY_HIGH

        # MEDIUM check
        is_medium_doc = (
            days_of_cover is not None
            and days_of_cover <= severity_rules.MEDIUM_DAYS_OF_COVER_THRESHOLD
        )
        if is_medium_doc or supply_gap_quantity > 0.0:
            return severity_rules.SEVERITY_MEDIUM

        # LOW check
        return severity_rules.SEVERITY_LOW

    @classmethod
    def analyze(
        cls,
        case_id: str,
        disruption: Disruption,
        supplier: Optional[Supplier],
        material: Optional[Material],
        plant: Optional[Plant],
        inventory: Optional[Inventory],
        demand: Optional[Demand],
        safety_stock: Optional[SafetyStock],
        purchase_orders: list[PurchaseOrder],
        base_date: Optional[datetime] = None,
    ) -> ImpactAnalysis:
        """
        Execute the full deterministic Agent 1 impact calculation.
        """
        avail_inv = cls.calculate_available_inventory(inventory)
        total_inv = inventory.quantity if inventory else 0.0
        res_inv = inventory.reserved_quantity if inventory else 0.0

        daily_d = demand.daily_demand if demand else None
        doc, demand_status = cls.calculate_days_of_cover(avail_inv, demand)
        stockout_dt = cls.calculate_stockout_date(doc, base_date=base_date)
        ss_breach = cls.calculate_safety_stock_breach(avail_inv, safety_stock)
        ss_qty = safety_stock.quantity if safety_stock else 0.0

        gap_qty = cls.calculate_supply_gap(
            available_inventory=avail_inv,
            safety_stock=safety_stock,
            demand=demand,
            delay_days=disruption.expected_delay_days,
            purchase_orders=purchase_orders,
        )

        severity = cls.evaluate_severity(
            days_of_cover=doc,
            supply_gap_quantity=gap_qty,
            available_inventory=avail_inv,
            safety_stock_breach=ss_breach,
        )

        # Downstream Exposure calculation
        delay_days = max(1, disruption.expected_delay_days)
        demand_exp = (daily_d * delay_days) if daily_d else 0.0
        unit_cost = material.unit_cost if material else 0.0
        financial_exp = round(max(demand_exp, gap_qty) * unit_cost, 2)

        risk_indicators = []
        if doc is not None and doc <= 3.0:
            risk_indicators.append(f"Immediate stockout hazard within {doc} days")
        if ss_breach:
            risk_indicators.append("Safety buffer depleted below mandatory operational threshold")
        if gap_qty > 0:
            risk_indicators.append(f"Projected supply gap of {gap_qty:,.1f} units")
        if supplier and supplier.reliability_score < 0.85:
            risk_indicators.append(f"High-risk supplier reliability: {supplier.reliability_score * 100:.0f}%")
        if not risk_indicators:
            risk_indicators.append("Sufficient inventory buffer; production lines nominal")

        downstream = DownstreamImpact(
            affected_material_id=material.material_id if material else disruption.material_id,
            affected_material_name=material.name if material else "Unknown Material",
            affected_plant_id=plant.plant_id if plant else disruption.plant_id,
            affected_plant_name=plant.name if plant else "Unknown Plant",
            affected_supplier_id=supplier.supplier_id if supplier else disruption.supplier_id,
            affected_supplier_name=supplier.name if supplier else "Unknown Supplier",
            affected_purchase_orders=[po.po_id for po in purchase_orders],
            demand_exposure_units=demand_exp,
            inventory_exposure_units=avail_inv,
            financial_exposure=financial_exp,
            production_risk_indicators=risk_indicators,
        )

        return ImpactAnalysis(
            case_id=case_id,
            severity=severity,
            available_inventory=avail_inv,
            reserved_quantity=res_inv,
            total_inventory=total_inv,
            daily_demand=daily_d,
            demand_status=demand_status,
            days_of_cover=doc,
            stockout_date=stockout_dt,
            safety_stock_quantity=ss_qty,
            safety_stock_breach=ss_breach,
            supply_gap_quantity=gap_qty,
            downstream_impact=downstream,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            ai_explanation=None,
            ai_status="UNAVAILABLE",
        )
