sap.ui.define([
    "sap/m/MessageToast"
], function (MessageToast) {
    "use strict";

    var STEP_ROUTES = {
        1: "caseOverview",
        2: "impactAnalysis",
        3: "checkpoint1",
        4: "constraints",
        5: "recoveryPlanning",
        6: "decision",
        7: "executionMonitoring",
        8: "outcome"
    };

    var STEP_NAMES = {
        1: "Case",
        2: "Impact Analysis",
        3: "Priority",
        4: "Constraints",
        5: "Recovery Planning",
        6: "Decision",
        7: "Execution & Monitoring",
        8: "Outcome"
    };

    return {
        onWorkflowStagePress: function (oEvent, oController) {
            var ctrl = oController || this;
            var aCustomData = oEvent.getSource().getCustomData();
            var nTargetStep = 1;
            if (aCustomData && aCustomData.length > 0) {
                nTargetStep = parseInt(aCustomData[0].getValue(), 10);
            }

            // Audit Trail: independent, always accessible
            if (nTargetStep === 9) {
                var sCaseId = ctrl.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
                var sHash = ctrl.getOwnerComponent().getRouter().getURL("outcome", { caseId: sCaseId });
                var sUrl = window.location.href.split('#')[0] + "#/" + (sHash.replace(/^\/?/, ''));
                window.open(sUrl, "_blank");
                return;
            }

            var oAppModel = ctrl.getOwnerComponent().getModel("app");
            var nAllowedStep = oAppModel.getProperty("/stageStep") || 1;
            var sCaseId = oAppModel.getProperty("/selectedCaseId") || "CASE-0001";
            var sStatus = (oAppModel.getProperty("/caseStatus") || "").toUpperCase();

            // RESOLVED cases unlock all 8 steps
            if (sStatus === "RESOLVED") {
                nAllowedStep = 8;
            }

            // RULE: Navigate freely to any completed stage (nTargetStep <= nAllowedStep)
            // Block future/uncompleted stages (nTargetStep > nAllowedStep)
            if (nTargetStep <= nAllowedStep) {
                var sRoute = STEP_ROUTES[nTargetStep] || "caseOverview";
                ctrl.getOwnerComponent().getRouter().navTo(sRoute, { caseId: sCaseId });
            } else {
                var sBlockedName = STEP_NAMES[nTargetStep] || "this stage";
                var sCurrentName = STEP_NAMES[nAllowedStep] || "the current stage";
                MessageToast.show(
                    "Complete \"" + sCurrentName + "\" first to unlock \"" + sBlockedName + "\"."
                );
            }
        }
    };
});
