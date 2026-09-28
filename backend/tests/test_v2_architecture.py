"""
Unit & Integration Test Suite for Architecture v2:
- Strict state machine transitions and 409 guard enforcement
- Priority influence on scoring and ranking
- Hard vs Soft constraint evaluations
- Separation of Agent 1, Agent 2, and Agent 3
- Checkpoint 2 Human Decision & Immutable Snapshots
- Execution simulator and Outcome locking
"""

import unittest
from app.workflow.state_machine import CaseState, validate_and_transition, InvalidStateTransitionError, normalize_state
from app.models.case import Case
from app.models.impact import ImpactAnalysis, DownstreamImpact
from app.models.recovery import CandidatePlan, Checkpoint2Request, ManagerConstraints
from app.agents.agent2_generator import Agent2PlanGenerator
from app.agents.agent3_evaluator import Agent3Evaluator
from app.repositories.mock_repository import MockRepository
from app.services.audit_service import AuditService
from app.services.case_service import CaseService


class TestV2Architecture(unittest.TestCase):
    def test_state_machine_illegal_transition(self):
        case = Case(
            case_id="CASE-TEST-01",
            disruption_type="WEATHER",
            description="Typhoon delay",
            supplier_id="SUP-001",
            material_id="MAT-001",
            plant_id="PLANT-001",
            status=CaseState.CASE_OVERVIEW.value,
        )

        # Illegal transition: cannot jump from CASE_OVERVIEW straight to approve_plan
        with self.assertRaises(InvalidStateTransitionError):
            validate_and_transition(case, "approve_plan", "TEST_ACTOR")

    def test_priority_influence_on_ranking(self):
        repo = MockRepository()
        audit = AuditService(repo)
        service = CaseService(repo, audit)

        case = Case(
            case_id="CASE-TEST-02",
            disruption_type="PORT_CONGESTION",
            description="Port customs hold",
            supplier_id="SUP-001",
            material_id="MAT-001",
            plant_id="PLANT-001",
            expected_delay_days=5,
            affected_quantity=500.0,
            status=CaseState.CASE_OVERVIEW.value,
        )
        repo.create_case(case)

        impact = ImpactAnalysis(
            case_id=case.case_id,
            severity="HIGH",
            available_inventory=50.0,
            days_of_cover=2.0,
            safety_stock_breach=True,
            supply_gap_quantity=450.0,
            downstream_impact=DownstreamImpact(
                affected_material_id="MAT-001",
                affected_material_name="Microcontroller",
                affected_plant_id="PLANT-001",
                affected_plant_name="Berlin Plant",
                affected_supplier_id="SUP-001",
                affected_supplier_name="Alpha Tech",
            ),
        )
        repo.save_impact_analysis(impact)

        # Agent 2 generates candidate plans
        candidates = Agent2PlanGenerator.generate_candidates(case, impact, repo, priority="BALANCED")
        self.assertGreaterEqual(len(candidates), 3, f"Expected >= 3 candidates, got {len(candidates)}")

        # Evaluate with TIME priority
        eval_time = Agent3Evaluator.evaluate_candidate_plans(case, impact, candidates, repo, priority="TIME")
        self.assertGreater(len(eval_time.feasible_plans), 0)

        # Evaluate with COST priority
        eval_cost = Agent3Evaluator.evaluate_candidate_plans(case, impact, candidates, repo, priority="COST")
        self.assertGreater(len(eval_cost.feasible_plans), 0)

        # Top plan or scores should reflect different priorities
        time_scores = {p.plan_id: p.score for p in eval_time.feasible_plans}
        cost_scores = {p.plan_id: p.score for p in eval_cost.feasible_plans}
        self.assertNotEqual(time_scores, cost_scores, "Different priorities must produce different score distributions")

    def test_hard_constraint_breach_infeasible(self):
        repo = MockRepository()
        case = Case(
            case_id="CASE-TEST-03",
            disruption_type="FIRE",
            description="Factory incident",
            supplier_id="SUP-002",
            material_id="MAT-002",
            plant_id="PLANT-002",
            expected_delay_days=10,
            affected_quantity=400.0,
            status=CaseState.CASE_OVERVIEW.value,
        )
        impact = ImpactAnalysis(
            case_id=case.case_id,
            severity="CRITICAL",
            available_inventory=10.0,
            days_of_cover=1.0,
            safety_stock_breach=True,
            supply_gap_quantity=400.0,
            downstream_impact=DownstreamImpact(
                affected_material_id="MAT-002",
                affected_material_name="Battery",
                affected_plant_id="PLANT-002",
                affected_plant_name="Munich Plant",
                affected_supplier_id="SUP-002",
                affected_supplier_name="Beta Power",
            ),
        )

        candidates = Agent2PlanGenerator.generate_candidates(case, impact, repo, priority="BALANCED")

        # Set very strict budget ($1,000) that all plans will breach
        strict_constraints = ManagerConstraints(max_budget=1000.0)
        eval_result = Agent3Evaluator.evaluate_candidate_plans(
            case, impact, candidates, repo, priority="COST", manager_constraints=strict_constraints
        )

        # All plans should breach budget and be infeasible
        self.assertGreater(len(eval_result.infeasible_plans), 0)
        for p in eval_result.infeasible_plans:
            self.assertEqual(p.feasibility_status, "NOT FEASIBLE")
            self.assertIsNotNone(p.infeasibility_reason)
            self.assertTrue("budget" in p.infeasibility_reason.lower() or "limit" in p.infeasibility_reason.lower())

    def test_approval_requires_comment_and_creates_snapshot(self):
        repo = MockRepository()
        audit = AuditService(repo)
        service = CaseService(repo, audit)

        case = Case(
            case_id="CASE-TEST-04",
            disruption_type="SHORTAGE",
            description="Silicon shortage",
            supplier_id="SUP-001",
            material_id="MAT-001",
            plant_id="PLANT-001",
            expected_delay_days=4,
            affected_quantity=500.0,
            status=CaseState.DECISION_PENDING.value,
            planning_cycle=1,
        )
        repo.create_case(case)

        impact = ImpactAnalysis(
            case_id=case.case_id,
            severity="MEDIUM",
            available_inventory=100.0,
            days_of_cover=4.0,
            safety_stock_breach=False,
            supply_gap_quantity=400.0,
            downstream_impact=DownstreamImpact(
                affected_material_id="MAT-001",
                affected_material_name="Microcontroller",
                affected_plant_id="PLANT-001",
                affected_plant_name="Berlin Plant",
                affected_supplier_id="SUP-001",
                affected_supplier_name="Alpha Tech",
            ),
        )
        repo.save_impact_analysis(impact)

        candidates = Agent2PlanGenerator.generate_candidates(case, impact, repo, priority="BALANCED")
        eval_result = Agent3Evaluator.evaluate_candidate_plans(case, impact, candidates, repo, priority="BALANCED")
        repo.save_recovery_plan_set(eval_result)

        feasible_plan = eval_result.feasible_plans[0]

        # Rejection of approval without comment
        with self.assertRaises(ValueError):
            service.submit_decision(
                case.case_id,
                Checkpoint2Request(
                    decision="APPROVE",
                    plan_id=feasible_plan.plan_id,
                    version=feasible_plan.version,
                    comment="",
                ),
            )

        # Valid approval with comment
        updated_case, resp = service.submit_decision(
            case.case_id,
            Checkpoint2Request(
                decision="APPROVE",
                plan_id=feasible_plan.plan_id,
                version=feasible_plan.version,
                comment="Approved by Supply Chain Lead after verifying carrier reliability.",
            ),
        )
        self.assertEqual(updated_case.status, CaseState.EXECUTION.value)
        self.assertEqual(updated_case.approved_plan_id, feasible_plan.plan_id)
        self.assertIsNotNone(resp.snapshot_id)

        # Verify immutable snapshot exists
        snapshots = service.get_snapshots(case.case_id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].plan_id, feasible_plan.plan_id)
        self.assertTrue(snapshots[0].is_active)


if __name__ == "__main__":
    unittest.main()
