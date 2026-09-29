import re

stages = [
    "Case", "Impact Analysis", "Priority", "Constraints", 
    "Recovery Planning", "Decision", "Exec & Monitoring", "Outcome"
]

xml = """
        <!-- Workflow Stepper Card -->
        <VBox class="quadsStepperCard sapUiSmallMarginBottom" width="100%">
            <HBox alignItems="Center">
                <ScrollContainer width="100%" horizontal="true" vertical="false">
                    <HBox class="sapUiTinyMarginTop sapUiTinyMarginBottom" style="min-width:700px; padding-top:4px; padding-bottom:4px;" width="100%">
"""

for i, stage in enumerate(stages):
    n = i + 1
    
    xml += f"""
                        <!-- {n}. {stage.upper()} -->
                        <VBox alignItems="Center" style="width: 80px;">
                            <HBox alignItems="Center" justifyContent="Center" 
                                class="{{= ${{app>/completedStage}} >= {n} && ${{app>/activeStep}} === {n} ? 'quadsTimelineNode current-completed' : (${{app>/completedStage}} >= {n} ? 'quadsTimelineNode completed' : (${{app>/activeStep}} === {n} ? 'quadsTimelineNode current' : 'quadsTimelineNode pending')) }}">
                                <core:Icon src="sap-icon://accept" visible="{{= ${{app>/completedStage}} >= {n}}}" class="quadsTimelineIcon" />
                                <Text text="{n}" visible="{{= ${{app>/completedStage}} < {n}}}" />
                            </HBox>
                            <Text text="{stage}" textAlign="Center" class="{{= ${{app>/completedStage}} >= {n} && ${{app>/activeStep}} === {n} ? 'quadsWfTimelineLabel current' : (${{app>/completedStage}} >= {n} ? 'quadsWfTimelineLabel completed' : (${{app>/activeStep}} === {n} ? 'quadsWfTimelineLabel current' : 'quadsWfTimelineLabel pending')) }}" />
                        </VBox>"""
    
    if n < 8:
        xml += f"""
                        <HBox class="{{= ${{app>/completedStage}} >= {n} ? 'quadsWfTimelineLine completed' : 'quadsWfTimelineLine pending' }}" />"""

xml += """
                    </HBox>
                </ScrollContainer>
                <!-- Audit Trail (separate, always accessible) -->
                <Button
                    text="Audit Trail"
                    icon="sap-icon://history"
                    press=".onWorkflowStagePress"
                    class="quadsWfTab quadsWfAudit sapUiSmallMarginBegin">
                    <customData>
                        <core:CustomData key="step" value="9" />
                    </customData>
                </Button>
            </HBox>
        </VBox>
"""

with open('/Users/srisaran/Quads/frontend/webapp/view/CaseWorkflowHeader.fragment.xml', 'r') as f:
    content = f.read()

# Replace between <!-- Workflow Stepper Card --> and <!-- Spacer -->
start = content.find("<!-- Workflow Stepper Card -->")
end = content.find("</VBox>\n    </VBox>\n</core:FragmentDefinition>")

if start != -1 and end != -1:
    new_content = content[:start] + xml.strip() + "\n    " + content[end:]
    with open('/Users/srisaran/Quads/frontend/webapp/view/CaseWorkflowHeader.fragment.xml', 'w') as f:
        f.write(new_content)
    print("Done")
else:
    print("Failed to find boundaries")
