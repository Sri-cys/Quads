from abc import ABC, abstractmethod
from typing import Optional, Any
from app.models.supplier import Supplier, Plant, Material
from app.models.inventory import Inventory, Demand, SafetyStock, PurchaseOrder
from app.models.case import Case
from app.models.impact import ImpactAnalysis, AuditEvent
from app.models.recovery import (
    RecoveryPlanSet,
    Checkpoint2Response,
    ContractEvidence,
    HistoricalPrecedent,
    TransportOption,
)


class BaseRepository(ABC):
    """
    Abstract base repository defining enterprise data access contract.
    Both MockRepository (Phase 1) and HANACloudRepository (Phase 2/Future) implement this.
    """

    @abstractmethod
    def get_supplier(self, supplier_id: str) -> Optional[Supplier]:
        """Fetch supplier by supplier_id."""
        pass

    @abstractmethod
    def list_suppliers(self) -> list[Supplier]:
        """List all suppliers."""
        pass

    @abstractmethod
    def get_material(self, material_id: str) -> Optional[Material]:
        """Fetch material by material_id."""
        pass

    @abstractmethod
    def list_materials(self) -> list[Material]:
        """List all materials."""
        pass

    @abstractmethod
    def get_plant(self, plant_id: str) -> Optional[Plant]:
        """Fetch plant by plant_id."""
        pass

    @abstractmethod
    def list_plants(self) -> list[Plant]:
        """List all plants."""
        pass

    @abstractmethod
    def get_inventory(self, material_id: str, plant_id: str) -> Optional[Inventory]:
        """Fetch current inventory for a specific material and plant."""
        pass

    @abstractmethod
    def get_demand(self, material_id: str, plant_id: str) -> Optional[Demand]:
        """Fetch daily demand for a specific material and plant."""
        pass

    @abstractmethod
    def get_safety_stock(self, material_id: str, plant_id: str) -> Optional[SafetyStock]:
        """Fetch safety stock requirement for a material and plant."""
        pass

    @abstractmethod
    def get_purchase_orders(
        self,
        supplier_id: Optional[str] = None,
        material_id: Optional[str] = None,
        plant_id: Optional[str] = None,
    ) -> list[PurchaseOrder]:
        """Fetch purchase orders filtered by supplier, material, and/or plant."""
        pass

    @abstractmethod
    def create_case(self, case: Case) -> Case:
        """Persist a new disruption case."""
        pass

    @abstractmethod
    def get_case(self, case_id: str) -> Optional[Case]:
        """Fetch disruption case by case_id."""
        pass

    @abstractmethod
    def list_cases(self, limit: int = 25, offset: int = 0) -> tuple[int, list[Case]]:
        """List disruption cases with pagination. Returns (total_count, paginated_items)."""
        pass

    @abstractmethod
    def update_case(self, case: Case) -> Case:
        """Update an existing disruption case."""
        pass

    @abstractmethod
    def find_duplicate_case(
        self,
        supplier_id: str,
        material_id: str,
        plant_id: str,
        disruption_type: str,
    ) -> Optional[Case]:
        """Check if an open case with identical primary attributes already exists."""
        pass

    @abstractmethod
    def save_impact_analysis(self, analysis: ImpactAnalysis) -> ImpactAnalysis:
        """Persist deterministic and AI impact analysis for a case."""
        pass

    @abstractmethod
    def get_impact_analysis(self, case_id: str) -> Optional[ImpactAnalysis]:
        """Fetch impact analysis for a case."""
        pass

    @abstractmethod
    def save_checkpoint(self, case_id: str, priority: str) -> Case:
        """Save Checkpoint 1 decision."""
        pass

    @abstractmethod
    def save_audit_event(self, event: AuditEvent) -> AuditEvent:
        """Record an immutable audit log event."""
        pass

    @abstractmethod
    def get_audit_events(self, case_id: Optional[str] = None) -> list[AuditEvent]:
        """Fetch audit events, optionally filtered by case_id."""
        pass

    @abstractmethod
    def get_contracts(self, supplier_id: Optional[str] = None) -> list[ContractEvidence]:
        """Fetch commercial/contract evidence for suppliers."""
        pass

    @abstractmethod
    def get_contract(self, supplier_id: str) -> Optional[ContractEvidence]:
        """Fetch contract for a specific supplier."""
        pass

    @abstractmethod
    def get_historical_cases(
        self,
        material_id: Optional[str] = None,
        disruption_type: Optional[str] = None,
    ) -> list[HistoricalPrecedent]:
        """Fetch past disruption precedents for supporting evidence."""
        pass

    @abstractmethod
    def get_transport_options(self) -> list[TransportOption]:
        """Fetch available freight/logistics modes."""
        pass

    @abstractmethod
    def save_recovery_plan_set(self, plan_set: RecoveryPlanSet) -> RecoveryPlanSet:
        """Persist generated recovery plan alternatives for a case."""
        pass

    @abstractmethod
    def get_recovery_plan_set(self, case_id: str) -> Optional[RecoveryPlanSet]:
        """Fetch current recovery plan set for a case."""
        pass

    @abstractmethod
    def save_checkpoint2(self, case_id: str, decision: Checkpoint2Response) -> Case:
        """Persist Checkpoint 2 decision and update case status."""
        pass

    @abstractmethod
    def get_checkpoint2(self, case_id: str) -> Optional[Checkpoint2Response]:
        """Fetch Checkpoint 2 decision for a case."""
        pass

    @abstractmethod
    def save_execution_record(self, record: Any) -> Any:
        """Persist execution action record."""
        pass

    @abstractmethod
    def get_execution_record(self, case_id: str) -> Optional[Any]:
        """Fetch active execution action record for a case."""
        pass

    @abstractmethod
    def save_execution_baseline(self, baseline: Any) -> Any:
        """Persist immutable planned baseline for execution."""
        pass

    @abstractmethod
    def get_execution_baseline(self, case_id: str) -> Optional[Any]:
        """Fetch planned baseline for a case."""
        pass

    @abstractmethod
    def add_tracking_event(self, case_id: str, event: Any) -> Any:
        """Append tracking telematics / milestone event."""
        pass

    @abstractmethod
    def get_tracking_events(self, case_id: str) -> list[Any]:
        """Fetch tracking events for a case."""
        pass

    @abstractmethod
    def save_failed_plan(self, case_id: str, failed_plan: Any) -> Any:
        """Preserve record of a failed recovery plan."""
        pass

    @abstractmethod
    def get_failed_plans(self, case_id: str) -> list[Any]:
        """Fetch failed plan history for a case."""
        pass

    @abstractmethod
    def save_historical_outcome(self, outcome: Any) -> Any:
        """Record certified post-resolution outcome for future learning."""
        pass

    @abstractmethod
    def save_snapshot(self, snapshot: Any) -> Any:
        """Store immutable approved execution snapshot (append-only)."""
        pass

    @abstractmethod
    def get_snapshots(self, case_id: str) -> list[Any]:
        """Fetch all immutable execution snapshots for a case."""
        pass

    @abstractmethod
    def get_active_snapshot(self, case_id: str) -> Optional[Any]:
        """Fetch current active execution snapshot."""
        pass

    @abstractmethod
    def save_candidate_plan_set(self, plan_set: Any) -> Any:
        """Save Agent 2 generated candidate plan set."""
        pass

    @abstractmethod
    def get_candidate_plan_set(self, case_id: str) -> Optional[Any]:
        """Fetch Agent 2 candidate plan set."""
        pass

