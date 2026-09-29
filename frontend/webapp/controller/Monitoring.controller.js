sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageBox, MessageToast, WorkflowNavHelper) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.Monitoring", {
        onInit: function () {
            var oModel = new JSONModel({
                tracking_events: [],
                planned_quantity: 0,
                actual_quantity: 0,
                planned_arrival: "—",
                current_eta: "—",
                planned_cost: 0,
                actual_cost: 0,
                planned_status: "In Transit",
                current_status: "Pending",
                delay_days: 0,
                cost_variance: 0,
                track_status: "PENDING",
                track_status_display: "Pending",
                track_state: "None"
            });
            this.getView().setModel(oModel, "mon");

            var oRouter = this.getOwnerComponent().getRouter();
            ["monitoring", "monitoringAlt"].forEach(function (r) {
                var oR = oRouter.getRoute(r);
                if (oR) oR.attachPatternMatched(this._onPatternMatched, this);
            }, this);
        },

        _onPatternMatched: function (oEvent) {
            var sCaseId = oEvent.getParameter("arguments").caseId;
            if (!sCaseId) {
                sCaseId = this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            }
            this._sCaseId = sCaseId;
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.loadMonitoringData(sCaseId);
        },

        loadMonitoringData: function (sCaseId) {
            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("mon");
            var oPage = this.byId("monitoringPage");
            if (oPage) oPage.setBusy(true);

            fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/execution/progress")
                .then(function (res) {
                    if (res.status === 404) return null;
                    if (!res.ok) throw new Error("HTTP " + res.status);
                    return res.json();
                })
                .then(function (progress) {
                    if (!progress) {
                        oModel.setProperty("/track_status", "PENDING");
                        return;
                    }

                    var aEvents = progress.tracking_events || [];
                    var baseline = progress.baseline || {};
                    var deviation = progress.deviation || {};

                    // Determine track status
                    var sTrack = "PENDING";
                    var sTrackDisplay = "Pending";
                    var sTrackState = "None";

                    if (progress.is_success) {
                        sTrack = "COMPLETED";
                        sTrackDisplay = "Completed";
                        sTrackState = "Success";
                    } else if (progress.is_failed) {
                        sTrack = "FAILED";
                        sTrackDisplay = "Failed";
                        sTrackState = "Error";
                    } else if (deviation.delay_days > 2) {
                        sTrack = "DELAYED";
                        sTrackDisplay = "Delayed";
                        sTrackState = "Error";
                    } else if (deviation.delay_days > 0) {
                        sTrack = "AT_RISK";
                        sTrackDisplay = "At Risk";
                        sTrackState = "Warning";
                    } else if (aEvents.length > 0) {
                        sTrack = "ON_TRACK";
                        sTrackDisplay = "On Track";
                        sTrackState = "Success";
                    }

                    // Latest status
                    var sCurrentStatus = progress.execution_status || "ACCEPTED";
                    if (aEvents.length > 0) {
                        sCurrentStatus = aEvents[aEvents.length - 1].status;
                    }

                    oModel.setData({
                        tracking_events: aEvents,
                        planned_quantity: baseline.planned_quantity || 0,
                        actual_quantity: progress.current_confirmed_quantity || 0,
                        planned_arrival: baseline.planned_arrival_date || "—",
                        current_eta: progress.current_estimated_arrival || baseline.planned_arrival_date || "—",
                        planned_cost: baseline.planned_total_cost || 0,
                        actual_cost: progress.current_estimated_cost || 0,
                        planned_status: "In Transit",
                        current_status: sCurrentStatus.replace(/_/g, " "),
                        delay_days: deviation.delay_days || 0,
                        cost_variance: deviation.cost_variance || 0,
                        track_status: sTrack,
                        track_status_display: sTrackDisplay,
                        track_state: sTrackState
                    });
                })
                .catch(function (err) {
                    MessageBox.error("Failed to load monitoring data: " + err.message);
                })
                .finally(function () {
                    if (oPage) oPage.setBusy(false);
                });
        },

        onRefresh: function () {
            this.loadMonitoringData(this._sCaseId);
            MessageToast.show("Telemetry refreshed");
        },

        onGoToOutcome: function () {
            this.getOwnerComponent().getRouter().navTo("outcome", { caseId: this._sCaseId });
        },

        onGoToExecution: function () {
            this.getOwnerComponent().getRouter().navTo("executionMonitoring", { caseId: this._sCaseId });
        },

        onReturnToPlanning: function () {
            this.getOwnerComponent().getRouter().navTo("recoveryPlanning", { caseId: this._sCaseId });
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        }
    });
});
