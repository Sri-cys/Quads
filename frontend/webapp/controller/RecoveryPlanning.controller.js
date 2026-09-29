sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "sap/ui/core/Fragment",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageBox, MessageToast, Fragment, WorkflowNavHelper) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.RecoveryPlanning", {
        onInit: function () {
            var oModel = new JSONModel({
                state: "RUNNING", // RUNNING, COMPLETED, FAILED
                agent2_status: "RUNNING", // RUNNING, COMPLETED, FAILED
                agent3_status: "PENDING", // PENDING, RUNNING, COMPLETED, FAILED
                errorMessage: "",
                case_id: "",
                priority: "BALANCED",
                material_id: "",
                material_name: "",
                target_quantity: 0,
                days_of_cover: 0,
                candidates: [],
                feasible_plans: [],
                infeasible_plans: [],
                all_evaluated_plans: [],
                total_plans_count: 0,
                selectedPlanId: null,
                selectedPlanVersion: "v1"
            });
            this.getView().setModel(oModel, "rec");

            var oInspectModel = new JSONModel({});
            this.getView().setModel(oInspectModel, "inspect");

            var oRouter = this.getOwnerComponent().getRouter();
            ["recoveryPlanning", "recoveryPlanningKebab", "recoveryPlanningAlt", "recoveryPlans", "recoveryPlansAlt"].forEach(function (r) {
                var oR = oRouter.getRoute(r);
                if (oR) oR.attachPatternMatched(this._onPatternMatched, this);
            }, this);
        },

        _onPatternMatched: function (oEvent) {
            var sCaseId = oEvent.getParameter("arguments").caseId;
            if (!sCaseId) {
                sCaseId = this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            }
            this._sCurrentCaseId = sCaseId;
            sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {
                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, 5);
            }.bind(this));
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadRecoveryData(sCaseId);
        },

        loadRecoveryData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("rec");
            var that = this;

            oModel.setProperty("/state", "RUNNING");
            oModel.setProperty("/agent2_status", "RUNNING");
            oModel.setProperty("/agent3_status", "PENDING");
            oModel.setProperty("/errorMessage", "");

            Promise.all([
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId).then(function (r) {
                    if (!r.ok) throw new Error("Case record not found");
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact").then(function (r) {
                    if (r.ok) return r.json();
                    return {};
                })
            ])
            .then(function (caseAndImpact) {
                var caseData = caseAndImpact[0] || {};
                var impactData = caseAndImpact[1] || {};

                // Route guard: Priority must be saved before Recovery Planning
                if (!caseData.checkpoint1_decision && caseData.status !== "CHECKPOINT_APPROVED" && caseData.status !== "RECOVERY_APPROVED" && caseData.status !== "RESOLVED") {
                    MessageBox.warning(
                        "Human Checkpoint 1 priority has not been saved for " + sCaseId + ".\n\nPlease set recovery priority before proceeding to Recovery Planning.",
                        {
                            title: "Workflow Stage Locked",
                            onClose: function () {
                                that.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: sCaseId });
                            }
                        }
                    );
                    return;
                }

                var sPriority = caseData.checkpoint1_decision || "BALANCED";

                // Step 1: Check candidates from Agent 2
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/candidates")
                    .then(function (candRes) {
                        if (candRes.ok) return candRes.json();
                        return null;
                    })
                    .then(function (candidateSet) {
                        if (candidateSet && candidateSet.candidates) {
                            oModel.setProperty("/candidates", candidateSet.candidates);
                            oModel.setProperty("/agent2_status", "COMPLETED");
                            oModel.setProperty("/agent3_status", "RUNNING");
                        }

                        // Step 2: Fetch full evaluation from Agent 3
                        return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan")
                            .then(function (r) {
                                if (r.ok) return r.json();
                                // Trigger generation if not present
                                return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan", {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ priority: sPriority })
                                }).then(function (res) {
                                    if (!res.ok) throw new Error("Failed to evaluate recovery plans (HTTP " + res.status + ")");
                                    return res.json();
                                });
                            });
                    })
                    .then(function (planSetData) {
                        var feasible = planSetData.feasible_plans || [];
                        var infeasible = planSetData.infeasible_plans || [];
                        var allPlans = feasible.concat(infeasible);

                        // If candidates weren't fetched earlier, construct from plans
                        var candList = oModel.getProperty("/candidates");
                        if (!candList || candList.length === 0) {
                            candList = allPlans.map(function (p) {
                                return {
                                    plan_id: p.plan_id,
                                    version: p.version || "v1",
                                    strategy: p.strategy,
                                    source_name: p.source_name || "Alternate Sourcing Node",
                                    destination_name: p.destination_name || "Munich Assembly Hub",
                                    recovered_quantity: p.recovered_quantity,
                                    transport_name: p.transport_name || "Standard Freight Carrier",
                                    recovery_days: p.recovery_days,
                                    expected_customer_impact: p.customer_delay_days > 0 ? (p.customer_delay_days + " days delay") : "On-Time / Zero Delay",
                                    title: p.title
                                };
                            });
                            oModel.setProperty("/candidates", candList);
                        }

                        oModel.setProperty("/state", "COMPLETED");
                        oModel.setProperty("/agent2_status", "COMPLETED");
                        oModel.setProperty("/agent3_status", "COMPLETED");
                        oModel.setProperty("/case_id", sCaseId);
                        oModel.setProperty("/priority", sPriority);
                        oModel.setProperty("/material_id", caseData.material_id || "MAT-001");
                        oModel.setProperty("/material_name", caseData.material_name || "Lithium Battery Pack");
                        oModel.setProperty("/target_quantity", impactData.supply_gap_quantity || caseData.affected_quantity || 1000);
                        oModel.setProperty("/days_of_cover", impactData.days_of_cover !== undefined ? impactData.days_of_cover : 2.0);
                        oModel.setProperty("/feasible_plans", feasible);
                        oModel.setProperty("/infeasible_plans", infeasible);
                        oModel.setProperty("/all_evaluated_plans", allPlans);
                        oModel.setProperty("/total_plans_count", allPlans.length);

                        that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "DECISION_PENDING");
                        // Intentionally do NOT set stageStep to 6 here. The user must click "Proceed to Decision"
                        // to logically complete this stage in the UI, or it will be updated by App.controller.js on route change.
                    })
                    .catch(function (err) {
                        oModel.setProperty("/state", "FAILED");
                        oModel.setProperty("/agent3_status", "FAILED");
                        oModel.setProperty("/errorMessage", err.message);
                    });
            })
            .catch(function (err) {
                oModel.setProperty("/state", "FAILED");
                oModel.setProperty("/errorMessage", err.message);
            });
        },

        onRefreshPlans: function () {
            this.loadRecoveryData(this._sCurrentCaseId);
        },

        onInspectPlan: function (oEvent) {
            var oContext = oEvent.getSource().getBindingContext("rec");
            if (!oContext) return;
            var planObj = oContext.getObject();

            var oInspectModel = this.getView().getModel("inspect");
            oInspectModel.setData(planObj);

            var oView = this.getView();
            if (!this._pInspectDialog) {
                this._pInspectDialog = Fragment.load({
                    id: oView.getId(),
                    name: "com.quads.supplychain.view.InspectPlanDialog",
                    controller: this
                }).then(function (oDialog) {
                    oView.addDependent(oDialog);
                    return oDialog;
                });
            }
            this._pInspectDialog.then(function (oDialog) {
                oDialog.open();
            });
        },

        onCloseInspectDialog: function () {
            if (this._pInspectDialog) {
                this._pInspectDialog.then(function (oDialog) {
                    oDialog.close();
                });
            }
        },

        onProceedToDecision: function () {
            var sCaseId = this._sCurrentCaseId;
            WorkflowNavHelper.completeStage(sCaseId, 5, 5);
            this.getOwnerComponent().getRouter().navTo("decision", { caseId: sCaseId });
        },

        onBackToPriority: function () {
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: this._sCurrentCaseId });
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        }
    });
});
