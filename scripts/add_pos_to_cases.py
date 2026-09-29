import json

cases_file = "/Users/srisaran/Quads/data/mock/cases.json"
with open(cases_file, "r") as f:
    cases = json.load(f)

for case in cases:
    # "match the case's Open PO, affected quantity, and expected delivery date"
    open_po = case.get("open_po", "PO-2026-001")
    qty = case.get("affected_quantity", 500)
    
    # Expected delivery date logic
    import datetime
    # Assuming detected_at is around 2026-09-27
    expected_del_date_str = "2026-09-29"
    if "expected_delay_days" in case:
        expected_del_date_str = (datetime.datetime(2026, 9, 27) + datetime.timedelta(days=case["expected_delay_days"])).strftime("%Y-%m-%d")

    pos = [
        {
            "poId": open_po,
            "quantity": qty,
            "expectedDeliveryDate": expected_del_date_str,
            "status": "DELAYED"
        },
        {
            "poId": open_po[:-1] + str((int(open_po[-1]) + 1) if open_po[-1].isdigit() else "X"),
            "quantity": int(qty * 0.5),
            "expectedDeliveryDate": (datetime.datetime.strptime(expected_del_date_str, "%Y-%m-%d") + datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
            "status": "CONFIRMED"
        }
    ]
    case["purchaseOrders"] = pos

with open(cases_file, "w") as f:
    json.dump(cases, f, indent=2)

print("Added purchaseOrders to cases")
