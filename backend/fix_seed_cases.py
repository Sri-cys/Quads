import json

path = '/Users/srisaran/Quads/data/mock/cases.json'
with open(path, 'r') as f:
    cases = json.load(f)

for c in cases:
    # ANY case that has passed priority (i.e. not CREATED, TRIAGED, CASE_OVERVIEW, IMPACT_ANALYSIS)
    if c['status'] not in ["CREATED", "TRIAGED", "CASE_OVERVIEW", "IMPACT_ANALYSIS"]:
        if not c.get('checkpoint1_decision'):
            c['checkpoint1_decision'] = "TIME"
        if not c.get('completed_stages'):
            c['completed_stages'] = []
        required_stages = ["CASE_OVERVIEW", "IMPACT_ANALYSIS", "PRIORITY"]
        for s in required_stages:
            if s not in c['completed_stages']:
                c['completed_stages'].append(s)

with open(path, 'w') as f:
    json.dump(cases, f, indent=4)
print("Updated cases.json successfully")
