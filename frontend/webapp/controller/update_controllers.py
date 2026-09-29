import os
import re

controllers = {
    "CaseOverview": 1,
    "ImpactAnalysis": 2,
    "Checkpoint1": 3,
    "Constraints": 4,
    "RecoveryPlanning": 5,
    "Decision": 6,
    "ExecutionMonitoring": 7,
    "Outcome": 8
}

for name, step in controllers.items():
    file_path = f"/Users/srisaran/Quads/frontend/webapp/controller/{name}.controller.js"
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r") as f:
        content = f.read()

    # Find the function that handles route matching, it could be _onPatternMatched or _onRouteMatched
    # or handleRouteMatched
    
    # We will just inject the call to setStepperState right after setting this._sCurrentCaseId
    content = re.sub(
        r'(this\._sCurrentCaseId\s*=\s*[^;]+;)',
        rf'\1\n            sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {{\n                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, {step});\n            }}.bind(this));',
        content
    )
    
    # Add setStepperState after markStageCompleted
    content = re.sub(
        r'(WorkflowNavHelper\.markStageCompleted\([^,]+,\s*\d+\);)',
        rf'\1\n                    WorkflowNavHelper.setStepperState(sCaseId || this._sCurrentCaseId, {step});',
        content
    )
    
    # For ImpactAnalysis, add markStageCompleted when analysis finishes (COMPLETED)
    if name == "ImpactAnalysis":
        content = re.sub(
            r'(oModel\.setProperty\("/analysisState", "COMPLETED"\);)',
            r'\1\n                sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {\n                    WorkflowNavHelper.markStageCompleted(caseData.case_id || that._sCurrentCaseId, 2);\n                    WorkflowNavHelper.setStepperState(caseData.case_id || that._sCurrentCaseId, 2);\n                });',
            content
        )

    with open(file_path, "w") as f:
        f.write(content)
