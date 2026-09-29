import json
import os

cases_file = "/Users/srisaran/Quads/data/mock/cases.json"

with open(cases_file, "r") as f:
    cases = json.load(f)

for case in cases:
    if case["case_id"] == "CASE-0101":
        case.update({
            "supplier_reliability": "88%",
            "otd": "85%",
            "open_po": "PO-101",
            "supplier_capacity": "90%",
            "supplier_risk": "HIGH",
            "recent_performance": "Declining due to capacity constraints",
            "transit_time": "3 Days",
            "logistics_risk": "MEDIUM",
            "alternate_logistics": "Available",
            "production_rate": "40 units/day",
            "production_orders_affected": "3 lines",
            "material_requirement": "40 units/day",
            "production_interruption_risk": "CRITICAL",
            "financial_exposure": "$120,000"
        })
    elif case["case_id"] == "CASE-0102":
        case.update({
            "supplier_reliability": "92%",
            "otd": "90%",
            "open_po": "PO-102",
            "supplier_capacity": "85%",
            "supplier_risk": "MEDIUM",
            "recent_performance": "Stable",
            "transit_time": "14 Days",
            "logistics_risk": "HIGH",
            "alternate_logistics": "None (Port Congestion)",
            "production_rate": "40 units/day",
            "production_orders_affected": "2 lines",
            "material_requirement": "40 units/day",
            "production_interruption_risk": "HIGH",
            "financial_exposure": "$95,000"
        })
    elif case["case_id"] == "CASE-0103":
        case.update({
            "supplier_reliability": "95%",
            "otd": "94%",
            "open_po": "PO-103",
            "supplier_capacity": "88%",
            "supplier_risk": "LOW",
            "recent_performance": "Improving",
            "transit_time": "6 Days",
            "logistics_risk": "LOW",
            "alternate_logistics": "Available",
            "production_rate": "50 units/day",
            "production_orders_affected": "1 line",
            "material_requirement": "50 units/day",
            "production_interruption_risk": "MEDIUM",
            "financial_exposure": "$45,000"
        })
    elif case["case_id"] == "CASE-0104":
        case.update({
            "supplier_reliability": "85%",
            "otd": "82%",
            "open_po": "PO-104",
            "supplier_capacity": "92%",
            "supplier_risk": "HIGH",
            "recent_performance": "Volatile due to weather",
            "transit_time": "2 Days",
            "logistics_risk": "HIGH",
            "alternate_logistics": "Grounded",
            "production_rate": "30 units/day",
            "production_orders_affected": "2 lines",
            "material_requirement": "30 units/day",
            "production_interruption_risk": "HIGH",
            "financial_exposure": "$80,000"
        })
    elif case["case_id"] == "CASE-0105":
        case.update({
            "supplier_reliability": "98%",
            "otd": "98%",
            "open_po": "PO-105",
            "supplier_capacity": "80%",
            "supplier_risk": "LOW",
            "recent_performance": "Excellent",
            "transit_time": "5 Days",
            "logistics_risk": "LOW",
            "alternate_logistics": "Multiple Options",
            "production_rate": "50 units/day",
            "production_orders_affected": "Minimal",
            "material_requirement": "50 units/day",
            "production_interruption_risk": "LOW",
            "financial_exposure": "$15,000"
        })

with open(cases_file, "w") as f:
    json.dump(cases, f, indent=2)

print("Cases updated with extra fields.")
