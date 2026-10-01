import sys

with open('/Users/srisaran/Quads/frontend/webapp/view/RecoveryPlanning.view.xml', 'r') as f:
    content = f.read()
    
with open('/Users/srisaran/.gemini/antigravity-ide/brain/6d2fbed0-5ebe-4959-be05-e142b4037407/scratch/new_recovery_ui.xml', 'r') as f:
    new_content = f.read()

start_marker = "                <!-- Page Header: Title + Context Subtitle + Action Buttons -->"
end_marker = "                    <!-- Bottom Action Row: Proceed to Stage 6 Final Decision -->"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    final_content = content[:start_idx] + new_content + "\n" + content[end_idx:]
    with open('/Users/srisaran/Quads/frontend/webapp/view/RecoveryPlanning.view.xml', 'w') as f:
        f.write(final_content)
    print("Updated successfully")
else:
    print("Markers not found", start_idx, end_idx)

