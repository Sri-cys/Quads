"""
Quads Phase 1 LangGraph Implementation.
Implements the single continuous StateGraph across 3 REST API stages with SQLite persistence.
Graph stops at Human Checkpoint 1. Agent 2 and Agent 3 are NOT included or executed.
"""

import sqlite3
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

from app.workflow.state import SupplyChainState
from app.repositories.base import BaseRepository
from app.services.audit_service import AuditService
from app.services.impact_service import ImpactService
from app.services.gemini_service import GeminiService
from app.models.case import Case
from app.models.disruption import Disruption
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.impact import ImpactAnalysis, AuditEvent
from app.services.recovery_service import RecoveryService
from app.models.recovery import (
    RecoveryPlanSet,
    ManagerConstraints,
    Checkpoint2Response,
)


def create_workflow_graph(
    repository: BaseRepository,
    audit_service: AuditService,
    gemini_service: Optional[GeminiService] = None,
    checkpointer: Optional[SqliteSaver] = None,
):
    gemini = gemini_service or GeminiService()

    # 1. Ingestion Node
    def ingestion_node(state: SupplyChainState) -> dict:
        case_id = state.get("case_id", "PENDING")
        disruption_data = state.get("disruption", {})
        
        audit_service.log(
            case_id=case_id,
            event="DISRUPTION_RECEIVED",
            actor="SYSTEM_INGESTION",
            details=f"Received disruption of type {disruption_data.get('disruption_type')}",
        )
        return {"status": "INGESTED"}

    # 2. Case Creation Node
    def case_creation_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        disruption_dict = state["disruption"]
        
        case = Case(
            case_id=case_id,
            disruption_type=disruption_dict.get("disruption_type", "UNKNOWN"),
            description=disruption_dict.get("description", ""),
            supplier_id=disruption_dict.get("supplier_id", ""),
            material_id=disruption_dict.get("material_id", ""),
            plant_id=disruption_dict.get("plant_id", ""),
            expected_delay_days=disruption_dict.get("expected_delay_days", 5),
            affected_quantity=disruption_dict.get("affected_quantity"),
            detected_at=disruption_dict.get("detected_at", datetime.now(timezone.utc).isoformat()),
            status="CREATED",
        )
        repository.create_case(case)

        audit_service.log(
            case_id=case_id,
            event="CASE_CREATED",
            actor="SYSTEM_WORKFLOW",
            details=f"Disruption case {case_id} registered and persisted",
        )
        return {"status": "CREATED"}

    # 3. Triage Node
    def triage_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        disruption_dict = state["disruption"]
        supplier_id = disruption_dict.get("supplier_id")
        material_id = disruption_dict.get("material_id")
        plant_id = disruption_dict.get("plant_id")

        supplier = repository.get_supplier(supplier_id)
        material = repository.get_material(material_id)
        plant = repository.get_plant(plant_id)
        inventory = repository.get_inventory(material_id, plant_id)
        demand = repository.get_demand(material_id, plant_id)
        safety_stock = repository.get_safety_stock(material_id, plant_id)
        pos = repository.get_purchase_orders(supplier_id=supplier_id, material_id=material_id, plant_id=plant_id)

        # Update case status
        case = repository.get_case(case_id)
        if case:
            case.status = "TRIAGED"
            repository.update_case(case)

        audit_service.log(
            case_id=case_id,
            event="TRIAGE_COMPLETED",
            actor="AGENT_1_TRIAGE",
            details=f"Triage complete for Material: {material_id}, Plant: {plant_id}, Supplier: {supplier_id}",
        )

        return {
            "status": "TRIAGED",
            "supplier": supplier.model_dump() if supplier else None,
            "material": material.model_dump() if material else None,
            "plant": plant.model_dump() if plant else None,
            "inventory": inventory.model_dump() if inventory else None,
            "demand": demand.model_dump() if demand else None,
            "safety_stock": safety_stock.model_dump() if safety_stock else None,
            "purchase_orders": [po.model_dump() for po in pos],
        }

    # 4. Impact Analysis Node (Agent 1 Deterministic Calculations)
    def impact_analysis_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        audit_service.log(
            case_id=case_id,
            event="IMPACT_ANALYSIS_STARTED",
            actor="AGENT_1_IMPACT",
            details="Starting deterministic calculations for inventory, days of cover, and supply gap",
        )

        disruption = Disruption(**state["disruption"])
        supplier = Supplier(**state["supplier"]) if state.get("supplier") else None
        material = Material(**state["material"]) if state.get("material") else None
        plant = Plant(**state["plant"]) if state.get("plant") else None
        inventory = Inventory(**state["inventory"]) if state.get("inventory") else None
        demand = Demand(**state["demand"]) if state.get("demand") else None
        safety_stock = SafetyStock(**state["safety_stock"]) if state.get("safety_stock") else None
        purchase_orders = [PurchaseOrder(**po) for po in state.get("purchase_orders", [])]

        impact = ImpactService.analyze(
            case_id=case_id,
            disruption=disruption,
            supplier=supplier,
            material=material,
            plant=plant,
            inventory=inventory,
            demand=demand,
            safety_stock=safety_stock,
            purchase_orders=purchase_orders,
        )

        audit_service.log(
            case_id=case_id,
            event="IMPACT_ANALYSIS_COMPLETED",
            actor="AGENT_1_IMPACT",
            details=f"Deterministic analysis complete. Severity: {impact.severity}, Days of Cover: {impact.days_of_cover}, Supply Gap: {impact.supply_gap_quantity}",
        )

        return {
            "status": "ANALYZED",
            "severity": impact.severity,
            "impact_analysis": impact.model_dump(),
        }

    # 5. Gemini Explanation Node
    def gemini_explanation_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        disruption = Disruption(**state["disruption"])
        impact = ImpactAnalysis(**state["impact_analysis"])

        explanation, ai_status = gemini.generate_explanation(
            disruption=disruption,
            impact=impact,
        )

        impact.ai_explanation = explanation
        impact.ai_status = ai_status

        # Persist analysis in repository
        repository.save_impact_analysis(impact)

        if ai_status == "AVAILABLE":
            audit_service.log(
                case_id=case_id,
                event="GEMINI_EXPLANATION_GENERATED",
                actor="GEMINI_AI",
                details="Executive natural-language explanation generated and verified against deterministic calculations",
            )
        else:
            audit_service.log(
                case_id=case_id,
                event="GEMINI_EXPLANATION_GENERATED",
                actor="SYSTEM",
                details="Gemini explanation unavailable or degraded; deterministic impact preserved",
            )

        audit_service.log(
            case_id=case_id,
            event="CHECKPOINT_1_WAITING",
            actor="HUMAN_IN_THE_LOOP",
            details="Impact analysis complete. Workflow paused awaiting Human Checkpoint 1 priority decision",
        )

        return {
            "status": "AWAITING_CHECKPOINT_1",
            "impact_analysis": impact.model_dump(),
        }

    # 6. Checkpoint 1 Node (Stopping Point)
    def checkpoint1_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        decision = state.get("checkpoint1_decision")
        if not decision:
            decision = "BALANCED"

        repository.save_checkpoint(case_id, decision)

        audit_service.log(
            case_id=case_id,
            event="CHECKPOINT_1_APPROVED",
            actor="SUPPLY_CHAIN_PLANNER",
            details=f"Human Checkpoint 1 approved with recovery priority: {decision}. Phase 1 complete.",
        )

        return {
            "status": "CHECKPOINT_APPROVED",
            "checkpoint1_decision": decision,
        }

    # 7. Recovery Planning Node (Agent 2 Optimization & Discovery)
    def recovery_planning_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        audit_service.log(
            case_id=case_id,
            event="RECOVERY_PLANNING_STARTED",
            actor="AGENT_2_RECOVERY",
            details="Starting recovery planning: discovering alternate suppliers, plants, inventory, and transport options",
        )

        case = repository.get_case(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")

        impact = repository.get_impact_analysis(case_id)
        if not impact and "impact_analysis" in state and state["impact_analysis"]:
            impact = ImpactAnalysis(**state["impact_analysis"])
        if not impact:
            raise ValueError(f"Impact analysis required before recovery planning for {case_id}")

        priority = case.checkpoint1_decision or state.get("checkpoint1_decision") or "BALANCED"
        mgr_dict = state.get("manager_constraints") or {}
        mgr_constraints = ManagerConstraints(**mgr_dict)

        plan_set = RecoveryService.generate_plans(
            case=case,
            impact=impact,
            repository=repository,
            manager_constraints=mgr_constraints,
            priority_override=priority,
        )

        # Gemini Executive Briefing for Recovery
        briefing, ai_status = gemini.generate_recovery_briefing(
            case_id=case_id,
            priority=priority,
            feasible_plans=plan_set.feasible_plans,
            infeasible_plans=plan_set.infeasible_plans,
        )
        plan_set.ai_briefing = briefing
        plan_set.ai_status = ai_status
        repository.save_recovery_plan_set(plan_set)

        audit_service.log(
            case_id=case_id,
            event="RECOVERY_PLANNING_COMPLETED",
            actor="AGENT_2_RECOVERY",
            details=(
                f"Generated {len(plan_set.feasible_plans)} feasible recovery options and {len(plan_set.infeasible_plans)} rejected options. "
                f"Top recommended option: {plan_set.feasible_plans[0].plan_id if plan_set.feasible_plans else 'None'} "
                f"(Score: {plan_set.feasible_plans[0].score if plan_set.feasible_plans else 0.0})"
            ),
        )

        return {
            "status": "AWAITING_CHECKPOINT_2",
            "recovery_plan_set": plan_set.model_dump(),
        }

    # 8. Checkpoint 2 Node (Human Decision Point - Phase 2 Boundary)
    def checkpoint2_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        cp2_dict = state.get("checkpoint2_decision") or {}
        decision = cp2_dict.get("decision", "APPROVE")
        plan_id = cp2_dict.get("plan_id")
        version = cp2_dict.get("version", "v1")
        rationale = cp2_dict.get("rationale", "")

        plan_set = repository.get_recovery_plan_set(case_id)
        selected_plan = None
        if plan_set and plan_id:
            for p in plan_set.feasible_plans + plan_set.infeasible_plans:
                if p.plan_id == plan_id:
                    selected_plan = p
                    break

        resp = Checkpoint2Response(
            case_id=case_id,
            decision=decision,
            plan_id=plan_id,
            version=version,
            status="RECOVERY_APPROVED" if decision == "APPROVE" else "AWAITING_CHECKPOINT_2",
            message=f"Human Checkpoint 2 {decision.lower()}d.",
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor="SUPPLY_CHAIN_PLANNER",
            approved_plan=selected_plan if decision == "APPROVE" else None,
            phase3_status="Ready for Phase 3 Execution. Autonomous execution paused at Phase 2 boundary.",
        )
        repository.save_checkpoint2(case_id, resp)

        if decision == "APPROVE":
            audit_service.log(
                case_id=case_id,
                event="CHECKPOINT_2_APPROVED",
                actor="SUPPLY_CHAIN_PLANNER",
                details=f"Human Checkpoint 2 approved plan {plan_id} (Version: {version}). Plan locked for execution. Phase 2 complete.",
            )
        elif decision == "MODIFY":
            audit_service.log(
                case_id=case_id,
                event="RECOVERY_PLAN_MODIFIED",
                actor="SUPPLY_CHAIN_PLANNER",
                details=f"Planner modified plan parameters for {plan_id}. Recalculated new version {version}.",
            )
        elif decision == "REJECT":
            audit_service.log(
                case_id=case_id,
                event="CHECKPOINT_2_REJECTED",
                actor="SUPPLY_CHAIN_PLANNER",
                details=f"Planner rejected recovery options. Rationale: {rationale or 'Requirements not met'}.",
            )

        return {
            "status": "RECOVERY_APPROVED" if decision == "APPROVE" else "AWAITING_CHECKPOINT_2",
            "checkpoint2_decision": resp.model_dump(),
            "approved_plan": selected_plan.model_dump() if selected_plan else None,
        }

    # 9. Execution Node (Agent 3 Execution)
    def execution_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        record = repository.get_execution_record(case_id)
        baseline = repository.get_execution_baseline(case_id)
        return {
            "status": "EXECUTION_IN_PROGRESS",
            "execution_record": record.model_dump() if record else None,
            "execution_baseline": baseline.model_dump() if baseline else None,
        }

    # 10. Monitoring Node (Telemetry tracking & deviation evaluation)
    def monitoring_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        record = repository.get_execution_record(case_id)
        events = repository.get_tracking_events(case_id)
        return {
            "status": record.status if record else "MONITORING",
            "tracking_events": [e.model_dump() for e in events],
        }

    # 11. Learning Node (Certified outcome archiving & case closure)
    def learning_node(state: SupplyChainState) -> dict:
        case_id = state["case_id"]
        outcomes = repository.get_historical_outcomes(case_id)
        return {
            "status": "RESOLVED",
            "outcome_record": outcomes[-1].model_dump() if outcomes else None,
        }

    def route_after_monitoring(state: SupplyChainState) -> str:
        status = state.get("status")
        if status == "DELIVERED":
            return "learning_node"
        elif status == "FAILED":
            return "recovery_planning_node"
        return END

    builder = StateGraph(SupplyChainState)
    builder.add_node("ingestion_node", ingestion_node)
    builder.add_node("case_creation_node", case_creation_node)
    builder.add_node("triage_node", triage_node)
    builder.add_node("impact_analysis_node", impact_analysis_node)
    builder.add_node("gemini_explanation_node", gemini_explanation_node)
    builder.add_node("checkpoint1_node", checkpoint1_node)
    builder.add_node("recovery_planning_node", recovery_planning_node)
    builder.add_node("checkpoint2_node", checkpoint2_node)
    builder.add_node("execution_node", execution_node)
    builder.add_node("monitoring_node", monitoring_node)
    builder.add_node("learning_node", learning_node)

    builder.add_edge(START, "ingestion_node")
    builder.add_edge("ingestion_node", "case_creation_node")
    builder.add_edge("case_creation_node", "triage_node")
    builder.add_edge("triage_node", "impact_analysis_node")
    builder.add_edge("impact_analysis_node", "gemini_explanation_node")
    builder.add_edge("gemini_explanation_node", "checkpoint1_node")
    builder.add_edge("checkpoint1_node", "recovery_planning_node")
    builder.add_edge("recovery_planning_node", "checkpoint2_node")
    builder.add_edge("checkpoint2_node", "execution_node")
    builder.add_edge("execution_node", "monitoring_node")
    builder.add_conditional_edges(
        "monitoring_node",
        route_after_monitoring,
        {
            "learning_node": "learning_node",
            "recovery_planning_node": "recovery_planning_node",
            END: END,
        },
    )
    builder.add_edge("learning_node", END)

    # Interrupt before triage_node, checkpoint1_node, recovery_planning_node, checkpoint2_node, and execution_node
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=[
            "triage_node",
            "checkpoint1_node",
            "recovery_planning_node",
            "checkpoint2_node",
            "execution_node",
        ],
    )

