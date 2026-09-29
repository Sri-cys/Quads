import json
import os

cases_file = "/Users/srisaran/Quads/data/mock/cases.json"

with open(cases_file, "r") as f:
    cases = json.load(f)

new_cases = [
    {
        "case_id": "CASE-0101",
        "disruption_type": "FACTORY_INCIDENT",
        "description": "Factory fire halted battery cell production line.",
        "supplier_id": "SUP-101",
        "material_id": "MAT-101",
        "plant_id": "PLANT-101",
        "expected_delay_days": 14,
        "affected_quantity": 400,
        "detected_at": "2026-09-27T08:00:00Z",
        "status": "CASE_OVERVIEW",
        "completed_stages": []
    },
    {
        "case_id": "CASE-0102",
        "disruption_type": "PORT_CONGESTION",
        "description": "Port congestion holding container release.",
        "supplier_id": "SUP-102",
        "material_id": "MAT-102",
        "plant_id": "PLANT-102",
        "expected_delay_days": 7,
        "affected_quantity": 500,
        "detected_at": "2026-09-27T08:00:00Z",
        "status": "IMPACT_ANALYSIS",
        "completed_stages": ["Case"]
    },
    {
        "case_id": "CASE-0103",
        "disruption_type": "SUPPLIER_DELAY",
        "description": "Supplier raw material shortage delaying dispatch.",
        "supplier_id": "SUP-103",
        "material_id": "MAT-103",
        "plant_id": "PLANT-103",
        "expected_delay_days": 5,
        "affected_quantity": 600,
        "detected_at": "2026-09-27T08:00:00Z",
        "status": "PRIORITY_SAVED",
        "completed_stages": ["Case", "Impact Analysis", "Priority"]
    },
    {
        "case_id": "CASE-0104",
        "disruption_type": "WEATHER_EVENT",
        "description": "Severe storm grounded cargo flights.",
        "supplier_id": "SUP-104",
        "material_id": "MAT-104",
        "plant_id": "PLANT-104",
        "expected_delay_days": 3,
        "affected_quantity": 300,
        "detected_at": "2026-09-27T08:00:00Z",
        "status": "AGENT2_COMPLETED",
        "completed_stages": ["Case", "Impact Analysis", "Priority", "Constraints", "Recovery Planning"]
    },
    {
        "case_id": "CASE-0105",
        "disruption_type": "EQUIPMENT_BREAKDOWN",
        "description": "Machining equipment breakdown reducing output.",
        "supplier_id": "SUP-105",
        "material_id": "MAT-105",
        "plant_id": "PLANT-105",
        "expected_delay_days": 2,
        "affected_quantity": 800,
        "detected_at": "2026-09-27T08:00:00Z",
        "status": "RESOLVED",
        "completed_stages": ["Case", "Impact Analysis", "Priority", "Constraints", "Recovery Planning", "Decision", "Exec & Monitoring", "Outcome"]
    }
]

# Ensure we don't duplicate
existing_ids = {c["case_id"] for c in cases}
for nc in new_cases:
    if nc["case_id"] not in existing_ids:
        cases.append(nc)

with open(cases_file, "w") as f:
    json.dump(cases, f, indent=2)

print("Cases added.")
