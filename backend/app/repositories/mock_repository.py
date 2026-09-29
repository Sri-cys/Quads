import json
import os
import sqlite3
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone

from app.repositories.base import BaseRepository
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.case import Case
from app.workflow.state_machine import normalize_state, CaseState
from app.models.impact import ImpactAnalysis, AuditEvent
from app.models.recovery import (
    RecoveryPlanSet,
    Checkpoint2Response,
    ContractEvidence,
    HistoricalPrecedent,
    TransportOption,
)
from app.models.execution import (
    ExecutionAction,
    ExecutionBaseline,
    TrackingEvent,
    FailedPlanRecord,
    HistoricalOutcomeRecord,
)



class MockRepository(BaseRepository):
    """
    MockRepository loads and manages local mock data for Phase 1.
    All data is kept in-memory with optional persistence to data/mock/*.json or SQLite.
    """

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir:
            self.data_dir = Path(data_dir)
        else:
            # Default to repo root data/mock
            current_file = Path(__file__).resolve()
            # current_file: backend/app/repositories/mock_repository.py -> 4 levels up to root
            repo_root = current_file.parents[3]
            self.data_dir = repo_root / "data" / "mock"

        self._suppliers: dict[str, Supplier] = {}
        self._materials: dict[str, Material] = {}
        self._plants: dict[str, Plant] = {}
        self._inventory: dict[tuple[str, str], Inventory] = {}
        self._demand: dict[tuple[str, str], Demand] = {}
        self._db_path = os.environ.get("DATABASE_PATH")
        self._safety_stock: dict[tuple[str, str], SafetyStock] = {}
        self._purchase_orders: list[PurchaseOrder] = []

        self._cases: dict[str, Case] = {}
        self._impact_analyses: dict[str, ImpactAnalysis] = {}
        self._audit_events: list[AuditEvent] = []
        self._case_counter: int = 0

        # Phase 2 stores
        self._contracts: dict[str, ContractEvidence] = {}
        self._historical_cases: list[HistoricalPrecedent] = []
        self._transports: list[TransportOption] = []
        self._recovery_plan_sets: dict[str, RecoveryPlanSet] = {}
        self._checkpoint2_decisions: dict[str, Checkpoint2Response] = {}

        # Phase 3 stores
        self._execution_records: dict[str, ExecutionAction] = {}
        self._execution_baselines: dict[str, ExecutionBaseline] = {}
        self._tracking_events: dict[str, list[TrackingEvent]] = {}
        self._failed_plans: dict[str, list[FailedPlanRecord]] = {}
        self._historical_outcomes: list[HistoricalOutcomeRecord] = []

        self.load_all()

    def _read_json(self, filename: str) -> list[dict]:
        file_path = self.data_dir / filename
        if not file_path.exists():
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def load_all(self) -> None:
        """Load entities from mock json files."""
        # Suppliers
        for item in self._read_json("suppliers.json"):
            sup = Supplier(**item)
            self._suppliers[sup.supplier_id] = sup

        # Materials
        for item in self._read_json("materials.json"):
            mat = Material(**item)
            self._materials[mat.material_id] = mat

        # Plants
        for item in self._read_json("plants.json"):
            plant = Plant(**item)
            self._plants[plant.plant_id] = plant

        # Inventory
        for item in self._read_json("inventory.json"):
            inv = Inventory(**item)
            self._inventory[(inv.material_id, inv.plant_id)] = inv

        # Demand
        for item in self._read_json("demand.json"):
            dem = Demand(**item)
            self._demand[(dem.material_id, dem.plant_id)] = dem

        # Safety Stock
        for item in self._read_json("safety_stock.json"):
            ss = SafetyStock(**item)
            self._safety_stock[(ss.material_id, ss.plant_id)] = ss

        # Purchase Orders
        for item in self._read_json("purchase_orders.json"):
            po = PurchaseOrder(**item)
            self._purchase_orders.append(po)

        # Pre-seeded cases
        cases_data = self._read_json("cases.json")
        for item in cases_data:
            item["status"] = normalize_state(item.get("status")).value
            case = Case(**item)
            self._cases[case.case_id] = case
            # Track max counter
            if case.case_id.startswith("CASE-"):
                try:
                    num = int(case.case_id.split("-")[1])
                    if num > self._case_counter:
                        self._case_counter = num
                except ValueError:
                    pass

        # Contracts
        for item in self._read_json("contracts.json"):
            ctr = ContractEvidence(**item)
            self._contracts[ctr.supplier_id] = ctr

        # Historical Cases
        for item in self._read_json("historical_cases.json"):
            hist = HistoricalPrecedent(**item)
            self._historical_cases.append(hist)

        # Transport Options
        for item in self._read_json("transports.json"):
            tr = TransportOption(**item)
            self._transports.append(tr)

        if self._db_path:
            self._init_sqlite()

    def _init_sqlite(self):
        if not self._db_path:
            return
        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, data TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS impacts (case_id TEXT PRIMARY KEY, data TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS recovery_plans (case_id TEXT PRIMARY KEY, data TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS checkpoint2 (case_id TEXT PRIMARY KEY, data TEXT)")
                conn.execute("CREATE TABLE IF NOT EXISTS audits (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, data TEXT)")
                for row in conn.execute("SELECT data FROM cases"):
                    c = Case.model_validate_json(row[0])
                    self._cases[c.case_id] = c
                for row in conn.execute("SELECT data FROM impacts"):
                    imp = ImpactAnalysis.model_validate_json(row[0])
                    self._impact_analyses[imp.case_id] = imp
                for row in conn.execute("SELECT data FROM recovery_plans"):
                    rec = RecoveryPlanSet.model_validate_json(row[0])
                    self._recovery_plan_sets[rec.case_id] = rec
                for row in conn.execute("SELECT data FROM checkpoint2"):
                    cp2 = Checkpoint2Response.model_validate_json(row[0])
                    self._checkpoint2_decisions[cp2.case_id] = cp2
                for row in conn.execute("SELECT data FROM audits"):
                    aud = AuditEvent.model_validate_json(row[0])
                    self._audit_events.append(aud)
        except Exception:
            pass

    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        return self._suppliers.get(supplier_id)

    def list_suppliers(self) -> list[Supplier]:
        return list(self._suppliers.values())

    def get_material(self, material_id: str) -> Optional[Material]:
        return self._materials.get(material_id)

    def list_materials(self) -> list[Material]:
        return list(self._materials.values())

    def get_plant(self, plant_id: str) -> Optional[Plant]:
        return self._plants.get(plant_id)

    def list_plants(self) -> list[Plant]:
        return list(self._plants.values())

    def get_inventory(self, material_id: str, plant_id: str) -> Optional[Inventory]:
        return self._inventory.get((material_id, plant_id))

    def get_demand(self, material_id: str, plant_id: str) -> Optional[Demand]:
        return self._demand.get((material_id, plant_id))

    def get_safety_stock(self, material_id: str, plant_id: str) -> Optional[SafetyStock]:
        return self._safety_stock.get((material_id, plant_id))

    def get_purchase_orders(
        self,
        supplier_id: Optional[str] = None,
        material_id: Optional[str] = None,
        plant_id: Optional[str] = None,
    ) -> list[PurchaseOrder]:
        results = self._purchase_orders
        if supplier_id:
            results = [po for po in results if po.supplier_id == supplier_id]
        if material_id:
            results = [po for po in results if po.material_id == material_id]
        if plant_id:
            results = [po for po in results if po.plant_id == plant_id]
        return results

    def _next_case_id(self) -> str:
        self._case_counter += 1
        return f"CASE-{self._case_counter:04d}"

    def create_case(self, case: Case) -> Case:
        if not case.case_id:
            case.case_id = self._next_case_id()
        self._cases[case.case_id] = case
        if self._db_path:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("INSERT OR REPLACE INTO cases (case_id, data) VALUES (?, ?)", (case.case_id, case.model_dump_json()))
            except Exception:
                pass
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        return self._cases.get(case_id)

    def list_cases(self, limit: int = 25, offset: int = 0) -> tuple[int, list[Case]]:
        all_cases = sorted(self._cases.values(), key=lambda c: c.detected_at, reverse=True)
        total = len(all_cases)
        return total, all_cases[offset : offset + limit]

    def update_case(self, case: Case) -> Case:
        self._cases[case.case_id] = case
        if self._db_path:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("INSERT OR REPLACE INTO cases (case_id, data) VALUES (?, ?)", (case.case_id, case.model_dump_json()))
            except Exception:
                pass
        return case

    def find_duplicate_case(
        self,
        supplier_id: str,
        material_id: str,
        plant_id: str,
        disruption_type: str,
    ) -> Optional[Case]:
        now = datetime.now(timezone.utc)
        for c in self._cases.values():
            if (
                c.supplier_id == supplier_id
                and c.material_id == material_id
                and c.plant_id == plant_id
                and c.disruption_type == disruption_type
                and c.status in {"CREATED", "TRIAGED", CaseState.CASE_CREATED.value, CaseState.CASE_OVERVIEW.value, CaseState.IMPACT_ANALYSIS_PENDING.value, CaseState.IMPACT_ANALYSIS_RUNNING.value}
            ):
                try:
                    dt = datetime.fromisoformat(c.detected_at.replace("Z", "+00:00"))
                    if abs((now - dt).total_seconds()) < 300:
                        return c
                except Exception:
                    pass
        return None

    def save_impact_analysis(self, analysis: ImpactAnalysis) -> ImpactAnalysis:
        self._impact_analyses[analysis.case_id] = analysis
        # Also update case status & severity if in earlier triage stages
        if analysis.case_id in self._cases:
            case = self._cases[analysis.case_id]
            case.severity = analysis.severity
            if case.status in {"CREATED", "TRIAGED"}:
                case.status = "ANALYZED"
            self.update_case(case)
        if self._db_path:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("INSERT OR REPLACE INTO impacts (case_id, data) VALUES (?, ?)", (analysis.case_id, analysis.model_dump_json()))
            except Exception:
                pass
        return analysis

    def get_impact_analysis(self, case_id: str) -> Optional[ImpactAnalysis]:
        res = self._impact_analyses.get(case_id)
        if res:
            return res
        
        case = self._cases.get(case_id)
        if case and case.status not in {"CREATED", "TRIAGED", "CASE_CREATED", "CASE_OVERVIEW", "IMPACT_ANALYSIS_PENDING", "IMPACT_ANALYSIS_RUNNING", "IMPACT_ANALYSIS_FAILED"}:
            from app.models.disruption import Disruption
            from app.services.impact_service import ImpactService
            disruption = Disruption(
                disruption_type=case.disruption_type,
                description=case.description,
                detected_at=case.detected_at,
                expected_delay_days=case.expected_delay_days,
                affected_quantity=case.affected_quantity,
            )
            impact = ImpactService.analyze(
                case_id=case_id,
                disruption=disruption,
                supplier=self.get_supplier(case.supplier_id),
                material=self.get_material(case.material_id),
                plant=self.get_plant(case.plant_id),
                inventory=self.get_inventory(case.material_id, case.plant_id),
                demand=self.get_demand(case.material_id, case.plant_id),
                safety_stock=self.get_safety_stock(case.material_id, case.plant_id),
                purchase_orders=self.get_purchase_orders(case.supplier_id, case.material_id, case.plant_id),
            )
            impact.ai_explanation = "Mock AI explanation auto-generated for pre-seeded case."
            impact.ai_status = "MOCK_FALLBACK"
            self._impact_analyses[case_id] = impact
            return impact

        return None

    def save_checkpoint(self, case_id: str, priority: str) -> Case:
        case = self._cases.get(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")
        case.checkpoint1_decision = priority
        case.checkpoint1_timestamp = datetime.now(timezone.utc).isoformat()
        case.status = "CHECKPOINT_APPROVED"
        self.update_case(case)
        return case

    def save_audit_event(self, event: AuditEvent) -> AuditEvent:
        self._audit_events.append(event)
        if self._db_path:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("INSERT INTO audits (case_id, data) VALUES (?, ?)", (event.case_id, event.model_dump_json()))
            except Exception:
                pass
        return event

    def get_audit_events(self, case_id: Optional[str] = None) -> list[AuditEvent]:
        if case_id:
            return [e for e in self._audit_events if e.case_id == case_id]
        return list(self._audit_events)

    def get_contracts(self, supplier_id: Optional[str] = None) -> list[ContractEvidence]:
        if supplier_id:
            ctr = self._contracts.get(supplier_id)
            return [ctr] if ctr else []
        return list(self._contracts.values())

    def get_contract(self, supplier_id: str) -> Optional[ContractEvidence]:
        return self._contracts.get(supplier_id)

    def get_historical_cases(
        self,
        material_id: Optional[str] = None,
        disruption_type: Optional[str] = None,
    ) -> list[HistoricalPrecedent]:
        results = self._historical_cases
        if material_id:
            results = [h for h in results if h.material_id == material_id]
        if disruption_type:
            results = [h for h in results if h.disruption_type == disruption_type]
        # If filtered list is empty, return top precedents by general similarity
        return results if results else self._historical_cases

    def get_transport_options(self) -> list[TransportOption]:
        return list(self._transports)

    def save_recovery_plan_set(self, plan_set: RecoveryPlanSet) -> RecoveryPlanSet:
        self._recovery_plan_sets[plan_set.case_id] = plan_set
        if self._db_path:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("INSERT OR REPLACE INTO recovery_plans (case_id, data) VALUES (?, ?)", (plan_set.case_id, plan_set.model_dump_json()))
            except Exception:
                pass
        return plan_set

    def get_recovery_plan_set(self, case_id: str) -> Optional[RecoveryPlanSet]:
        return self._recovery_plan_sets.get(case_id)

    def save_checkpoint2(self, case_id: str, decision: Checkpoint2Response) -> Case:
        case = self._cases.get(case_id)
        if not case:
            raise KeyError(f"Case {case_id} not found")
        
        self._checkpoint2_decisions[case_id] = decision
        case.checkpoint2_decision = decision.decision
        case.checkpoint2_timestamp = decision.timestamp
        case.approved_plan_id = decision.plan_id
        case.approved_plan_version = decision.version

        if case.status not in {CaseState.EXECUTION.value, "EXECUTION_IN_PROGRESS", "MONITORING", "RESOLVED"}:
            if decision.decision == "APPROVE":
                case.status = "RECOVERY_APPROVED"
            elif decision.decision == "MODIFY":
                case.status = "AWAITING_CHECKPOINT_2"
            elif decision.decision == "REJECT":
                case.status = "AWAITING_CHECKPOINT_2"

        # Update in plan set if exists
        plan_set = self._recovery_plan_sets.get(case_id)
        if plan_set:
            plan_set.checkpoint2_status = decision.decision
            plan_set.checkpoint2_decision = decision.model_dump()

        if self._db_path:
            try:
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("INSERT OR REPLACE INTO cases (case_id, data) VALUES (?, ?)", (case.case_id, case.model_dump_json()))
                    conn.execute("INSERT OR REPLACE INTO checkpoint2 (case_id, data) VALUES (?, ?)", (case_id, decision.model_dump_json()))
            except Exception:
                pass

        return case

    def get_checkpoint2(self, case_id: str) -> Optional[Checkpoint2Response]:
        return self._checkpoint2_decisions.get(case_id)

    # Phase 3 Execution & Monitoring Methods
    def save_execution_record(self, record: ExecutionAction) -> ExecutionAction:
        self._execution_records[record.case_id] = record
        # Update case execution reference & status
        case = self._cases.get(record.case_id)
        if case:
            case.execution_action_id = record.action_id
            case.execution_status = record.status
            if record.status in {"ACCEPTED", "SUPPLIER_CONFIRMED", "SHIPMENT_CREATED"}:
                case.status = "EXECUTION_IN_PROGRESS"
            elif record.status in {"SHIPMENT_DISPATCHED", "IN_TRANSIT", "DELAYED"}:
                case.status = "MONITORING"
            elif record.status == "DELIVERED":
                case.status = "RESOLVED"
            elif record.status == "FAILED":
                case.status = "RECOVERY_PLANNING"
                case.checkpoint2_decision = None
                case.approved_plan_id = None
                case.approved_plan_version = None
                self._checkpoint2_decisions.pop(record.case_id, None)
        return record

    def get_execution_record(self, case_id: str) -> Optional[ExecutionAction]:
        return self._execution_records.get(case_id)

    def save_execution_baseline(self, baseline: ExecutionBaseline) -> ExecutionBaseline:
        self._execution_baselines[baseline.case_id] = baseline
        return baseline

    def get_execution_baseline(self, case_id: str) -> Optional[ExecutionBaseline]:
        return self._execution_baselines.get(case_id)

    def add_tracking_event(self, case_id: str, event: TrackingEvent) -> TrackingEvent:
        if case_id not in self._tracking_events:
            self._tracking_events[case_id] = []
        self._tracking_events[case_id].append(event)
        return event

    def get_tracking_events(self, case_id: str) -> list[TrackingEvent]:
        return list(self._tracking_events.get(case_id, []))

    def save_failed_plan(self, case_id: str, failed_plan: FailedPlanRecord) -> FailedPlanRecord:
        if case_id not in self._failed_plans:
            self._failed_plans[case_id] = []
        self._failed_plans[case_id].append(failed_plan)
        return failed_plan

    def get_failed_plans(self, case_id: str) -> list[FailedPlanRecord]:
        return list(self._failed_plans.get(case_id, []))

    def save_historical_outcome(self, outcome: HistoricalOutcomeRecord) -> HistoricalOutcomeRecord:
        self._historical_outcomes.append(outcome)

        # Also register as HistoricalPrecedent so future recovery discovery can retrieve it
        precedent = HistoricalPrecedent(
            precedent_id=outcome.record_id,
            disruption_type=outcome.disruption_type,
            material_id=outcome.material_id,
            material_name=f"Material {outcome.material_id}",
            disrupted_supplier_id=outcome.supplier_id,
            strategy_used=outcome.strategy_used,
            recovery_source=f"Executed Plan {outcome.plan_id} ({outcome.plan_version})",
            recovered_quantity=outcome.actual_quantity,
            recovery_days=outcome.actual_days,
            outcome_summary=outcome.outcome_summary,
            similarity_score=0.95,
            success_rate=1.0 if outcome.success else 0.0,
        )
        self._historical_cases.append(precedent)

        # Update case resolved timestamp if successful
        case = self._cases.get(outcome.case_id)
        if case and outcome.success:
            case.status = "RESOLVED"
            case.resolved_at = outcome.recorded_at

        return outcome

    def get_historical_outcomes(self, case_id: Optional[str] = None) -> list[HistoricalOutcomeRecord]:
        if case_id:
            return [o for o in self._historical_outcomes if o.case_id == case_id]
        return list(self._historical_outcomes)

    def save_snapshot(self, snapshot: Any) -> Any:
        if not hasattr(self, "_snapshots"):
            self._snapshots = {}
        if snapshot.case_id not in self._snapshots:
            self._snapshots[snapshot.case_id] = []
        for s in self._snapshots[snapshot.case_id]:
            if getattr(s, "is_active", False):
                s.is_active = False
                s.is_superseded = True
        self._snapshots[snapshot.case_id].append(snapshot)
        return snapshot

    def get_snapshots(self, case_id: str) -> list[Any]:
        if not hasattr(self, "_snapshots"):
            self._snapshots = {}
        return list(self._snapshots.get(case_id, []))

    def get_active_snapshot(self, case_id: str) -> Optional[Any]:
        snaps = self.get_snapshots(case_id)
        for s in reversed(snaps):
            if getattr(s, "is_active", False):
                return s
        return snaps[-1] if snaps else None

    def save_candidate_plan_set(self, plan_set: Any) -> Any:
        if not hasattr(self, "_candidate_plan_sets"):
            self._candidate_plan_sets = {}
        self._candidate_plan_sets[plan_set.case_id] = plan_set
        return plan_set

    def get_candidate_plan_set(self, case_id: str) -> Optional[Any]:
        if not hasattr(self, "_candidate_plan_sets"):
            self._candidate_plan_sets = {}
        return self._candidate_plan_sets.get(case_id)

