sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast"
], function (Controller, JSONModel, MessageBox, MessageToast) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.NewDisruption", {
        onInit: function () {
            var oNewCaseModel = new JSONModel({
                disruption_type: "SUPPLIER_DELAY",
                description: "Supplier shipment delayed by 5 days.",
                supplier_id: "SUP-001",
                material_id: "MAT-001",
                plant_id: "PLANT-001",
                expected_delay_days: 5,
                affected_quantity: 500
            });
            this.getView().setModel(oNewCaseModel, "newCase");

            var oMasterDataModel = new JSONModel({
                suppliers: [],
                materials: [],
                plants: []
            });
            this.getView().setModel(oMasterDataModel, "masterData");

            this.getOwnerComponent().getRouter().getRoute("newDisruption").attachPatternMatched(this._onPatternMatched, this);
        },

        _onPatternMatched: function () {
            this.loadMasterData();
        },

        loadMasterData: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oMasterModel = this.getView().getModel("masterData");

            Promise.all([
                fetch(sBackendUrl + "/api/v1/suppliers").then(function (r) { return r.json(); }),
                fetch(sBackendUrl + "/api/v1/materials").then(function (r) { return r.json(); }),
                fetch(sBackendUrl + "/api/v1/plants").then(function (r) { return r.json(); })
            ]).then(function (results) {
                oMasterModel.setProperty("/suppliers", results[0] || []);
                oMasterModel.setProperty("/materials", results[1] || []);
                oMasterModel.setProperty("/plants", results[2] || []);
            }).catch(function (err) {
                // Fallback default dropdown items if backend offline
                oMasterModel.setProperty("/suppliers", [
                    { supplier_id: "SUP-001", name: "Hyundai Mobis Supplier", location: "Chennai, India" },
                    { supplier_id: "SUP-002", name: "Apex Battery Solutions", location: "Incheon, South Korea" },
                    { supplier_id: "SUP-003", name: "Rhine Precision Forgings", location: "Stuttgart, Germany" }
                ]);
                oMasterModel.setProperty("/materials", [
                    { material_id: "MAT-001", name: "Semiconductor Microcontroller MCU-32", category: "Electronics" },
                    { material_id: "MAT-002", name: "Lithium-Ion Battery Cell Pack 48V", category: "Energy" },
                    { material_id: "MAT-003", name: "Titanium Drive Shaft Model-T", category: "Powertrain" }
                ]);
                oMasterModel.setProperty("/plants", [
                    { plant_id: "PLANT-001", name: "Munich Manufacturing Hub", location: "Munich, Germany" },
                    { plant_id: "PLANT-002", name: "Austin Assembly Plant", location: "Austin, Texas, USA" }
                ]);
            });
        },

        onResetDefaults: function () {
            this.getView().getModel("newCase").setData({
                disruption_type: "SUPPLIER_DELAY",
                description: "Supplier shipment delayed by 5 days.",
                supplier_id: "SUP-001",
                material_id: "MAT-001",
                plant_id: "PLANT-001",
                expected_delay_days: 5,
                affected_quantity: 500
            });
            MessageToast.show("Form reset to Section 29 Demo scenario defaults.");
        },

        onCancel: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onCreateDisruption: function () {
            var oData = this.getView().getModel("newCase").getData();
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var that = this;
            var oBtn = this.byId("btnCreateDisruption");

            // Validate inputs
            if (!oData.description || oData.description.trim().length < 5) {
                MessageBox.error("Please provide a description of at least 5 characters.");
                return;
            }
            if (!oData.supplier_id || !oData.material_id || !oData.plant_id) {
                MessageBox.error("Please select a Supplier, Material, and Plant.");
                return;
            }

            if (oBtn) {
                oBtn.setEnabled(false);
                oBtn.setText("Registering...");
            }

            var payload = {
                disruption_type: oData.disruption_type,
                description: oData.description.trim(),
                supplier_id: oData.supplier_id,
                material_id: oData.material_id,
                plant_id: oData.plant_id,
                expected_delay_days: parseInt(oData.expected_delay_days, 10) || 5,
                affected_quantity: oData.affected_quantity ? parseFloat(oData.affected_quantity) : 500
            };

            fetch(sBackendUrl + "/api/v1/cases", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(function (res) {
                return res.json().then(function (data) {
                    if (!res.ok) {
                        throw new Error(data.message || "Failed to create disruption case");
                    }
                    return data;
                });
            })
            .then(function (caseData) {
                if (oBtn) {
                    oBtn.setEnabled(true);
                    oBtn.setText("Create Disruption");
                }
                var sCaseId = caseData.case_id;
                MessageToast.show("Disruption case " + sCaseId + " registered. Opening Case Overview.");
                that.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
                that.getOwnerComponent().getModel("app").setProperty("/caseStatus", caseData.status || "CREATED");
                that.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
            })
            .catch(function (err) {
                if (oBtn) {
                    oBtn.setEnabled(true);
                    oBtn.setText("Create Disruption");
                }
                MessageBox.error("Failed to register disruption case: " + err.message);
            });
        },

        onSubmitAndAnalyze: function () {
            this.onCreateDisruption();
        }
    });
});
