from abc import ABC, abstractmethod
from typing import Any, Optional


class SAPAdapter(ABC):
    """
    Abstract interface for SAP enterprise system integrations:
    - SAP S/4HANA (Materials Management, Inventory)
    - SAP IBP (Integrated Business Planning - Demand & Supply Planning)
    - SAP TM (Transportation Management)
    - SAP Ariba / Business Network (Purchase Orders & Supplier Collaboration)
    """

    @abstractmethod
    def fetch_material_document(self, material_id: str, plant_id: str) -> Optional[dict[str, Any]]:
        """Fetch stock balance / material valuation from S/4HANA."""
        pass

    @abstractmethod
    def fetch_demand_forecast(self, material_id: str, plant_id: str) -> Optional[dict[str, Any]]:
        """Fetch consensus demand forecast from SAP IBP."""
        pass

    @abstractmethod
    def fetch_shipment_status(self, po_id: str) -> Optional[dict[str, Any]]:
        """Fetch transport execution status from SAP TM."""
        pass

    @abstractmethod
    def fetch_supplier_network_status(self, supplier_id: str) -> Optional[dict[str, Any]]:
        """Fetch supplier scorecard and network signals from SAP Business Network / Ariba."""
        pass

    @abstractmethod
    def create_recovery_order(
        self,
        case_id: str,
        plan_id: str,
        strategy: str,
        source_id: str,
        target_plant_id: str,
        material_id: str,
        quantity: float,
        transport_mode: str,
    ) -> dict[str, Any]:
        """Create recovery execution order in SAP S/4HANA & SAP TM."""
        pass

    @abstractmethod
    def poll_telematics_update(self, external_reference: str) -> dict[str, Any]:
        """Fetch tracking telematics from SAP TM / Business Network."""
        pass

