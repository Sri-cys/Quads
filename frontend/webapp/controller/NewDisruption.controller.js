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
                    { supplier_id: "SUP-001", name: "Global Chips Ltd", location: "Hsinchu, Taiwan" },
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

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onSubmitAndAnalyze: function () {
            var oData = this.getView().getModel("newCase").getData();
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var that = this;
            var oBtn = this.byId("btnAnalyzeDisruption");

            // Validate inputs
            if (!oData.description || oData.description.trim().length < 5) {
                MessageBox.error("Please provide a description of at least 5 characters.");
                return;
            }
            if (!oData.supplier_id || !oData.material_id || !oData.plant_id) {
                MessageBox.error("Please select a Supplier, Material, and Plant.");
                return;
            }

            // Section 24: Disable duplicate submission and immediately change button label
            if (oBtn) {
                oBtn.setEnabled(false);
                oBtn.setText("Analyzing...");
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

            // Section 24: Compact progress state (Creating case → Calculating impact → Preparing analysis)
            var oStep1Text = new sap.m.Text({ text: "● Creating case", class: "sapProgressStepActive" });
            var oStep2Text = new sap.m.Text({ text: "○ Calculating impact", class: "sapProgressStepPending" });
            var oStep3Text = new sap.m.Text({ text: "○ Preparing analysis", class: "sapProgressStepPending" });

            var oProgressIndicator = new sap.m.ProgressIndicator({
                percentValue: 33,
                displayValue: "Creating case...",
                state: "Information"
            }).addStyleClass("sapUiSmallMarginTopBottom");

            var oDialog = new sap.m.Dialog({
                title: "Analyzing Disruption",
                contentWidth: "400px",
                type: "Message",
                escapeHandler: function (oPromise) { oPromise.reject(); },
                content: [
                    new sap.m.VBox({
                        class: "sapUiSmallMargin",
                        items: [
                            new sap.m.Text({ text: "Please wait while Agent 1 evaluates supply chain disruption signals.", class: "sapUiTinyMarginBottom" }),
                            oProgressIndicator,
                            new sap.m.VBox({
                                class: "sapUiTinyMarginTop",
                                items: [oStep1Text, oStep2Text, oStep3Text]
                            })
                        ]
                    })
                ]
            });
            oDialog.open();

            // Execute Ingestion & Case Creation
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
                var sCaseId = caseData.case_id;

                // Step 2: Calculating impact
                oStep1Text.setText("✓ Creating case");
                oStep1Text.removeStyleClass("sapProgressStepActive").addStyleClass("sapProgressStepDone");
                oStep2Text.setText("● Calculating impact");
                oStep2Text.removeStyleClass("sapProgressStepPending").addStyleClass("sapProgressStepActive");
                oProgressIndicator.setPercentValue(66);
                oProgressIndicator.setDisplayValue("Calculating impact...");

                return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/analyze", {
                    method: "POST"
                })
                .then(function (res) {
                    return res.json().then(function (impactData) {
                        if (!res.ok) {
                            throw new Error(impactData.message || "Failed to run impact analysis");
                        }
                        return sCaseId;
                    });
                });
            })
            .then(function (sCaseId) {
                // Step 3: Preparing analysis
                oStep2Text.setText("✓ Calculating impact");
                oStep2Text.removeStyleClass("sapProgressStepActive").addStyleClass("sapProgressStepDone");
                oStep3Text.setText("✓ Preparing analysis");
                oStep3Text.removeStyleClass("sapProgressStepPending").addStyleClass("sapProgressStepDone");
                oProgressIndicator.setPercentValue(100);
                oProgressIndicator.setDisplayValue("Complete");
                oProgressIndicator.setState("Success");

                setTimeout(function () {
                    oDialog.close();
                    oDialog.destroy();
                    if (oBtn) {
                        oBtn.setEnabled(true);
                        oBtn.setText("Analyze Disruption");
                    }
                    MessageToast.show("Disruption analyzed successfully. Routing to Impact Analysis.");
                    that.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
                    that.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
                }, 600);
            })
            .catch(function () {
                oDialog.close();
                oDialog.destroy();
                if (oBtn) {
                    oBtn.setEnabled(true);
                    oBtn.setText("Analyze Disruption");
                }
                // Section 25: Professional error message with Retry
                MessageBox.error(
                    "Unable to complete impact analysis.\n\nPlease verify the disruption details and try again.",
                    {
                        title: "Analysis Failure",
                        actions: ["Retry", MessageBox.Action.CLOSE],
                        emphasizedAction: "Retry",
                        onClose: function (sAction) {
                            if (sAction === "Retry") {
                                that.onSubmitAndAnalyze();
                            }
                        }
                    }
                );
            });
        }
    });
});
