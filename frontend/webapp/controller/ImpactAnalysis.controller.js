sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageBox, MessageToast, WorkflowNavHelper) {
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
        formatter: {
            formatExecLine1: function(delay, revised, original) {
                if (delay === undefined || delay === null) return "—";
                return "The supplier shipment is delayed by " + delay + " days and is now expected on " + (revised || "—") + " instead of " + (original || "—") + ".";
            },
            formatExecLine2: function(doc) {
                if (doc === undefined || doc === null) return "—";
                return "The plant has " + doc + " days of stock remaining, so production may be affected if the material does not arrive on time.";
            },
            formatExecLine3: function(prodOrdersStr, custOrdersCount) {
                if (prodOrdersStr === undefined || prodOrdersStr === null) return "—";
                var prodCount = 0;
                if (prodOrdersStr) {
                    prodCount = prodOrdersStr.split(",").length;
                }
                var custCount = custOrdersCount || 0;
                return prodCount + " critical production orders and " + custCount + " customer deliveries may be affected by the delay.";
            },
            formatExecLine4: function(exposure) {
                if (!exposure) return "—";
                return "The current gross financial exposure is " + exposure + ".";
            },
            
            formatSeverityBadge: function(severity) {
                if (!severity) return "—";
                var s = String(severity).toUpperCase();
                if (s === "CRITICAL") return "CRITICAL RISK";
                if (s === "HIGH") return "HIGH RISK";
                if (s === "MEDIUM") return "MODERATE RISK";
                if (s === "LOW") return "LOW RISK";
                return s + " RISK";
            },
            formatSeverityColor: function(severity) {
                if (!severity) return "green";
                var s = String(severity).toUpperCase();
                if (s === "CRITICAL" || s === "HIGH") return "red";
                if (s === "MEDIUM") return "amber";
                return "green";
            },
            formatTimelineDate: function(dateStr) {
                if (!dateStr) return "—";
                var d = new Date(dateStr);
                if (isNaN(d.getTime())) return "—";
                var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                var day = String(d.getDate()).padStart(2, "0");
                return day + " " + months[d.getMonth()];
            },
            formatDelayDays: function(expected, revised) {
                if (!expected || !revised) return "0 days delay";
                var d1 = new Date(expected).getTime();
                var d2 = new Date(revised).getTime();
                if (isNaN(d1) || isNaN(d2)) return "0 days delay";
                var diff = d2 - d1;
                var days = Math.round(diff / 86400000);
                return days + " days delay";
            },
            formatDelayVisible: function(expected, revised) {
                if (!expected || !revised) return false;
                var d1 = new Date(expected).getTime();
                var d2 = new Date(revised).getTime();
                if (isNaN(d1) || isNaN(d2)) return false;
                return d2 > d1;
            },
            formatProductionHighlight: function(prodOrdersStr) {
                if (!prodOrdersStr) return "0 Orders Affected";
                return prodOrdersStr.split(",").length + " Orders Affected";
            },
            formatProductionSubtext: function(breach, daysOfCover) {
                var doc = daysOfCover !== null && daysOfCover !== undefined ? daysOfCover : "—";
                if (breach === "BREACHED" || breach === true) {
                    return "Safety stock breach · Line stoppage hazard in " + doc + " Days";
                }
                return "Line stoppage hazard in " + doc + " Days";
            },
            formatInventoryBufferColor: function(doc, delay) {
                if (doc === null || doc === undefined) return "green";
                var delayNum = delay || 0;
                if (doc < delayNum || doc <= 3) return "red";
                return "green";
            },
            formatOperationalStatus: function(doc) {
                if (doc === null || doc === undefined) return "Normal";
                if (doc <= 3) return "Line Stoppage Hazard";
                return "Normal";
            },
            formatOperationalStatusColor: function(doc) {
                if (doc === null || doc === undefined) return "green";
                if (doc <= 3) return "red";
                return "green";
            },
            formatOperationalStatusIcon: function(doc) {
                if (doc === null || doc === undefined) return "sap-icon://sys-enter-2";
                if (doc <= 3) return "sap-icon://warning2";
                return "sap-icon://sys-enter-2";
            },
            
            formatSlaBadgeText: function(customerDelay) {
                if (customerDelay && parseInt(customerDelay, 10) > 0) return "SLA AT RISK";
                return "ON TRACK";
            },
            formatSlaBadgeColor: function(customerDelay) {
                if (customerDelay && parseInt(customerDelay, 10) > 0) return "amber";
                return "green";
            },
            formatCustomerHighlight: function(customerDelay) {
                if (customerDelay && parseInt(customerDelay, 10) > 0) {
                    return "+" + parseInt(customerDelay, 10) + " days delay";
                }
                return "No Delay";
            },
            formatSlaRiskText: function(customerDelay) {
                if (customerDelay && parseInt(customerDelay, 10) > 0) return "Late Delivery Clause Triggered";
                return "No clause triggered";
            },
            formatSlaRiskColor: function(customerDelay) {
                if (customerDelay && parseInt(customerDelay, 10) > 0) return "amber";
                return ""; 
            },
            formatCustomerETA: function(expectedEta, customerDelay) {
                if (!expectedEta) return "—";
                var cd = parseInt(customerDelay, 10) || 0;
                if (cd > 0) {
                    return expectedEta + " (+" + cd + "d variance)";
                }
                return expectedEta + " (On Track)";
            },
            formatCustomerETAColor: function(customerDelay) {
                if (customerDelay && parseInt(customerDelay, 10) > 0) return "amber";
                return ""; 
            },
            
            formatFinancialHighlight: function(prodLossStr, custPenaltyStr) {
                if (!prodLossStr && !custPenaltyStr) return "—";
                var v1 = prodLossStr ? parseFloat(prodLossStr.replace(/[^0-9.-]+/g, "")) : 0;
                var v2 = custPenaltyStr ? parseFloat(custPenaltyStr.replace(/[^0-9.-]+/g, "")) : 0;
                return "$" + (v1 + v2).toLocaleString(undefined, { minimumFractionDigits: 2 });
            },
            formatTotalHighlight: function(totalExposure) {
                return totalExposure || "—";
            }
        },

        onInit: function () {
            var oModel = new JSONModel({
                analysisState: "PENDING", // PENDING, RUNNING, COMPLETED, FAILED
                errorMessage: "",
                case: {},
                steps: [
                    { id: "inventory", label: "Inventory analysis", status: "PENDING" },
                    { id: "supplier", label: "Supplier analysis", status: "PENDING" },
                    { id: "logistics", label: "Logistics analysis", status: "PENDING" },
                    { id: "production", label: "Production analysis", status: "PENDING" },
                    { id: "customer", label: "Customer analysis", status: "PENDING" },
                    { id: "financial", label: "Financial exposure", status: "PENDING" },
                    { id: "overall", label: "End-to-end propagation", status: "PENDING" }
                ],
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
            if (this._pollTimer) {
                clearInterval(this._pollTimer);
                this._pollTimer = null;
            }
            var sCaseId = oEvent.getParameter("arguments").caseId;
            if (!sCaseId) {
                sCaseId = this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            }
            this._sCurrentCaseId = sCaseId;
            sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {
                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, 2);
            }.bind(this));
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadImpactData(sCaseId);
        },

        loadImpactData: function (sCaseId) {
            var oPage = this.byId("impactPage");
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("impact");
            var that = this;

            // Fetch current status first
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact/status")
                .then(function (r) {
                    if (!r.ok) throw new Error("Case status not found (HTTP " + r.status + ")");
                    return r.json();
                })
                .then(function (statusData) {
                    var sStatus = statusData.status || "IMPACT_ANALYSIS_PENDING";
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", sStatus);

                    if (sStatus === "IMPACT_ANALYSIS_RUNNING") {
                        oModel.setProperty("/analysisState", "RUNNING");
                        that._updateStepsFromProgress(statusData.steps_progress);
                        that._startProgressPolling(sCaseId);
                    } else if (sStatus === "IMPACT_ANALYSIS_COMPLETED" || sStatus === "ANALYZED" || sStatus === "PRIORITY_PENDING" || sStatus === "PRIORITY_SAVED" || sStatus === "AGENT2_RUNNING" || sStatus === "AGENT2_COMPLETED" || sStatus === "AGENT3_RUNNING" || sStatus === "DECISION_PENDING" || sStatus === "EXECUTION" || sStatus === "RESOLVED") {
                        // Load full impact data
                        that._fetchCompletedImpact(sCaseId);
                    } else if (sStatus === "IMPACT_ANALYSIS_FAILED") {
                        oModel.setProperty("/analysisState", "FAILED");
                        oModel.setProperty("/errorMessage", statusData.last_error || "Impact analysis failed.");
                    } else {
                        oModel.setProperty("/analysisState", "PENDING");
                    }
                })
                .catch(function (err) {
                    oModel.setProperty("/analysisState", "FAILED");
                    oModel.setProperty("/errorMessage", err.message);
                });
        },

        _updateStepsFromProgress: function (stepsProgress) {
            stepsProgress = stepsProgress || {};
            var aSteps = [
                { id: "inventory", label: "Inventory analysis", status: stepsProgress.inventory || "PENDING" },
                { id: "supplier", label: "Supplier analysis", status: stepsProgress.supplier || "PENDING" },
                { id: "logistics", label: "Logistics analysis", status: stepsProgress.logistics || "PENDING" },
                { id: "production", label: "Production analysis", status: stepsProgress.production || "PENDING" },
                { id: "customer", label: "Customer analysis", status: stepsProgress.customer || "PENDING" },
                { id: "financial", label: "Financial exposure", status: stepsProgress.financial || "PENDING" },
                { id: "overall", label: "End-to-end propagation", status: stepsProgress.overall || "PENDING" }
            ];
            this.getView().getModel("impact").setProperty("/steps", aSteps);
        },

        _startProgressPolling: function (sCaseId) {
            var that = this;
            if (this._pollTimer) clearInterval(this._pollTimer);
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("impact");

            this._pollTimer = setInterval(function () {
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact/status")
                    .then(function (r) { return r.json(); })
                    .then(function (statusData) {
                        var sStatus = statusData.status;
                        that._updateStepsFromProgress(statusData.steps_progress);

                        if (sStatus === "IMPACT_ANALYSIS_COMPLETED" || sStatus === "ANALYZED" || sStatus === "PRIORITY_PENDING") {
                            clearInterval(that._pollTimer);
                            that._pollTimer = null;
                            that._fetchCompletedImpact(sCaseId);
                        } else if (sStatus === "IMPACT_ANALYSIS_FAILED") {
                            clearInterval(that._pollTimer);
                            that._pollTimer = null;
                            oModel.setProperty("/analysisState", "FAILED");
                            oModel.setProperty("/errorMessage", statusData.last_error || "Analysis execution failed.");
                        }
                    })
                    .catch(function (e) {
                        console.warn("Polling error:", e);
                    });
            }, 400);
        },

        _fetchCompletedImpact: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("impact");
            var that = this;

            Promise.all([
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId).then(function (r) { return r.json(); }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact").then(function (r) {
                    if (!r.ok) throw new Error("Impact results not available yet (HTTP " + r.status + ")");
                    return r.json();
                })
            ])
            .then(function (results) {
                var caseData = results[0];
                var impactData = results[1];
                oModel.setProperty("/case", caseData);
                that._populateImpactData(caseData, impactData);
                oModel.setProperty("/analysisState", "COMPLETED");
                that.getOwnerComponent().getModel("app").setProperty("/caseStatus", caseData.status);
            })
            .catch(function (err) {
                oModel.setProperty("/analysisState", "FAILED");
                oModel.setProperty("/errorMessage", err.message);
            });
        },

        onRetryImpactAnalysis: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var oModel = this.getView().getModel("impact");
            var that = this;

            oModel.setProperty("/analysisState", "RUNNING");
            oModel.setProperty("/errorMessage", "");

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact/retry", { method: "POST" })
                .then(function (res) {
                    if (!res.ok) throw new Error("Retry failed (HTTP " + res.status + ")");
                    return res.json();
                })
                .then(function () {
                    that._startProgressPolling(sCaseId);
                })
                .catch(function (err) {
                    oModel.setProperty("/analysisState", "FAILED");
                    oModel.setProperty("/errorMessage", err.message);
                });
        },

        _populateImpactData: function (caseData, impactData) {
            var oModel = this.getView().getModel("impact");
            var ds = impactData.downstream_impact || {};

            var dDetected = caseData.detected_at ? new Date(caseData.detected_at) : new Date();
            var dExpDelivery = new Date(dDetected.getTime() + 2 * 86400000);
            var delayDays = caseData.expected_delay_days || 0;
            var dCurrentEta = new Date(dExpDelivery.getTime() + (delayDays * 86400000));
            caseData.expected_delivery_date = dExpDelivery.toISOString();
            caseData.current_eta = dCurrentEta.toISOString();

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
                reliabilityScore: caseData.supplier_reliability || "96%",
                otdScore: caseData.otd || "94.2%",
                openPos: caseData.open_po || ((ds.affected_purchase_orders && ds.affected_purchase_orders.length) ? ds.affected_purchase_orders.join(", ") : "PO-2026-001, PO-2026-003"),
                riskTier: caseData.supplier_risk || "MEDIUM RISK",
                delayReason: caseData.description || "Supply schedule bottleneck"
            };

            // 3. Logistics Data
            var logisticsFormatted = {
                origin: caseData.origin || (caseData.supplier_id === "SUP-001" ? "Seoul, South Korea" : (caseData.supplier_id === "SUP-003" ? "Rotterdam, Netherlands" : "Hamburg, Germany")),
                destination: caseData.destination || ((PLANT_NAMES[caseData.plant_id] || "Munich Plant") + ", Germany"),
                carrier: caseData.carrier || (caseData.supplier_id === "SUP-001" ? "DHL Global Forwarding" : (caseData.supplier_id === "SUP-003" ? "Hapag-Lloyd Ocean" : "DB Schenker Logistics")),
                mode: caseData.transport_mode || (caseData.supplier_id === "SUP-001" ? "Air Cargo Express" : (caseData.supplier_id === "SUP-003" ? "Ocean Container Freight" : "Road Freight")),
                eta: caseData.current_eta || new Date(Date.now() + (caseData.expected_delay_days || 5) * 86400000).toLocaleDateString()
            };

            // 4. Plant / Production Data
            var productionFormatted = {
                plantId: ds.affected_plant_id || caseData.plant_id || "PLANT-001",
                plantName: ds.affected_plant_name || PLANT_NAMES[caseData.plant_id] || "Munich Assembly Hub",
                dailyRequirement: caseData.material_requirement || impactData.daily_demand || 25,
                stoppageHazard: caseData.production_interruption_risk || ((impactData.days_of_cover !== null && impactData.days_of_cover <= 3) ? "CRITICAL (Line stoppage hazard within " + daysOfCoverStr + ")" : "MODERATE BUFFER"),
                stoppageRisk: caseData.production_interruption_risk || ((impactData.days_of_cover !== null && impactData.days_of_cover <= 3) ? "IMMEDIATE STOPPAGE RISK" : "NOMINAL"),
                affectedOrders: caseData.production_orders_affected || "PO-ASSY-4401, PO-ASSY-4402"
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
            
            console.log("[TIMELINE] caseData.expected_delivery_date raw value:", caseData.expected_delivery_date, "type:", typeof caseData.expected_delivery_date);
            console.log("[TIMELINE] caseData.current_eta raw value:", caseData.current_eta, "type:", typeof caseData.current_eta);
            console.log("[TIMELINE] impactData.stockout_date raw value:", impactData.stockout_date, "type:", typeof impactData.stockout_date);
            console.log("[TIMELINE] caseData.expected_delay_days raw value:", caseData.expected_delay_days, "type:", typeof caseData.expected_delay_days);
            console.log("[TIMELINE] Formatter output for expected_delivery_date (none used currently in UI): N/A");
            console.log("[TIMELINE] Binding path for Expected Delivery (Node 6): {impact>/case/expected_delivery_date}");
            console.log("[TIMELINE] Binding path for Revised Delivery (Node 5): {impact>/inventory/stockoutDate_formatted}");
            
        },

        onProceedPriority: function () {
            var sCaseId = this._sCurrentCaseId;
            var that = this;

            // Stage 2 already done → pure navigation, no backend call
            if (WorkflowNavHelper.getCompletedStage(sCaseId) >= 2) {
                that.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: sCaseId });
                return;
            }

            // Stage not yet complete: analysis must be finished first
            var sState = this.getView().getModel("impact").getProperty("/analysisState");
            if (sState !== "COMPLETED") {
                MessageBox.warning("Please wait for Impact Analysis to complete before proceeding.");
                return;
            }

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact/proceed", { method: "POST" })
                .then(function () {
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "PRIORITY_PENDING");
                    WorkflowNavHelper.completeStage(sCaseId, 2, 2);
                    that.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: sCaseId });
                })
                .catch(function () {
                    // Proceed anyway (backend may already be in this state)
                    WorkflowNavHelper.completeStage(sCaseId, 2, 2);
                    that.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: sCaseId });
                });
        },

        onNavBackToCaseOverview: function () {
            this.getOwnerComponent().getRouter().navTo("caseOverview", { caseId: this._sCurrentCaseId });
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        }
    });
});
