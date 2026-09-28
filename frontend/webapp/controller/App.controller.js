sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/m/MessageToast"
], function (Controller, MessageToast) {
    "use strict";

    var ROUTE_TO_STEP = {
        "caseOverview": 1,
        "caseOverviewAlias": 1,
        "impactAnalysis": 2,
        "impactAnalysisKebab": 2,
        "impactAnalysisAlt": 2,
        "checkpoint1": 3,
        "checkpoint1Kebab": 3,
        "checkpoint1Alt": 3,
        "constraints": 4,
        "constraintsAlt": 4,
        "recoveryPlanning": 5,
        "recoveryPlanningKebab": 5,
        "recoveryPlanningAlt": 5,
        "recoveryPlans": 5,
        "recoveryPlansAlt": 5,
        "decision": 6,
        "decisionAlt": 6,
        "checkpoint2": 6,
        "checkpoint2Kebab": 6,
        "checkpoint2Alt": 6,
        "executionMonitoring": 7,
        "executionMonitoringAlt": 7,
        "monitoring": 7,
        "monitoringAlt": 7,
        "outcome": 8,
        "outcomeAlt": 8
    };

    var STEP_TO_STAGE_NAME = {
        1: "1. CASE OVERVIEW",
        2: "2. IMPACT ANALYSIS",
        3: "3. PRIORITY",
        4: "4. CONSTRAINTS (AGENT 2)",
        5: "5. RECOVERY PLANNING (AGENT 3)",
        6: "6. FINAL DECISION",
        7: "7. EXECUTION & MONITORING",
        8: "8. OUTCOME"
    };

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
            this._updateWorkflowSteps(sRouteName);

            var bInWorkflow = (sRouteName !== "dashboard" && sRouteName !== "cases" && sRouteName !== "newDisruption" && !!sRouteName);
            var oNavHeader = this.byId("unifiedNavHeader");
            if (oNavHeader) {
                oNavHeader.toggleStyleClass("inWorkflow", bInWorkflow);
            }
        },

        _syncCaseState: function (sCaseId, sRouteName) {
            var oAppModel = this.getOwnerComponent().getModel("app");
            var sBackendUrl = oAppModel.getProperty("/backendUrl");
            var that = this;

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (res) {
                    if (res.ok) return res.json();
                    return null;
                })
                .then(function (caseData) {
                    if (!caseData) return;
                    var sStatus = caseData.status || "NEW";
                    oAppModel.setProperty("/caseStatus", sStatus);

                    var sStatusText = "Case Created";
                    var nMaxStep = 1;

                    if (sStatus === "RESOLVED") {
                        sStatusText = "Resolved";
                        nMaxStep = 8;
                    } else if (sStatus === "PLAN_APPROVED" || sStatus === "RECOVERY_APPROVED" || sStatus === "EXECUTION" || sStatus === "EXECUTION_IN_PROGRESS" || sStatus === "MONITORING" || sStatus === "ON_TRACK" || sStatus === "AT_RISK" || sStatus === "ACTION_REQUIRED" || sStatus === "REPLANNING" || sStatus === "DELIVERED") {
                        sStatusText = "In Execution";
                        nMaxStep = 7;
                    } else if (sStatus === "AGENT3_COMPLETED" || sStatus === "AWAITING_CHECKPOINT_2" || sStatus === "DECISION_PENDING" || sStatus === "PLAN_MODIFIED" || sStatus === "PLAN_REJECTED") {
                        sStatusText = "Decision Pending";
                        nMaxStep = 6;
                    } else if (sStatus === "AGENT2_COMPLETED" || sStatus === "RECOVERY_PLANNING" || sStatus === "AGENT3_RUNNING" || sStatus === "AGENT3_FAILED") {
                        sStatusText = "Recovery Planning";
                        nMaxStep = 5;
                    } else if (sStatus === "PRIORITY_SAVED" || sStatus === "CHECKPOINT_APPROVED" || sStatus === "AGENT2_RUNNING" || sStatus === "AGENT2_FAILED") {
                        sStatusText = "Priority Saved";
                        nMaxStep = 4;
                    } else if (sStatus === "ANALYZED" || sStatus === "IMPACT_ANALYSIS_COMPLETED" || sStatus === "PRIORITY_PENDING") {
                        sStatusText = "Analysis Complete";
                        nMaxStep = 3;
                    } else if (sStatus === "IMPACT_ANALYSIS_RUNNING" || sStatus === "IMPACT_ANALYSIS_FAILED" || sStatus === "IMPACT_ANALYSIS_PENDING" || sStatus === "TRIAGED") {
                        sStatusText = "Impact Analysis";
                        nMaxStep = 2;
                    } else {
                        sStatusText = "Case Created";
                        nMaxStep = 1;
                    }

                    var sSev = (caseData.severity || "CRITICAL").toUpperCase();
                    var sTitle = caseData.description || "Disruption Recovery";

                    // The active page determines the displayed stage: avoids any stage/view desync
                    var nCurrentStep = ROUTE_TO_STEP[sRouteName] || nMaxStep;
                    var sStageName = STEP_TO_STAGE_NAME[nCurrentStep] || "1. CASE OVERVIEW";

                    oAppModel.setProperty("/caseTitle", sTitle);
                    oAppModel.setProperty("/caseSeverity", sSev);
                    oAppModel.setProperty("/currentStageName", sStageName);
                    oAppModel.setProperty("/lastUpdated", "Just now");
                    oAppModel.setProperty("/caseStatusText", sStatusText);
                    oAppModel.setProperty("/stageStep", nMaxStep);
                    oAppModel.setProperty("/activeStep", nCurrentStep);
                })
                .catch(function (e) {
                    console.warn("Could not sync case state: " + e.message);
                });
        },

        _updateNavHighlight: function (sRoute) {
            var aNavs = [
                { id: "topNavDashboard",      routes: ["dashboard", "dashboardAlias"] },
                { id: "topNavCases",          routes: ["cases", "newDisruption"] },
                { id: "topNavImpactAnalysis", routes: ["caseOverview", "caseOverviewAlias", "impactAnalysis", "impactAnalysisKebab", "impactAnalysisAlt"] },
                { id: "topNavRecovery",       routes: ["checkpoint1", "checkpoint1Kebab", "checkpoint1Alt", "constraints", "constraintsAlt", "recoveryPlanning", "recoveryPlanningKebab", "recoveryPlanningAlt", "recoveryPlans", "recoveryPlansAlt", "decision", "decisionAlt", "checkpoint2", "checkpoint2Kebab", "checkpoint2Alt"] },
                { id: "topNavExecution",      routes: ["executionMonitoring", "executionMonitoringAlt", "monitoring", "monitoringAlt"] },
                { id: "topNavOutcome",        routes: ["outcome", "outcomeAlt"] }
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

        _updateWorkflowSteps: function (sRouteName) {
            var oAppModel = this.getOwnerComponent().getModel("app");
            var nActiveStep = ROUTE_TO_STEP[sRouteName] || 1;
            oAppModel.setProperty("/activeStep", nActiveStep);
        },

        _showLockedStageDialog: function (sTitle, sMessage, sCurrentRoute) {
            var that = this;

            var oVBox = new sap.m.VBox({ class: "sapUiSmallMargin" });
            oVBox.addItem(new sap.m.Text({ text: sMessage }).addStyleClass("sapUiSmallMarginBottom textDark bold"));

            var oDialog = new sap.m.Dialog({
                title: sTitle,
                type: "Message",
                state: "Warning",
                content: oVBox,
                beginButton: new sap.m.Button({
                    type: "Emphasized",
                    text: "CONTINUE WORKFLOW",
                    icon: "sap-icon://navigation-right-arrow",
                    press: function () {
                        oDialog.close();
                        that.getOwnerComponent().getRouter().navTo(sCurrentRoute, { caseId: that._getCaseId() });
                    }
                }),
                endButton: new sap.m.Button({
                    text: "Close",
                    press: function () {
                        oDialog.close();
                    }
                }),
                afterClose: function () {
                    oDialog.destroy();
                }
            });

            oDialog.open();
        },

        // Top Navigation with Strict Workflow Guards (Section 29, 30)
        onTopNavDashboard:      function () { this.getOwnerComponent().getRouter().navTo("dashboard"); },
        onTopNavCases:          function () { this.getOwnerComponent().getRouter().navTo("cases"); },
        onTopNavNewDisruption:  function () { this.getOwnerComponent().getRouter().navTo("newDisruption"); },

        onTopNavImpactAnalysis: function () {
            var sCaseId = this._getCaseId();
            var sStatus = (this.getOwnerComponent().getModel("app").getProperty("/caseStatus") || "CREATED").toUpperCase();
            if (sStatus === "NEW" || sStatus === "CREATED") {
                this.getOwnerComponent().getRouter().navTo("caseOverview", { caseId: sCaseId });
            } else {
                this.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
            }
        },

        onTopNavRecovery: function () {
            var sStatus = (this.getOwnerComponent().getModel("app").getProperty("/caseStatus") || "CREATED").toUpperCase();
            var aAllowed = ["PRIORITY_SAVED", "CHECKPOINT_APPROVED", "AGENT2_RUNNING", "AGENT2_COMPLETED", "RECOVERY_PLANNING", "AGENT3_RUNNING", "AGENT3_COMPLETED", "AWAITING_CHECKPOINT_2", "DECISION_PENDING", "PLAN_APPROVED", "RECOVERY_APPROVED", "EXECUTION", "EXECUTION_IN_PROGRESS", "MONITORING", "RESOLVED"];

            if (aAllowed.indexOf(sStatus) !== -1) {
                if (sStatus === "PRIORITY_SAVED" || sStatus === "CHECKPOINT_APPROVED") {
                    this.getOwnerComponent().getRouter().navTo("constraints", { caseId: this._getCaseId() });
                } else {
                    this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: this._getCaseId() });
                }
            } else {
                this._showLockedStageDialog(
                    "Recovery Planning is locked.",
                    "Recovery Planning is locked until Impact Analysis and Priority Analysis are completed.",
                    sStatus === "ANALYZED" ? "checkpoint1" : "impactAnalysis"
                );
            }
        },

        onTopNavExecution: function () {
            var sStatus = (this.getOwnerComponent().getModel("app").getProperty("/caseStatus") || "CREATED").toUpperCase();
            var aAllowed = ["PLAN_APPROVED", "RECOVERY_APPROVED", "EXECUTION", "EXECUTION_IN_PROGRESS", "MONITORING", "RESOLVED"];
            if (aAllowed.indexOf(sStatus) !== -1) {
                this.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: this._getCaseId() });
            } else {
                this._showLockedStageDialog(
                    "Execution & Monitoring is locked.",
                    "Execution is locked until a recovery plan is approved by manager at Final Decision.",
                    "decision"
                );
            }
        },

        onTopNavOutcome: function () {
            var sStatus = (this.getOwnerComponent().getModel("app").getProperty("/caseStatus") || "CREATED").toUpperCase();
            if (sStatus === "RESOLVED") {
                this.getOwnerComponent().getRouter().navTo("outcome", { caseId: this._getCaseId() });
            } else {
                this._showLockedStageDialog(
                    "Outcome is not available yet.",
                    "Outcome is locked until the case is fully resolved.",
                    "executionMonitoring"
                );
            }
        },

        _getCaseId: function () {
            return this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
        },

        onSearchPress:       function () { this.getOwnerComponent().getRouter().navTo("cases"); },
        onNotificationPress: function () { MessageToast.show("Supply Chain Alerts: Active Disruptions Monitored"); },
        onHelpPress:         function () { MessageToast.show("Supply Chain Control Tower: 8-Stage Sequential Recovery Help"); },
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
