from datetime import datetime, timezone, timedelta
import pytest
from app.services.impact_service import ImpactService
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.disruption import Disruption
from app.config import severity_rules


def test_calculate_available_inventory():
    # Normal case
    inv = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0, reserved_quantity=20.0)
    assert ImpactService.calculate_available_inventory(inv) == 80.0

    # Reserved equals total
    inv2 = Inventory(material_id="MAT-001", plant_id="PLANT-001", quantity=50.0, reserved_quantity=50.0)
    assert ImpactService.calculate_available_inventory(inv2) == 0.0

    # None inventory
    assert ImpactService.calculate_available_inventory(None) == 0.0


def test_calculate_days_of_cover():
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=20.0)
    doc, status = ImpactService.calculate_days_of_cover(100.0, demand)
    assert doc == 5.0
    assert status == "AVAILABLE"

    # Zero demand -> None, ZERO_DEMAND
    zero_demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=0.0)
    doc_z, status_z = ImpactService.calculate_days_of_cover(100.0, zero_demand)
    assert doc_z is None
    assert status_z == "ZERO_DEMAND"

    # Missing demand -> None, DATA_UNAVAILABLE
    doc_m, status_m = ImpactService.calculate_days_of_cover(100.0, None)
    assert doc_m is None
    assert status_m == "DATA_UNAVAILABLE"


def test_calculate_stockout_date():
    base = datetime(2026, 9, 27, 6, 0, 0, tzinfo=timezone.utc)
    res = ImpactService.calculate_stockout_date(5.0, base_date=base)
    expected = (base + timedelta(days=5)).isoformat()
    assert res == expected

    # When doc is None -> None
    assert ImpactService.calculate_stockout_date(None) is None


def test_calculate_safety_stock_breach():
    ss = SafetyStock(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0)
    assert ImpactService.calculate_safety_stock_breach(50.0, ss) is True
    assert ImpactService.calculate_safety_stock_breach(100.0, ss) is False
    assert ImpactService.calculate_safety_stock_breach(150.0, ss) is False
    assert ImpactService.calculate_safety_stock_breach(50.0, None) is False


def test_calculate_supply_gap():
    ss = SafetyStock(material_id="MAT-001", plant_id="PLANT-001", quantity=100.0)
    demand = Demand(material_id="MAT-001", plant_id="PLANT-001", daily_demand=20.0)
    # Required = 100 + (20 * 5) = 200
    # Available = 50, Open PO = 100 -> Total available = 150 -> Gap = 50
    po = PurchaseOrder(
        po_id="PO-001",
        supplier_id="SUP-001",
        material_id="MAT-001",
        plant_id="PLANT-001",
        quantity=100.0,
        expected_delivery_date="2026-10-01T00:00:00Z",
        status="OPEN",
    )
    gap = ImpactService.calculate_supply_gap(
        available_inventory=50.0,
        safety_stock=ss,
        demand=demand,
        delay_days=5,
        purchase_orders=[po],
    )
    assert gap == 50.0


def test_severity_rules_critical_doc():
    # Condition: days_of_cover <= 3.0
    sev = ImpactService.evaluate_severity(
        days_of_cover=2.5,
        supply_gap_quantity=0.0,
        available_inventory=50.0,
        safety_stock_breach=False,
    )
    assert sev == severity_rules.SEVERITY_CRITICAL


def test_severity_rules_critical_gap_zero_inventory():
    # Condition: supply_gap > 0 and available_inventory <= 0
    sev = ImpactService.evaluate_severity(
        days_of_cover=None,
        supply_gap_quantity=200.0,
        available_inventory=0.0,
        safety_stock_breach=True,
    )
    assert sev == severity_rules.SEVERITY_CRITICAL


def test_severity_rules_high_safety_stock_breach():
    # Condition: safety_stock_breach is True
    sev = ImpactService.evaluate_severity(
        days_of_cover=8.0,
        supply_gap_quantity=0.0,
        available_inventory=80.0,
        safety_stock_breach=True,
    )
    assert sev == severity_rules.SEVERITY_HIGH


def test_severity_rules_high_doc():
    # Condition: days_of_cover <= 7.0
    sev = ImpactService.evaluate_severity(
        days_of_cover=6.5,
        supply_gap_quantity=0.0,
        available_inventory=130.0,
        safety_stock_breach=False,
    )
    assert sev == severity_rules.SEVERITY_HIGH


def test_severity_rules_medium_doc():
    # Condition: days_of_cover <= 14.0
    sev = ImpactService.evaluate_severity(
        days_of_cover=12.0,
        supply_gap_quantity=0.0,
        available_inventory=240.0,
        safety_stock_breach=False,
    )
    assert sev == severity_rules.SEVERITY_MEDIUM


def test_severity_rules_medium_gap():
    # Condition: supply_gap > 0 (and not critical or high)
    sev = ImpactService.evaluate_severity(
        days_of_cover=18.0,
        supply_gap_quantity=50.0,
        available_inventory=200.0,
        safety_stock_breach=False,
    )
    assert sev == severity_rules.SEVERITY_MEDIUM


def test_severity_rules_low():
    # Condition: none of the above
    sev = ImpactService.evaluate_severity(
        days_of_cover=25.0,
        supply_gap_quantity=0.0,
        available_inventory=500.0,
        safety_stock_breach=False,
    )
    assert sev == severity_rules.SEVERITY_LOW
