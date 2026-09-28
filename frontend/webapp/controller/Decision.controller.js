sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "sap/ui/core/Fragment"
], function (Controller, JSONModel, MessageBox, MessageToast, Fragment) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.Decision", {
        onInit: function () {
            var oModel = new JSONModel({
                decisionState: "PENDING", // PENDING, APPROVED, REJECTED
                case_id: "",
                selectedPlan: {},
                plannerRationale: "",
                approvalTimestamp: "",
                approvalActor: "SUPPLY_CHAIN_PLANNER",
                rejectionReason: ""
            });
            this.getView().setModel(oModel, "dec");

            var oModModel = new JSONModel({});
            this.getView().setModel(oModModel, "mod");

            var oRouter = this.getOwnerComponent().getRouter();
            ["decision", "decisionAlt", "checkpoint2", "checkpoint2Kebab", "checkpoint2Alt"].forEach(function (r) {
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
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadDecisionData(sCaseId);
        },

        loadDecisionData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("dec");
            var that = this;

            Promise.all([
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId).then(function (r) {
                    if (!r.ok) throw new Error("Case not found");
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan").then(function (r) {
                    if (r.status === 404) return null;
                    if (!r.ok) throw new Error("Recovery plans not found");
                    return r.json();
                })
            ])
            .then(function (results) {
                var caseData = results[0] || {};
                var planSet = results[1];

                // Route guard: Feasible plans must exist before final decision can be made
                if (!planSet || !planSet.feasible_plans || planSet.feasible_plans.length === 0) {
                    MessageBox.warning(
                        "Recovery plans have not been generated yet for " + sCaseId + ".\n\nPlease generate and review plans in Stage 5 before making a final decision.",
                        {
                            title: "Workflow Stage Locked",
                            onClose: function () {
                                that.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: sCaseId });
                            }
                        }
                    );
                    return;
                }

                var feasible = planSet.feasible_plans;
                var sChosenId = caseData.approved_plan_id || that.getOwnerComponent().getModel("app").getProperty("/selectedPlanId") || feasible[0].plan_id;
                var selectedPlan = feasible[0];
                for (var i = 0; i < feasible.length; i++) {
                    if (feasible[i].plan_id === sChosenId) {
                        selectedPlan = feasible[i];
                        break;
                    }
                }

                var bApproved = caseData.checkpoint2_decision === "APPROVE" || caseData.status === "RECOVERY_APPROVED" || caseData.status === "EXECUTION_IN_PROGRESS" || caseData.status === "RESOLVED";

                oModel.setData({
                    decisionState: bApproved ? "APPROVED" : "PENDING",
                    case_id: sCaseId,
                    selectedPlan: selectedPlan,
                    plannerRationale: caseData.checkpoint2_rationale || "",
                    approvalTimestamp: caseData.checkpoint2_timestamp ? new Date(caseData.checkpoint2_timestamp).toLocaleString() : new Date().toLocaleString(),
                    approvalActor: "SUPPLY_CHAIN_PLANNER",
                    rejectionReason: ""
                });
            })
            .catch(function (err) {
                MessageBox.error("Failed to load decision data: " + err.message);
            });
        },

        onApprovePlan: function () {
            var oModel = this.getView().getModel("dec");
            var selectedPlan = oModel.getProperty("/selectedPlan");
            var sRationale = oModel.getProperty("/plannerRationale") || "Manager approved optimal recovery strategy.";
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;

            MessageBox.confirm(
                "Authorize execution of Plan " + selectedPlan.plan_id + " (" + (selectedPlan.version || "v1") + ")?\n\nThis will lock the plan baseline and advance the case to Stage 7: Execution & Monitoring.",
                {
                    title: "Authorize Plan Execution",
                    actions: [MessageBox.Action.OK, MessageBox.Action.CANCEL],
                    emphasizedAction: MessageBox.Action.OK,
                    onClose: function (sAction) {
                        if (sAction === MessageBox.Action.OK) {
                            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/checkpoint2", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    decision: "APPROVE",
                                    plan_id: selectedPlan.plan_id,
                                    version: selectedPlan.version || "v1",
                                    rationale: sRationale
                                })
                            })
                            .then(function (res) {
                                if (!res.ok) {
                                    return res.json().then(function (d) {
                                        throw new Error(d.message || "Approval failed");
                                    });
                                }
                                return res.json();
                            })
                            .then(function (resp) {
                                oModel.setProperty("/decisionState", "APPROVED");
                                oModel.setProperty("/approvalTimestamp", new Date().toLocaleString());

                                that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "RECOVERY_APPROVED");
                                that.getOwnerComponent().getModel("app").setProperty("/stageStep", 7);
                                MessageToast.show("Plan " + selectedPlan.plan_id + " approved. Proceeding to Execution & Monitoring...");

                                setTimeout(function () {
                                    that.onProceedToExecution();
                                }, 800);
                            })
                            .catch(function (err) {
                                MessageBox.error("Approval failed: " + err.message);
                            });
                        }
                    }
                }
            );
        },

        onOpenRejectDialog: function () {
            var oView = this.getView();
            var that = this;
            if (!this._pRejectDialog) {
                this._pRejectDialog = Fragment.load({
                    id: oView.getId(),
                    name: "com.quads.supplychain.view.RejectPlanDialog",
                    controller: this
                }).then(function (oDialog) {
                    oView.addDependent(oDialog);
                    return oDialog;
                });
            }
            this._pRejectDialog.then(function (oDialog) {
                oDialog.open();
            });
        },

        onConfirmReject: function () {
            var sReason = this.byId("rejectReasonInput") ? this.byId("rejectReasonInput").getValue() : "";
            if (!sReason || sReason.trim().length < 5) {
                MessageBox.warning("Please provide a valid rejection reason (minimum 5 characters).");
                return;
            }

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var oModel = this.getView().getModel("dec");
            var that = this;

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/checkpoint2", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    decision: "REJECT",
                    rationale: sReason
                })
            })
            .then(function (res) {
                return res.json();
            })
            .then(function () {
                oModel.setProperty("/decisionState", "REJECTED");
                oModel.setProperty("/rejectionReason", sReason);
                that.onCloseRejectDialog();
                MessageToast.show("Recovery proposals rejected. Return to Recovery Planning for new cycle.");
            })
            .catch(function (err) {
                MessageBox.error("Rejection recording failed: " + err.message);
            });
        },

        onCloseRejectDialog: function () {
            if (this._pRejectDialog) {
                this._pRejectDialog.then(function (oDialog) {
                    oDialog.close();
                });
            }
        },

        onOpenModifyDialog: function () {
            var selectedPlan = this.getView().getModel("dec").getProperty("/selectedPlan") || {};
            var oModModel = this.getView().getModel("mod");
            oModModel.setData({
                plan_id: selectedPlan.plan_id || "PLAN-01",
                quantity: selectedPlan.recovered_quantity || 1000,
                transport_mode: selectedPlan.transport_name || "Express Air Cargo",
                cost_budget: selectedPlan.total_cost || 25000,
                lead_time_cap: selectedPlan.recovery_days || 5,
                source_supplier: selectedPlan.source_name || "Bavaria CellTech"
            });

            var oView = this.getView();
            if (!this._pModifyDialog) {
                this._pModifyDialog = Fragment.load({
                    id: oView.getId(),
                    name: "com.quads.supplychain.view.ModifyPlanDialog",
                    controller: this
                }).then(function (oDialog) {
                    oView.addDependent(oDialog);
                    return oDialog;
                });
            }
            this._pModifyDialog.then(function (oDialog) {
                oDialog.open();
            });
        },

        onSavePlanModification: function () {
            var modData = this.getView().getModel("mod").getData();
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/modify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    plan_id: modData.plan_id,
                    modified_quantity: Number(modData.quantity),
                    modified_transport_name: modData.transport_mode,
                    cost_ceiling: Number(modData.cost_budget),
                    max_recovery_days: Number(modData.lead_time_cap)
                })
            })
            .then(function (res) {
                if (!res.ok) throw new Error("Plan modification failed");
                return res.json();
            })
            .then(function (planSet) {
                that.onCloseModifyDialog();
                MessageToast.show("Plan modified. New version generated. Returning to Recovery Planning...");
                that.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: sCaseId });
            })
            .catch(function (err) {
                MessageBox.error(err.message);
            });
        },

        onCloseModifyDialog: function () {
            if (this._pModifyDialog) {
                this._pModifyDialog.then(function (oDialog) {
                    oDialog.close();
                });
            }
        },

        onProceedToExecution: function () {
            this.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: this._sCurrentCaseId });
        },

        onBackToRecoveryPlanning: function () {
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: this._sCurrentCaseId });
        }
    });
});
