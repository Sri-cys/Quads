sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast"
], function (Controller, JSONModel, MessageBox, MessageToast) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.Outcome", {
        onInit: function () {
            var oModel = new JSONModel({
                state: "PENDING",
                case_id: "",
                plan_id: "",
                plan_version: "",
                strategy: "",
                planned_quantity: 0,
                actual_quantity: 0,
                planned_arrival: "—",
                actual_arrival: "—",
                planned_cost: 0,
                actual_cost: 0,
                delay_days: 0,
                failure_reason: "",
                lessons_learned: "",
                audit_events: []
            });
            this.getView().setModel(oModel, "out");

            var oRouter = this.getOwnerComponent().getRouter();
            ["outcome", "outcomeAlt"].forEach(function (r) {
                var oR = oRouter.getRoute(r);
                if (oR) oR.attachPatternMatched(this._onPatternMatched, this);
            }, this);
        },

        _onPatternMatched: function (oEvent) {
            var sCaseId = oEvent.getParameter("arguments").caseId;
            if (!sCaseId) {
                sCaseId = this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            }
            this._sCaseId = sCaseId;
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadOutcomeData(sCaseId);
        },

        loadOutcomeData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("out");
            var oPage = this.byId("outcomePage");
            if (oPage) oPage.setBusy(true);

            var that = this;

            Promise.all([
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId).then(function (r) {
                    if (!r.ok) throw new Error("Case not found");
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/progress").then(function (r) {
                    if (r.status === 404) return null;
                    if (!r.ok) throw new Error("Execution progress error");
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/outcomes").then(function (r) {
                    if (!r.ok) return [];
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/audit").then(function (r) {
                    if (!r.ok) return [];
                    return r.json();
                })
            ])
            .then(function (results) {
                var caseData   = results[0];
                var progress   = results[1];
                var outcomes   = results[2] || [];
                var auditRaw   = results[3] || [];

                var auditEvents = auditRaw.events || auditRaw || [];

                // Determine state from backend
                var sState = "PENDING";

                if (!progress) {
                    // No execution started
                    oModel.setData({
                        state: "PENDING",
                        case_id: sCaseId,
                        plan_id: caseData.approved_plan_id || "—",
                        plan_version: caseData.approved_plan_version || "—",
                        strategy: "", planned_quantity: 0, actual_quantity: 0,
                        planned_arrival: "—", actual_arrival: "—",
                        planned_cost: 0, actual_cost: 0, delay_days: 0,
                        failure_reason: "", lessons_learned: "", audit_events: auditEvents
                    });
                    return;
                }

                if (progress.is_success) {
                    sState = "SUCCESS";
                } else if (progress.is_failed) {
                    sState = "FAILED";
                } else {
                    sState = "PENDING";
                }

                var baseline   = progress.baseline || {};
                var deviation  = progress.deviation || {};

                // Try to pull actual values from outcome record if available
                var oOutRec = outcomes.length > 0 ? outcomes[outcomes.length - 1] : null;

                var sActualArrival = "—";
                var nActualQty     = progress.current_confirmed_quantity || 0;
                var nActualCost    = progress.current_estimated_cost || 0;
                var sLessons       = "";
                var sFailureReason = progress.failure_reason || "";

                if (oOutRec) {
                    nActualQty    = oOutRec.actual_quantity || nActualQty;
                    nActualCost   = oOutRec.actual_cost || nActualCost;
                    sLessons      = oOutRec.lessons_learned || "";
                    sActualArrival = oOutRec.actual_arrival_date || "—";
                }

                oModel.setData({
                    state: sState,
                    case_id: sCaseId,
                    plan_id: baseline.plan_id || caseData.approved_plan_id || "—",
                    plan_version: baseline.plan_version || caseData.approved_plan_version || "—",
                    strategy: baseline.strategy || "—",
                    planned_quantity: baseline.planned_quantity || 0,
                    actual_quantity: nActualQty,
                    planned_arrival: baseline.planned_arrival_date || "—",
                    actual_arrival: sActualArrival,
                    planned_cost: baseline.planned_total_cost || 0,
                    actual_cost: nActualCost,
                    delay_days: deviation.delay_days || 0,
                    failure_reason: sFailureReason,
                    lessons_learned: sLessons,
                    audit_events: auditEvents
                });
            })
            .catch(function (err) {
                MessageBox.error("Failed to load outcome: " + err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        onRefresh: function () {
            this.loadOutcomeData(this._sCaseId);
        },

        onBackToCases: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onReturnToPlanning: function () {
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: this._sCaseId });
        }
    });
});
