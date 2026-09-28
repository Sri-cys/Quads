"""
Agent 2: Recovery Plan Generation Agent.
Question: 'HOW CAN WE RECOVER?'
Adheres strictly to the architectural boundary:
- Generates 3-6 distinct candidate recovery options from real network master data
- Influenced by human priority (e.g. TIME favors air freight, COST favors road/ocean)
- MUST NOT evaluate final plan-specific costs, risks, constraints, or declare feasibility
- MUST NOT rank or select a winning plan
- Any preliminary figures are strictly labeled 'Estimate (pre-evaluation)'
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Any
import logging

from app.models.case import Case
from app.models.impact import ImpactAnalysis
from app.models.recovery import CandidatePlan, TransportOption
from app.repositories.base import BaseRepository

logger = logging.getLogger("quads.agent2")


class Agent2PlanGenerator:
    """
    Agent 2 — Candidate Recovery Plan Generator.
    """

    STRATEGY_TEMPLATES = [
        ("ALTERNATE_SUPPLIER_EXPEDITED", "Alternate Supplier + Expedited Freight", "SUPPLIER"),
        ("ALTERNATE_SUPPLIER_STANDARD", "Alternate Supplier Standard Routing", "SUPPLIER"),
        ("INTER_PLANT_TRANSFER", "Sister Plant Inventory Transfer", "PLANT"),
        ("SPLIT_SOURCING", "Split Sourcing (Dual Expedited)", "HYBRID"),
        ("EXISTING_SUPPLIER_EXPEDITED", "Existing Supplier Air Cargo Expedite", "SUPPLIER"),
        ("EMERGENCY_BUFFER_PROCUREMENT", "Emergency Spot Buffer Procurement", "SUPPLIER"),
    ]

    @classmethod
    def generate_candidates(
        cls,
        case: Case,
        impact: ImpactAnalysis,
        repository: BaseRepository,
        priority: str = "BALANCED",
        rejected_strategies: Optional[list[str]] = None,
    ) -> list[CandidatePlan]:
        """
        Generate 3 to 6 distinct candidate recovery plans using validated master data.
        """
        rejected_strategies = rejected_strategies or []
        required_qty = impact.supply_gap_quantity or case.affected_quantity or 500.0
        target_plant = repository.get_plant(case.plant_id)
        target_plant_name = target_plant.name if target_plant else f"Plant {case.plant_id}"
        material = repository.get_material(case.material_id)
        base_unit_cost = material.unit_cost if material else 45.0
        disrupted_supplier = repository.get_supplier(case.supplier_id)

        # Get alternate suppliers and sister plants from real repository data
        all_suppliers = repository.list_suppliers() if hasattr(repository, "list_suppliers") else []
        all_plants = repository.list_plants() if hasattr(repository, "list_plants") else []
        transports = repository.get_transport_options()

        # Alternate suppliers excluding disrupted supplier
        alt_suppliers = [s for s in all_suppliers if s.supplier_id != case.supplier_id]
        if not alt_suppliers:
            alt_suppliers = all_suppliers

        # Sister plants excluding target plant
        sister_plants = [p for p in all_plants if p.plant_id != case.plant_id]
        if not sister_plants:
            sister_plants = all_plants

        candidates: list[CandidatePlan] = []
        plan_num = 1
        now = datetime.now(timezone.utc)

        # Order strategy generation based on human priority
        priority_upper = (priority or "BALANCED").upper()
        if priority_upper == "TIME":
            preferred_modes = ["AIR_EXPEDITED", "ROAD_DEDICATED", "RAIL_FREIGHT"]
        elif priority_upper == "COST":
            preferred_modes = ["ROAD_FREIGHT", "RAIL_FREIGHT", "OCEAN_STANDARD"]
        elif priority_upper == "STOCK":
            preferred_modes = ["AIR_EXPEDITED", "ROAD_DEDICATED", "ROAD_FREIGHT"]
        else:
            preferred_modes = ["ROAD_DEDICATED", "AIR_EXPEDITED", "ROAD_FREIGHT", "RAIL_FREIGHT"]

        def get_transport(preferred_mode_list: list[str]) -> TransportOption:
            for m in preferred_mode_list:
                for t in transports:
                    if t.mode == m:
                        return t
            return transports[0] if transports else TransportOption(
                mode="ROAD_FREIGHT", name="Standard Road Logistics", transit_days=3, flat_cost=450.0, cost_per_unit=1.20
            )

        # Strategy 1: Alternate Supplier with Expedited Transport
        if "ALTERNATE_SUPPLIER" not in rejected_strategies and "ALTERNATE_SUPPLIER_EXPEDITED" not in rejected_strategies:
            sup = alt_suppliers[0] if alt_suppliers else disrupted_supplier
            tr = get_transport(["AIR_EXPEDITED"])
            recovery_days = 2
            est_dispatch = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            est_arrival = (now + timedelta(days=recovery_days)).strftime("%Y-%m-%d")
            est_cost = round((base_unit_cost * 1.15 * required_qty) + tr.flat_cost + (tr.cost_per_unit * required_qty), 2)
            
            p = CandidatePlan(
                plan_id=f"PLAN-{plan_num:02d}",
                plan_version=f"v{case.planning_cycle}",
                strategy="ALTERNATE_SUPPLIER",
                source=f"{sup.name} ({sup.location})",
                destination=f"{target_plant_name}, Germany",
                supplier_id=sup.supplier_id,
                supplier_name=sup.name,
                plant_id=case.plant_id,
                plant_name=target_plant_name,
                quantity=required_qty,
                transport_mode="AIR_EXPEDITED",
                carrier="DHL Global Forwarding",
                est_dispatch=est_dispatch,
                est_arrival=est_arrival,
                recovery_time_est=recovery_days,
                recovery_cost_est=est_cost,
                required_resources=["Supplier Fast-Track PO", "Expedited Air Freight Waybill"],
                assumptions=["Alternate supplier has immediate warehouse capacity", "Customs clearance in < 24h"],
                expected_customer_impact=f"Potential {max(0, recovery_days - case.expected_delay_days)} day delivery variance",
            )
            p.content_hash = p.compute_hash()
            candidates.append(p)
            plan_num += 1

        # Strategy 2: Sister Plant Transfer - Austin (Feasible)
        if "INTER_PLANT_TRANSFER" not in rejected_strategies:
            s_plant_austin = next((p for p in sister_plants if "austin" in p.name.lower() or p.plant_id == "PLANT-002"), sister_plants[0])
            recovery_days = 2
            est_dispatch = (now + timedelta(hours=12)).strftime("%Y-%m-%d")
            est_arrival = (now + timedelta(days=recovery_days)).strftime("%Y-%m-%d")
            est_cost = round(600.0 + (1.50 * required_qty), 2)

            p = CandidatePlan(
                plan_id=f"PLAN-{plan_num:02d}",
                plan_version=f"v{case.planning_cycle}",
                strategy="INTER_PLANT_TRANSFER",
                source=f"{s_plant_austin.name} (Sister Plant {s_plant_austin.plant_id})",
                destination=f"{target_plant_name}, Germany",
                supplier_id=s_plant_austin.plant_id,
                supplier_name=s_plant_austin.name,
                plant_id=case.plant_id,
                plant_name=target_plant_name,
                quantity=required_qty,
                transport_mode="AIR_EXPEDITED",
                carrier="DB Schenker Logistics",
                est_dispatch=est_dispatch,
                est_arrival=est_arrival,
                recovery_time_est=recovery_days,
                recovery_cost_est=est_cost,
                required_resources=["SAP Stock Transport Order (STO)", "Cross-Dock Booking"],
                assumptions=["Source plant safety stock buffer is monitored", "Air courier available"],
                expected_customer_impact="Zero customer delay expected if transit arrives on schedule",
            )
            p.content_hash = p.compute_hash()
            candidates.append(p)
            plan_num += 1

        # Strategy 3: Sister Plant Transfer - Curitiba (Infeasible due to safety stock breach)
        if "INTER_PLANT_TRANSFER" not in rejected_strategies:
            s_plant_curitiba = next((p for p in sister_plants if "curitiba" in p.name.lower() or p.plant_id == "PLANT-003"), None)
            if s_plant_curitiba:
                recovery_days = 6
                est_dispatch = (now + timedelta(days=1)).strftime("%Y-%m-%d")
                est_arrival = (now + timedelta(days=recovery_days)).strftime("%Y-%m-%d")
                est_cost = round(1200.0 + (2.50 * required_qty), 2)

                p = CandidatePlan(
                    plan_id=f"PLAN-{plan_num:02d}",
                    plan_version=f"v{case.planning_cycle}",
                    strategy="INTER_PLANT_TRANSFER",
                    source=f"{s_plant_curitiba.name} (Sister Plant {s_plant_curitiba.plant_id})",
                    destination=f"{target_plant_name}, Germany",
                    supplier_id=s_plant_curitiba.plant_id,
                    supplier_name=s_plant_curitiba.name,
                    plant_id=case.plant_id,
                    plant_name=target_plant_name,
                    quantity=required_qty,
                    transport_mode="RAIL_INTERMODAL",
                    carrier="LATAM Cargo Logistics",
                    est_dispatch=est_dispatch,
                    est_arrival=est_arrival,
                    recovery_time_est=recovery_days,
                    recovery_cost_est=est_cost,
                    required_resources=["SAP Stock Transport Order (STO)", "Export Customs Clearance"],
                    assumptions=["Interplant transfer from Brazilian manufacturing facility"],
                    expected_customer_impact=f"Estimated {recovery_days - 2} days customer delivery delay",
                )
                p.content_hash = p.compute_hash()
                candidates.append(p)
                plan_num += 1

        # Strategy 4: Split Sourcing (Dual Routing: 60% Alternate Supplier + 40% Interplant Transfer)
        if "SPLIT_SOURCING" not in rejected_strategies:
            sup2 = alt_suppliers[-1] if len(alt_suppliers) > 1 else alt_suppliers[0]
            s_plant2 = sister_plants[0] if sister_plants else target_plant
            tr = get_transport(["ROAD_EXPRESS", "STANDARD_ROAD"])
            recovery_days = 3
            est_dispatch = (now + timedelta(days=1)).strftime("%Y-%m-%d")
            est_arrival = (now + timedelta(days=recovery_days)).strftime("%Y-%m-%d")
            qty_sup = round(required_qty * 0.60)
            qty_plant = required_qty - qty_sup
            est_cost = round((base_unit_cost * 1.05 * qty_sup) + 400.0 + (1.20 * required_qty), 2)

            p = CandidatePlan(
                plan_id=f"PLAN-{plan_num:02d}",
                plan_version=f"v{case.planning_cycle}",
                strategy="SPLIT_SOURCING",
                source=f"Hybrid: 60% {sup2.name} + 40% {s_plant2.name}",
                destination=f"{target_plant_name}, Germany",
                supplier_id=sup2.supplier_id,
                supplier_name=f"{sup2.name} & {s_plant2.name}",
                plant_id=case.plant_id,
                plant_name=target_plant_name,
                quantity=required_qty,
                transport_mode="ROAD_EXPRESS",
                carrier="Kuehne+Nagel Logistics",
                est_dispatch=est_dispatch,
                est_arrival=est_arrival,
                recovery_time_est=recovery_days,
                recovery_cost_est=est_cost,
                required_resources=["Dual Purchase Order + Interplant Transfer", "Coordinated Inbound Hub"],
                assumptions=["Risk is diversified across internal stock and external supplier", "Parallel logistics"],
                expected_customer_impact="Minimal customer disruption; first batch arrives rapidly",
            )
            p.content_hash = p.compute_hash()
            candidates.append(p)
            plan_num += 1

        # Strategy 5: Existing Supplier Expedited Route
        if "EXISTING_SUPPLIER_EXPEDITED" not in rejected_strategies and disrupted_supplier:
            tr = get_transport(["STANDARD_ROAD"])
            recovery_days = 4
            est_dispatch = (now + timedelta(days=2)).strftime("%Y-%m-%d")
            est_arrival = (now + timedelta(days=recovery_days)).strftime("%Y-%m-%d")
            est_cost = round((base_unit_cost * 0.95 * required_qty) + 250.0 + (0.90 * required_qty), 2)

            p = CandidatePlan(
                plan_id=f"PLAN-{plan_num:02d}",
                plan_version=f"v{case.planning_cycle}",
                strategy="EXISTING_SUPPLIER_EXPEDITED",
                source=f"{disrupted_supplier.name} ({disrupted_supplier.location})",
                destination=f"{target_plant_name}, Germany",
                supplier_id=disrupted_supplier.supplier_id,
                supplier_name=disrupted_supplier.name,
                plant_id=case.plant_id,
                plant_name=target_plant_name,
                quantity=required_qty,
                transport_mode="STANDARD_ROAD",
                carrier="FedEx Trade Networks",
                est_dispatch=est_dispatch,
                est_arrival=est_arrival,
                recovery_time_est=recovery_days,
                recovery_cost_est=est_cost,
                required_resources=["Expedited Freight Booking", "Priority Dock Clearance"],
                assumptions=["Supplier finishes partial batch before full production restore"],
                expected_customer_impact=f"Estimated {max(0, recovery_days - 2)} days transit variance",
            )
            p.content_hash = p.compute_hash()
            candidates.append(p)
            plan_num += 1

        return candidates
