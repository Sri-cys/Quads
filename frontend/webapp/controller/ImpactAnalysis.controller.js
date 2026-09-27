sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast"
], function (Controller, JSONModel, MessageBox, MessageToast) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.ImpactAnalysis", {
        onInit: function () {
            var oModel = new JSONModel({});
            this.getView().setModel(oModel, "impact");

            var oRouter = this.getOwnerComponent().getRouter();
            ["impactAnalysis", "impactAnalysisAlt"].forEach(function (r) {
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
            this.loadImpactData(sCaseId);
        },

        loadImpactData: function (sCaseId) {
            var oPage = this.byId("impactPage");
            if (oPage) oPage.setBusy(true);

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("impact");

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
                    if (!r.ok) throw new Error("Failed to load impact analysis");
                    return r.json();
                })
            ])
            .then(function (results) {
                var caseData = results[0];
                var impactData = results[1];

                var ds = impactData.downstream_impact || {};
                var ai = impactData.ai_explanation || {};

                impactData.case = caseData;
                impactData.deterministic = {
                    days_of_cover: impactData.days_of_cover !== undefined ? impactData.days_of_cover : (caseData.expected_delay_days || 2.0),
                    stockout_date_formatted: impactData.stockout_date ? new Date(impactData.stockout_date).toLocaleDateString() : "2026-09-29",
                    supply_gap_quantity: impactData.supply_gap_quantity !== undefined ? impactData.supply_gap_quantity : 0,
                    severity: impactData.severity || "CRITICAL",
                    available_inventory: impactData.available_inventory !== undefined ? impactData.available_inventory : 50,
                    daily_demand: impactData.daily_demand !== undefined ? impactData.daily_demand : 25,
                    safety_stock_level: impactData.safety_stock_quantity !== undefined ? impactData.safety_stock_quantity : 100,
                    safety_stock_breached: impactData.safety_stock_breach !== undefined ? impactData.safety_stock_breach : true
                };

                impactData.downstream = {
                    affected_supplier: {
                        name: ds.affected_supplier_name || caseData.supplier_id || "Hyundai Mobis",
                        id: ds.affected_supplier_id || caseData.supplier_id || "SUP-001"
                    },
                    affected_material: {
                        name: ds.affected_material_name || caseData.material_id || "Semiconductor MCU-32",
                        id: ds.affected_material_id || caseData.material_id || "MAT-001"
                    },
                    affected_plant: {
                        name: ds.affected_plant_name || caseData.plant_id || "Munich Assembly Hub",
                        id: ds.affected_plant_id || caseData.plant_id || "PLANT-001"
                    },
                    production_risk: (ds.production_risk_indicators && ds.production_risk_indicators[0]) ? ds.production_risk_indicators[0] : "Buffer Depletion Hazard",
                    financial_exposure_display: ds.financial_exposure ? "$" + Number(ds.financial_exposure).toLocaleString() : "$5,625.00",
                    affected_pos: ds.affected_purchase_orders || ["PO-2026-001"]
                };

                impactData.ai = {
                    situation: ai.situation || "Supplier shipment delayed by 5 days due to packaging bottleneck. Replenishment postponed.",
                    impact: ai.impact || "Inventory buffer drops to 2 days of cover, breaching safety stock threshold within 48 hours.",
                    risks: ai.key_risks || "Assembly line stoppage risk at Munich plant. Production halts unless expedited or rerouted.",
                    recommendation: ai.recommendation || "Immediate recovery orchestration required at Human Checkpoint 1 to select recovery objective."
                };

                oModel.setData(impactData);
            })
            .catch(function (err) {
                MessageBox.error("Error loading impact analysis for " + sCaseId + ": " + err.message);
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
            });
        },

        onReAnalyze: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var oPage = this.byId("impactPage");
            var oModel = this.getView().getModel("impact");
            var that = this;

            if (oPage) oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/analyze", { method: "POST" })
                .then(function (res) {
                    if (!res.ok) throw new Error("Analysis failed: " + res.status);
                    return res.json();
                })
                .then(function (data) {
                    var currentCase = oModel.getProperty("/case");
                    data.case = currentCase;
                    oModel.setData(data);
                    MessageToast.show("Deterministic impact recalculation complete.");
                })
                .catch(function (err) {
                    MessageBox.error("Re-analysis failed: " + err.message);
                })
                .finally(function () {
                    if (oPage) oPage.setBusy(false);
                });
        },

        onProceedCheckpoint: function () {
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: this._sCurrentCaseId });
        },

        onProceedToCheckpoint: function () {
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: this._sCurrentCaseId });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        formatDateOnly: function (sIso) {
            if (!sIso) return "None (Protected)";
            try {
                return new Date(sIso).toLocaleDateString();
            } catch (e) {
                return sIso.substring(0, 10);
            }
        },

        formatCurrency: function (num) {
            if (num === null || num === undefined) return "$0.00";
            return "$" + Number(num).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    });
});
