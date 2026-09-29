import json

def fix_inventory():
    with open("/Users/srisaran/Quads/data/mock/inventory.json", "r") as f:
        data = json.load(f)
    for d in data:
        if "current_stock" in d:
            d["quantity"] = d.pop("current_stock")
        if "reserved_stock" in d:
            d["reserved_quantity"] = d.pop("reserved_stock")
        d.pop("available_stock", None)
    with open("/Users/srisaran/Quads/data/mock/inventory.json", "w") as f:
        json.dump(data, f, indent=2)

def fix_safety_stock():
    with open("/Users/srisaran/Quads/data/mock/safety_stock.json", "r") as f:
        data = json.load(f)
    for d in data:
        if "minimum_quantity" in d:
            d["quantity"] = d.pop("minimum_quantity")
        d.pop("target_quantity", None)
    with open("/Users/srisaran/Quads/data/mock/safety_stock.json", "w") as f:
        json.dump(data, f, indent=2)

def fix_demand():
    with open("/Users/srisaran/Quads/data/mock/demand.json", "r") as f:
        data = json.load(f)
    for d in data:
        if "daily_consumption_rate" in d:
            d["daily_demand"] = d.pop("daily_consumption_rate")
        d.pop("upcoming_orders_30d", None)
    with open("/Users/srisaran/Quads/data/mock/demand.json", "w") as f:
        json.dump(data, f, indent=2)

fix_inventory()
fix_safety_stock()
fix_demand()
print("Fixed.")
