sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast"
], function (Controller, JSONModel, MessageBox, MessageToast) {
    "use strict";

    var PRIORITY_CARDS = ["Time", "Cost", "Stock", "Risk", "Customer", "Balanced"];

    return Controller.extend("com.quads.supplychain.controller.Checkpoint1", {
        onInit: function () {
            var oModel = new JSONModel({
                case_id: "",
                status: "PENDING",
                severity: "",
                selectedPriority: "BALANCED",
                prioritySaved: false,
                impact: {
                    days_of_cover_display: "2.0 Days",
                    stockout_date_display: "2026-09-29",
                    supply_gap_display: "0 Units",
                    severity: "CRITICAL"
                }
            });
            this.getView().setModel(oModel, "cp");

            this.getView().addEventDelegate({
                onAfterRendering: function () {
                    var that = this;
                    var sPriority = this.getView().getModel("cp").getProperty("/selectedPriority") || "BALANCED";
                    this._updateCardSelection(sPriority);

                    // Attach click handlers to cards
                    PRIORITY_CARDS.forEach(function (name) {
                        var oCard = that.byId("card" + name);
                        if (oCard) {
                            var domRef = oCard.getDomRef();
                            if (domRef) {
                                domRef.onclick = function () {
                                    that.setSelectedPriority(name.toUpperCase());
                                };
                            }
                        }
                    });
                }
            }, this);

            var oRouter = this.getOwnerComponent().getRouter();
            ["checkpoint1", "checkpoint1Kebab", "checkpoint1Alt"].forEach(function (r) {
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
                    if (r.status === 404) return null;
                    if (!r.ok) throw new Error("Impact analysis not found");
                    return r.json();
                })
            ])
            .then(function (results) {
                var caseData = results[0] || {};
                var impactData = results[1];

                // Route guard: Impact Analysis must be completed first
                if (!impactData && caseData.status !== "ANALYZED" && caseData.status !== "CHECKPOINT_APPROVED" && caseData.status !== "RECOVERY_APPROVED" && caseData.status !== "RESOLVED") {
                    MessageBox.warning(
                        "Impact Analysis has not been performed yet for " + sCaseId + ".\n\nPlease complete Stage 2 before setting recovery priority.",
                        {
                            title: "Workflow Stage Locked",
                            onClose: function () {
                                that.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
                            }
                        }
                    );
                    return;
                }

                var docStr = "Data unavailable";
                if (impactData && impactData.days_of_cover !== null && impactData.days_of_cover !== undefined) {
                    docStr = impactData.days_of_cover + " Days";
                } else if (impactData && (impactData.demand_status === "ZERO_DEMAND" || impactData.daily_demand === 0)) {
                    docStr = "N/A (Daily consumption data unavailable)";
                }

                var stockoutStr = "Data unavailable";
                if (impactData && impactData.stockout_date) {
                    try {
                        stockoutStr = new Date(impactData.stockout_date).toLocaleDateString();
                    } catch (e) {
                        stockoutStr = impactData.stockout_date;
                    }
                }

                var gapStr = "0 Units";
                if (impactData && impactData.supply_gap_quantity !== null && impactData.supply_gap_quantity !== undefined) {
                    gapStr = impactData.supply_gap_quantity.toLocaleString() + " Units";
                }

                var sev = (impactData && impactData.severity) || caseData.severity || "CRITICAL";
                var bAlreadySaved = !!caseData.checkpoint1_decision;
                var sChosen = caseData.checkpoint1_decision || "BALANCED";

                oModel.setData({
                    case_id: sCaseId,
                    status: caseData.status,
                    severity: sev,
                    selectedPriority: sChosen,
                    prioritySaved: bAlreadySaved,
                    impact: {
                        days_of_cover_display: docStr,
                        stockout_date_display: stockoutStr,
                        supply_gap_display: gapStr,
                        severity: sev
                    }
                });

                that.setSelectedPriority(sChosen);
            })
            .catch(function (err) {
                MessageBox.error("Failed to load Checkpoint 1: " + err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        setSelectedPriority: function (sPriority) {
            this.getView().getModel("cp").setProperty("/selectedPriority", sPriority);
            this._updateCardSelection(sPriority);
        },

        _updateCardSelection: function (sPriority) {
            var that = this;
            PRIORITY_CARDS.forEach(function (name) {
                var oCard = that.byId("card" + name);
                if (oCard) {
                    var bSelected = (name.toUpperCase() === sPriority);
                    oCard.toggleStyleClass("sapChoiceSelected", bSelected);
                }
            });
        },

        onSelectTime:     function () { this.setSelectedPriority("TIME"); },
        onSelectCost:     function () { this.setSelectedPriority("COST"); },
        onSelectStock:    function () { this.setSelectedPriority("STOCK"); },
        onSelectRisk:     function () { this.setSelectedPriority("RISK"); },
        onSelectCustomer: function () { this.setSelectedPriority("CUSTOMER"); },
        onSelectBalanced: function () { this.setSelectedPriority("BALANCED"); },

        onSavePriority: function () {
            var sPriority = this.getView().getModel("cp").getProperty("/selectedPriority") || "BALANCED";
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
                if (res.status === 409) {
                    // Already saved previously, treated as confirmed
                    return res.json().then(function () {
                        return { status: "CHECKPOINT_APPROVED", priority: sPriority };
                    });
                }
                if (!res.ok) {
                    return res.json().then(function (data) {
                        throw new Error(data.message || "Failed to persist priority");
                    });
                }
                return res.json();
            })
            .then(function () {
                oModel.setProperty("/prioritySaved", true);
                that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "CHECKPOINT_APPROVED");
                that.getOwnerComponent().getModel("app").setProperty("/stageStep", 4);
                MessageToast.show("Priority '" + sPriority + "' saved successfully. Stage 4: Constraints is unlocked.");
            })
            .catch(function (err) {
                MessageBox.error("Priority persistence failed: " + err.message);
            })
            .finally(function () {
                oPage.setBusy(false);
            });
        },

        onProceedToConstraints: function () {
            var bSaved = this.getView().getModel("cp").getProperty("/prioritySaved");
            if (!bSaved) {
                MessageBox.warning("Please click 'SAVE PRIORITY' before proceeding to Constraints.");
                return;
            }
            this.getOwnerComponent().getRouter().navTo("constraints", { caseId: this._sCurrentCaseId });
        },

        onBackToImpact: function () {
            this.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: this._sCurrentCaseId });
        }
    });
});
