sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageBox, MessageToast, WorkflowNavHelper) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.Constraints", {
        onInit: function () {
            var oModel = new JSONModel({
                state: "RUNNING", // RUNNING, COMPLETED, FAILED
                errorMessage: "",
                case_id: "",
                priority: "BALANCED",
                cost: {},
                risk: {},
                contract: {},
                constraints: {}
            });
            this.getView().setModel(oModel, "con");

            var oRouter = this.getOwnerComponent().getRouter();
            ["constraints", "constraintsAlt"].forEach(function (r) {
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
                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, 4);
            }.bind(this));
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadConstraintsData(sCaseId);
        },

        loadConstraintsData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("con");
            var that = this;

            oModel.setProperty("/state", "RUNNING");
            oModel.setProperty("/errorMessage", "");

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (r) {
                    if (!r.ok) throw new Error("Case record not found");
                    return r.json();
                })
                .then(function (caseData) {
                    // Route guard: Priority must be saved before Constraints can run
                    if (!caseData.checkpoint1_decision && caseData.status !== "CHECKPOINT_APPROVED" && caseData.status !== "RECOVERY_APPROVED" && caseData.status !== "RESOLVED") {
                        MessageBox.warning(
                            "Human Checkpoint 1 priority has not been saved for " + sCaseId + ".\n\nPlease save recovery priority before proceeding to Stage 4 Constraints.",
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

                    // Cost Analysis
                    var costData = {
                        procurement: "$22,500.00 (Standard PO)",
                        freight: "$3,400.00 (Confirmed)",
                        premiumFreight: "$7,200.00 (Expedited Air Option)",
                        penalties: "$12,500.00 (Tier 1 OEM Delay Exposure)",
                        totalExposure: "$25,900.00 (Base Scenario)"
                    };

                    // Risk Analysis
                    var riskData = {
                        supplierRisk: "LOW (96% Reliability Precedent)",
                        logisticsRisk: "MEDIUM (Air corridor open, ocean congested)",
                        productionRisk: "HIGH (Munich Line 2 buffer depleted)",
                        customerRisk: "HIGH (SLA penalty risk within 48h)",
                        overallRisk: "HIGH OVERALL DISRUPTION RISK"
                    };

                    // Contract Clauses
                    var contractData = {
                        agreementId: "CTR-2024-MOBIS",
                        emergencyClause: "Permitted (Clause 11.4 Authorized)",
                        costSharing: "25% Supplier Expedite Claimable",
                        penaltyTerms: "Active SLA Tier 1 ($2,500/day after Day 5)",
                        qualityTerms: "ISO-26262 ASIL-B Mandatory"
                    };

                    // Hard & Soft Constraints
                    var constraintsData = {
                        hardSafetyStock: ">= 100 Units Buffer Required",
                        hardMaxLeadTime: "<= 5 Days Arrival (Hard Limit)",
                        hardMaxCost: "<= $35,000 Total Budget Limit",
                        softCarrierPref: "DHL Aviation or DB Schenker",
                        softHistoricalPref: "Sister Plant Transfer Preferred"
                    };

                    oModel.setData({
                        state: "COMPLETED",
                        errorMessage: "",
                        case_id: sCaseId,
                        priority: sPriority,
                        cost: costData,
                        risk: riskData,
                        contract: contractData,
                        constraints: constraintsData
                    });

                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "AGENT2_COMPLETED");
                    that.getOwnerComponent().getModel("app").setProperty("/stageStep", 5);
                })
                .catch(function (err) {
                    oModel.setProperty("/state", "FAILED");
                    oModel.setProperty("/errorMessage", err.message);
                });
        },

        onRunConstraints: function () {
            this.loadConstraintsData(this._sCurrentCaseId);
        },

        onProceedToRecoveryPlanning: function () {
            WorkflowNavHelper.markStageCompleted(this._sCurrentCaseId, 4);
                    WorkflowNavHelper.setStepperState(sCaseId || this._sCurrentCaseId, 4);
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: this._sCurrentCaseId });
        },

        onBackToPriority: function () {
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: this._sCurrentCaseId });
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        }
    });
});
