sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast"
], function (Controller, JSONModel, MessageBox, MessageToast) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.Checkpoint1", {
        onInit: function () {
            var oModel = new JSONModel({
                case_id: "",
                status: "PENDING",
                severity: "",
                decision: null,
                decisionTimestamp: null,
                selectedPriority: "BALANCED",
                impact: {}
            });
            this.getView().setModel(oModel, "cp");

            var oRouter = this.getOwnerComponent().getRouter();
            ["checkpoint1", "checkpoint1Alt"].forEach(function (r) {
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
            this.loadCheckpointData(sCaseId);
        },

        loadCheckpointData: function (sCaseId) {
            var oPage = this.byId("checkpoint1Page");
            if (oPage) oPage.setBusy(true);

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("cp");
            var that = this;

            Promise.all([
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId).then(function (r) {
                    if (!r.ok) throw new Error("Case not found");
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact").then(function (r) {
                    if (r.status === 404) {
                        return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/analyze", { method: "POST" })
                            .then(function (res) { return res.json(); });
                    }
                    if (!r.ok) throw new Error("Impact analysis not found");
                    return r.json();
                })
            ])
            .then(function (results) {
                var caseData = results[0] || {};
                var impactData = results[1] || {};

                var doc = impactData.days_of_cover !== undefined ? impactData.days_of_cover : 5.0;
                var stockout = impactData.stockout_date ? (new Date(impactData.stockout_date).toLocaleDateString()) : "2026-09-29";
                var gap = impactData.supply_gap_quantity !== undefined ? impactData.supply_gap_quantity : 0;
                var sev = impactData.severity || caseData.severity || "CRITICAL";

                oModel.setData({
                    case_id: sCaseId,
                    status: caseData.status,
                    severity: sev,
                    decision: caseData.checkpoint1_decision,
                    decisionTimestamp: caseData.checkpoint1_timestamp,
                    selectedPriority: caseData.checkpoint1_decision || "BALANCED",
                    impact: {
                        days_of_cover: doc,
                        stockout_date: stockout,
                        supply_gap_quantity: gap,
                        severity: sev
                    }
                });
            })
            .catch(function (err) {
                MessageBox.error("Failed to load Checkpoint 1 details: " + err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        onSelectOption: function (oEvent) {
            var oCard = oEvent.getSource();
            var aCustom = oCard.getCustomData();
            var sPriority = "BALANCED";
            for (var i = 0; i < aCustom.length; i++) {
                if (aCustom[i].getKey() === "priority") {
                    sPriority = aCustom[i].getValue();
                    break;
                }
            }
            this.getView().getModel("cp").setProperty("/selectedPriority", sPriority);
        },

        onSelectTime: function () {
            this.getView().getModel("cp").setProperty("/selectedPriority", "TIME");
        },

        onSelectCost: function () {
            this.getView().getModel("cp").setProperty("/selectedPriority", "COST");
        },

        onSelectRisk: function () {
            this.getView().getModel("cp").setProperty("/selectedPriority", "RISK");
        },

        onSelectBalanced: function () {
            this.getView().getModel("cp").setProperty("/selectedPriority", "BALANCED");
        },

        onBackToCases: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onBackToImpact: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            this.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
        },

        onRadioSelect: function (oEvent) {
            var sPriority = oEvent.getSource().getText();
            this.getView().getModel("cp").setProperty("/selectedPriority", sPriority);
        },

        onApproveDecision: function () {
            var sPriority = this.getView().getModel("cp").getProperty("/selectedPriority") || "BALANCED";
            var that = this;

            MessageBox.confirm(
                "Approve Human Checkpoint 1 with recovery objective '" + sPriority + "'?\n\nThis records the governance decision and completes Phase 1 analysis.",
                {
                    title: "Confirm Recovery Objective",
                    actions: [MessageBox.Action.OK, MessageBox.Action.CANCEL],
                    emphasizedAction: MessageBox.Action.OK,
                    onClose: function (sAction) {
                        if (sAction === MessageBox.Action.OK) {
                            that._submitPriority(sPriority);
                        }
                    }
                }
            );
        },

        _submitPriority: function (sPriority) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var oPage = this.byId("checkpoint1Page");
            var oModel = this.getView().getModel("cp");
            var that = this;

            oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/checkpoint1", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ priority: sPriority })
            })
            .then(function (res) {
                return res.json().then(function (data) {
                    if (!res.ok) {
                        throw new Error(data.message || "Failed to submit checkpoint decision");
                    }
                    return data;
                });
            })
            .then(function (resp) {
                oModel.setProperty("/status", "CHECKPOINT_APPROVED");
                oModel.setProperty("/decision", sPriority);
                oModel.setProperty("/decisionTimestamp", new Date().toISOString());

                MessageToast.show("Checkpoint 1 approved (" + sPriority + "). Proceeding to Recovery Planning...");
                
                // Immediately transition to Recovery Planning stage
                that.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
                that.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: sCaseId });
            })
            .catch(function (err) {
                MessageBox.error(err.message);
            })
            .finally(function () {
                oPage.setBusy(false);
            });
        },

        onProceedToPhase2: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: sCaseId });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        formatDate: function (sIso) {
            if (!sIso) return "N/A";
            try {
                var d = new Date(sIso);
                return d.toLocaleString();
            } catch (e) {
                return sIso;
            }
        }
    });
});
