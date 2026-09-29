import re

stages = [
    "Case", "Impact Analysis", "Priority", "Constraints", 
    "Recovery Planning", "Decision", "Exec & Monitoring", "Outcome"
]

xml = """
        <!-- Workflow Stepper Card -->
        <VBox class="quadsStepperCard sapUiSmallMarginBottom" width="100%">
            <HBox alignItems="Center" width="100%">
                <ScrollContainer class="quadsTimelineScroll" horizontal="true" vertical="false">
                    <HBox class="quadsTimelineFlexRow">
"""

for i, stage in enumerate(stages):
    n = i + 1
    # Replace & with &amp;
    stage_safe = stage.replace("&", "&amp;")
    
    xml += f"""
                        <!-- {n}. {stage_safe} -->
                        <VBox class="{{= ${{app>/completedStage}} >= {n} &amp;&amp; ${{app>/activeStep}} === {n} ? 'quadsTimelineItem current-completed' : (${{app>/completedStage}} >= {n} ? 'quadsTimelineItem completed' : (${{app>/activeStep}} === {n} ? 'quadsTimelineItem current' : 'quadsTimelineItem pending')) }}">
                            <HBox alignItems="Center" justifyContent="Center" class="quadsTimelineCircleBox">
                                <core:Icon src="sap-icon://accept" visible="{{= ${{app>/completedStage}} >= {n}}}" class="quadsTimelineIcon" />
                                <Text text="{n}" visible="{{= ${{app>/completedStage}} &lt; {n}}}" class="quadsTimelineText" />
                            </HBox>
                            <Text text="{stage_safe}" class="quadsTimelineLabel" />
                        </VBox>"""

xml += """
                    </HBox>
                </ScrollContainer>
                
                <!-- Audit Trail (separate, always accessible) -->
                <Button
                    text="Audit Trail"
                    icon="sap-icon://history"
                    press=".onWorkflowStagePress"
                    class="quadsWfAudit sapUiSmallMarginBegin">
                    <customData>
                        <core:CustomData key="step" value="9" />
                    </customData>
                </Button>
            </HBox>
        </VBox>
"""

with open('/Users/srisaran/Quads/frontend/webapp/view/CaseWorkflowHeader.fragment.xml', 'r') as f:
    content = f.read()

start = content.find("<!-- Workflow Stepper Card -->")
end = content.find("</VBox>\n</core:FragmentDefinition>")

if start != -1 and end != -1:
    new_content = content[:start] + xml.strip() + "\n    " + content[end:]
    with open('/Users/srisaran/Quads/frontend/webapp/view/CaseWorkflowHeader.fragment.xml', 'w') as f:
        f.write(new_content)
    print("Rewrote CaseWorkflowHeader")
else:
    print(f"Failed to find boundaries, start: {start}, end: {end}")
