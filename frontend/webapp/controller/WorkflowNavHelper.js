sap.ui.define([
    "sap/m/MessageToast"
], function (MessageToast) {
    "use strict";

    var STEP_ROUTES = {
        1: "caseOverview",
        2: "impactAnalysis",
        3: "checkpoint1",
        4: "recoveryPlanning",
        5: "recoveryPlanning",
        6: "decision",
        7: "executionMonitoring",
        8: "outcome"
    };

    return {
        onWorkflowStagePress: function (oEvent, oController) {
            var ctrl = oController || this;
            var aCustomData = oEvent.getSource().getCustomData();
            var nTargetStep = 1;
            if (aCustomData && aCustomData.length > 0) {
                nTargetStep = parseInt(aCustomData[0].getValue(), 10);
            }

            var oAppModel = ctrl.getOwnerComponent().getModel("app");
            var nAllowedStep = oAppModel.getProperty("/stageStep") || 1;
            var sCaseId = oAppModel.getProperty("/selectedCaseId") || "CASE-0001";

            // If resolved, outcome is unlocked
            var sStatus = (oAppModel.getProperty("/caseStatus") || "").toUpperCase();
            if (sStatus === "RESOLVED") {
                nAllowedStep = 8;
            }

            if (nTargetStep <= nAllowedStep) {
                var sRoute = STEP_ROUTES[nTargetStep] || "caseOverview";
                ctrl.getOwnerComponent().getRouter().navTo(sRoute, { caseId: sCaseId });
            } else {
                MessageToast.show("Complete the current workflow stage first.");
            }
        }
    };
});
