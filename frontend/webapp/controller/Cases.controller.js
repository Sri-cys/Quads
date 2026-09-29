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

    var WORKFLOW_STAGES = [
        {no: 1, name: "Case"},
        {no: 2, name: "Impact Analysis"},
        {no: 3, name: "Priority"},
        {no: 4, name: "Constraints"},
        {no: 5, name: "Recovery Planning"},
        {no: 6, name: "Decision"},
        {no: 7, name: "Exec & Monitoring"},
        {no: 8, name: "Outcome"}
    ];

    return Controller.extend("com.quads.supplychain.controller.Cases", {
        formatter: {
            formatStatus: function (vStatusOrObj) {
                var sStatus = "";
                if (typeof vStatusOrObj === "string") {
                    sStatus = vStatusOrObj;
                } else if (vStatusOrObj && vStatusOrObj.status) {
                    sStatus = vStatusOrObj.status;
                }
                if (!sStatus) return "Pending Approval";
                var upper = sStatus.toUpperCase();
                if (upper === "RECOVERY_APPROVED" || upper === "PLAN_APPROVED" || upper === "EXECUTION" || upper === "EXECUTION_IN_PROGRESS" || upper === "MONITORING" || upper === "RESOLVED") {
                    return "Approved";
                }
                return "Pending Approval";
            },
            
            formatStatusState: function (vStatusOrObj) {
                var sStatus = "";
                if (typeof vStatusOrObj === "string") {
                    sStatus = vStatusOrObj;
                } else if (vStatusOrObj && vStatusOrObj.status) {
                    sStatus = vStatusOrObj.status;
                }
                if (!sStatus) return "Warning";
                var upper = sStatus.toUpperCase();
                if (upper === "RECOVERY_APPROVED" || upper === "PLAN_APPROVED" || upper === "EXECUTION" || upper === "EXECUTION_IN_PROGRESS" || upper === "MONITORING" || upper === "RESOLVED") {
                    return "Success";
                }
                return "Warning";
            },

            formatWorkflowStage: function (vCaseIdOrObj) {
                var sCaseId = "";
                if (typeof vCaseIdOrObj === "string") {
                    sCaseId = vCaseIdOrObj;
                } else if (vCaseIdOrObj && vCaseIdOrObj.case_id) {
                    sCaseId = vCaseIdOrObj.case_id;
                }
                if (!sCaseId) return "1. Case";
                
                var sKey = "quads_completed_stage_" + sCaseId;
                var sStored = window.localStorage.getItem(sKey);
                var nCompleted = sStored ? parseInt(sStored, 10) : 0;
                var nStage = nCompleted + 1;
                if (nStage > 8) nStage = 8;
                var oStage = WORKFLOW_STAGES[nStage - 1];
                return oStage.no + ". " + oStage.name;
            }
        },
        
        onInit: function () {
            var oModel = new JSONModel({
                items: [],
                rawItems: [],
                total: 0,
                totalFiltered: 0,
                counts: {
                    all: 0,
                    actionRequired: 0,
                    atRisk: 0,
                    onTrack: 0,
                    resolved: 0
                }
            });
            this.getView().setModel(oModel, "casesModel");

            this.getOwnerComponent().getRouter().getRoute("cases").attachPatternMatched(this._onPatternMatched, this);
        },

        _onPatternMatched: function (oEvent) {
            var oArgs = oEvent.getParameter("arguments");
            var oQuery = oArgs["?query"];
            var sCategory = (oQuery && oQuery.category) ? oQuery.category : "ALL";
            
            var aValidTabs = ["ALL", "ACTION_REQUIRED", "AT_RISK", "ON_TRACK", "RESOLVED", "ALL_ACTIVE", "ACTIVE_RECOVERIES", "IN_EXECUTION"];
            if (aValidTabs.indexOf(sCategory) === -1) {
                sCategory = "ALL";
            }
            
            this.getView().getModel("casesModel").setProperty("/selectedCategory", sCategory);
            this.loadCases();
        },

        onCategoryTabPress: function (oEvent) {
            var sCategory = oEvent.getSource().data("category");
            this.getView().getModel("casesModel").setProperty("/selectedCategory", sCategory);
            this._applyFilters();
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
                    sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {
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

                            // Prime WorkflowNavHelper from list data without sync XHR
                            if (c.checkpoint1_decision) {
                                WorkflowNavHelper.savePriority(c.case_id, c.checkpoint1_decision);
                            }
                            if (WorkflowNavHelper.getCompletedStage(c.case_id) === 0) {
                                var maxCompleted = 0;
                                if (c.completed_stages && Array.isArray(c.completed_stages) && c.completed_stages.length > 0) {
                                    c.completed_stages.forEach(function (stageName) {
                                        var n = 0;
                                        var sLower = stageName.toLowerCase();
                                        if (sLower.indexOf("case") !== -1) n = 1;
                                        if (sLower.indexOf("impact") !== -1) n = 2;
                                        if (sLower.indexOf("priority") !== -1) n = 3;
                                        if (sLower.indexOf("constraints") !== -1) n = 4;
                                        if (sLower.indexOf("recovery") !== -1) n = 5;
                                        if (sLower.indexOf("decision") !== -1) n = 6;
                                        if (sLower.indexOf("exec") !== -1 || sLower.indexOf("monitoring") !== -1) n = 7;
                                        if (sLower.indexOf("outcome") !== -1) n = 8;
                                        if (n > maxCompleted) maxCompleted = n;
                                    });
                                } else {
                                    // Fallback if completed_stages is not provided
                                    var sStat = c.status || "";
                                    if (sStat === "RESOLVED") maxCompleted = 8;
                                    else if (["EXECUTION_IN_PROGRESS", "MONITORING"].indexOf(sStat) !== -1) maxCompleted = 7;
                                    else if (sStat === "RECOVERY_APPROVED") maxCompleted = 6;
                                    else if (sStat === "AWAITING_CHECKPOINT_2") maxCompleted = 5;
                                    else if (sStat === "CONSTRAINTS_ANALYZED") maxCompleted = 4;
                                    else if (sStat === "CHECKPOINT_APPROVED") maxCompleted = 3;
                                    else if (["ANALYZED", "AWAITING_CHECKPOINT_1"].indexOf(sStat) !== -1) maxCompleted = 2;
                                    else if (sStat !== "CREATED") maxCompleted = 1;
                                }

                                if (maxCompleted >= 3 && !WorkflowNavHelper.isPrioritySaved(c.case_id)) {
                                    maxCompleted = 2;
                                }
                                if (maxCompleted > 0) {
                                    window.localStorage.setItem("quads_completed_stage_" + c.case_id, String(maxCompleted));
                                }
                            }

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

                    // CATEGORY CLASSIFICATION (Exactly matching Dashboard logic)
                    var nActionRequired = 0;
                    var nAtRisk = 0;
                    var nResolved = 0;
                    var nActive = 0;
                    var nTotal = items.length;

                    items.forEach(function (c) {
                        var sStatus = (c.status || "CREATED").toUpperCase();
                        var sSev = (c.severity || "LOW").toUpperCase();
                        var sExec = (c.execution_status || "").toUpperCase();

                        c._isResolved = (sStatus === "RESOLVED");
                        c._isActive = !c._isResolved;
                        c._isAtRisk = (sSev === "CRITICAL" || sSev === "HIGH" || sExec === "AT_RISK");
                        c._isActionRequired = (sStatus === "ANALYZED" || sStatus === "AWAITING_CHECKPOINT_2" || sExec === "ACTION_REQUIRED" || sExec === "FAILED");
                        
                        var aRecoveryStatuses = ["CHECKPOINT_APPROVED", "RECOVERY_PLANNING", "AWAITING_CHECKPOINT_2", "RECOVERY_APPROVED", "EXECUTION_IN_PROGRESS", "MONITORING"];
                        c._isActiveRecovery = (aRecoveryStatuses.indexOf(sStatus) !== -1);
                        c._isInExecution = (sStatus === "EXECUTION_IN_PROGRESS" || sStatus === "MONITORING");
                        
                        if (c._isResolved) nResolved++;
                        else nActive++;

                        if (c._isAtRisk) nAtRisk++;
                        if (c._isActionRequired) nActionRequired++;
                    });
                    
                    var nOnTrack = Math.max(0, nActive - nAtRisk);
                    
                    items.forEach(function (c) {
                        c._isOnTrack = (!c._isResolved && !c._isAtRisk);
                    });

                    oModel.setProperty("/counts", {
                        all: nTotal,
                        actionRequired: nActionRequired,
                        atRisk: nAtRisk,
                        onTrack: nOnTrack,
                        resolved: nResolved
                    });

                    oModel.setProperty("/rawItems", items);
                    oModel.setProperty("/total", nTotal);
                    that._applyFilters();
                    }); // Close sap.ui.require
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

            var sCategory = oModel.getProperty("/selectedCategory") || "ALL";

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
                    var sFmtStatus = this.formatter.formatStatus(item.status);
                    if (sStatus === "PENDING_APPROVAL") matchesStatus = (sFmtStatus === "Pending Approval");
                    else if (sStatus === "APPROVED") matchesStatus = (sFmtStatus === "Approved");
                }

                var matchesSupplier = true;
                if (sSupplier !== "ALL") {
                    matchesSupplier = item.supplier_id === sSupplier;
                }

                var matchesCategory = true;
                if (sCategory === "ACTION_REQUIRED") matchesCategory = item._isActionRequired;
                else if (sCategory === "AT_RISK") matchesCategory = item._isAtRisk;
                else if (sCategory === "ON_TRACK") matchesCategory = item._isOnTrack;
                else if (sCategory === "RESOLVED") matchesCategory = item._isResolved;
                else if (sCategory === "ALL_ACTIVE") matchesCategory = item._isActive;
                else if (sCategory === "ACTIVE_RECOVERIES") matchesCategory = item._isActiveRecovery;
                else if (sCategory === "IN_EXECUTION") matchesCategory = item._isInExecution;

                return matchesQuery && matchesSeverity && matchesStatus && matchesSupplier && matchesCategory;
            }.bind(this)); // bind this to access formatter

            // Sorting logic: CRITICAL -> HIGH -> MEDIUM -> LOW
            var severityRank = { "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4 };
            filtered.sort(function(a, b) {
                var rankA = severityRank[(a.severity || "LOW").toUpperCase()] || 5;
                var rankB = severityRank[(b.severity || "LOW").toUpperCase()] || 5;
                if (rankA !== rankB) {
                    return rankA - rankB; // Ascending rank (1 is first)
                }
                return 0; // Days of Cover removed
            });

            oModel.setProperty("/items", filtered);
            oModel.setProperty("/totalFiltered", filtered.length);

            var sTitle = "ALL CASES";
            if (sCategory === "ACTION_REQUIRED") sTitle = "ACTION REQUIRED";
            else if (sCategory === "AT_RISK") sTitle = "AT RISK";
            else if (sCategory === "ON_TRACK") sTitle = "ON TRACK";
            else if (sCategory === "RESOLVED") sTitle = "RESOLVED";
            else if (sCategory === "ALL_ACTIVE") sTitle = "ACTIVE DISRUPTIONS";
            else if (sCategory === "ACTIVE_RECOVERIES") sTitle = "ACTIVE RECOVERIES";
            else if (sCategory === "IN_EXECUTION") sTitle = "IN EXECUTION";
            
            oModel.setProperty("/tableTitle", sTitle);
        },

        onTableSettings: function () {
            MessageToast.show("Personalization: Case ID, Disruption, Supplier, Material, Plant, Severity, Status");
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
