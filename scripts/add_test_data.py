import json

def update_json(filename, new_data, id_key):
    path = f"/Users/srisaran/Quads/data/mock/{filename}"
    with open(path, "r") as f:
        data = json.load(f)
    existing_ids = {d[id_key] if isinstance(id_key, str) else tuple(d[k] for k in id_key) for d in data}
    for item in new_data:
        k = item[id_key] if isinstance(id_key, str) else tuple(item[k] for k in id_key)
        if k not in existing_ids:
            data.append(item)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

suppliers = [
    {"supplier_id": "SUP-101", "name": "Alpha Cells GmbH", "location": "Hamburg, Germany", "reliability_score": 88, "on_time_delivery_rate": 0.85, "average_lead_time_days": 10, "risk_level": "HIGH", "recent_performance_trend": "Declining due to capacity constraints"},
    {"supplier_id": "SUP-102", "name": "Nordic Steel AB", "location": "Rotterdam, Netherlands", "reliability_score": 92, "on_time_delivery_rate": 0.90, "average_lead_time_days": 14, "risk_level": "MEDIUM", "recent_performance_trend": "Stable"},
    {"supplier_id": "SUP-103", "name": "Baltic Wiring Ltd", "location": "Gdansk, Poland", "reliability_score": 95, "on_time_delivery_rate": 0.94, "average_lead_time_days": 7, "risk_level": "LOW", "recent_performance_trend": "Improving"},
    {"supplier_id": "SUP-104", "name": "Shanghai Electronics Co", "location": "Shanghai, China", "reliability_score": 85, "on_time_delivery_rate": 0.82, "average_lead_time_days": 21, "risk_level": "HIGH", "recent_performance_trend": "Volatile due to weather"},
    {"supplier_id": "SUP-105", "name": "Rhein Precision", "location": "Stuttgart, Germany", "reliability_score": 98, "on_time_delivery_rate": 0.98, "average_lead_time_days": 3, "risk_level": "LOW", "recent_performance_trend": "Excellent"}
]
update_json("suppliers.json", suppliers, "supplier_id")

materials = [
    {"material_id": "MAT-101", "name": "Lithium Battery Cell", "category": "Energy", "unit_cost": 250.0},
    {"material_id": "MAT-102", "name": "Steel Housing", "category": "Chassis", "unit_cost": 120.0},
    {"material_id": "MAT-103", "name": "Wiring Harness", "category": "Electrical", "unit_cost": 85.0},
    {"material_id": "MAT-104", "name": "Control Unit", "category": "Electronics", "unit_cost": 340.0},
    {"material_id": "MAT-105", "name": "Gear Assembly", "category": "Drivetrain", "unit_cost": 410.0}
]
update_json("materials.json", materials, "material_id")

plants = [
    {"plant_id": "PLANT-101", "name": "Leipzig Battery Plant", "location": "Leipzig, Germany", "capacity_utilization": 0.90, "production_rate_per_day": 40},
    {"plant_id": "PLANT-102", "name": "Munich Assembly Plant", "location": "Munich, Germany", "capacity_utilization": 0.85, "production_rate_per_day": 40},
    {"plant_id": "PLANT-103", "name": "Berlin Plant", "location": "Berlin, Germany", "capacity_utilization": 0.88, "production_rate_per_day": 50},
    {"plant_id": "PLANT-104", "name": "Frankfurt Plant", "location": "Frankfurt, Germany", "capacity_utilization": 0.92, "production_rate_per_day": 30},
    {"plant_id": "PLANT-105", "name": "Stuttgart Plant", "location": "Stuttgart, Germany", "capacity_utilization": 0.80, "production_rate_per_day": 50}
]
update_json("plants.json", plants, "plant_id")

inventory = [
    {"material_id": "MAT-101", "plant_id": "PLANT-101", "current_stock": 80, "reserved_stock": 40, "available_stock": 40},
    {"material_id": "MAT-102", "plant_id": "PLANT-102", "current_stock": 300, "reserved_stock": 100, "available_stock": 200},
    {"material_id": "MAT-103", "plant_id": "PLANT-103", "current_stock": 600, "reserved_stock": 100, "available_stock": 500},
    {"material_id": "MAT-104", "plant_id": "PLANT-104", "current_stock": 150, "reserved_stock": 30, "available_stock": 120},
    {"material_id": "MAT-105", "plant_id": "PLANT-105", "current_stock": 1200, "reserved_stock": 200, "available_stock": 1000}
]
update_json("inventory.json", inventory, ("material_id", "plant_id"))

safety_stock = [
    {"material_id": "MAT-101", "plant_id": "PLANT-101", "minimum_quantity": 60, "target_quantity": 100},
    {"material_id": "MAT-102", "plant_id": "PLANT-102", "minimum_quantity": 120, "target_quantity": 200},
    {"material_id": "MAT-103", "plant_id": "PLANT-103", "minimum_quantity": 150, "target_quantity": 250},
    {"material_id": "MAT-104", "plant_id": "PLANT-104", "minimum_quantity": 80, "target_quantity": 150},
    {"material_id": "MAT-105", "plant_id": "PLANT-105", "minimum_quantity": 200, "target_quantity": 400}
]
update_json("safety_stock.json", safety_stock, ("material_id", "plant_id"))

demand = [
    {"material_id": "MAT-101", "plant_id": "PLANT-101", "daily_consumption_rate": 40, "upcoming_orders_30d": 1200},
    {"material_id": "MAT-102", "plant_id": "PLANT-102", "daily_consumption_rate": 40, "upcoming_orders_30d": 1200},
    {"material_id": "MAT-103", "plant_id": "PLANT-103", "daily_consumption_rate": 50, "upcoming_orders_30d": 1500},
    {"material_id": "MAT-104", "plant_id": "PLANT-104", "daily_consumption_rate": 30, "upcoming_orders_30d": 900},
    {"material_id": "MAT-105", "plant_id": "PLANT-105", "daily_consumption_rate": 50, "upcoming_orders_30d": 1500}
]
update_json("demand.json", demand, ("material_id", "plant_id"))

purchase_orders = [
    {"po_id": "PO-101", "supplier_id": "SUP-101", "material_id": "MAT-101", "plant_id": "PLANT-101", "quantity": 400, "status": "DELAYED", "expected_delivery_date": "2026-09-29T00:00:00Z"},
    {"po_id": "PO-102", "supplier_id": "SUP-102", "material_id": "MAT-102", "plant_id": "PLANT-102", "quantity": 500, "status": "DELAYED", "expected_delivery_date": "2026-10-01T00:00:00Z"},
    {"po_id": "PO-103", "supplier_id": "SUP-103", "material_id": "MAT-103", "plant_id": "PLANT-103", "quantity": 600, "status": "DELAYED", "expected_delivery_date": "2026-10-05T00:00:00Z"},
    {"po_id": "PO-104", "supplier_id": "SUP-104", "material_id": "MAT-104", "plant_id": "PLANT-104", "quantity": 300, "status": "DELAYED", "expected_delivery_date": "2026-10-02T00:00:00Z"},
    {"po_id": "PO-105", "supplier_id": "SUP-105", "material_id": "MAT-105", "plant_id": "PLANT-105", "quantity": 800, "status": "DELAYED", "expected_delivery_date": "2026-10-08T00:00:00Z"}
]
update_json("purchase_orders.json", purchase_orders, "po_id")

print("All mock data updated.")
