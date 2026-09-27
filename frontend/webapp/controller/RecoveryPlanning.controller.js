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
                case_id: "",
                disruption_name: "Disruption Recovery",
                priority: "BALANCED",
                checkpoint2_status: "PENDING",
                approved_plan_id: null,
                approved_plan_version: null,
                checkpoint2_timestamp: null,
                material_id: "",
                material_name: "",
                target_plant_id: "",
                target_plant_name: "",
                supplier_id: "",
                supplier_name: "",
                expected_delay_days: 0,
                target_quantity: 0,
                days_of_cover: 0,
                ai_briefing: "",
                ai_status: "FALLBACK",
                feasible_plans: [],
                infeasible_plans: [],
                selectedPlanId: null,
                selectedPlanVersion: "v1",
                plannerRationale: ""
            });
            this.getView().setModel(oModel, "rec");

            var oInspectModel = new JSONModel({});
            this.getView().setModel(oInspectModel, "inspect");

            var oModModel = new JSONModel({});
            this.getView().setModel(oModModel, "mod");

            var oRouter = this.getOwnerComponent().getRouter();
            var aRoutes = ["recoveryPlanning", "recoveryPlanningAlt", "recoveryPlans", "recoveryPlansAlt", "checkpoint2", "checkpoint2Alt"];
            aRoutes.forEach(function (rName) {
                var oR = oRouter.getRoute(rName);
                if (oR) oR.attachPatternMatched(this._onPatternMatched, this);
            }, this);
        },

        _onPatternMatched: function (oEvent) {
            var sCaseId = oEvent.getParameter("arguments").caseId;
            if (!sCaseId) {
                sCaseId = this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            }
            this._sCurrentCaseId = sCaseId;
            this.loadRecoveryData(sCaseId);
        },

        loadRecoveryData: function (sCaseId) {
            var oPage = this.byId("recoveryPlanningPage");
            if (oPage) oPage.setBusy(true);

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("rec");
            var that = this;

            // Step 1: Fetch Case and Impact metadata
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

                var sPriority = caseData.checkpoint1_decision || "BALANCED";

                // Step 2: Fetch or Generate Recovery Plans
                return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan")
                    .then(function (r) {
                        if (r.ok) return r.json();
                        // If not generated yet, call POST to generate
                        return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ priority: sPriority })
                        }).then(function (res) {
                            if (!res.ok) throw new Error("Failed to generate recovery alternatives");
                            return res.json();
                        });
                    })
                    .then(function (planSetData) {
                        var feasible = planSetData.feasible_plans || [];
                        var infeasible = planSetData.infeasible_plans || [];

                        // Selection defaults: approved plan if approved, else top feasible plan
                        var sSelId = caseData.approved_plan_id;
                        var sSelVer = caseData.approved_plan_version || "v1";

                        if (!sSelId && feasible.length > 0) {
                            sSelId = feasible[0].plan_id;
                            sSelVer = feasible[0].version || "v1";
                        }

                        oModel.setData({
                            case_id: sCaseId,
                            disruption_name: caseData.title || "Supplier Disruption",
                            priority: sPriority,
                            checkpoint2_status: caseData.checkpoint2_decision === "APPROVE" ? "RECOVERY_APPROVED" : (caseData.status || "PENDING"),
                            approved_plan_id: caseData.approved_plan_id || (caseData.checkpoint2_decision === "APPROVE" ? sSelId : null),
                            approved_plan_version: caseData.approved_plan_version || (caseData.checkpoint2_decision === "APPROVE" ? sSelVer : null),
                            checkpoint2_timestamp: caseData.checkpoint2_timestamp ? new Date(caseData.checkpoint2_timestamp).toLocaleString() : null,
                            material_id: caseData.affected_material_id || impactData.material_id || "MAT-001",
                            material_name: caseData.affected_material_name || "Lithium-Ion Battery Pack",
                            target_plant_id: caseData.affected_plant_id || impactData.plant_id || "PLANT-001",
                            target_plant_name: caseData.affected_plant_name || "Munich Assembly Plant",
                            supplier_id: caseData.affected_supplier_id || "SUP-001",
                            supplier_name: caseData.affected_supplier_name || "Bavaria CellTech",
                            expected_delay_days: caseData.expected_delay_days || 14,
                            target_quantity: impactData.supply_gap_quantity || caseData.affected_quantity || 1000,
                            days_of_cover: impactData.days_of_cover !== undefined ? impactData.days_of_cover : 5.0,
                            ai_briefing: planSetData.ai_briefing || "Evaluating alternatives to mitigate disruption...",
                            ai_status: planSetData.ai_status || "FALLBACK",
                            feasible_plans: feasible,
                            infeasible_plans: infeasible,
                            selectedPlanId: sSelId,
                            selectedPlanVersion: sSelVer,
                            plannerRationale: ""
                        });
                    });
            })
            .catch(function (err) {
                MessageBox.error("Failed to load Phase 2 recovery data: " + err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        onSelectPlan: function (oEvent) {
            var oContext = oEvent.getSource().getBindingContext("rec");
            if (!oContext) return;
            var oPlan = oContext.getObject();

            this.getView().getModel("rec").setProperty("/selectedPlanId", oPlan.plan_id);
            this.getView().getModel("rec").setProperty("/selectedPlanVersion", oPlan.version || "v1");

            MessageToast.show("Selected " + oPlan.plan_id + " (" + (oPlan.version || "v1") + ") for Checkpoint 2 approval.");
        },

        onInspectPlan: function (oEvent) {
            var oContext = oEvent.getSource().getBindingContext("rec");
            if (!oContext) return;
            var oPlan = oContext.getObject();

            var oInspectData = JSON.parse(JSON.stringify(oPlan));
            oInspectData.manager_priority = this.getView().getModel("rec").getProperty("/priority");

            this.getView().getModel("inspect").setData(oInspectData);

            var oView = this.getView();
            var that = this;

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

        onSelectPlanFromDialog: function () {
            var oInspectData = this.getView().getModel("inspect").getData();
            if (oInspectData && oInspectData.plan_id) {
                this.getView().getModel("rec").setProperty("/selectedPlanId", oInspectData.plan_id);
                this.getView().getModel("rec").setProperty("/selectedPlanVersion", oInspectData.version || "v1");
                MessageToast.show("Selected " + oInspectData.plan_id + " (" + oInspectData.version + ")");
            }
            this.onCloseInspectDialog();
        },

        onCloseInspectDialog: function () {
            if (this._pInspectDialog) {
                this._pInspectDialog.then(function (oDialog) {
                    oDialog.close();
                });
            }
        },

        onOpenModifyDialog: function (oEvent) {
            var oPlan = null;
            if (oEvent && oEvent.getSource) {
                var oContext = oEvent.getSource().getBindingContext("rec");
                if (oContext) {
                    oPlan = oContext.getObject();
                }
            }

            if (!oPlan) {
                var sSelectedId = this.getView().getModel("rec").getProperty("/selectedPlanId");
                var aPlans = this.getView().getModel("rec").getProperty("/feasible_plans") || [];
                for (var i = 0; i < aPlans.length; i++) {
                    if (aPlans[i].plan_id === sSelectedId) {
                        oPlan = aPlans[i];
                        break;
                    }
                }
            }

            if (!oPlan) {
                MessageBox.warning("Please select a feasible recovery plan to modify.");
                return;
            }

            var oModData = {
                plan_id: oPlan.plan_id,
                version: oPlan.version || "v1",
                strategy: oPlan.strategy,
                source_name: oPlan.source_name,
                requested_quantity: oPlan.recovered_quantity,
                transport_mode: oPlan.transport_mode || "AIR_EXPEDITED",
                max_cost_limit: null,
                max_acceptable_delay_days: null,
                modification_notes: ""
            };

            this.getView().getModel("mod").setData(oModData);

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

        onCloseModifyDialog: function () {
            if (this._pModifyDialog) {
                this._pModifyDialog.then(function (oDialog) {
                    oDialog.close();
                });
            }
        },

        onConfirmModify: function () {
            var oModData = this.getView().getModel("mod").getData();
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var oModel = this.getView().getModel("rec");
            var that = this;

            var payload = {
                plan_id: oModData.plan_id,
                requested_quantity: parseInt(oModData.requested_quantity, 10),
                transport_mode: oModData.transport_mode,
                max_cost_limit: oModData.max_cost_limit ? parseFloat(oModData.max_cost_limit) : null,
                max_acceptable_delay_days: oModData.max_acceptable_delay_days ? parseInt(oModData.max_acceptable_delay_days, 10) : null,
                notes: oModData.modification_notes || null
            };

            var oPage = this.byId("recoveryPlanningPage");
            if (oPage) oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/modify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(function (res) {
                return res.json().then(function (data) {
                    if (!res.ok) {
                        throw new Error(data.message || data.detail || "Failed to recalculate modified plan");
                    }
                    return data;
                });
            })
            .then(function (planSet) {
                oModel.setProperty("/feasible_plans", planSet.feasible_plans || []);
                oModel.setProperty("/infeasible_plans", planSet.infeasible_plans || []);
                oModel.setProperty("/ai_briefing", planSet.ai_briefing || oModel.getProperty("/ai_briefing"));

                // Select the modified plan and updated version
                var aFeasible = planSet.feasible_plans || [];
                for (var i = 0; i < aFeasible.length; i++) {
                    if (aFeasible[i].plan_id === oModData.plan_id) {
                        oModel.setProperty("/selectedPlanId", aFeasible[i].plan_id);
                        oModel.setProperty("/selectedPlanVersion", aFeasible[i].version);
                        break;
                    }
                }

                that.onCloseModifyDialog();
                MessageToast.show("Plan " + oModData.plan_id + " modified & deterministically re-evaluated!");
            })
            .catch(function (err) {
                MessageBox.error(err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        onApproveCheckpoint2: function () {
            var oModel = this.getView().getModel("rec");
            var sSelectedPlanId = oModel.getProperty("/selectedPlanId");
            var sSelectedPlanVersion = oModel.getProperty("/selectedPlanVersion") || "v1";
            var sRationale = oModel.getProperty("/plannerRationale") || "";
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;

            if (!sSelectedPlanId) {
                MessageBox.warning("Please select a valid feasible recovery plan before approving Checkpoint 2.");
                return;
            }

            MessageBox.confirm(
                "Approve Human Checkpoint 2 with Plan '" + sSelectedPlanId + "' (Version: " + sSelectedPlanVersion + ")?\n\n" +
                "Governance Rule:\n" +
                "• The system will lock this exact plan version in the audit trail.\n" +
                "• Phase 2 will conclude.\n" +
                "• Autonomous execution remains PAUSED at the Phase 2 boundary.\n" +
                "• Phase 3 will consume this approved plan.",
                {
                    title: "Confirm Checkpoint 2 Approval",
                    actions: [MessageBox.Action.OK, MessageBox.Action.CANCEL],
                    emphasizedAction: MessageBox.Action.OK,
                    onClose: function (sAction) {
                        if (sAction === MessageBox.Action.OK) {
                            var oPage = that.byId("recoveryPlanningPage");
                            if (oPage) oPage.setBusy(true);

                            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/checkpoint2", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    decision: "APPROVE",
                                    selected_plan_id: sSelectedPlanId,
                                    selected_plan_version: sSelectedPlanVersion,
                                    rationale: sRationale,
                                    manager_id: "SUPPLY_CHAIN_PLANNER"
                                })
                            })
                            .then(function (res) {
                                return res.json().then(function (data) {
                                    if (!res.ok) {
                                        throw new Error(data.message || data.detail || "Failed to approve Checkpoint 2");
                                    }
                                    return data;
                                });
                            })
                            .then(function (resp) {
                                oModel.setProperty("/checkpoint2_status", "RECOVERY_APPROVED");
                                oModel.setProperty("/approved_plan_id", sSelectedPlanId);
                                oModel.setProperty("/approved_plan_version", sSelectedPlanVersion);
                                oModel.setProperty("/checkpoint2_timestamp", new Date().toLocaleString());

                                MessageToast.show("Checkpoint 2 Approved (" + sSelectedPlanId + "). Proceeding to Execution...");

                                // Automatically advance to Phase 3 Execution stage
                                that.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
                                that.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: sCaseId });
                            })
                            .catch(function (err) {
                                MessageBox.error(err.message);
                            })
                            .finally(function () {
                                if (oPage) oPage.setBusy(false);
                            });
                        }
                    }
                }
            );
        },

        onRejectCheckpoint2: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;

            MessageBox.confirm(
                "Reject current recovery proposals?\n\nThis will reject the proposed alternatives and trigger a new recovery planning cycle.",
                {
                    title: "Reject Proposals",
                    actions: [MessageBox.Action.OK, MessageBox.Action.CANCEL],
                    emphasizedAction: MessageBox.Action.CANCEL,
                    onClose: function (sAction) {
                        if (sAction === MessageBox.Action.OK) {
                            var oPage = that.byId("recoveryPlanningPage");
                            if (oPage) oPage.setBusy(true);

                            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/checkpoint2", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    decision: "REJECT",
                                    rationale: "Planner rejected proposed alternatives; requested fresh cycle.",
                                    manager_id: "SUPPLY_CHAIN_PLANNER"
                                })
                            })
                            .then(function () {
                                // Trigger fresh planning cycle
                                return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan", {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ priority: that.getView().getModel("rec").getProperty("/priority") })
                                });
                            })
                            .then(function (res) { return res.json(); })
                            .then(function (planSet) {
                                var oModel = that.getView().getModel("rec");
                                oModel.setProperty("/feasible_plans", planSet.feasible_plans || []);
                                oModel.setProperty("/infeasible_plans", planSet.infeasible_plans || []);
                                oModel.setProperty("/ai_briefing", planSet.ai_briefing);
                                oModel.setProperty("/selectedPlanId", (planSet.feasible_plans && planSet.feasible_plans[0]) ? planSet.feasible_plans[0].plan_id : null);
                                oModel.setProperty("/selectedPlanVersion", "v1");
                                MessageToast.show("Proposals rejected. Fresh recovery planning cycle generated.");
                            })
                            .catch(function (err) {
                                MessageBox.error("Failed to cycle recovery plans: " + err.message);
                            })
                            .finally(function () {
                                if (oPage) oPage.setBusy(false);
                            });
                        }
                    }
                }
            );
        },

        onRefreshPlans: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;
            var oPage = this.byId("recoveryPlanningPage");
            if (oPage) oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ priority: this.getView().getModel("rec").getProperty("/priority") })
            })
            .then(function (res) { return res.json(); })
            .then(function (planSet) {
                var oModel = that.getView().getModel("rec");
                oModel.setProperty("/feasible_plans", planSet.feasible_plans || []);
                oModel.setProperty("/infeasible_plans", planSet.infeasible_plans || []);
                oModel.setProperty("/ai_briefing", planSet.ai_briefing);
                MessageToast.show("Recovery alternatives recalculated and ranked.");
            })
            .catch(function (err) {
                MessageBox.error(err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        onBackToCheckpoint1: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: sCaseId });
        },

        onProceedToExecution: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            this.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: sCaseId });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        }

    });
});
