import json

path = '/Users/srisaran/Quads/data/mock/cases.json'
with open(path, 'r') as f:
    cases = json.load(f)

def clean_array(arr):
    out = []
    for x in arr:
        mapping = {
            "CASE_OVERVIEW": "Case",
            "IMPACT_ANALYSIS": "Impact Analysis",
            "PRIORITY": "Priority",
            "CONSTRAINTS": "Constraints",
            "RECOVERY_PLANNING": "Recovery Planning",
            "DECISION": "Decision",
            "EXEC_MONITORING": "Exec & Monitoring",
            "OUTCOME": "Outcome"
        }
        val = mapping.get(x, x)
        if val not in out:
            out.append(val)
    return out

for c in cases:
    if c['case_id'] == 'CASE-0001':
        c['completed_stages'] = ["Case", "Impact Analysis", "Priority", "Recovery Planning"]
    else:
        c['completed_stages'] = clean_array(c.get('completed_stages', []))

with open(path, 'w') as f:
    json.dump(cases, f, indent=4)
print("done")
