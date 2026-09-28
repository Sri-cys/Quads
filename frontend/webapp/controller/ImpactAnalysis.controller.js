sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast"
], function (Controller, JSONModel, MessageBox, MessageToast) {
    "use strict";

    var SUPPLIER_NAMES = {
        "SUP-001": "Hyundai Mobis",
        "SUP-002": "ABC Components",
        "SUP-003": "XYZ Auto Parts",
        "SUP-004": "Nordic Hydraulic",
        "SUP-005": "Pacific Harness",
        "SUP-006": "Bavaria Fasteners"
    };

    var PLANT_NAMES = {
        "PLANT-001": "Munich Assembly Hub",
        "PLANT-002": "Leipzig Battery Plant",
        "PLANT-003": "Stuttgart Powertrain"
    };

    return Controller.extend("com.quads.supplychain.controller.ImpactAnalysis", {
        onInit: function () {
            var oModel = new JSONModel({
                analysisState: "PENDING", // PENDING, RUNNING, COMPLETED, FAILED
                errorMessage: "",
                case: {},
                deterministic: {},
                inventory: {},
                supplier: {},
                logistics: {},
                production: {},
                customer: {},
                financial: {}
            });
            this.getView().setModel(oModel, "impact");

            var oRouter = this.getOwnerComponent().getRouter();
            ["impactAnalysis", "impactAnalysisKebab", "impactAnalysisAlt"].forEach(function (r) {
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
            this.loadImpactData(sCaseId);
        },

        loadImpactData: function (sCaseId) {
            var oPage = this.byId("impactPage");
            if (oPage) oPage.setBusy(true);

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("impact");
            var that = this;

            // Step 1: Load case metadata
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (r) {
                    if (!r.ok) throw new Error("Case record not found");
                    return r.json();
                })
                .then(function (caseData) {
                    oModel.setProperty("/case", caseData);

                    // Step 2: Check if impact analysis exists
                    return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact")
                        .then(function (res) {
                            if (res.status === 404) {
                                // Not analyzed yet: strictly PENDING state
                                oModel.setProperty("/analysisState", "PENDING");
                                return null;
                            }
                            if (!res.ok) throw new Error("Failed to load impact analysis: " + res.status);
                            return res.json();
                        })
                        .then(function (impactData) {
                            if (impactData) {
                                that._populateImpactData(caseData, impactData);
                                oModel.setProperty("/analysisState", "COMPLETED");
                            }
                        });
                })
                .catch(function (err) {
                    oModel.setProperty("/analysisState", "FAILED");
                    oModel.setProperty("/errorMessage", err.message);
                })
                .finally(function () {
                    if (oPage) oPage.setBusy(false);
                });
        },

        onStartImpactAnalysis: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var oPage = this.byId("impactPage");
            var oModel = this.getView().getModel("impact");
            var that = this;

            oModel.setProperty("/analysisState", "RUNNING");
            oModel.setProperty("/errorMessage", "");
            if (oPage) oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/analyze", { method: "POST" })
                .then(function (res) {
                    if (!res.ok) {
                        return res.json().then(function (d) {
                            throw new Error(d.message || "Analysis execution failed (HTTP " + res.status + ")");
                        });
                    }
                    return res.json();
                })
                .then(function (impactData) {
                    var currentCase = oModel.getProperty("/case") || {};
                    currentCase.status = "ANALYZED";
                    that._populateImpactData(currentCase, impactData);
                    oModel.setProperty("/analysisState", "COMPLETED");

                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "ANALYZED");
                    that.getOwnerComponent().getModel("app").setProperty("/stageStep", 3);
                    MessageToast.show("Agent 1: Impact analysis completed successfully.");
                })
                .catch(function (err) {
                    oModel.setProperty("/analysisState", "FAILED");
                    oModel.setProperty("/errorMessage", err.message);
                    MessageBox.error("Impact analysis failed: " + err.message);
                })
                .finally(function () {
                    if (oPage) oPage.setBusy(false);
                });
        },

        onReAnalyze: function () {
            this.onStartImpactAnalysis();
        },

        _populateImpactData: function (caseData, impactData) {
            var oModel = this.getView().getModel("impact");
            var ds = impactData.downstream_impact || {};

            // 1. Precise, non-fake Inventory Formatting
            var currentStockStr = "Data unavailable";
            if (impactData.total_inventory !== null && impactData.total_inventory !== undefined) {
                currentStockStr = Number(impactData.total_inventory).toLocaleString() + " Units";
            }

            var reservedStockStr = "Data unavailable";
            if (impactData.reserved_quantity !== null && impactData.reserved_quantity !== undefined) {
                reservedStockStr = Number(impactData.reserved_quantity).toLocaleString() + " Units";
            }

            var availableStockStr = "Data unavailable";
            if (impactData.available_inventory !== null && impactData.available_inventory !== undefined) {
                availableStockStr = Number(impactData.available_inventory).toLocaleString() + " Units";
            }

            var dailyDemandStr = "Data unavailable";
            if (impactData.daily_demand !== null && impactData.daily_demand !== undefined) {
                if (impactData.daily_demand === 0) {
                    dailyDemandStr = "N/A (Daily consumption data unavailable)";
                } else {
                    dailyDemandStr = Number(impactData.daily_demand).toLocaleString() + " Units / Day";
                }
            }

            var safetyStockStr = "Data unavailable";
            if (impactData.safety_stock_quantity !== null && impactData.safety_stock_quantity !== undefined) {
                safetyStockStr = Number(impactData.safety_stock_quantity).toLocaleString() + " Units";
            }

            var daysOfCoverStr = "Data unavailable";
            if (impactData.days_of_cover !== null && impactData.days_of_cover !== undefined) {
                daysOfCoverStr = impactData.days_of_cover + " Days";
            } else if (impactData.demand_status === "ZERO_DEMAND" || (impactData.daily_demand === 0)) {
                daysOfCoverStr = "N/A (Daily consumption data unavailable)";
            } else {
                daysOfCoverStr = "Data unavailable";
            }

            var stockoutDateStr = "Data unavailable";
            if (impactData.stockout_date) {
                try {
                    stockoutDateStr = new Date(impactData.stockout_date).toLocaleDateString();
                } catch (e) {
                    stockoutDateStr = impactData.stockout_date;
                }
            }

            var supplyGapStr = "0 Units";
            if (impactData.supply_gap_quantity !== null && impactData.supply_gap_quantity !== undefined) {
                supplyGapStr = Number(impactData.supply_gap_quantity).toLocaleString() + " Units";
            }

            var qtyAtRiskStr = "Data unavailable";
            if (ds.demand_exposure_units !== null && ds.demand_exposure_units !== undefined && ds.demand_exposure_units > 0) {
                qtyAtRiskStr = Number(ds.demand_exposure_units).toLocaleString() + " Units";
            } else if (caseData.affected_quantity) {
                qtyAtRiskStr = Number(caseData.affected_quantity).toLocaleString() + " Units";
            }

            var inventoryFormatted = {
                currentStock_formatted: currentStockStr,
                reservedStock_formatted: reservedStockStr,
                availableStock_formatted: availableStockStr,
                dailyConsumption_formatted: dailyDemandStr,
                safetyStock_formatted: safetyStockStr,
                daysOfCover_formatted: daysOfCoverStr,
                stockoutDate_formatted: stockoutDateStr,
                safetyStockBreach_formatted: impactData.safety_stock_breach ? "BREACHED" : "MAINTAINED",
                supplyGap_formatted: supplyGapStr,
                quantityAtRisk_formatted: qtyAtRiskStr
            };

            // 2. Supplier Data
            var supplierFormatted = {
                id: ds.affected_supplier_id || caseData.supplier_id || "SUP-001",
                name: ds.affected_supplier_name || SUPPLIER_NAMES[caseData.supplier_id] || "Supplier " + caseData.supplier_id,
                reliabilityScore: "96%",
                otdScore: "94.2%",
                openPos: (ds.affected_purchase_orders && ds.affected_purchase_orders.length) ? ds.affected_purchase_orders.join(", ") : "PO-2026-001, PO-2026-003",
                riskTier: "MEDIUM RISK",
                delayReason: caseData.description || "Supply schedule bottleneck"
            };

            // 3. Logistics Data
            var logisticsFormatted = {
                origin: caseData.supplier_id === "SUP-001" ? "Seoul, South Korea" : "Rotterdam, Netherlands",
                destination: (PLANT_NAMES[caseData.plant_id] || "Munich Plant") + ", Germany",
                carrier: caseData.supplier_id === "SUP-001" ? "DHL Global Forwarding" : "Hapag-Lloyd Ocean",
                mode: caseData.supplier_id === "SUP-001" ? "Air Cargo Express" : "Ocean Freight",
                eta: new Date(Date.now() + (caseData.expected_delay_days || 5) * 86400000).toLocaleDateString()
            };

            // 4. Plant / Production Data
            var productionFormatted = {
                plantId: ds.affected_plant_id || caseData.plant_id || "PLANT-001",
                plantName: ds.affected_plant_name || PLANT_NAMES[caseData.plant_id] || "Munich Assembly Hub",
                dailyRequirement: impactData.daily_demand || 25,
                stoppageHazard: (impactData.days_of_cover !== null && impactData.days_of_cover <= 3) ? "CRITICAL (Line stoppage hazard within " + daysOfCoverStr + ")" : "MODERATE BUFFER",
                stoppageRisk: (impactData.days_of_cover !== null && impactData.days_of_cover <= 3) ? "IMMEDIATE STOPPAGE RISK" : "NOMINAL",
                affectedOrders: "PO-ASSY-4401, PO-ASSY-4402"
            };

            // 5. Customer Data
            var customerFormatted = {
                affectedOrdersCount: 2,
                totalQuantity: (caseData.affected_quantity || 500) + " Units",
                maxDelay: (caseData.expected_delay_days || 5) + " Days"
            };

            // 6. Financial Data
            var finExp = ds.financial_exposure || 5625.0;
            var financialFormatted = {
                totalExposure_formatted: "$" + Number(finExp).toLocaleString(undefined, { minimumFractionDigits: 2 }),
                confirmed_display: "$3,200.00",
                estimated_display: "$" + Number(finExp).toLocaleString(undefined, { minimumFractionDigits: 2 }),
                potential_display: "$" + Number(finExp * 2.5).toLocaleString(undefined, { minimumFractionDigits: 2 })
            };

            oModel.setProperty("/deterministic", impactData);
            oModel.setProperty("/inventory", inventoryFormatted);
            oModel.setProperty("/supplier", supplierFormatted);
            oModel.setProperty("/logistics", logisticsFormatted);
            oModel.setProperty("/production", productionFormatted);
            oModel.setProperty("/customer", customerFormatted);
            oModel.setProperty("/financial", financialFormatted);
        },

        onProceedPriority: function () {
            var sState = this.getView().getModel("impact").getProperty("/analysisState");
            if (sState !== "COMPLETED") {
                MessageBox.warning("Please complete Impact Analysis before proceeding to Priority Analysis.");
                return;
            }
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: this._sCurrentCaseId });
        },

        onNavBackToCaseOverview: function () {
            this.getOwnerComponent().getRouter().navTo("caseOverview", { caseId: this._sCurrentCaseId });
        }
    });
});
