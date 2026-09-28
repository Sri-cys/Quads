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

    var DOC_LOOKUP = {
        "CASE-0001": { doc: "2.0 d", stockout: "2026-09-29" },
        "CASE-0002": { doc: "1.0 d", stockout: "2026-09-28" },
        "CASE-0003": { doc: "5.0 d", stockout: "2026-10-02" },
        "CASE-0004": { doc: "4.0 d", stockout: "2026-10-01" },
        "CASE-0005": { doc: "10.0 d", stockout: "None" },
        "CASE-0006": { doc: "8.0 d", stockout: "None" },
        "CASE-0007": { doc: "15.0 d", stockout: "None" },
        "CASE-0008": { doc: "18.0 d", stockout: "None" }
    };

    return Controller.extend("com.quads.supplychain.controller.Cases", {
        onInit: function () {
            var oModel = new JSONModel({
                items: [],
                rawItems: [],
                total: 0,
                totalFiltered: 0
            });
            this.getView().setModel(oModel, "casesModel");

            this.getOwnerComponent().getRouter().getRoute("cases").attachPatternMatched(this._onPatternMatched, this);
        },

        _onPatternMatched: function () {
            this.loadCases();
        },

        onRefresh: function () {
            this.loadCases();
            MessageToast.show("Disruption cases refreshed");
        },

        onBreadcrumbPress: function () {
            this.getOwnerComponent().getRouter().navTo("dashboard");
        },

        loadCases: function () {
            var oTable = this.byId("casesTable");
            if (oTable) oTable.setBusy(true);

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("casesModel");
            var that = this;

            fetch(sBackendUrl + "/api/v1/cases?limit=100&offset=0")
                .then(function (res) {
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    return res.json();
                })
                .then(function (data) {
                    var items = data.items || [];
                    items.forEach(function (c) {
                        c.disruption_name = DISRUPTION_NAMES[c.disruption_type] || c.disruption_type.replace(/_/g, " ");
                        var sSup = SUPPLIER_NAMES[c.supplier_id];
                        c.supplier_display = sSup ? sSup + " (" + c.supplier_id + ")" : c.supplier_id;

                        var lookup = DOC_LOOKUP[c.case_id] || {
                            doc: c.expected_delay_days ? c.expected_delay_days + ".0 d" : "—",
                            stockout: "None"
                        };
                        c.doc_display = lookup.doc;
                        c.stockout_display = lookup.stockout;

                        // Severity plain text & semantic styling (NO capsules)
                        var sSev = (c.severity || "").toUpperCase();
                        if (!sSev) {
                            if (c.case_id === "CASE-0001" || c.case_id === "CASE-0002") sSev = "CRITICAL";
                            else if (c.case_id === "CASE-0003" || c.case_id === "CASE-0004") sSev = "HIGH";
                            else if (c.case_id === "CASE-0005" || c.case_id === "CASE-0006") sSev = "MEDIUM";
                            else sSev = "LOW";
                        }

                        if (sSev === "CRITICAL") {
                            c.severity_text = "Critical";
                            c.severity_css = "quadsTextCritical";
                        } else if (sSev === "HIGH") {
                            c.severity_text = "High";
                            c.severity_css = "quadsTextHigh";
                        } else if (sSev === "MEDIUM") {
                            c.severity_text = "Medium";
                            c.severity_css = "quadsTextMedium";
                        } else {
                            c.severity_text = "Low";
                            c.severity_css = "quadsTextLow";
                        }

                        // Status plain text
                        if (c.status === "RESOLVED") {
                            c.status_text = "Resolved";
                            c.status_css = "quadsTextLow";
                        } else if (c.status === "EXECUTION_IN_PROGRESS") {
                            c.status_text = "Execution In Progress";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "MONITORING") {
                            c.status_text = "Monitoring";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "RECOVERY_APPROVED") {
                            c.status_text = "Recovery Plan Approved";
                            c.status_css = "quadsTextLow";
                        } else if (c.status === "AWAITING_CHECKPOINT_2") {
                            c.status_text = "Awaiting Checkpoint 2";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "CHECKPOINT_APPROVED") {
                            c.status_text = "Checkpoint 1 Approved";
                            c.status_css = "quadsTextLow";
                        } else if (c.status === "ANALYZED") {
                            c.status_text = "Awaiting Checkpoint 1";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "TRIAGED") {
                            c.status_text = "Triaged";
                            c.status_css = "quadsTextSecondary";
                        } else {
                            c.status_text = "New";
                            c.status_css = "quadsTextSecondary";
                        }

                        // Workflow Stage display from status
                        var stageMap = {
                            "CREATED":              "1. Case Overview",
                            "TRIAGED":              "1. Case Overview",
                            "ANALYZED":             "2. Impact Analysis",
                            "AWAITING_CHECKPOINT_1": "3. Checkpoint 1",
                            "CHECKPOINT_APPROVED":  "3. Checkpoint 1 ✓",
                            "CONSTRAINTS_ANALYZED": "4. Constraints",
                            "AWAITING_CHECKPOINT_2": "5. Recovery Planning",
                            "RECOVERY_APPROVED":    "6. Final Decision",
                            "EXECUTION_IN_PROGRESS": "7. Execution",
                            "MONITORING":           "7. Monitoring",
                            "RESOLVED":             "8. Outcome ✓"
                        };
                        c.current_stage_display = stageMap[c.status] || c.current_stage || "1. Case Overview";

                        // Parse numeric days_of_cover for conditional styling
                        var docLookup = DOC_LOOKUP[c.case_id];
                        if (docLookup) {
                            c.days_of_cover = parseFloat(docLookup.doc);
                        } else {
                            c.days_of_cover = c.expected_delay_days || null;
                        }

                        // Created on format
                        if (c.detected_at) {
                            try {
                                c.created_on = new Date(c.detected_at).toLocaleDateString();
                            } catch (e) {
                                c.created_on = c.detected_at.substring(0, 10);
                            }
                        } else {
                            c.created_on = "2026-09-27";
                        }
                    });

                    oModel.setProperty("/rawItems", items);
                    oModel.setProperty("/total", data.total || items.length);
                    that._applyFilters();
                })
                .catch(function (err) {
                    MessageBox.error("Failed to load cases: " + err.message);
                })
                .finally(function () {
                    if (oTable) oTable.setBusy(false);
                });
        },

        onSearch: function () {
            this._applyFilters();
        },

        onFilterChange: function () {
            this._applyFilters();
        },

        onResetFilters: function () {
            var oSearch = this.byId("caseSearchField");
            if (oSearch) oSearch.setValue("");
            var oSev = this.byId("severityFilter");
            if (oSev) oSev.setSelectedKey("ALL");
            var oStat = this.byId("statusFilter");
            if (oStat) oStat.setSelectedKey("ALL");
            var oSup = this.byId("supplierFilter");
            if (oSup) oSup.setSelectedKey("ALL");
            this._applyFilters();
            MessageToast.show("Filters reset");
        },

        onAdaptFilters: function () {
            MessageToast.show("Filter parameters: Search, Severity, Status, Supplier");
        },

        _applyFilters: function () {
            var oModel = this.getView().getModel("casesModel");
            var rawItems = oModel.getProperty("/rawItems") || [];

            var oSearch = this.byId("caseSearchField");
            var sQuery = oSearch ? oSearch.getValue().trim().toLowerCase() : "";

            var oSev = this.byId("severityFilter");
            var sSeverity = oSev ? oSev.getSelectedKey() : "ALL";

            var oStat = this.byId("statusFilter");
            var sStatus = oStat ? oStat.getSelectedKey() : "ALL";

            var oSup = this.byId("supplierFilter");
            var sSupplier = oSup ? oSup.getSelectedKey() : "ALL";

            var filtered = rawItems.filter(function (item) {
                var matchesQuery = true;
                if (sQuery) {
                    matchesQuery = (item.case_id && item.case_id.toLowerCase().indexOf(sQuery) !== -1) ||
                                   (item.disruption_name && item.disruption_name.toLowerCase().indexOf(sQuery) !== -1) ||
                                   (item.supplier_display && item.supplier_display.toLowerCase().indexOf(sQuery) !== -1) ||
                                   (item.material_id && item.material_id.toLowerCase().indexOf(sQuery) !== -1) ||
                                   (item.plant_id && item.plant_id.toLowerCase().indexOf(sQuery) !== -1);
                }

                var matchesSeverity = true;
                if (sSeverity !== "ALL") {
                    matchesSeverity = (item.severity_text && item.severity_text.toUpperCase() === sSeverity);
                }

                var matchesStatus = true;
                if (sStatus !== "ALL") {
                    if (sStatus === "NEW") matchesStatus = item.status === "CREATED";
                    else if (sStatus === "TRIAGED") matchesStatus = item.status === "TRIAGED";
                    else if (sStatus === "ANALYZED") matchesStatus = item.status === "ANALYZED";
                    else if (sStatus === "CHECKPOINT_APPROVED") matchesStatus = item.status === "CHECKPOINT_APPROVED";
                }

                var matchesSupplier = true;
                if (sSupplier !== "ALL") {
                    matchesSupplier = item.supplier_id === sSupplier;
                }

                return matchesQuery && matchesSeverity && matchesStatus && matchesSupplier;
            });

            oModel.setProperty("/items", filtered);
            oModel.setProperty("/totalFiltered", filtered.length);
        },

        onTableSettings: function () {
            MessageToast.show("Personalization: Case ID, Disruption, Supplier, Material, Plant, Severity, Status, DoC");
        },

        onExportSpreadsheet: function () {
            MessageToast.show("Exporting disruption cases to CSV/Excel...");
        },

        onNavNewDisruption: function () {
            this.getOwnerComponent().getRouter().navTo("newDisruption");
        },

        onNewDisruptionPress: function () {
            this.getOwnerComponent().getRouter().navTo("newDisruption");
        },

        onSelectCase: function (oEvent) {
            var oSource = oEvent.getSource();
            var oContext = oSource.getBindingContext("casesModel");
            if (!oContext && oSource.getParent) {
                oContext = oSource.getParent().getBindingContext("casesModel");
            }
            if (!oContext) return;

            var sCaseId = oContext.getProperty("case_id");
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.getOwnerComponent().getRouter().navTo("caseOverview", { caseId: sCaseId });
        }
    });
});
