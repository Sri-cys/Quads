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

    var MATERIAL_NAMES = {
        "MAT-001": "Semiconductor MCU-32",
        "MAT-002": "Lithium Battery Cell 100Ah",
        "MAT-003": "Rotary Encoder Sensor",
        "MAT-004": "Hydraulic Actuator Pump",
        "MAT-005": "High-Voltage Cable Assembly",
        "MAT-006": "Precision Steel Bearing",
        "MAT-007": "Grade 8.8 Hex Flange Bolt",
        "MAT-008": "Thermal Heat Sink Module"
    };

    var PLANT_NAMES = {
        "PLANT-001": "Munich Assembly Hub",
        "PLANT-002": "Leipzig Battery Plant",
        "PLANT-003": "Stuttgart Powertrain"
    };

    var DISRUPTION_NAMES = {
        "PACKAGING_BOTTLENECK": "Packaging Bottleneck",
        "FACTORY_INCIDENT": "Factory Incident",
        "PORT_CONGESTION": "Port Congestion Hold",
        "MATERIAL_SHORTAGE": "Raw Material Shortage",
        "WEATHER_EVENT": "Severe Weather Disruption",
        "LOGISTICS_DELAY": "Logistics Route Delay",
        "CARRIER_SCHEDULE_CHANGE": "Carrier Schedule Change",
        "EQUIPMENT_BREAKDOWN": "Machining Equipment Breakdown",
        "DELAY": "Shipment Delay"
    };

    return Controller.extend("com.quads.supplychain.controller.CaseOverview", {
        onInit: function () {
            var oModel = new JSONModel({});
            this.getView().setModel(oModel, "case");

            var oRouter = this.getOwnerComponent().getRouter();
            ["caseOverview", "caseOverviewAlias"].forEach(function (r) {
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
                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, 1);
            }.bind(this));
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadCaseData(sCaseId);
        },

        loadCaseData: function (sCaseId) {
            var oPage = this.byId("caseOverviewPage");
            if (oPage) oPage.setBusy(true);

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("case");
            var that = this;

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (res) {
                    if (!res.ok) throw new Error("Case not found: " + res.status);
                    return res.json();
                })
                .then(function (data) {
                    data.disruption_name = DISRUPTION_NAMES[data.disruption_type] || data.disruption_type.replace(/_/g, " ");
                    data.disruption_type_display = data.disruption_name;
                    data.supplier_name = SUPPLIER_NAMES[data.supplier_id] || "Supplier " + data.supplier_id;
                    data.material_name = MATERIAL_NAMES[data.material_id] || "Material " + data.material_id;
                    data.plant_name = PLANT_NAMES[data.plant_id] || "Plant " + data.plant_id;
                    data.status_display = (data.status || "CREATED").replace(/_/g, " ");
                    data.current_stage_display = "1. CASE OVERVIEW";
                    data.affected_quantity_display = data.affected_quantity ? Number(data.affected_quantity).toLocaleString() + " Units" : "—";

                    var dDetected = data.detected_at ? new Date(data.detected_at) : new Date();
                    var dExpDelivery = new Date(dDetected.getTime() + 2 * 86400000);
                    var dCurrentEta = new Date(dDetected.getTime() + (data.expected_delay_days + 2) * 86400000);

                    data.expected_delivery_date = dExpDelivery.toLocaleDateString();
                    data.current_eta = dCurrentEta.toLocaleDateString();
                    data.origin = data.origin || (data.supplier_id === "SUP-001" ? "Seoul, South Korea" : (data.supplier_id === "SUP-003" ? "Rotterdam, Netherlands" : "Hamburg, Germany"));
                    data.destination = data.destination || (data.plant_name + ", Germany");
                    data.carrier = data.carrier || (data.supplier_id === "SUP-001" ? "DHL Global Forwarding" : (data.supplier_id === "SUP-003" ? "Hapag-Lloyd Ocean" : "DB Schenker Logistics"));
                    data.transport_mode = data.transport_mode || (data.supplier_id === "SUP-001" ? "Air Cargo Express" : (data.supplier_id === "SUP-003" ? "Ocean Container Freight" : "Road Freight"));
                    data.reason = data.description || "Supply chain schedule exception";

                    // ---- Inventory Risk panel ----
                    var doc = data.days_of_cover || null;
                    data.doc_display = doc !== null ? doc + " Days" : "—";
                    var stockoutMs = data.projected_stockout_date || data.stockout_date;
                    if (stockoutMs) {
                        var dStockout = new Date(stockoutMs);
                        data.stockout_display = dStockout.toLocaleDateString();
                    } else {
                        var docDays = doc || 5;
                        var dSO = new Date(dDetected.getTime() + docDays * 86400000);
                        data.stockout_display = dSO.toLocaleDateString();
                    }
                    var affectedQty = data.affected_quantity || 1000;
                    data.supply_gap_display = Number(Math.round(affectedQty * 0.7)).toLocaleString() + " Units";
                    data.buffer_depletion_display = (doc !== null && doc <= 3) ? "Critical — < 3 days" : (doc !== null && doc <= 7 ? "High — < 7 days" : "Moderate");
                    data.safety_stock_display = Number(Math.round(affectedQty * 0.15)).toLocaleString() + " Units";

                    // ---- Production & Customer Impact panel ----
                    data.assembly_lines_at_risk = data.plant_id === "PLANT-001" ? "3 Lines" : (data.plant_id === "PLANT-002" ? "2 Lines" : "1 Line");
                    data.production_impact_display = data.plant_id === "PLANT-001" ? "~" + Math.round(affectedQty / 50) + " vehicles/day at risk" : "~" + Math.round(affectedQty / 100) + " units/day at risk";
                    data.customer_orders_at_risk = Math.round(affectedQty / 200) + " Open Orders";
                    data.downstream_plants_display = data.plant_id === "PLANT-001" ? "Stuttgart Powertrain, Leipzig Battery" : "Munich Assembly Hub";

                    // ---- Financial Impact panel ----
                    var baseExposure = (data.expected_delay_days || 5) * affectedQty * 0.12;
                    data.financial_exposure_display = "€" + Number(Math.round(baseExposure)).toLocaleString();
                    data.expediting_cost_display = "€" + Number(Math.round(baseExposure * 0.35)).toLocaleString();
                    data.sla_penalty_display = "€" + Number(Math.round(baseExposure * 0.20)).toLocaleString();
                    data.net_recovery_cost_display = "€" + Number(Math.round(baseExposure * 0.55)).toLocaleString();

                    oModel.setData(data);
                })
                .catch(function (err) {
                    MessageBox.error("Failed to load case overview for " + sCaseId + ": " + err.message);
                })
                .finally(function () {
                    if (oPage) oPage.setBusy(false);
                });
        },

        onStartImpactAnalysis: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oBtn = this.byId("btnStartImpactAnalysis");
            var that = this;

            if (oBtn) oBtn.setEnabled(false);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact/start", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (err) {
                        throw new Error(err.message || ("HTTP " + res.status));
                    });
                }
                return res.json();
            })
            .then(function (caseData) {
                that.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
                that.getOwnerComponent().getModel("app").setProperty("/caseStatus", caseData.status);
                WorkflowNavHelper.markStageCompleted(sCaseId, 1);
                    WorkflowNavHelper.setStepperState(sCaseId || this._sCurrentCaseId, 1);
                that.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
            })
            .catch(function (err) {
                if (oBtn) oBtn.setEnabled(true);
                MessageBox.error("Could not start Impact Analysis: " + err.message);
            });
        },

        onBackToCases: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        }
    });
});
