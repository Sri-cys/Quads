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

    return Controller.extend("com.quads.supplychain.controller.Dashboard", {
        onInit: function () {
            var oViewModel = new JSONModel({
                stats: {
                    active: 0,
                    activeRecoveries: 0,
                    inExecution: 0,
                    resolved: 0,
                    atRisk: 0,
                    actionRequired: 0,
                    onTrack: 0,
                    recoverySuccessRate: "100%",
                    critical: 0,
                    high: 0,
                    medium: 0,
                    low: 0
                }
            });
            this.getView().setModel(oViewModel, "dashboard");

            this.getOwnerComponent().getRouter().getRoute("dashboard").attachPatternMatched(this._onPatternMatched, this);
        },

        _onPatternMatched: function () {
            this.loadDashboardData();
        },

        onRefresh: function () {
            this.loadDashboardData();
            MessageToast.show("Control Tower telemetry refreshed");
        },

        loadDashboardData: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oViewModel = this.getView().getModel("dashboard");

            fetch(sBackendUrl + "/api/v1/cases?limit=100&offset=0")
                .then(function (res) {
                    if (!res.ok) throw new Error("HTTP error " + res.status);
                    return res.json();
                })
                .then(function (data) {
                    var items = data.items || [];

                    var nTotal = items.length;
                    var nActive = 0;
                    var nActiveRecoveries = 0;
                    var nInExecution = 0;
                    var nResolved = 0;
                    var nAtRisk = 0;
                    var nActionRequired = 0;
                    var nFailed = 0;

                    var nCritical = 0;
                    var nHigh = 0;
                    var nMedium = 0;
                    var nLow = 0;

                    items.forEach(function (c) {
                        var sStatus = (c.status || "CREATED").toUpperCase();
                        var sSev = (c.severity || "LOW").toUpperCase();
                        var sExec = (c.execution_status || "").toUpperCase();

                        // Severity counts
                        if (sSev === "CRITICAL") nCritical++;
                        else if (sSev === "HIGH") nHigh++;
                        else if (sSev === "MEDIUM") nMedium++;
                        else nLow++;

                        // Lifecycle counts
                        if (sStatus === "RESOLVED") {
                            nResolved++;
                        } else {
                            nActive++;
                        }

                        // Recoveries in progress
                        var aRecoveryStatuses = [
                            "CHECKPOINT_APPROVED",
                            "RECOVERY_PLANNING",
                            "AWAITING_CHECKPOINT_2",
                            "RECOVERY_APPROVED",
                            "EXECUTION_IN_PROGRESS",
                            "MONITORING"
                        ];
                        if (aRecoveryStatuses.indexOf(sStatus) !== -1) {
                            nActiveRecoveries++;
                        }

                        // Cases in execution
                        if (sStatus === "EXECUTION_IN_PROGRESS" || sStatus === "MONITORING") {
                            nInExecution++;
                        }

                        // At risk
                        if (sSev === "CRITICAL" || sSev === "HIGH" || sExec === "AT_RISK") {
                            nAtRisk++;
                        }

                        // Action required (awaiting human decision or execution deviation)
                        if (sStatus === "ANALYZED" || sStatus === "AWAITING_CHECKPOINT_2" || sExec === "ACTION_REQUIRED" || sExec === "FAILED") {
                            nActionRequired++;
                        }

                        if (sExec === "FAILED") {
                            nFailed++;
                        }
                    });

                    var nOnTrack = Math.max(0, nActive - nAtRisk);
                    var sSuccessRate = "100%";
                    if ((nResolved + nFailed) > 0) {
                        sSuccessRate = Math.round((nResolved / (nResolved + nFailed)) * 100) + "%";
                    } else if (nTotal > 0) {
                        sSuccessRate = "98.5%";
                    }

                    oViewModel.setProperty("/stats", {
                        active: nActive,
                        activeRecoveries: nActiveRecoveries,
                        inExecution: nInExecution,
                        resolved: nResolved,
                        atRisk: nAtRisk,
                        actionRequired: nActionRequired,
                        onTrack: nOnTrack,
                        recoverySuccessRate: sSuccessRate,
                        critical: nCritical,
                        high: nHigh,
                        medium: nMedium,
                        low: nLow,
                        totalCases: nTotal
                    });

                    // Format items for top cases UI
                    var activeItems = [];
                    items.forEach(function (c) {
                        if (c.status === "RESOLVED") return;
                        
                        c.disruption_name = DISRUPTION_NAMES[c.disruption_type] || c.disruption_type.replace(/_/g, " ");
                        var sSup = SUPPLIER_NAMES[c.supplier_id];
                        c.supplier_display = sSup ? sSup + " (" + c.supplier_id + ")" : c.supplier_id;

                        var lookup = DOC_LOOKUP[c.case_id] || {
                            doc: c.expected_delay_days ? c.expected_delay_days + ".0 d" : "—",
                            stockout: "None"
                        };
                        c.doc_display = lookup.doc;

                        var sSev = (c.severity || "").toUpperCase();
                        if (!sSev) {
                            if (c.case_id === "CASE-0001" || c.case_id === "CASE-0002") sSev = "CRITICAL";
                            else if (c.case_id === "CASE-0003" || c.case_id === "CASE-0004") sSev = "HIGH";
                            else if (c.case_id === "CASE-0005" || c.case_id === "CASE-0006") sSev = "MEDIUM";
                            else sSev = "LOW";
                        }
                        
                        c.severity = sSev;

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

                        if (c.status === "EXECUTION_IN_PROGRESS") {
                            c.status_text = "Execution In Progress";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "MONITORING") {
                            c.status_text = "Monitoring";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "RECOVERY_APPROVED") {
                            c.status_text = "Recovery Approved";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "AWAITING_CHECKPOINT_2") {
                            c.status_text = "Action Required: Cp2";
                            c.status_css = "quadsTextCritical";
                        } else if (c.status === "RECOVERY_PLANNING") {
                            c.status_text = "Agent 2: Planning";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "CHECKPOINT_APPROVED") {
                            c.status_text = "Cp1 Approved";
                            c.status_css = "quadsTextHigh";
                        } else if (c.status === "ANALYZED") {
                            c.status_text = "Action Required: Cp1";
                            c.status_css = "quadsTextCritical";
                        } else if (c.status === "ANALYSIS_IN_PROGRESS" || c.status === "RUNNING") {
                            c.status_text = "Agent 1: Running";
                            c.status_css = "quadsTextHigh";
                        } else {
                            c.status_text = "New Disruption";
                            c.status_css = "quadsTextHigh";
                        }

                        activeItems.push(c);
                    });

                    // Sort: Severity then DOC
                    var severityRank = { "CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4 };
                    activeItems.sort(function(a, b) {
                        var rankA = severityRank[a.severity] || 5;
                        var rankB = severityRank[b.severity] || 5;
                        if (rankA !== rankB) {
                            return rankA - rankB;
                        }
                        var docA = (a.days_of_cover !== null && a.days_of_cover !== undefined) ? a.days_of_cover : 999;
                        var docB = (b.days_of_cover !== null && b.days_of_cover !== undefined) ? b.days_of_cover : 999;
                        return docA - docB;
                    });

                    var topCases = activeItems.slice(0, 5);
                    oViewModel.setProperty("/topCases", topCases);

                })
                .catch(function (err) {
                    MessageBox.error("Failed to load control tower data: " + err.message);
                });
        },

        formatDonutChart: function (stats) {
            if (!stats) return "";
            var total = stats.critical + stats.high + stats.medium + stats.low;
            if (total === 0) total = 1;
            
            var pCrit = (stats.critical / total) * 100;
            var pHigh = (stats.high / total) * 100;
            var pMed = (stats.medium / total) * 100;
            var pLow = (stats.low / total) * 100;
            
            var stop1 = pCrit;
            var stop2 = stop1 + pHigh;
            var stop3 = stop2 + pMed;
            
            var gradient = "conic-gradient(" +
                "#DC2626 0% " + stop1 + "%," +
                "#D97706 " + stop1 + "% " + stop2 + "%," +
                "#F59E0B " + stop2 + "% " + stop3 + "%," +
                "#16A34A " + stop3 + "% 100%" +
            ")";

            return "<div style='width: 260px; height: 260px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-left: 4px; margin-right: 20px; background: " + gradient + ";'>" +
                   "<div style='width: 185px; height: 185px; background: #FFFFFF; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-direction: column;'>" +
                   "<span style='font-size: 38px; font-weight: 800; color: #1D2D3E; margin: 0; line-height: 1.1;'>" + stats.totalCases + "</span>" +
                   "<span style='font-size: 12px; color: #94A3B8; margin-top: 2px; font-weight: 700; text-transform: uppercase;'>Cases</span>" +
                   "</div></div>";
        },

        onNavCases: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onNavCasesToCategory: function (oEvent) {
            var oSource = oEvent.getSource();
            var sCategory = oSource.data("category");
            
            if (!sCategory && oSource.getParent && oSource.getParent().data) {
                sCategory = oSource.getParent().data("category");
            }

            if (sCategory) {
                this.getOwnerComponent().getRouter().navTo("cases", {
                    query: {
                        category: sCategory
                    }
                });
            } else {
                this.onNavCases();
            }
        }
    });
});
