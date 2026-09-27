sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/m/MessageToast"
], function (Controller, MessageToast) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.App", {
        onInit: function () {
            this.getView().addStyleClass("sapUiSizeCompact");
            this.getOwnerComponent().getRouter().attachRouteMatched(this._onRouteMatched, this);
            this.onQuickHealthCheck();
        },

        _onRouteMatched: function (oEvent) {
            var sRouteName = oEvent.getParameter("name");
            var oArgs = oEvent.getParameter("arguments") || {};
            var sCaseId = oArgs.caseId || this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId");

            if (sCaseId && sCaseId !== "undefined") {
                this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
                this._syncCaseState(sCaseId, sRouteName);
            }

            this.getOwnerComponent().getModel("app").setProperty("/currentRoute", sRouteName);
            this._updateNavHighlight(sRouteName);
        },

        _syncCaseState: function (sCaseId, sRouteName) {
            var oAppModel = this.getOwnerComponent().getModel("app");
            var sBackendUrl = oAppModel.getProperty("/backendUrl");

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (res) {
                    if (res.ok) return res.json();
                    return null;
                })
                .then(function (caseData) {
                    if (!caseData) return;
                    var sStatus = caseData.status || "NEW";
                    oAppModel.setProperty("/caseStatus", sStatus);

                    var sStatusText = sStatus.replace(/_/g, " ");
                    var nStep = 1;

                    if (sStatus === "RESOLVED") {
                        sStatusText = "Resolved";
                        nStep = 7;
                    } else if (sStatus === "MONITORING") {
                        sStatusText = "Monitoring";
                        nStep = 6;
                    } else if (sStatus === "EXECUTION_IN_PROGRESS") {
                        sStatusText = "Execution In Progress";
                        nStep = 5;
                    } else if (sStatus === "RECOVERY_APPROVED") {
                        sStatusText = "Ready for Execution";
                        nStep = 5;
                    } else if (sStatus === "AWAITING_CHECKPOINT_2") {
                        sStatusText = "Awaiting Checkpoint 2";
                        nStep = 4;
                    } else if (sStatus === "RECOVERY_PLANNING") {
                        sStatusText = "Recovery Planning";
                        nStep = 3;
                    } else if (sStatus === "CHECKPOINT_APPROVED") {
                        sStatusText = "Checkpoint 1 Approved";
                        nStep = 3;
                    } else if (sStatus === "ANALYZED") {
                        sStatusText = "Analysis Complete";
                        nStep = 2;
                    } else {
                        sStatusText = "Impact Analysis";
                        nStep = 1;
                    }

                    oAppModel.setProperty("/caseStatusText", sStatusText);
                    oAppModel.setProperty("/stageStep", nStep);
                })
                .catch(function (e) {
                    console.warn("Could not sync case state: " + e.message);
                });
        },

        _updateNavHighlight: function (sRoute) {
            var aNavs = [
                { id: "topNavDashboard",     routes: ["dashboard"] },
                { id: "topNavCases",         routes: ["cases"] },
                { id: "topNavNewDisruption", routes: ["newDisruption"] }
            ];

            aNavs.forEach(function (item) {
                var oBtn = this.byId(item.id);
                if (oBtn) {
                    if (item.routes.indexOf(sRoute) !== -1) {
                        oBtn.addStyleClass("sapTopNavActive");
                    } else {
                        oBtn.removeStyleClass("sapTopNavActive");
                    }
                }
            }, this);
        },

        // App nav
        onTopNavDashboard:     function () { this.getOwnerComponent().getRouter().navTo("dashboard"); },
        onTopNavCases:         function () { this.getOwnerComponent().getRouter().navTo("cases"); },
        onTopNavNewDisruption: function () { this.getOwnerComponent().getRouter().navTo("newDisruption"); },

        // Workflow nav helpers
        _getCaseId: function () {
            return this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
        },

        onNavWorkflowImpact:    function () { this.getOwnerComponent().getRouter().navTo("impactAnalysis",    { caseId: this._getCaseId() }); },
        onNavWorkflowCp1:       function () { this.getOwnerComponent().getRouter().navTo("checkpoint1",       { caseId: this._getCaseId() }); },
        onNavWorkflowRecovery:  function () { this.getOwnerComponent().getRouter().navTo("recoveryPlanning",  { caseId: this._getCaseId() }); },
        onNavWorkflowCp2:       function () { this.getOwnerComponent().getRouter().navTo("recoveryPlanning",  { caseId: this._getCaseId() }); },
        onNavWorkflowExecution: function () { this.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: this._getCaseId() }); },
        onNavWorkflowMonitoring:function () { this.getOwnerComponent().getRouter().navTo("monitoring",        { caseId: this._getCaseId() }); },
        onNavWorkflowOutcome:   function () { this.getOwnerComponent().getRouter().navTo("outcome",           { caseId: this._getCaseId() }); },

        // Utility buttons
        onSearchPress:       function () { this.getOwnerComponent().getRouter().navTo("cases"); },
        onNotificationPress: function () { MessageToast.show("Supply Chain Alerts: Active Disruptions Monitored"); },
        onSettingsPress:     function () { MessageToast.show("Control Tower Settings: Localhost Mode"); },
        onUserPress:         function () { MessageToast.show("Operator: Supply Chain Specialist (SC)"); },

        onQuickHealthCheck: function () {
            var oAppModel = this.getOwnerComponent().getModel("app");
            var sBackendUrl = oAppModel.getProperty("/backendUrl");

            fetch(sBackendUrl + "/api/health")
                .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
                .then(function (data) {
                    oAppModel.setProperty("/systemStatus/backend", data.status);
                    oAppModel.setProperty("/systemStatus/gemini", data.gemini);
                })
                .catch(function () {
                    oAppModel.setProperty("/systemStatus/backend", "OFFLINE");
                });
        }
    });
});
