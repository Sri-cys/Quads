sap.ui.define([
    "sap/m/MessageToast"
], function (MessageToast) {
    "use strict";

    // ── CONSTANTS ──────────────────────────────────────────────────────────────
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
        7: "Exec & Monitoring",
        8: "Outcome"
    };

    var ROUTE_TO_STEP = {
        "caseOverview": 1, "caseOverviewAlias": 1, "caseOverviewKebab": 1,
        "impactAnalysis": 2, "impactAnalysisKebab": 2, "impactAnalysisAlt": 2,
        "checkpoint1": 3, "checkpoint1Kebab": 3, "checkpoint1Alt": 3,
        "constraints": 4, "constraintsAlt": 4,
        "recoveryPlanning": 5, "recoveryPlanningKebab": 5, "recoveryPlanningAlt": 5,
        "recoveryPlans": 5, "recoveryPlansAlt": 5,
        "decision": 6, "decisionAlt": 6,
        "executionMonitoring": 7, "executionMonitoringKebab": 7, "executionMonitoringAlt": 7,
        "monitoring": 7, "monitoringAlt": 7,
        "outcome": 8, "outcomeAlt": 8
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
            var sStored = window.localStorage.getItem(_lsKey(sCaseId));
            var n = sStored ? parseInt(sStored, 10) : 0;
            return isNaN(n) ? 0 : n;
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
            var nCompleted = this.getCompletedStage(sCaseId);
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
         * correct completedStage if it has not been set yet.
         */
        syncFromBackend: function (sCaseId) {
            if (!sCaseId) return;
            if (this.getCompletedStage(sCaseId) > 0) return; // already primed

            try {
                var xhr = new XMLHttpRequest();
                xhr.open("GET", "http://localhost:8000/api/v1/cases/" + sCaseId, false /*sync*/);
                xhr.send(null);
                if (xhr.status === 200) {
                    var caseData = JSON.parse(xhr.responseText);
                    
                    if (caseData.checkpoint1_decision) {
                        this.savePriority(sCaseId, caseData.checkpoint1_decision);
                    }

                    var maxCompleted = 0;
                    if (caseData.completed_stages && Array.isArray(caseData.completed_stages) && caseData.completed_stages.length > 0) {
                        caseData.completed_stages.forEach(function (stageName) {
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
                    } else {
                        var sStat = caseData.status || "";
                        if (sStat === "RESOLVED") maxCompleted = 8;
                        else if (["EXECUTION_IN_PROGRESS", "MONITORING"].indexOf(sStat) !== -1) maxCompleted = 7;
                        else if (sStat === "RECOVERY_APPROVED") maxCompleted = 6;
                        else if (sStat === "AWAITING_CHECKPOINT_2") maxCompleted = 5;
                        else if (sStat === "CONSTRAINTS_ANALYZED") maxCompleted = 4;
                        else if (sStat === "CHECKPOINT_APPROVED") maxCompleted = 3;
                        else if (["ANALYZED", "AWAITING_CHECKPOINT_1"].indexOf(sStat) !== -1) maxCompleted = 2;
                        else if (sStat !== "CREATED") maxCompleted = 1;
                    }

                    // Fix for mock data: don't let completed stages surpass priority if it isn't saved
                    if (maxCompleted >= 3 && !this.isPrioritySaved(sCaseId)) {
                        maxCompleted = 2; // rollback to stage 2
                    }

                    if (maxCompleted > 0) {
                        window.localStorage.setItem(_lsKey(sCaseId), String(maxCompleted));
                    }
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
            if (nCurrent >= 8) return; // Outcome has no forward
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
            // Audit trail (step 9) — open in new tab
            if (nTargetStep === 9) {
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
                    var sBlockedName     = STEP_NAMES[nTargetStep]   || "that stage";
                    var sRequiredName    = STEP_NAMES[nAccessibleStep] || "the previous stage";
                    MessageToast.show(
                        "Please complete " + sRequiredName +
                        " before opening " + sBlockedName + "."
                    );
                    var that = this;
                    setTimeout(function () {
                        oRouter.navTo(STEP_ROUTES[nAccessibleStep], { caseId: sCaseId }, true);
                    }, 0);
                }
            }.bind(this));
        }
    };
});
