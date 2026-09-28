sap.ui.define([
    "sap/ui/model/json/JSONModel",
    "sap/ui/Device"
], function (JSONModel, Device) {
    "use strict";

    return {
        createDeviceModel: function () {
            var oModel = new JSONModel(Device);
            oModel.setDefaultBindingMode("OneWay");
            return oModel;
        },

        createAppModel: function () {
            // Use relative path for single-origin integrated application (http://localhost:8000/)
            // When running on standalone UI5 dev server (port 8080), route to backend port 8000
            var sBackendUrl = (window.location.port === "8080") ? "http://localhost:8000" : "";

            var oModel = new JSONModel({
                backendUrl: sBackendUrl,
                selectedCaseId: "CASE-0001",
                currentRoute: "",
                stageStep: 5,
                activeStep: 5,
                caseStatus: "EXECUTION_IN_PROGRESS",
                caseStatusText: "Execution In Progress",
                caseStatusState: "Information",
                currentStageName: "Impact Analysis",
                nextStageName: "Checkpoint 1",
                isBusy: false,
                systemStatus: {
                    frontend: "ONLINE",
                    backend: "CHECKING...",
                    gemini: "UNKNOWN",
                    mockRepository: "ONLINE",
                    sapIntegration: "MOCK_MODE",
                    hanaCloud: "NOT_CONNECTED_PHASE_1",
                    btp: "LOCAL_DEVELOPMENT_MODE"
                }
            });
            return oModel;
        }
    };
});
