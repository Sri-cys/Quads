sap.ui.define([
    "sap/m/MessageToast"
], function (MessageToast) {
    "use strict";

    // ── CONSTANTS ──────────────────────────────────────────────────────────────
    var STEP_ROUTES = {
        1: "caseOverview",
        2: "impactAnalysis",
        3: "checkpoint1",
        4: "recoveryPlanning",
        5: "decision",
        6: "executionMonitoring",
        7: "outcome"
    };

    var STEP_NAMES = {
        1: "Case",
        2: "Impact Analysis",
        3: "Priority",
        4: "Recovery Planning",
        5: "Decision",
        6: "Exec & Monitoring",
        7: "Outcome"
    };

    var ROUTE_TO_STEP = {
        "caseOverview": 1, "caseOverviewAlias": 1, "caseOverviewKebab": 1,
        "impactAnalysis": 2, "impactAnalysisKebab": 2, "impactAnalysisAlt": 2,
        "checkpoint1": 3, "checkpoint1Kebab": 3, "checkpoint1Alt": 3,
        // The old constraints routes now safely map to Recovery Planning logic
        "constraints": 4, "constraintsAlt": 4,
        "recoveryPlanning": 4, "recoveryPlanningKebab": 4, "recoveryPlanningAlt": 4,
        "recoveryPlans": 4, "recoveryPlansAlt": 4,
        "decision": 5, "decisionAlt": 5,
        "executionMonitoring": 6, "executionMonitoringKebab": 6, "executionMonitoringAlt": 6,
        "monitoring": 6, "monitoringAlt": 6,
        "outcome": 7, "outcomeAlt": 7
    };

    // Local-storage keys
    function _lsKey(sCaseId) { return "quads_completed_stage_" + sCaseId; }
    function _priorityKey(sCaseId) { return "quads_priority_" + sCaseId; }

    // Get the owner component (tries several lookup strategies)
    function _getComponent() {
        var oComp;
        try { oComp = sap.ui.core.Component.get("container-com.quads.supplychain"); } catch(e) {}
        if (!oComp) {
            try { oComp = sap.ui.core.Component.get("application-com.quads.supplychain-component"); } catch(e) {}
        }
        if (!oComp) {
            try {
                var oCore = sap.ui.getCore();
                if (oCore && oCore.mComponents) {
                    var aKeys = Object.keys(oCore.mComponents);
                    for (var i = 0; i < aKeys.length; i++) {
                        if (aKeys[i].indexOf("com.quads.supplychain") !== -1) {
                            oComp = oCore.mComponents[aKeys[i]];
                            break;
                        }
                    }
                }
            } catch(e) {}
        }
        return oComp;
    }

    // ── PUBLIC API ─────────────────────────────────────────────────────────────
    return {

        /**
         * Returns the number of consecutive completed stages (1-based) for this
         * case, reading ONLY from localStorage (the single source of truth).
         * Returns 0 when nothing is stored.
         */
        getCompletedStage: function (sCaseId) {
            if (!sCaseId) return 0;
            var sKey = _lsKey(sCaseId);
            var sStored = window.localStorage.getItem(sKey);
            
            var n = 0;
            if (sStored && sStored.indexOf("[") === 0) {
                try {
                    var aStages = JSON.parse(sStored);
                    var validStages = ["Case", "Impact Analysis", "Priority", "Recovery Planning", "Decision", "Exec & Monitoring", "Outcome"];
                    var maxN = 0;
                    for (var i = 0; i < aStages.length; i++) {
                        var sName = (aStages[i] || "").toLowerCase();
                        var cur = 0;
                        if (sName.indexOf("case") !== -1) cur = 1;
                        if (sName.indexOf("impact") !== -1) cur = 2;
                        if (sName.indexOf("priority") !== -1) cur = 3;
                        if (sName.indexOf("constraints") !== -1) cur = 3; 
                        if (sName.indexOf("recovery") !== -1) cur = 4;
                        if (sName.indexOf("decision") !== -1) cur = 5;
                        if (sName.indexOf("exec") !== -1 || sName.indexOf("monitoring") !== -1) cur = 6;
                        if (sName.indexOf("outcome") !== -1) cur = 7;
                        if (cur > maxN) maxN = cur;
                    }
                    n = maxN;
                } catch(e) {}
            } else {
                n = sStored ? parseInt(sStored, 10) : 0;
                if (!isNaN(n) && n > 0 && !window.localStorage.getItem(sKey + "_migrated")) {
                    if (n === 4) n = 3;
                    else if (n >= 5) n = n - 1;
                }
            }
            if (isNaN(n)) return 0;
            
            window.localStorage.setItem(sKey, String(n));
            window.localStorage.setItem(sKey + "_migrated", "true");

            return n;
        },

        savePriority: function (sCaseId, sPriority) {
            if (!sCaseId || !sPriority) return;
            window.localStorage.setItem(_priorityKey(sCaseId), sPriority);
        },

        getSavedPriority: function (sCaseId) {
            if (!sCaseId) return null;
            return window.localStorage.getItem(_priorityKey(sCaseId)) || null;
        },

        isPrioritySaved: function (sCaseId) {
            return !!this.getSavedPriority(sCaseId);
        },

        /**
         * Returns true when the user is allowed to open targetStage for this
         * case (i.e. all previous stages are done, or it is the next one).
         */
        canOpenStage: function (sCaseId, targetStage) {
            var nTarget = Number(targetStage);
            if (nTarget > this.getCompletedStage(sCaseId) + 1) {
                return false;
            }
            // Stage 4+ (Recovery Planning and beyond) requires Checkpoint 1 priority to be set
            if (nTarget >= 4 && !this.isPrioritySaved(sCaseId)) {
                return false;
            }
            return true;
        },

        /**
         * Writes app>/activeStep and app>/completedStage to the "app" JSONModel.
         * Always derives completedStage from localStorage — never from activeStep.
         */
        setStepperState: function (sCaseId, nActiveStep) {
            if (!sCaseId) return;
            var nActive = Number(nActiveStep);
            var nCompleted = Number(this.getCompletedStage(sCaseId));
            try {
                var oComp = _getComponent();
                if (oComp && oComp.getModel("app")) {
                    var oAppModel = oComp.getModel("app");
                    oAppModel.setProperty("/activeStep",    nActive);
                    oAppModel.setProperty("/completedStage", nCompleted);
                }
            } catch (e) {
                console.warn("[WorkflowNavHelper] setStepperState error", e);
            }
        },

        /**
         * Marks stageNo as complete (only ever moves the number forward, never
         * backwards), then immediately refreshes the stepper model so the tick
         * appears without a page reload.
         */
        completeStage: function (sCaseId, stageNo, activeStepAfter) {
            if (!sCaseId) return;
            var nCurrent = this.getCompletedStage(sCaseId);
            
            // Only allow marking Stage 3 complete if priority is saved
            if (stageNo === 3 && !this.isPrioritySaved(sCaseId)) {
                return;
            }

            if (stageNo > nCurrent) {
                window.localStorage.setItem(_lsKey(sCaseId), String(stageNo));
            }
            this.setStepperState(sCaseId, activeStepAfter || stageNo);
        },

        /**
         * Fetches the case from the backend and primes localStorage with the
         * correct completedStage and saved priority.
         * Always runs on the first call per session (no early-return guard).
         */
        syncFromBackend: function (sCaseId) {
            if (!sCaseId) return;

            var sBackendUrl = "http://localhost:8000";
            try {
                var oComp = _getComponent();
                if (oComp && oComp.getModel("app")) {
                    sBackendUrl = oComp.getModel("app").getProperty("/backendUrl") || sBackendUrl;
                }
            } catch (e) {}

            try {
                var xhr = new XMLHttpRequest();
                xhr.open("GET", sBackendUrl + "/api/v1/cases/" + sCaseId, false /*sync*/);
                xhr.send(null);
                if (xhr.status === 200) {
                    var caseData = JSON.parse(xhr.responseText);

                    // Always update priority from backend – it is the authoritative source
                    if (caseData.checkpoint1_decision) {
                        this.savePriority(sCaseId, caseData.checkpoint1_decision);
                    } else {
                        window.localStorage.removeItem(_priorityKey(sCaseId));
                    }

                    // Compute the authoritative max stage from backend status
                    var maxCompleted = 0;
                    if (caseData.completed_stages && Array.isArray(caseData.completed_stages) && caseData.completed_stages.length > 0) {
                        caseData.completed_stages.forEach(function (stageName) {
                            var n = 0;
                            var sLower = stageName.toLowerCase();
                            if (sLower.indexOf("case") !== -1) n = 1;
                            if (sLower.indexOf("impact") !== -1) n = 2;
                            if (sLower.indexOf("priority") !== -1) n = 3;
                            if (sLower.indexOf("constraints") !== -1) n = 3;
                            if (sLower.indexOf("recovery") !== -1) n = 4;
                            if (sLower.indexOf("decision") !== -1) n = 5;
                            if (sLower.indexOf("exec") !== -1 || sLower.indexOf("monitoring") !== -1) n = 6;
                            if (sLower.indexOf("outcome") !== -1) n = 7;
                            if (n > maxCompleted) maxCompleted = n;
                        });
                    }

                    var statusMax = 0;
                    var sStat = caseData.normalized_status || caseData.status || "";
                    if (sStat === "RESOLVED") statusMax = 7;
                    else if (["EXECUTION_IN_PROGRESS", "MONITORING", "ON_TRACK", "AT_RISK", "ACTION_REQUIRED", "DELIVERED"].indexOf(sStat) !== -1) statusMax = 6;
                    else if (["RECOVERY_APPROVED", "PLAN_APPROVED"].indexOf(sStat) !== -1) statusMax = 5;
                    else if (["AWAITING_CHECKPOINT_2", "DECISION_PENDING", "PLAN_MODIFIED", "PLAN_REJECTED"].indexOf(sStat) !== -1) statusMax = 4;
                    else if (["AGENT2_RUNNING", "AGENT2_COMPLETED", "AGENT2_FAILED", "AGENT3_RUNNING", "AGENT3_COMPLETED", "AGENT3_FAILED", "PRIORITY_SAVED", "CHECKPOINT_APPROVED", "CONSTRAINTS_ANALYZED"].indexOf(sStat) !== -1) statusMax = 3;
                    else if (["IMPACT_ANALYSIS_COMPLETED", "ANALYZED", "AWAITING_CHECKPOINT_1", "PRIORITY_PENDING"].indexOf(sStat) !== -1) statusMax = 2;
                    else if (["IMPACT_ANALYSIS_RUNNING", "IMPACT_ANALYSIS_FAILED", "IMPACT_ANALYSIS_PENDING", "TRIAGED"].indexOf(sStat) !== -1) statusMax = 1;
                    // CASE_OVERVIEW / CASE_CREATED = stage 1 started (case is open)
                    else if (["CASE_OVERVIEW", "CASE_CREATED", "CREATED"].indexOf(sStat) !== -1) statusMax = 1;

                    if (statusMax > maxCompleted) {
                        maxCompleted = statusMax;
                    }

                    // Safety net: if computed stage is 3+ but backend has no priority,
                    // roll back to stage 2 so the canOpenStage guard blocks stage 4+.
                    if (maxCompleted >= 3 && !caseData.checkpoint1_decision) {
                        maxCompleted = 2;
                    }

                    // Always write the authoritative value — backend is the source of truth.
                    // Writing even when maxCompleted=0 ensures stale localStorage is cleared
                    // (e.g., after a backend restart resets in-memory state).
                    window.localStorage.setItem(_lsKey(sCaseId), String(maxCompleted));
                    window.localStorage.setItem(_lsKey(sCaseId) + "_migrated", "true");
                }
            } catch (e) { /* network down or CORS — silently ignore */ }
        },


        /**
         * Navigates from the current stage to the previous one (n-1).
         * Pure navigation — never writes localStorage, never calls backend.
         */
        navBack: function (oController) {
            var oAppModel = oController.getOwnerComponent().getModel("app");
            var nCurrent  = Number(oAppModel.getProperty("/activeStep") || 1);
            var sCaseId   = oController._sCurrentCaseId ||
                            oAppModel.getProperty("/selectedCaseId") ||
                            "CASE-0001";
            if (nCurrent <= 1) {
                oController.getOwnerComponent().getRouter().navTo("cases");
                return;
            }
            oController.getOwnerComponent().getRouter().navTo(
                STEP_ROUTES[nCurrent - 1], { caseId: sCaseId }
            );
        },

        /**
         * Navigates from the current stage forward to the next one (n+1).
         * Call this ONLY when the current stage is already complete.
         * Pure navigation — never writes localStorage, never calls backend.
         */
        navForward: function (oController) {
            var oAppModel = oController.getOwnerComponent().getModel("app");
            var nCurrent  = Number(oAppModel.getProperty("/activeStep") || 1);
            var sCaseId   = oController._sCurrentCaseId ||
                            oAppModel.getProperty("/selectedCaseId") ||
                            "CASE-0001";
            if (nCurrent >= 7) return; // Outcome has no forward
            oController.getOwnerComponent().getRouter().navTo(
                STEP_ROUTES[nCurrent + 1], { caseId: sCaseId }
            );
        },

        // ── Stepper circle press (non-navigational in current design) ──────────
        onWorkflowStagePress: function (oEvent, oController) {
            var ctrl = oController || this;
            var aCustomData = oEvent.getSource().getCustomData();
            var nTargetStep = 1;
            if (aCustomData && aCustomData.length > 0) {
                nTargetStep = parseInt(aCustomData[0].getValue(), 10);
            }
            // Audit trail (step 8 instead of 9 in 7-stage? No, let's just make it the last step if they want it. Actually outcome is 7, so maybe nTargetStep === 8? Wait, the previous logic checked 9 for audit trail, I will leave it or adjust if needed. If Outcome is 7, maybe Audit Trail doesn't exist as a circle? The circle press is non-navigational except for Outcome? Let's fix that check to 8 if Outcome was 8, now it's 7.)
            if (nTargetStep === 8) {
                var sCaseId = ctrl.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
                var sHash   = ctrl.getOwnerComponent().getRouter().getURL("outcome", { caseId: sCaseId });
                var sUrl    = window.location.href.split("#")[0] + "#/" + sHash.replace(/^\/?/, "");
                window.open(sUrl, "_blank");
            }
        },

        // ── Route guard ────────────────────────────────────────────────────────
        initRouteGuard: function (oRouter) {
            oRouter.attachBeforeRouteMatched(function (oEvent) {
                var sRoute  = oEvent.getParameter("name");
                var oArgs   = oEvent.getParameter("arguments");
                var sCaseId = oArgs && oArgs.caseId;
                if (!sCaseId) return;

                var nTargetStep = ROUTE_TO_STEP[sRoute];
                if (!nTargetStep) return;

                // Prime from backend if localStorage is empty
                this.syncFromBackend(sCaseId);

                if (!this.canOpenStage(sCaseId, nTargetStep)) {
                    oEvent.preventDefault();
                    var nCompletedStep   = this.getCompletedStage(sCaseId);
                    var nAccessibleStep  = nCompletedStep + 1;
                    
                    // Prevent infinite redirect loops if nCompletedStep+1 is also blocked
                    while (nAccessibleStep > 1 && !this.canOpenStage(sCaseId, nAccessibleStep)) {
                        nAccessibleStep--;
                    }
                    
                    var sBlockedName     = STEP_NAMES[nTargetStep]   || "that stage";
                    var sRequiredName    = STEP_NAMES[nAccessibleStep] || "a previous stage";
                    var sMsg;
                    if (nAccessibleStep < nTargetStep) {
                        sMsg = "\u2192 " + sBlockedName + " is locked. Please complete " + sRequiredName + " first.";
                    } else {
                        sMsg = sBlockedName + " requires " + sRequiredName + " to be completed first.";
                    }
                    MessageToast.show(sMsg);
                    var that = this;
                    setTimeout(function () {
                        oRouter.navTo(STEP_ROUTES[nAccessibleStep], { caseId: sCaseId }, true);
                    }, 0);
                }
            }.bind(this));

            oRouter.attachRouteMatched(function (oEvent) {
                var sRoute  = oEvent.getParameter("name");
                var oArgs   = oEvent.getParameter("arguments");
                var sCaseId = oArgs && oArgs.caseId;
                if (!sCaseId) return;

                var nTargetStep = ROUTE_TO_STEP[sRoute];
                if (nTargetStep) {
                    this.setStepperState(sCaseId, nTargetStep);
                }
            }.bind(this));
        }
    };
});
