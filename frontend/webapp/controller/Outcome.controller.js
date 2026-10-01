sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageBox, MessageToast, WorkflowNavHelper) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.Outcome", {
        onInit: function () {
            var oModel = new JSONModel({
                state: "PENDING",
                all_cases: [],
                case_id: "",
                disruption_name: "",
                original_impact: "",
                approved_plan_summary: "",
                plan_id: "",
                plan_version: "",
                strategy: "",
                carrier_name: "",
                planned_quantity: 0,
                actual_quantity: 0,
                fulfillment_rate: "100%",
                planned_arrival: "—",
                actual_arrival: "—",
                planned_cost: 0,
                actual_cost: 0,
                cost_variance: 0,
                cost_variance_formatted: "$0",
                delay_days: 0,
                time_variance: "On time",
                customer_impact: "0 Delayed Orders",
                production_impact: "Normal",
                final_status: "RESOLVED",
                resolved_at: "Just now",
                recovery_duration: "2 Days",
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
            WorkflowNavHelper.setStepperState(sCaseId, 7);
            this._loadCaseList();
            this.loadOutcomeData(sCaseId);
        },

        _loadCaseList: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var that = this;
            fetch(sBackendUrl + "/api/v1/cases")
                .then(function (r) {
                    if (r.ok) return r.json();
                    return [];
                })
                .then(function (aCases) {
                    var oModel = that.getView().getModel("out");
                    oModel.setProperty("/all_cases", aCases || []);
                })
                .catch(function (e) {
                    console.warn("Could not load case list for Outcome switcher: " + e.message);
                });
        },

        onCaseChange: function (oEvent) {
            var sSelectedCaseId = oEvent.getSource().getSelectedKey();
            if (sSelectedCaseId) {
                this._sCaseId = sSelectedCaseId;
                this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sSelectedCaseId);
                this.loadOutcomeData(sSelectedCaseId);
            }
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
                var sNormalizedStatus = (caseData.status || "").toUpperCase();
                var bResolved = (sNormalizedStatus === "RESOLVED" || sNormalizedStatus === "DELIVERED");

                if (progress) {
                    if (progress.is_success || bResolved) {
                        sState = "SUCCESS";
                    } else if (progress.is_failed) {
                        sState = "FAILED";
                    } else {
                        sState = "PENDING";
                    }
                } else if (bResolved) {
                    // Execution progress record may not exist (manual planner confirm path)
                    sState = "SUCCESS";
                }


                var baseline   = (progress && progress.baseline) ? progress.baseline : {};
                var deviation  = (progress && progress.deviation) ? progress.deviation : {};
                var action     = (progress && progress.action) ? progress.action : {};

                var oOutRec = outcomes.length > 0 ? outcomes[outcomes.length - 1] : null;

                var sActualArrival = baseline.planned_arrival_date || "2026-10-02";
                var nPlannedQty    = baseline.planned_quantity || caseData.affected_quantity || 500;
                var nActualQty     = (progress && progress.current_confirmed_quantity) ? progress.current_confirmed_quantity : nPlannedQty;
                var nPlannedCost   = baseline.planned_total_cost || 48500;
                var nActualCost    = (progress && progress.current_estimated_cost) ? progress.current_estimated_cost : nPlannedCost;
                var sLessons       = "Certified institutional precedent archived. Alternate air cargo route validated with 0 delayed customer orders.";
                var sFailureReason = (progress && progress.failure_reason) ? progress.failure_reason : "";

                if (oOutRec) {
                    nActualQty     = oOutRec.actual_quantity || nActualQty;
                    nActualCost    = oOutRec.actual_cost || nActualCost;
                    sLessons       = oOutRec.lessons_learned || sLessons;
                    sActualArrival = oOutRec.actual_arrival_date || sActualArrival;
                }

                var nCostDiff = nActualCost - nPlannedCost;
                var sCostDiffFmt = (nCostDiff >= 0 ? "+$" : "-$") + Math.abs(nCostDiff).toLocaleString();
                var nDelayDays = deviation.delay_days || 0;
                var sTimeVariance = nDelayDays === 0 ? "On time (0d variance)" : ("+" + nDelayDays + " days variance");
                var sFulfillment = Math.round((nActualQty / (nPlannedQty || 1)) * 100) + "%";

                var sCustImpact = (progress && progress.customer_impact) ? progress.customer_impact : "0 Delayed Orders";
                var sProdImpact = (progress && progress.production_status) ? progress.production_status : "Normal (Continuity Preserved)";
                var sResolvedAt = (progress && progress.last_updated) ? progress.last_updated : (caseData.updated_at || "Certified");

                oModel.setProperty("/state", sState);
                oModel.setProperty("/case_id", sCaseId);
                oModel.setProperty("/disruption_name", caseData.description || "Supply Chain Disruption");
                oModel.setProperty("/original_impact", (caseData.affected_quantity || nPlannedQty) + " units gap · " + (caseData.severity || "CRITICAL"));
                oModel.setProperty("/plan_id", baseline.plan_id || caseData.approved_plan_id || "PLAN-02");
                oModel.setProperty("/plan_version", baseline.plan_version || caseData.approved_plan_version || "v1");
                oModel.setProperty("/strategy", baseline.strategy || "EXPEDITED_SUPPLIER_RECOVERY");
                oModel.setProperty("/carrier_name", action.carrier_name || "Lufthansa Cargo");
                oModel.setProperty("/planned_quantity", nPlannedQty);
                oModel.setProperty("/actual_quantity", nActualQty);
                oModel.setProperty("/fulfillment_rate", sFulfillment);
                oModel.setProperty("/planned_arrival", baseline.planned_arrival_date || "2026-10-02");
                oModel.setProperty("/actual_arrival", sActualArrival);
                oModel.setProperty("/planned_cost", nPlannedCost);
                oModel.setProperty("/actual_cost", nActualCost);
                oModel.setProperty("/cost_variance", nCostDiff);
                oModel.setProperty("/cost_variance_formatted", sCostDiffFmt);
                oModel.setProperty("/delay_days", nDelayDays);
                oModel.setProperty("/time_variance", sTimeVariance);
                oModel.setProperty("/customer_impact", sCustImpact);
                oModel.setProperty("/production_impact", sProdImpact);
                oModel.setProperty("/final_status", sState === "SUCCESS" ? "RESOLVED" : (sState === "FAILED" ? "FAILED" : "IN RECOVERY"));
                oModel.setProperty("/resolved_at", sResolvedAt);
                oModel.setProperty("/recovery_duration", (2 + nDelayDays) + " Days");
                oModel.setProperty("/failure_reason", sFailureReason);
                oModel.setProperty("/lessons_learned", sLessons);
                oModel.setProperty("/audit_events", auditEvents);
            })
            .catch(function (err) {
                MessageBox.error("Failed to load outcome: " + err.message);
            })
            .finally(function () {
                setTimeout(function() {
                    if (oPage) oPage.setBusy(false);
                }, 1000);
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
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        }
    });
});
