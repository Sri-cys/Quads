with open('/Users/srisaran/Quads/frontend/webapp/view/Decision.view.xml', 'r') as f:
    lines = f.readlines()

with open('new_cards.xml', 'r') as f:
    new_xml = f.read()

# Lines 134 to 249 in 1-indexed is index 133 to 248.
# Find the exact boundaries:
# We know they start at "<!-- No Plan Selected Message -->" around line 134.
start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if "<!-- No Plan Selected Message -->" in line:
        start_idx = i
    if "<!-- Decision Rationale Input (Enabled when PENDING) -->" in line:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    lines = lines[:start_idx] + [new_xml + "\n"] + lines[end_idx:]
    with open('/Users/srisaran/Quads/frontend/webapp/view/Decision.view.xml', 'w') as f:
        f.writelines(lines)
    print("Replaced successfully!")
else:
    print("Could not find boundaries")
