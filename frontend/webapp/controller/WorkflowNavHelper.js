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
            }
        },

        setStepperState: function(sCaseId, nActiveStep) {
            if (!sCaseId) return;
            try {
                var oComp = sap.ui.core.Component.get("container-com.quads.supplychain") || 
                            sap.ui.core.Component.get("application-com.quads.supplychain-component");
                if (!oComp) {
                    var oCore = sap.ui.getCore();
                    if (oCore && oCore.mComponents) {
                        var aKeys = Object.keys(oCore.mComponents);
                        for (var i=0; i<aKeys.length; i++) {
                            if (aKeys[i].indexOf("com.quads.supplychain") !== -1) {
                                oComp = oCore.mComponents[aKeys[i]];
                                break;
                            }
                        }
                    }
                }
                if (oComp && oComp.getModel("app")) {
                    var oAppModel = oComp.getModel("app");
                    oAppModel.setProperty("/activeStep", nActiveStep);
                    
                    var sKey = "quads_completed_stage_" + sCaseId;
                    var sStored = window.localStorage.getItem(sKey);
                    var nCompletedStep = sStored ? parseInt(sStored, 10) : 0;
                    oAppModel.setProperty("/completedStage", nCompletedStep);
                }
            } catch(e) {
                console.warn("Could not set stepper state", e);
            }
        },

        markStageCompleted: function(sCaseId, nStage) {
            if (!sCaseId) return;
            var sKey = "quads_completed_stage_" + sCaseId;
            var nCurrent = parseInt(window.localStorage.getItem(sKey) || "0", 10);
            if (nStage > nCurrent) {
                window.localStorage.setItem(sKey, nStage.toString());
                
                // Attempt to update the app model instantly
                try {
                    var oComp = sap.ui.core.Component.get("container-com.quads.supplychain") || 
                                sap.ui.core.Component.get("application-com.quads.supplychain-component");
                    if (!oComp) {
                        var oCore = sap.ui.getCore();
                        if (oCore && oCore.mComponents) {
                            var aKeys = Object.keys(oCore.mComponents);
                            for (var i=0; i<aKeys.length; i++) {
                                if (aKeys[i].indexOf("com.quads.supplychain") !== -1) {
                                    oComp = oCore.mComponents[aKeys[i]];
                                    break;
                                }
                            }
                        }
                    }
                    if (oComp && oComp.getModel("app")) {
                        oComp.getModel("app").setProperty("/completedStage", nStage);
                    }
                } catch(e) {}
            }
        },

        initRouteGuard: function(oRouter) {
            oRouter.attachBeforeRouteMatched(function (oEvent) {
                var sRoute = oEvent.getParameter("name");
                var oArgs = oEvent.getParameter("arguments");
                var sCaseId = oArgs.caseId;
                if (!sCaseId) return;

                var ROUTE_TO_STEP = {
                    "caseOverview": 1, "caseOverviewAlias": 1, "caseOverviewKebab": 1,
                    "impactAnalysis": 2, "impactAnalysisKebab": 2, "impactAnalysisAlt": 2,
                    "checkpoint1": 3, "checkpoint1Kebab": 3, "checkpoint1Alt": 3,
                    "constraints": 4, "constraintsAlt": 4,
                    "recoveryPlanning": 5, "recoveryPlanningKebab": 5, "recoveryPlanningAlt": 5, "recoveryPlans": 5, "recoveryPlansAlt": 5,
                    "decision": 6, "decisionAlt": 6,
                    "executionMonitoring": 7, "executionMonitoringKebab": 7, "executionMonitoringAlt": 7, "monitoring": 7, "monitoringAlt": 7,
                    "outcome": 8, "outcomeAlt": 8
                };

                var nTargetStep = ROUTE_TO_STEP[sRoute];
                if (!nTargetStep) return;

                var sStored = window.localStorage.getItem("quads_completed_stage_" + sCaseId);
                var nCompletedStep = sStored ? parseInt(sStored, 10) : 0; 
                
                if (!sStored) {
                    try {
                        var xhr = new XMLHttpRequest();
                        xhr.open("GET", "http://localhost:8000/api/v1/cases/" + sCaseId, false);
                        xhr.send(null);
                        if (xhr.status === 200) {
                            var caseData = JSON.parse(xhr.responseText);
                            if (caseData.completed_stages && Array.isArray(caseData.completed_stages)) {
                                var maxCompleted = 0;
                                caseData.completed_stages.forEach(function(stageName) {
                                    var n = 0;
                                    var sLower = stageName.toLowerCase();
                                    if (sLower.indexOf("case") !== -1) n = 1;
                                    if (sLower.indexOf("impact") !== -1) n = 2;
                                    if (sLower.indexOf("priority") !== -1) n = 3;
                                    if (sLower.indexOf("constraints") !== -1) n = 4;
                                    if (sLower.indexOf("recovery") !== -1) n = 5;
                                    if (sLower.indexOf("decision") !== -1) n = 6;
                                    if (sLower.indexOf("exec") !== -1 || sLower.indexOf("monitoring") !== -1) n = 7;
                                    if (sLower.indexOf("outcome") !== -1) n = 8;
                                    if (n > maxCompleted) maxCompleted = n;
                                });
                                nCompletedStep = maxCompleted;
                                window.localStorage.setItem("quads_completed_stage_" + sCaseId, maxCompleted.toString());
                            }
                        }
                    } catch(e) {
                        // ignore
                    }
                }

                var nAccessibleStep = nCompletedStep + 1;

                if (nTargetStep > nAccessibleStep) {
                    oEvent.preventDefault(); // Stop navigation
                    var sBlockedName = STEP_NAMES[nTargetStep] || "target stage";
                    var sRequiredName = STEP_NAMES[nAccessibleStep] || "previous stage";
                    MessageToast.show("Complete " + sRequiredName + " before proceeding to " + sBlockedName + ".");

                    // Redirect to the highest accessible stage
                    setTimeout(function() {
                        oRouter.navTo(STEP_ROUTES[nAccessibleStep], { caseId: sCaseId }, true); // true for replace
                    }, 0);
                }
            });
        }
    };
});
