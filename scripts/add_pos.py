import json
from datetime import datetime, timedelta

def format_date(dt):
    return dt.strftime("%d %b %Y")

with open("/Users/srisaran/Quads/data/mock/cases.json", "r") as f:
    cases = json.load(f)

for i, case in enumerate(cases):
    # Calculate expected delivery date as in the frontend
    detected_at = case.get("detected_at")
    if detected_at:
        try:
            dt = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
        except:
            dt = datetime.utcnow()
    else:
        dt = datetime.utcnow()
        
    exp_delivery = dt + timedelta(days=2)
    qty = case.get("affected_quantity", 500)
    
    # 1 delayed, 1 confirmed (if index even)
    po_delayed = {
        "poId": f"PO-2026-{i*2+1:03d}",
        "quantity": f"{qty} Units",
        "expectedDeliveryDate": format_date(exp_delivery),
        "status": "DELAYED"
    }
    
    pos = [po_delayed]
    
    if i % 2 == 0:
        pos.append({
            "poId": f"PO-2026-{i*2+2:03d}",
            "quantity": f"{qty} Units",
            "expectedDeliveryDate": format_date(exp_delivery + timedelta(days=7)),
            "status": "CONFIRMED"
        })
        
    case["purchaseOrders"] = pos

with open("/Users/srisaran/Quads/data/mock/cases.json", "w") as f:
    json.dump(cases, f, indent=2)

print("done")
