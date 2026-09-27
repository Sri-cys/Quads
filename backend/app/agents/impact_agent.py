"""
Agent 1: Impact Analysis Agent.
Orchestrates deterministic business calculations and AI executive explanation.
Adheres strictly to the architectural boundary:
- Deterministic numerical calculations in Python via ImpactService
- Gemini provides natural language explanation only without inventing numbers
- Graceful degradation if Gemini is absent or fails
"""

from typing import Optional
from app.services.impact_service import ImpactService
from app.services.gemini_service import GeminiService
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.disruption import Disruption
from app.models.impact import ImpactAnalysis


class ImpactAgent:
    """
    Agent 1 (Impact Analysis)
    The only active autonomous agent in Quads Phase 1.
    """

    def __init__(self, gemini_service: Optional[GeminiService] = None):
        self.gemini_service = gemini_service or GeminiService()

    def run(
        self,
        case_id: str,
        disruption: Disruption,
        supplier: Optional[Supplier],
        material: Optional[Material],
        plant: Optional[Plant],
        inventory: Optional[Inventory],
        demand: Optional[Demand],
        safety_stock: Optional[SafetyStock],
        purchase_orders: list[PurchaseOrder],
    ) -> ImpactAnalysis:
        """
        Execute deterministic impact calculation followed by structured Gemini explanation.
        """
        # Step 1: Pure Deterministic Python Calculations
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

        # Step 2: Executive AI Explanation (Resilient backend integration)
        explanation, status = self.gemini_service.generate_explanation(
            disruption=disruption,
            impact=impact,
        )

        impact.ai_explanation = explanation
        impact.ai_status = status

        return impact
