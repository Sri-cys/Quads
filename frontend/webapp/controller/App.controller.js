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
        "recoveryPlanning": 4,
        "recoveryPlanningKebab": 4,
        "recoveryPlanningAlt": 4,
        "recoveryPlans": 4,
        "recoveryPlansAlt": 4,
        "decision": 5,
        "decisionAlt": 5,
        "checkpoint2": 5,
        "checkpoint2Kebab": 5,
        "checkpoint2Alt": 5,
        "executionMonitoring": 6,
        "executionMonitoringAlt": 6,
        "monitoring": 6,
        "monitoringAlt": 6,
        "outcome": 7,
        "outcomeAlt": 7
    };

    var STEP_TO_STAGE_NAME = {
        1: "1. CASE",
        2: "2. IMPACT ANALYSIS",
        3: "3. PRIORITY",
        4: "4. RECOVERY PLANNING",
        5: "5. DECISION",
        6: "6. EXECUTION & MONITORING",
        7: "7. OUTCOME"
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
                
                var aWorkflowRoutes = [
                    "caseOverview", "caseOverviewAlias", "impactAnalysis", "impactAnalysisKebab", "impactAnalysisAlt",
                    "checkpoint1", "checkpoint1Kebab", "checkpoint1Alt", "constraints", "constraintsAlt",
                    "recoveryPlanning", "recoveryPlanningKebab", "recoveryPlanningAlt", "recoveryPlans", "recoveryPlansAlt",
                    "decision", "decisionAlt", "checkpoint2", "checkpoint2Kebab", "checkpoint2Alt",
                    "executionMonitoring", "executionMonitoringAlt", "monitoring", "monitoringAlt",
                    "outcome", "outcomeAlt"
                ];
                if (aWorkflowRoutes.indexOf(sRouteName) !== -1) {
                    window.localStorage.setItem("quads_case_stage_" + sCaseId, sRouteName);
                }
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
                    var sStatus = caseData.status || "CASE_CREATED";
                    oAppModel.setProperty("/caseStatus", sStatus);

                    var sStatusText = "Case Created";
                    var nMaxStep = 1;

                    if (sStatus === "RESOLVED") {
                        sStatusText = "Resolved";
                        nMaxStep = 7;
                    } else if (["EXECUTION", "EXECUTION_IN_PROGRESS", "MONITORING", "ON_TRACK", "AT_RISK", "ACTION_REQUIRED", "REPLANNING", "DELIVERED"].indexOf(sStatus) !== -1) {
                        sStatusText = "In Execution";
                        nMaxStep = 6;
                    } else if (["PLAN_APPROVED", "RECOVERY_APPROVED"].indexOf(sStatus) !== -1) {
                        sStatusText = "Awaiting Execution";
                        nMaxStep = 6;
                    } else if (["DECISION_PENDING", "AWAITING_CHECKPOINT_2", "PLAN_MODIFIED", "PLAN_REJECTED"].indexOf(sStatus) !== -1) {
                        sStatusText = "Decision Pending";
                        nMaxStep = 5;
                    } else if (["AGENT3_RUNNING", "AGENT3_COMPLETED", "AGENT3_FAILED", "AGENT2_RUNNING", "AGENT2_COMPLETED", "AGENT2_FAILED", "RECOVERY_PLANNING"].indexOf(sStatus) !== -1) {
                        sStatusText = "Evaluating Plans";
                        nMaxStep = 4;
                    } else if (["PRIORITY_SAVED", "CHECKPOINT_APPROVED", "PRIORITY_PENDING"].indexOf(sStatus) !== -1) {
                        sStatusText = "Priority Saved";
                        nMaxStep = 3;
                    } else if (["IMPACT_ANALYSIS_COMPLETED", "ANALYZED"].indexOf(sStatus) !== -1) {
                        sStatusText = "Impact Completed";
                        nMaxStep = 3;
                    } else if (["IMPACT_ANALYSIS_RUNNING", "IMPACT_ANALYSIS_FAILED", "IMPACT_ANALYSIS_PENDING", "TRIAGED"].indexOf(sStatus) !== -1) {
                        sStatusText = "Impact Running";
                        nMaxStep = 2;
                    } else {
                        sStatusText = "Case Created";
                        nMaxStep = 1;
                    }

                    var sSev = (caseData.severity || "CRITICAL").toUpperCase();
                    var sTitle = caseData.description || "Disruption Recovery";

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
            var sCaseId = this._getCaseId();
            if (sCaseId) {
                sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {
                    WorkflowNavHelper.setStepperState(sCaseId, nActiveStep);
                });
            } else {
                oAppModel.setProperty("/activeStep", nActiveStep);
            }
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

        _getCaseId: function () {
            return this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
        },

        onSearchPress:       function () { this.getOwnerComponent().getRouter().navTo("cases"); },
        onNotificationPress: function () { MessageToast.show("Supply Chain Alerts: Active Disruptions Monitored"); },
        onHelpPress:         function () { MessageToast.show("Supply Chain Control Tower: 8-Stage Sequential Recovery Help"); },
        onSettingsPress:     function () { MessageToast.show("Control Tower Settings: Localhost Mode"); },
        onUserPress:         function () { MessageToast.show("Operator: Supply Chain Specialist (SC)"); },
        onAuditTrailPress:   function () { MessageToast.show("Audit Trail accessed."); },

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
