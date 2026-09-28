sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "sap/ui/core/Fragment"
], function (Controller, JSONModel, MessageBox, MessageToast, Fragment) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.RecoveryPlanning", {
        onInit: function () {
            var oModel = new JSONModel({
                state: "RUNNING", // RUNNING, COMPLETED, FAILED
                errorMessage: "",
                case_id: "",
                priority: "BALANCED",
                material_id: "",
                material_name: "",
                target_quantity: 0,
                days_of_cover: 0,
                ai_briefing: "",
                ai_status: "FALLBACK",
                feasible_plans: [],
                infeasible_plans: [],
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
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadRecoveryData(sCaseId);
        },

        loadRecoveryData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("rec");
            var that = this;

            oModel.setProperty("/state", "RUNNING");
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
                        "Human Checkpoint 1 priority has not been saved for " + sCaseId + ".\n\nPlease save recovery priority before proceeding to Stage 5 Recovery Planning.",
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

                // Fetch or generate recovery plans
                return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan")
                    .then(function (r) {
                        if (r.ok) return r.json();
                        return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ priority: sPriority })
                        }).then(function (res) {
                            if (!res.ok) throw new Error("Failed to generate recovery plans: " + res.status);
                            return res.json();
                        });
                    })
                    .then(function (planSetData) {
                        var feasible = planSetData.feasible_plans || [];
                        var infeasible = planSetData.infeasible_plans || [];

                        var sSelId = caseData.approved_plan_id;
                        var sSelVer = caseData.approved_plan_version || "v1";

                        if (!sSelId && feasible.length > 0) {
                            sSelId = feasible[0].plan_id;
                            sSelVer = feasible[0].version || "v1";
                        }

                        oModel.setData({
                            state: "COMPLETED",
                            errorMessage: "",
                            case_id: sCaseId,
                            priority: sPriority,
                            material_id: caseData.material_id || impactData.material_id || "MAT-001",
                            material_name: caseData.material_name || "Lithium Battery Pack",
                            target_quantity: impactData.supply_gap_quantity || caseData.affected_quantity || 1000,
                            days_of_cover: impactData.days_of_cover !== undefined ? impactData.days_of_cover : 2.0,
                            ai_briefing: planSetData.ai_briefing || "Evaluating alternatives to mitigate disruption...",
                            ai_status: planSetData.ai_status || "FALLBACK",
                            feasible_plans: feasible,
                            infeasible_plans: infeasible,
                            selectedPlanId: sSelId,
                            selectedPlanVersion: sSelVer
                        });

                        that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "AGENT3_COMPLETED");
                        that.getOwnerComponent().getModel("app").setProperty("/stageStep", 6);
                    });
            })
            .catch(function (err) {
                oModel.setProperty("/state", "FAILED");
                oModel.setProperty("/errorMessage", err.message);
            });
        },

        onRefreshPlans: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var sPriority = this.getView().getModel("rec").getProperty("/priority") || "BALANCED";
            var oModel = this.getView().getModel("rec");
            var that = this;

            oModel.setProperty("/state", "RUNNING");
            oModel.setProperty("/errorMessage", "");

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan?force_regenerate=true", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ priority: sPriority })
            })
            .then(function (res) {
                if (!res.ok) throw new Error("Failed to re-generate plans");
                return res.json();
            })
            .then(function (planSetData) {
                var feasible = planSetData.feasible_plans || [];
                var infeasible = planSetData.infeasible_plans || [];

                oModel.setProperty("/state", "COMPLETED");
                oModel.setProperty("/feasible_plans", feasible);
                oModel.setProperty("/infeasible_plans", infeasible);
                oModel.setProperty("/ai_briefing", planSetData.ai_briefing);

                if (feasible.length > 0) {
                    oModel.setProperty("/selectedPlanId", feasible[0].plan_id);
                    oModel.setProperty("/selectedPlanVersion", feasible[0].version || "v1");
                }
                MessageToast.show("Agent 3 re-generated " + feasible.length + " feasible recovery combinations.");
            })
            .catch(function (err) {
                oModel.setProperty("/state", "FAILED");
                oModel.setProperty("/errorMessage", err.message);
            });
        },

        onSelectPlan: function (oEvent) {
            var oContext = oEvent.getSource().getBindingContext("rec");
            if (!oContext) return;

            var planId = oContext.getProperty("plan_id");
            var version = oContext.getProperty("version") || "v1";

            this.getView().getModel("rec").setProperty("/selectedPlanId", planId);
            this.getView().getModel("rec").setProperty("/selectedPlanVersion", version);
            MessageToast.show("Plan " + planId + " (" + version + ") selected for final decision.");
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
            var sPlanId = this.getView().getModel("rec").getProperty("/selectedPlanId");
            var sVersion = this.getView().getModel("rec").getProperty("/selectedPlanVersion") || "v1";
            this.getOwnerComponent().getModel("app").setProperty("/selectedPlanId", sPlanId);
            this.getOwnerComponent().getModel("app").setProperty("/selectedPlanVersion", sVersion);
            this.getOwnerComponent().getRouter().navTo("decision", { caseId: this._sCurrentCaseId });
        },

        onBackToConstraints: function () {
            this.getOwnerComponent().getRouter().navTo("constraints", { caseId: this._sCurrentCaseId });
        }
    });
});
