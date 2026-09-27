from typing import Any, Optional
from app.adapters.sap.base import SAPAdapter


class MockSAPAdapter(SAPAdapter):
    """
    Mock implementation of SAP enterprise system integration for Phase 1.
    Simulates responses from S/4HANA, SAP IBP, SAP TM, and SAP Ariba
    without network calls or real credentials.
    """

    def __init__(self, mode: str = "MOCK"):
        self.mode = mode

    def fetch_material_document(self, material_id: str, plant_id: str) -> Optional[dict[str, Any]]:
        return {
            "source_system": "SAP S/4HANA (Mock)",
            "material_id": material_id,
            "plant_id": plant_id,
            "valuation_area": plant_id,
            "status": "ACTIVE",
        }

    def fetch_demand_forecast(self, material_id: str, plant_id: str) -> Optional[dict[str, Any]]:
        return {
            "source_system": "SAP IBP (Mock)",
            "material_id": material_id,
            "plant_id": plant_id,
            "planning_level": "WEEKLY",
            "forecast_accuracy": 0.92,
        }

    def fetch_shipment_status(self, po_id: str) -> Optional[dict[str, Any]]:
        return {
            "source_system": "SAP Transportation Management (Mock)",
            "po_id": po_id,
            "freight_order_status": "IN_TRANSIT",
            "telematics_verified": True,
        }

    def fetch_supplier_network_status(self, supplier_id: str) -> Optional[dict[str, Any]]:
        return {
            "source_system": "SAP Business Network / Ariba (Mock)",
            "supplier_id": supplier_id,
            "collaboration_tier": "PREFERRED",
            "asn_acknowledged": True,
        }

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
        doc_num_hash = abs(hash(f"{case_id}:{plan_id}:{quantity}")) % 900000 + 100000
        
        carrier_map = {
            "AIR_EXPEDITED": ("Lufthansa Cargo Priority", "AIR"),
            "ROAD_EXPRESS": ("DHL Express Dedicated Fleet", "ROAD"),
            "STANDARD_ROAD": ("Schenker European Logistics", "ROAD"),
            "RAIL_INTERMODAL": ("DB Cargo Rail Intermodal", "RAIL"),
            "MULTIMODAL_HYBRID": ("DHL Global Forwarding Multimodal", "HYBRID"),
        }
        carrier_name, mode_type = carrier_map.get(transport_mode, ("DHL Express Dedicated Fleet", "ROAD"))

        if strategy == "ALTERNATE_SUPPLIER":
            action_type = "EMERGENCY_PURCHASE_ORDER"
            ext_ref = f"SAP-PO-{doc_num_hash}"
            ext_sys = "SAP S/4HANA Procurement & Ariba Network"
        elif strategy == "INTER_PLANT_TRANSFER":
            action_type = "STOCK_TRANSPORT_ORDER"
            ext_ref = f"SAP-STO-{doc_num_hash}"
            ext_sys = "SAP S/4HANA Inventory & Logistics"
        elif strategy == "SPLIT_SOURCING":
            action_type = "SPLIT_SOURCING_ORDER"
            ext_ref = f"SAP-SPLIT-{doc_num_hash}"
            ext_sys = "SAP S/4HANA & TM Multi-Leg Execution"
        else:
            action_type = "EXPEDITED_FREIGHT_BOOKING"
            ext_ref = f"SAP-FO-{doc_num_hash}"
            ext_sys = "SAP Transportation Management"

        return {
            "action_type": action_type,
            "external_reference": ext_ref,
            "external_system": ext_sys,
            "status": "ACCEPTED",
            "carrier_name": carrier_name,
            "tracking_number": f"TRK-{ext_ref}",
            "confirmed_quantity": quantity,
        }

    def poll_telematics_update(self, external_reference: str) -> dict[str, Any]:
        return {
            "external_reference": external_reference,
            "source_system": "SAP Transportation Management (Mock)",
            "telematics_online": True,
            "gps_lat": 48.1371,
            "gps_lon": 11.5754,
            "status": "IN_TRANSIT",
        }


class RealSAPAdapter(SAPAdapter):
    """
    Future production SAP adapter boundary.
    In future phases, this will use SAP Cloud SDK / SAP BTP Destination Service
    to interact with real SAP OData/REST APIs.
    """

    def __init__(self, destination_name: str = "SAP_S4HANA_DESTINATION"):
        self.destination_name = destination_name

    def fetch_material_document(self, material_id: str, plant_id: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError("RealSAPAdapter will be enabled upon SAP BTP destination configuration.")

    def fetch_demand_forecast(self, material_id: str, plant_id: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError("RealSAPAdapter will be enabled upon SAP BTP destination configuration.")

    def fetch_shipment_status(self, po_id: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError("RealSAPAdapter will be enabled upon SAP BTP destination configuration.")

    def fetch_supplier_network_status(self, supplier_id: str) -> Optional[dict[str, Any]]:
        raise NotImplementedError("RealSAPAdapter will be enabled upon SAP BTP destination configuration.")

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
        raise NotImplementedError("RealSAPAdapter will be enabled upon SAP BTP destination configuration.")

    def poll_telematics_update(self, external_reference: str) -> dict[str, Any]:
        raise NotImplementedError("RealSAPAdapter will be enabled upon SAP BTP destination configuration.")

