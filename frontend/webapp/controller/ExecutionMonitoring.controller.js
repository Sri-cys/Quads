sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageToast",
    "sap/m/MessageBox",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageToast, MessageBox, WorkflowNavHelper) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.ExecutionMonitoring", {

        onInit: function () {
            var oModel = new JSONModel({
                case_id: "",
                pending_execution: false,
                approved_plan: {},
                checkpoint2_manager_id: "SUPPLY_CHAIN_PLANNER",
                checkpoint2_timestamp: "",
                execution_status: "ACCEPTED",
                baseline: {},
                action: {},
                tracking_events: [],
                audit_events: [],
                historical_outcomes: [],
                failed_plans: [],
                current_confirmed_quantity: 0,
                current_estimated_arrival: "",
                current_estimated_cost: 0,
                deviation: {
                    quantity_shortage: 0,
                    delay_days: 0,
                    cost_variance: 0,
                    is_critical_deviation: false,
                    explanation: ""
                },
                is_success: false,
                is_failed: false,
                failure_reason: null,
                ai_summary: "",
                ai_status: "GROUNDED",
                can_replan: false,
                can_resolve: false
            });
            this.getView().setModel(oModel, "exec");

            var oRouter = this.getOwnerComponent().getRouter();
            ["executionMonitoring", "executionMonitoringAlt", "monitoring", "monitoringAlt"].forEach(function (rName) {
                var oR = oRouter.getRoute(rName);
                if (oR) oR.attachPatternMatched(this._onRouteMatched, this);
            }, this);
        },

        _onRouteMatched: function (oEvent) {
            var sCaseId = oEvent.getParameter("arguments").caseId || this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            this._sCurrentCaseId = sCaseId;
            sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {
                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, 6);
                
                var nCompleted = WorkflowNavHelper.getCompletedStage(this._sCurrentCaseId);
                var oAppModel = this.getOwnerComponent().getModel("app");
                var sStored = window.localStorage.getItem("quads_completed_stage_" + this._sCurrentCaseId);
                console.log("[EXEC-LAYOUT] STEPPER VALUES:");
                console.log("[EXEC-LAYOUT] Stored string list/value:", sStored, typeof sStored);
                console.log("[EXEC-LAYOUT] computed completedStage:", nCompleted, typeof nCompleted);
                console.log("[EXEC-LAYOUT] app>/activeStep:", oAppModel.getProperty("/activeStep"), typeof oAppModel.getProperty("/activeStep"));
                console.log("[EXEC-LAYOUT] app>/completedStage:", oAppModel.getProperty("/completedStage"), typeof oAppModel.getProperty("/completedStage"));
                console.log("[EXEC-LAYOUT] Header status text:", oAppModel.getProperty("/caseStatusText"));
            }.bind(this));
            this.loadExecutionData(sCaseId);
        },

        loadExecutionData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var that = this;
            var oPage = this.byId("executionMonitoringPage");
            if (oPage) oPage.setBusy(true);

            // Step A: Attempt to load existing execution progress
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/progress")
                .then(function (res) {
                    if (res.ok) {
                        return res.json().then(function (progress) {
                            var oModel = that.getView().getModel("exec");
                            oModel.setData(Object.assign({}, oModel.getData(), progress, { pending_execution: false }));
                            console.log("[EXEC-LAYOUT] EXECUTING STATE:", progress);
                            console.log("[EXEC-LAYOUT] pending_execution (Awaiting flag) = ", oModel.getProperty("/pending_execution"));
                            console.log("[EXEC-LAYOUT] execution_status = ", oModel.getProperty("/execution_status"));
                            that._loadAuditHistory(sBackendUrl, sCaseId);
                            if (progress.is_success) {
                                that._loadOutcomes(sBackendUrl, sCaseId);
                            } else if (progress.is_failed) {
                                that._loadFailedPlans(sBackendUrl, sCaseId);
                            }
                        });
                    } else if (res.status === 404) {
                        // Execution not yet started -> Load approved plan details for execution review
                        return that._loadApprovedPlanForExecution(sBackendUrl, sCaseId);
                    } else {
                        throw new Error("Failed to load execution status (Code: " + res.status + ")");
                    }
                })
                .catch(function (err) {
                    MessageBox.error("Execution & Monitoring error: " + err.message);
                })
                .finally(function () {
                    setTimeout(function() {
                        if (oPage) oPage.setBusy(false);
                    }, 1000);
                });
        },

        _loadApprovedPlanForExecution: function (sBackendUrl, sCaseId) {
            var that = this;
            return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (res) {
                    if (!res.ok) throw new Error("Could not fetch case details for " + sCaseId);
                    return res.json();
                })
                .then(function (caseData) {
                    if (!caseData.approved_plan_id) {
                        // No approved plan yet — silently redirect to Decision page
                        // (Route guard already notified the user via MessageToast)
                        MessageToast.show("No approved recovery plan for " + sCaseId + ". Please complete Checkpoint 2 first.");
                        that.getOwnerComponent().getRouter().navTo("decision", { caseId: sCaseId });
                        return;
                    }

                    // Fetch plan set to get full plan attributes
                    return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan")
                        .then(function (pr) {
                            if (pr.ok) return pr.json();
                            return null;
                        })
                        .then(function (planSet) {
                            var matchedPlan = null;
                            if (planSet && planSet.feasible_plans) {
                                for (var i = 0; i < planSet.feasible_plans.length; i++) {
                                    if (planSet.feasible_plans[i].plan_id === caseData.approved_plan_id) {
                                        matchedPlan = planSet.feasible_plans[i];
                                        break;
                                    }
                                }
                            }

                            if (!matchedPlan) {
                                matchedPlan = {
                                    plan_id: caseData.approved_plan_id,
                                    version: caseData.approved_plan_version || "v1",
                                    strategy: "EXPEDITED_SUPPLIER_RECOVERY",
                                    source_name: caseData.supplier_id || "Certified Supplier",
                                    destination_name: caseData.plant_id || "Target Plant",
                                    recovered_quantity: caseData.affected_quantity || 500,
                                    transport_name: "Air Expedited Freight",
                                    expected_delivery_date: "2026-09-30",
                                    total_cost: 48500
                                };
                            }

                            var oModel = that.getView().getModel("exec");
                            oModel.setProperty("/case_id", sCaseId);
                            oModel.setProperty("/pending_execution", true);
                            oModel.setProperty("/approved_plan", matchedPlan);
                            console.log("[EXEC-LAYOUT] AWAITING STATE:");
                            console.log("[EXEC-LAYOUT] pending_execution (Awaiting flag) = ", oModel.getProperty("/pending_execution"));
                            console.log("[EXEC-LAYOUT] approved_plan = ", matchedPlan);
                            oModel.setProperty("/checkpoint2_manager_id", "SUPPLY_CHAIN_PLANNER");
                            oModel.setProperty("/checkpoint2_timestamp", new Date().toLocaleString());
                            oModel.setProperty("/execution_status", "AWAITING_EXECUTION");
                            that._loadAuditHistory(sBackendUrl, sCaseId);
                        });
                });
        },

        onStartExecutionAction: function () {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;
            var oPage = this.byId("executionMonitoringPage");
            if (oPage) oPage.setBusy(true);

            this._initializeExecution(sBackendUrl, sCaseId)
                .then(function (progress) {
                    var oModel = that.getView().getModel("exec");
                    oModel.setData(Object.assign({}, oModel.getData(), progress, { pending_execution: false }));
                    that._loadAuditHistory(sBackendUrl, sCaseId);
                    MessageToast.show("Execution Action Created in SAP TM. Telematics Monitoring Active.");
                })
                .catch(function (err) {
                    MessageBox.error("Execution initialization failed: " + err.message);
                })
                .finally(function () {
                    setTimeout(function() {
                        if (oPage) oPage.setBusy(false);
                    }, 1000);
                });
        },

        _initializeExecution: function (sBackendUrl, sCaseId) {
            var that = this;
            return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId)
                .then(function (res) {
                    if (!res.ok) throw new Error("Could not fetch case details for " + sCaseId);
                    return res.json();
                })
                .then(function (caseData) {
                    if (!caseData.approved_plan_id) {
                        throw new Error("Cannot execute case " + sCaseId + ": No recovery plan has been approved at Checkpoint 2.");
                    }
                    var sPlanId = caseData.approved_plan_id;
                    var sVersion = caseData.approved_plan_version || "v1";

                    return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/start", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            plan_id: sPlanId,
                            version: sVersion,
                            manager_id: "SUPPLY_CHAIN_PLANNER"
                        })
                    });
                })
                .then(function (startRes) {
                    if (!startRes.ok) {
                        return startRes.json().then(function (err) {
                            throw new Error(err.message || "Failed to start execution action");
                        });
                    }
                    return startRes.json();
                });
        },

        _loadOutcomes: function (sBackendUrl, sCaseId) {
            var that = this;
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/outcomes")
                .then(function (res) {
                    if (res.ok) return res.json();
                    return [];
                })
                .then(function (outcomes) {
                    that.getView().getModel("exec").setProperty("/historical_outcomes", outcomes || []);
                })
                .catch(function (e) {
                    console.warn("Could not load outcomes: " + e.message);
                });
        },

        _loadFailedPlans: function (sBackendUrl, sCaseId) {
            var that = this;
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/failed-plans")
                .then(function (res) {
                    if (res.ok) return res.json();
                    return [];
                })
                .then(function (failed) {
                    that.getView().getModel("exec").setProperty("/failed_plans", failed || []);
                })
                .catch(function (e) {
                    console.warn("Could not load failed plans: " + e.message);
                });
        },

        _loadAuditHistory: function (sBackendUrl, sCaseId) {
            var that = this;
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/audit")
                .then(function (res) { return res.json(); })
                .then(function (events) {
                    var oModel = that.getView().getModel("exec");
                    var sorted = (events || []).sort(function (a, b) {
                        return new Date(b.timestamp) - new Date(a.timestamp);
                    });
                    oModel.setProperty("/audit_events", sorted);
                })
                .catch(function (e) {
                    console.warn("Could not load audit events: " + e.message);
                });
        },

        onRefreshProgress: function () {
            if (this._sCurrentCaseId) {
                this.loadExecutionData(this._sCurrentCaseId);
                MessageToast.show("Telemetry synchronized from SAP adapter.");
            }
        },

        _postSimulationEvent: function (payload, sSuccessMsg) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var sCaseId = this._sCurrentCaseId;
            var that = this;
            var oPage = this.byId("executionMonitoringPage");
            if (oPage) oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/event", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(function (res) {
                if (!res.ok) {
                    return res.json().then(function (e) { throw new Error(e.message || "Simulation failed"); });
                }
                return res.json();
            })
            .then(function (updatedProgress) {
                var oModel = that.getView().getModel("exec");
                oModel.setData(Object.assign({}, oModel.getData(), updatedProgress));
                that._loadAuditHistory(sBackendUrl, sCaseId);
                MessageToast.show(sSuccessMsg);

                if (updatedProgress.is_success) {
                    that._loadOutcomes(sBackendUrl, sCaseId);
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "RESOLVED");
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatusText", "Resolved & Archived");
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatusState", "Success");
                    that.getOwnerComponent().getModel("app").setProperty("/stageStep", 8);
                    that.getOwnerComponent().getModel("app").setProperty("/currentStageName", "Outcome (Resolved)");
                    MessageBox.success("Success: 100% quantity recovered within tolerance. Case closed and precedent archived!");
                } else if (updatedProgress.is_failed) {
                    that._loadFailedPlans(sBackendUrl, sCaseId);
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "RECOVERY_PLANNING");
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatusText", "Replanning Required");
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatusState", "Error");
                    that.getOwnerComponent().getModel("app").setProperty("/stageStep", 3);
                    that.getOwnerComponent().getModel("app").setProperty("/currentStageName", "Recovery Replanning");
                    MessageBox.warning("Escalation: Recovery plan failed. Case returned to Recovery Planning for cycle 2.");
                } else {
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatus", updatedProgress.execution_status);
                    that.getOwnerComponent().getModel("app").setProperty("/caseStatusText", updatedProgress.execution_status.replace(/_/g, " "));
                    that.getOwnerComponent().getModel("app").setProperty("/stageStep", 6);
                }
            })
            .catch(function (err) {
                MessageBox.error("Telematics simulation error: " + err.message);
            })
            .finally(function () {
                setTimeout(function() {
                    if (oPage) oPage.setBusy(false);
                }, 1000);
            });
        },

        onSimulateSupplierConfirmed: function () {
            var oModel = this.getView().getModel("exec");
            var nQty = oModel.getProperty("/baseline/planned_quantity") || 500;
            this._postSimulationEvent({
                status: "SUPPLIER_CONFIRMED",
                confirmed_quantity: nQty,
                description: "Supplier confirmed purchase order and staged freight for carrier pickup."
            }, "Supplier confirmed order.");
        },

        onSimulateDispatched: function () {
            var oModel = this.getView().getModel("exec");
            var sLoc = oModel.getProperty("/baseline/source_location") || "Regional Supply Hub";
            this._postSimulationEvent({
                status: "SHIPMENT_DISPATCHED",
                location: sLoc + " Central Logistics Dock",
                description: "Carrier completed loading and freight departed inbound facility."
            }, "Shipment dispatched by carrier.");
        },

        onSimulateInTransit: function () {
            this._postSimulationEvent({
                status: "IN_TRANSIT",
                location: "Frankfurt Aviation Hub (Customs Cleared)",
                description: "Waybill cleared customs inspection. Connecting flight scheduled on time."
            }, "In transit telematics ping received.");
        },

        onSimulateDelay: function () {
            var that = this;
            var oModel = this.getView().getModel("exec");
            var sCurrentEta = oModel.getProperty("/current_estimated_arrival") || "2026-09-30";
            var oDate = new Date(sCurrentEta);
            oDate.setDate(oDate.getDate() + 2);
            var sDelayedEta = oDate.toISOString().split("T")[0];

            this._postSimulationEvent({
                status: "DELAYED",
                delay_days: 2,
                estimated_arrival: sDelayedEta,
                reason: "Airspace traffic congestion over continental corridor caused 2-day delivery slip.",
                description: "Carrier telematics update: Arrival postponed by 2 days."
            }, "Shipment delay recorded. Deviation calculated.");
        },

        onSimulateDelivered: function () {
            var oModel = this.getView().getModel("exec");
            var nQty = oModel.getProperty("/baseline/planned_quantity") || 500;
            var sPlant = oModel.getProperty("/baseline/target_plant_name") || "Plant Inbound Dock";
            this._postSimulationEvent({
                status: "DELIVERED",
                confirmed_quantity: nQty,
                location: sPlant + " Bay 3 Receiving",
                description: nQty + " units received, verified against packing slip, and registered in SAP inventory."
            }, "Delivery confirmed. Disruption marked RESOLVED.");
        },

        onSimulateFailure: function () {
            var oModel = this.getView().getModel("exec");
            var nShortQty = Math.round((oModel.getProperty("/baseline/planned_quantity") || 500) * 0.2);
            this._postSimulationEvent({
                status: "FAILED",
                confirmed_quantity: nShortQty,
                reason: "Air transport cargo hold canceled due to severe regulatory airspace embargo; 80% quantity shortage.",
                description: "Critical failure in transport corridor. Shortage exceeds accepted operational tolerance."
            }, "Execution failure recorded. Escalated to recovery planning.");
        },

        onTakeActionAlert: function () {
            MessageToast.show("Intervention acknowledged. Supply Chain Controller dispatching expedited ground transit.");
        },

        onReplanRecovery: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            MessageToast.show("Triggering recovery replanning cycle for " + sCaseId);
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: sCaseId });
        },

        onGoToMonitoring: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            this.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: sCaseId });
        },

        onGoToOutcome: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            WorkflowNavHelper.completeStage(sCaseId, 6, 6);
            this.getOwnerComponent().getRouter().navTo("outcome", { caseId: sCaseId });
        },

        /**
         * Planner confirms recovery was successful.
         * Calls /resolve to mark case RESOLVED on backend, then navigates to Outcome page.
         */
        onRecoveryCompleted: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var that = this;

            var oPage = this.byId("executionMonitoringPage");
            if (oPage) oPage.setBusy(true);

            // Call the backend /resolve endpoint — sets case status = RESOLVED
            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/resolve", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            })
            .then(function (res) {
                if (!res.ok) {
                    // Non-fatal: still navigate even if resolve fails
                    console.warn("QUADS: /resolve returned " + res.status + " — navigating anyway");
                }
                return res.json().catch(function () { return {}; });
            })
            .catch(function () {
                // Network error — still navigate
            })
            .finally(function () {
                if (oPage) oPage.setBusy(false);
                // Mark stage 6 done, set completedStage=7 in localStorage
                WorkflowNavHelper.completeStage(sCaseId, 6, 7);
                // Update app model so header badge shows Resolved
                var oAppModel = that.getOwnerComponent().getModel("app");
                oAppModel.setProperty("/caseStatus", "RESOLVED");
                oAppModel.setProperty("/caseStatusText", "Resolved & Archived");
                oAppModel.setProperty("/caseStatusState", "Success");

                MessageToast.show("Recovery confirmed. Case resolved — navigating to Outcome.");
                setTimeout(function () {
                    that.getOwnerComponent().getRouter().navTo("outcome", { caseId: sCaseId });
                }, 600);
            });
        },

        /**
         * Planner marks recovery as NOT completed — shows reason dialog.
         */
        onRecoveryNotCompleted: function () {
            this._showReopenReasonDialog();
        },

        _showReopenReasonDialog: function () {
            var that = this;
            var sCaseId = this._sCurrentCaseId || "CASE-0001";

            // Build inline dialog
            sap.ui.require(["sap/m/Dialog", "sap/m/TextArea", "sap/m/Button", "sap/m/VBox", "sap/m/Text", "sap/m/Label"], function (Dialog, TextArea, Button, VBox, Text, Label) {
                var oTextArea = new TextArea({
                    id: "quadsReopenReasonArea",
                    width: "100%",
                    rows: 4,
                    placeholder: "Describe why recovery was not completed (e.g. insufficient quantity received, logistics failure, etc.)",
                    maxLength: 500
                });

                var oDialog = new Dialog({
                    title: "Restart Planning Cycle — Reason Required",
                    titleAlignment: "Center",
                    content: [
                        new VBox({
                            items: [
                                new Text({ text: "Please provide a reason before restarting the recovery planning cycle. The case will be reset to Impact Analysis and all previous plans will be cleared.", class: "sapUiSmallMarginBottom" }),
                                new Label({ text: "Reason for Restart", design: "Bold", class: "sapUiTinyMarginBottom" }),
                                oTextArea
                            ]
                        }).addStyleClass("sapUiSmallMargin")
                    ],
                    beginButton: new Button({
                        text: "Confirm Restart",
                        type: "Reject",
                        icon: "sap-icon://journey-change",
                        press: function () {
                            var sReason = oTextArea.getValue().trim();
                            if (!sReason || sReason.length < 10) {
                                MessageToast.show("Please enter a reason (minimum 10 characters).");
                                return;
                            }
                            oDialog.setBusy(true);
                            var sBackendUrl = that.getOwnerComponent().getModel("app").getProperty("/backendUrl");

                            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/reopen", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ reason: sReason })
                            })
                            .then(function (res) {
                                if (!res.ok) throw new Error("Server error: " + res.status);
                                return res.json();
                            })
                            .then(function (caseData) {
                                oDialog.close();
                                // Clear localStorage for this case so the route guard re-syncs from backend
                                window.localStorage.removeItem("quads_completed_stage_" + sCaseId);
                                window.localStorage.removeItem("quads_completed_stage_" + sCaseId + "_migrated");
                                window.localStorage.removeItem("quads_priority_" + sCaseId);
                                window.localStorage.removeItem("quads_selected_plan_" + sCaseId);

                                MessageToast.show("Planning cycle restarted (Cycle " + (caseData.planning_cycle || 2) + "). Returning to Impact Analysis.");

                                setTimeout(function () {
                                    that.getOwnerComponent().getRouter().navTo("impactAnalysis", { caseId: sCaseId });
                                }, 800);
                            })
                            .catch(function (err) {
                                oDialog.setBusy(false);
                                MessageBox.error("Failed to restart planning cycle: " + err.message);
                            });
                        }
                    }),
                    endButton: new Button({
                        text: "Cancel",
                        type: "Transparent",
                        press: function () { oDialog.close(); }
                    }),
                    afterClose: function () { oDialog.destroy(); }
                });

                oDialog.open();
            });
        },

        onReturnToPlanning: function () {
            var sCaseId = this._sCurrentCaseId || "CASE-0001";
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: sCaseId });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("cases");
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        },

        // --- Formatters for New Design ---
        // --- Formatters for New Design ---
        formatMissing: function(val) {
            if (val === undefined || val === null || val === "") return "—";
            return val;
        },
        formatStrategy: function(val) {
            if (!val) return "—";
            if (val === "INTER_PLANT_TRANSFER") return "INTER-PLANT TRANSFER";
            return val.replace(/_/g, " ");
        },
        formatDate: function(sDate) {
            if (!sDate) return "—";
            var oDate = new Date(sDate);
            if (isNaN(oDate.getTime())) return sDate;
            var aMonths = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            var day = String(oDate.getDate()).padStart(2, '0');
            var hours = String(oDate.getHours()).padStart(2, '0');
            var minutes = String(oDate.getMinutes()).padStart(2, '0');
            return day + " " + aMonths[oDate.getMonth()] + " " + oDate.getFullYear() + ", " + hours + ":" + minutes;
        },
        formatDateOnly: function(sDate) {
            if (!sDate) return "—";
            var oDate = new Date(sDate);
            if (isNaN(oDate.getTime())) return sDate;
            var aMonths = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            var day = String(oDate.getDate()).padStart(2, '0');
            return day + " " + aMonths[oDate.getMonth()] + " " + oDate.getFullYear();
        },
        formatCurrency: function(val) {
            if (val === undefined || val === null || val === "") return "—";
            return "$" + Number(val).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        },
        formatStatusColor: function(sStatus) {
            if (!sStatus) return "None";
            var s = sStatus.toUpperCase();
            if (s.indexOf("ON TRACK") !== -1 || s.indexOf("ON_TRACK") !== -1 || s.indexOf("IN TRANSIT") !== -1 || s.indexOf("IN_TRANSIT") !== -1 || s.indexOf("DELIVERED") !== -1 || s.indexOf("SUCCESS") !== -1 || s.indexOf("ACCEPTED") !== -1) {
                return "Success";
            }
            if (s.indexOf("DELAY") !== -1 || s.indexOf("AT RISK") !== -1 || s.indexOf("AT_RISK") !== -1 || s.indexOf("WARNING") !== -1) {
                return "Warning";
            }
            if (s.indexOf("FAIL") !== -1 || s.indexOf("ERROR") !== -1 || s.indexOf("CRITICAL") !== -1) {
                return "Error";
            }
            return "None";
        },
        formatStatusText: function(sStatus) {
            if (!sStatus) return "—";
            return sStatus.replace(/_/g, " ").toUpperCase();
        },
        formatDelayDaysToMin: function(delayDays) {
            if (delayDays === undefined || delayDays === null) return "—";
            var mins = Number(delayDays) * 1440;
            return mins + " min";
        },
        formatDelayState: function(delayDays) {
            if (delayDays === undefined || delayDays === null) return "None";
            var mins = Number(delayDays) * 1440;
            return mins === 0 ? "Success" : "Error";
        },
        formatCurrentLocation: function(events) {
            if (!events || events.length === 0) return "—";
            return events[events.length - 1].location || "—";
        },
        formatTrackerStepState: function(events, stepName) {
            if (!events) return "upcoming";
            var mapping = {
                "Plan Confirmed": "ACCEPTED",
                "Execution Initiated": "ACCEPTED",
                "Inventory Allocated": "SUPPLIER_CONFIRMED",
                "Dispatch Ready": "SHIPMENT_CREATED",
                "Picked Up": "SHIPMENT_DISPATCHED",
                "In Transit": "IN_TRANSIT",
                "Arrived at Destination": "DELIVERED",
                "Inventory Received": "DELIVERED"
            };
            var targetStatus = mapping[stepName];
            var hasStatus = false;
            if (events && events.length > 0) {
                for (var i = 0; i < events.length; i++) {
                    if (events[i].status === targetStatus) hasStatus = true;
                }
            }
            if (!hasStatus) return "upcoming";
            var lastEventStatus = events[events.length - 1].status;
            var isCurrent = (targetStatus === lastEventStatus);
            if (isCurrent) {
                if (stepName === "Plan Confirmed" && lastEventStatus === "ACCEPTED") return "completed";
                if (stepName === "Arrived at Destination" && lastEventStatus === "DELIVERED") return "completed";
                return "current";
            }
            return "completed";
        },
        formatTrackerIconSrc: function(events, stepName) {
            var state = this.formatTrackerStepState(events, stepName);
            if (state === "completed") return "sap-icon://accept";
            if (state === "current") return "sap-icon://circle-task-2";
            return "";
        }
    });
});
