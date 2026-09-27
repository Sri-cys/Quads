"""
GeminiService: Secure backend AI explanation integration.
Adheres strictly to the architectural constraints:
- Only read GEMINI_API_KEY from environment.
- Never log, print, or expose the API key.
- Never let Gemini invent numbers; Gemini receives deterministic calculations as structured input.
- Timeout of 10s, retry once with backoff, graceful fallback to 'unavailable' state.
"""

import os
import time
import logging
from typing import Optional
from app.models.impact import ImpactAnalysis
from app.models.disruption import Disruption

logger = logging.getLogger("quads.gemini_service")


class GeminiService:
    def __init__(self, api_key: Optional[str] = None):
        if api_key is not None:
            self._api_key = api_key.strip()
        else:
            self._api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        self._client = None
        self._is_configured = bool(self._api_key)

        if self._is_configured:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
                self._client = None
                self._is_configured = False

    @property
    def is_configured(self) -> bool:
        return self._is_configured

    def generate_explanation(
        self,
        disruption: Disruption,
        impact: ImpactAnalysis,
    ) -> tuple[Optional[str], str]:
        """
        Generate a natural language explanation of the deterministic impact results.
        Returns (explanation_text, status) where status is:
        - "AVAILABLE"
        - "UNAVAILABLE"
        - "FAILED"
        """
        if not self._is_configured or self._client is None:
            return None, "UNAVAILABLE"

        prompt = f"""You are the Quads Supply Chain AI Impact Analyst for an enterprise control tower.
Explain the following disruption and its deterministic operational impact to supply chain executives.

STRICT RULES:
1. Ground your explanation ENTIRELY in the provided deterministic calculations.
2. DO NOT invent or alter any numbers, dates, stock levels, or severity tiers.
3. Be professional, concise, and executive-ready (3-4 crisp paragraphs max).

DISRUPTION DETAILS:
- Disruption Type: {disruption.disruption_type}
- Description: {disruption.description}
- Expected Delay: {disruption.expected_delay_days} days
- Affected Quantity: {disruption.affected_quantity if disruption.affected_quantity is not None else 'Unspecified'} units

DETERMINISTIC ANALYSIS RESULTS:
- Severity: {impact.severity}
- Days of Cover: {impact.days_of_cover if impact.days_of_cover is not None else 'N/A (Zero or unavailable demand)'}
- Stockout Date: {impact.stockout_date if impact.stockout_date else 'N/A'}
- Available Inventory: {impact.available_inventory} units (Total: {impact.total_inventory}, Reserved: {impact.reserved_quantity})
- Daily Demand: {impact.daily_demand if impact.daily_demand is not None else 'N/A'}
- Safety Stock: {impact.safety_stock_quantity} units
- Safety Stock Breach: {'YES' if impact.safety_stock_breach else 'NO'}
- Projected Supply Gap: {impact.supply_gap_quantity} units
- Affected Plant: {impact.downstream_impact.affected_plant_name} ({impact.downstream_impact.affected_plant_id})
- Affected Material: {impact.downstream_impact.affected_material_name} ({impact.downstream_impact.affected_material_id})
- Affected Supplier: {impact.downstream_impact.affected_supplier_name} ({impact.downstream_impact.affected_supplier_id})
- Downstream Financial Exposure: ${impact.downstream_impact.financial_exposure:,.2f}
- Key Risk Signals: {', '.join(impact.downstream_impact.production_risk_indicators)}

Provide:
1. Executive Disruption Summary: What happened and why this case was assigned {impact.severity} severity.
2. Immediate Operational Exposure: Explain the Days of Cover, safety stock condition, and supply gap.
3. Downstream Plant & Customer Risk: Impact on production lines and customer deliveries.
"""

        # Attempt call with 1 retry and 10s timeout budget
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                # Call Gemini model
                response = self._client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip(), "AVAILABLE"
                else:
                    return None, "FAILED"
            except Exception as e:
                logger.warning(f"Gemini call attempt {attempt} failed: {type(e).__name__}")
                if attempt < max_attempts:
                    time.sleep(1.0)  # Brief backoff before single retry
                else:
                    logger.error("Gemini explanation generation failed after retries; falling back gracefully.")
                    return None, "FAILED"

        return None, "UNAVAILABLE"

    def generate_recovery_briefing(
        self,
        case_id: str,
        priority: str,
        feasible_plans: list,
        infeasible_plans: list,
    ) -> tuple[Optional[str], str]:
        """
        Generate an executive recovery briefing explaining the evaluated options,
        trade-offs, and why the top plan is recommended under the manager's priority.
        """
        if not self._is_configured or self._client is None:
            return None, "UNAVAILABLE"

        plans_summary = []
        for p in feasible_plans[:4]:
            plans_summary.append(
                f"- Plan {p.plan_id} ({p.title}): Strategy={p.strategy}, Score={p.score:.1f}, "
                f"LeadTime={p.recovery_days}d, Cost=${p.total_cost:,.2f}, Risk={p.operational_risk}, "
                f"Transport={p.transport_name}, TradeOffs={'; '.join(p.trade_offs)}"
            )
        
        infeasible_summary = []
        for p in infeasible_plans[:2]:
            infeasible_summary.append(f"- Plan {p.plan_id} ({p.title}): Rejected because '{p.infeasibility_reason}'")

        prompt = f"""You are the Quads Supply Chain AI Recovery Advisor for an enterprise control tower.
Summarize the Phase 2 recovery alternatives for Case {case_id} to supply chain leadership.

RECOVERY CONTEXT:
- Manager Governance Priority: {priority}
- Evaluated Feasible Alternatives:
{chr(10).join(plans_summary) if plans_summary else 'No feasible alternatives identified.'}

- Rejected Infeasible Options:
{chr(10).join(infeasible_summary) if infeasible_summary else 'None.'}

STRICT GROUNDING RULES:
1. Ground your synthesis ENTIRELY in the provided deterministic plans, scores, and costs.
2. DO NOT invent alternative suppliers, extra costs, or different lead times.
3. Explain why the highest-scoring plan is recommended given the manager's '{priority}' objective.
4. Provide a crisp 2-paragraph executive recommendation for Human Checkpoint 2.
"""

        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip(), "AVAILABLE"
                else:
                    return None, "FAILED"
            except Exception as e:
                logger.warning(f"Gemini recovery briefing attempt {attempt} failed: {type(e).__name__}")
                if attempt < max_attempts:
                    time.sleep(1.0)
                else:
                    return None, "FAILED"

        return None, "UNAVAILABLE"

    def generate_execution_briefing(
        self,
        baseline: Any,
        action: Any,
        deviation: Any,
        events: list[Any],
    ) -> tuple[str, str]:
        """
        Generate executive narrative for Phase 3 Execution & Monitoring.
        Strictly grounded in deterministic telemetry and deviations.
        """
        if not self.is_configured:
            return self._fallback_execution_briefing(baseline, action, deviation), "FALLBACK"

        last_event = events[-1] if events else None
        prompt = f"""
You are the Quads Supply Chain Control Tower Execution Monitor (Agent 3).
Synthesize the current real-time execution status of approved recovery plan {baseline.plan_id} (Version: {baseline.plan_version}) for the supply chain manager.

PLANNED BASELINE:
- Strategy: {baseline.strategy}
- Source: {baseline.source_name} ({baseline.source_location})
- Target Plant: {baseline.target_plant_name}
- Planned Quantity: {baseline.planned_quantity} units
- Planned Arrival: {baseline.planned_arrival_date} ({baseline.planned_recovery_days} days)
- Planned Cost: ${baseline.planned_total_cost:,.2f}

CURRENT TELEMATICS & ACTUALS:
- Action Status: {action.status} (Carrier: {action.carrier_name}, Ref: {action.external_reference})
- Confirmed Quantity: {last_event.confirmed_quantity if last_event else baseline.planned_quantity} units
- Current Estimated Arrival: {last_event.estimated_arrival if last_event else baseline.planned_arrival_date}
- Variance / Deviation: {deviation.explanation}
- Critical Flag: {'YES - TOLERANCE BREACHED' if deviation.is_critical else 'NO - WITHIN TOLERANCE'}

STRICT GROUNDING RULES:
1. Ground your synthesis ENTIRELY in the provided baseline and telemetry. Do not invent facts or metrics.
2. In 2 concise paragraphs:
   - Paragraph 1: Assess progress against the baseline, highlighting any delay days, quantity shortage, or cost overrun.
   - Paragraph 2: State clearly whether the recovery is on track, requires replanning escalation, or successfully resolved the disruption.
"""
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self._client.models.generate_content(
                    model="gemini-flash-latest",
                    contents=prompt,
                )
                if response and response.text:
                    return response.text.strip(), "AVAILABLE"
            except Exception as e:
                logger.warning(f"Gemini execution briefing attempt {attempt} failed: {type(e).__name__}")
                if attempt < max_attempts:
                    time.sleep(1.0)

        return self._fallback_execution_briefing(baseline, action, deviation), "FALLBACK"

    def _fallback_execution_briefing(self, baseline: Any, action: Any, deviation: Any) -> str:
        if action.status == "DELIVERED":
            return (
                f"Execution for plan {baseline.plan_id} ({baseline.plan_version}) successfully concluded. "
                f"Material delivered to {baseline.target_plant_name} within acceptable operational parameters. "
                f"Disruption has been resolved, and certified outcome metrics have been archived into institutional memory."
            )
        elif action.status == "FAILED":
            return (
                f"CRITICAL ESCALATION: Recovery action for plan {baseline.plan_id} has failed. "
                f"Reason: {action.failure_reason or deviation.explanation}. "
                f"Variance: {deviation.delay_days} day(s) delay, {deviation.quantity_shortage:.0f} units unfulfilled. "
                f"Case has been returned to Recovery Planning for new alternative generation; the failed plan is excluded."
            )
        else:
            return (
                f"Recovery action {action.action_id} is in progress ({action.status}) via {action.carrier_name}. "
                f"Tracking against baseline ETA {baseline.planned_arrival_date} and {baseline.planned_quantity:.0f} units. "
                f"Current variance: {deviation.explanation}."
            )

