steps = [
    (1, "Case"),
    (2, "Impact Analysis"),
    (3, "Priority"),
    (4, "Constraints"),
    (5, "Recovery Planning"),
    (6, "Decision"),
    (7, "Execution & Monitoring"),
    (8, "Outcome")
]

xml = []
xml.append('        <!-- Workflow Stepper Card -->')
xml.append('        <VBox class="quadsStepperCard sapUiSmallMarginBottom">')
xml.append('            <HBox class="quadsTimelineRow">')

for step, label in steps:
    is_last = (step == 8)
    
    # Node class
    node_class = f"{{= ${{app>/activeStep}} === {step} ? (${{app>/stageStep}} >= {step} ? 'quadsTimelineNode current-completed' : 'quadsTimelineNode current') : (${{app>/stageStep}} >= {step} ? 'quadsTimelineNode completed' : 'quadsTimelineNode pending') }}"
    
    # Label class
    label_class = f"{{= ${{app>/activeStep}} === {step} ? 'quadsTimelineLabel current' : (${{app>/stageStep}} >= {step} ? 'quadsTimelineLabel completed' : 'quadsTimelineLabel pending') }}"
    
    # Line class
    line_class = f"{{= ${{app>/stageStep}} >= {step} ? 'quadsTimelineLine completed' : 'quadsTimelineLine pending' }}"
    
    xml.append(f'                <!-- {step}. {label.upper()} -->')
    xml.append(f'                <HBox class="quadsTimelineStep">')
    
    # Node (circle)
    xml.append(f'                    <VBox class="{node_class}">')
    
    # Text or Icon inside node
    xml.append(f'                        <core:Icon src="sap-icon://accept" class="quadsTimelineIcon" visible="{{= ${{app>/stageStep}} >= {step} }}" />')
    xml.append(f'                        <Text text="{step}" visible="{{= ${{app>/stageStep}} < {step} }}" />')
    
    xml.append(f'                    </VBox>')
    
    # Label
    xml.append(f'                    <Text text="{label}" class="{label_class}" />')
    
    xml.append(f'                </HBox>')
    
    if not is_last:
        xml.append(f'                <VBox class="{line_class}" />')
        xml.append('')

xml.append('            </HBox>')
xml.append('        </VBox>')

print('\n'.join(xml))
