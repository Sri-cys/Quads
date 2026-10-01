sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/ui/model/json/JSONModel",
    "sap/m/MessageBox",
    "sap/m/MessageToast",
    "sap/ui/core/Fragment",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (Controller, JSONModel, MessageBox, MessageToast, Fragment, WorkflowNavHelper) {
    "use strict";

    return Controller.extend("com.quads.supplychain.controller.RecoveryPlanning", {
        _inFlight: {},

        onInit: function () {
            var oModel = new JSONModel({
                state: "RUNNING", // RUNNING, COMPLETED, FAILED
                agent2_status: "RUNNING", // RUNNING, COMPLETED, FAILED
                agent3_status: "PENDING", // PENDING, RUNNING, COMPLETED, FAILED
                errorMessage: "",
                case_id: "",
                priority: "BALANCED",
                material_id: "",
                material_name: "",
                target_quantity: 0,
                days_of_cover: 0,
                candidates: [],
                feasible_plans: [],
                infeasible_plans: [],
                all_evaluated_plans: [],
                total_plans_count: 0,
                selectedPlanId: null,
                selectedPlanVersion: "v1"
            });
            this.getView().setModel(oModel, "rec");

            var oInspectModel = new JSONModel({});
            this.getView().setModel(oInspectModel, "inspect");

            var oRouter = this.getOwnerComponent().getRouter();
            ["recoveryPlanning", "recoveryPlanningKebab", "recoveryPlanningAlt", "recoveryPlans", "recoveryPlansAlt"].forEach(function (r) {
                var oR = oRouter.getRoute(r);
                if (oR) oR.attachPatternMatched(this._onPatternMatched, this);
            }, this);
        },

        onExit: function () {
            var oRouter = this.getOwnerComponent().getRouter();
            ["recoveryPlanning", "recoveryPlanningKebab", "recoveryPlanningAlt", "recoveryPlans", "recoveryPlansAlt"].forEach(function (r) {
                var oR = oRouter.getRoute(r);
                if (oR) oR.detachPatternMatched(this._onPatternMatched, this);
            }, this);
        },

        _onPatternMatched: function (oEvent) {
            var sCaseId = oEvent.getParameter("arguments").caseId;
            if (!sCaseId) {
                sCaseId = this.getOwnerComponent().getModel("app").getProperty("/selectedCaseId") || "CASE-0001";
            }
            this._sCurrentCaseId = sCaseId;
            sap.ui.require(["com/quads/supplychain/controller/WorkflowNavHelper"], function(WorkflowNavHelper) {
                WorkflowNavHelper.setStepperState(this._sCurrentCaseId, 4);
            }.bind(this));
            this.getOwnerComponent().getModel("app").setProperty("/selectedCaseId", sCaseId);
            this.getView().getModel("rec").setProperty("/state", "RUNNING");
            this.loadRecoveryData(sCaseId);
        },

        loadRecoveryData: function (sCaseId) {
            if (this._inFlight[sCaseId]) {
                return;
            }
            this._inFlight[sCaseId] = true;

            var sBackendUrl = this.getOwnerComponent().getModel("app").getProperty("/backendUrl");
            var oModel = this.getView().getModel("rec");
            var that = this;

            oModel.setProperty("/state", "RUNNING");
            oModel.setProperty("/agent2_status", "RUNNING");
            oModel.setProperty("/agent3_status", "PENDING");
            oModel.setProperty("/errorMessage", "");

            Promise.all([
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId).then(function (r) {
                    if (!r.ok) throw new Error("Case record not found");
                    return r.json();
                }),
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/impact").then(function (r) {
                    if (r.ok) return r.json();
                    return {};
                })
            ])
            .then(function (caseAndImpact) {
                var caseData = caseAndImpact[0] || {};
                var impactData = caseAndImpact[1] || {};

                // Route guard: Priority must be saved before Recovery Planning
                // Rely strictly on the backend. If not set, silently redirect to Checkpoint1.
                // (The route guard's MessageToast already informed the user.)
                if (!caseData.checkpoint1_decision && caseData.status !== "CHECKPOINT_APPROVED" && caseData.status !== "RECOVERY_APPROVED" && caseData.status !== "RESOLVED") {
                    that._inFlight[sCaseId] = false;
                    that.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: sCaseId });
                    return Promise.reject(new Error("SILENT_ABORT"));
                }

                var sPriority = caseData.checkpoint1_decision || "BALANCED";

                // Step 1: Check candidates from Agent 2
                fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/candidates")
                        .then(function (candRes) {
                            if (candRes.ok) return candRes.json();
                            return null;
                        })
                        .then(function (candidateSet) {
                            if (candidateSet && candidateSet.candidates) {
                                oModel.setProperty("/candidates", candidateSet.candidates);
                                oModel.setProperty("/agent2_status", "COMPLETED");
                                oModel.setProperty("/agent3_status", "RUNNING");
                            }

                            // Step 2: Fetch full evaluation from Agent 3
                            return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan")
                                .then(function (r) {
                                    if (r.ok) return r.json();
                                    // Trigger generation if not present
                                    return fetch(sBackendUrl + "/api/v1/cases/" + sCaseId + "/recovery/plan", {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json" },
                                        body: JSON.stringify({ priority: sPriority })
                                    }).then(function (res) {
                                        if (!res.ok) {
                                            return res.text().then(function(text) {
                                                var msg = text;
                                                try {
                                                    var json = JSON.parse(text);
                                                    msg = json.detail ? (json.detail.message || json.detail) : (json.message || text);
                                                } catch(e) {}
                                                throw new Error("Failed to evaluate recovery plans (HTTP " + res.status + "): " + msg);
                                            });
                                        }
                                        return res.json();
                                    });
                                });
                        })
                    .then(function (planSetData) {
                        var feasible = planSetData.feasible_plans || [];
                        var infeasible = planSetData.infeasible_plans || [];
                        var allPlans = feasible.concat(infeasible);

                        // Sort all plans numerically by extracting the number from plan_id (e.g. PLAN-01 -> 1)
                        allPlans.sort(function(a, b) {
                            var numA = parseInt((a.plan_id || "").replace(/[^0-9]/g, ""), 10) || 0;
                            var numB = parseInt((b.plan_id || "").replace(/[^0-9]/g, ""), 10) || 0;
                            return numA - numB;
                        });

                        // Once Agent 3 is completed, update the candidates list to the fully evaluated plans
                        oModel.setProperty("/candidates", allPlans);

                        oModel.setProperty("/case_id", sCaseId);
                        oModel.setProperty("/priority", sPriority);
                        oModel.setProperty("/material_id", caseData.material_id || "MAT-001");
                        oModel.setProperty("/material_name", caseData.material_name || "Lithium Battery Pack");
                        oModel.setProperty("/target_quantity", impactData.supply_gap_quantity || caseData.affected_quantity || 1000);
                        oModel.setProperty("/days_of_cover", impactData.days_of_cover !== undefined ? impactData.days_of_cover : 2.0);
                        oModel.setProperty("/feasible_plans", feasible);
                        oModel.setProperty("/infeasible_plans", infeasible);
                        oModel.setProperty("/all_evaluated_plans", allPlans);
                        oModel.setProperty("/total_plans_count", allPlans.length);

                        var bestRecoveryDays = null;
                        feasible.forEach(function(p) {
                            if (bestRecoveryDays === null || p.recovery_days < bestRecoveryDays) {
                                bestRecoveryDays = p.recovery_days;
                            }
                        });
                        oModel.setProperty("/best_recovery_time", bestRecoveryDays !== null ? bestRecoveryDays : "—");
                        oModel.setProperty("/available_inventory", impactData.available_inventory !== undefined ? impactData.available_inventory : 0);
                        oModel.setProperty("/baseline_cost", impactData.financial_exposure); // fallback if baseline is in financial_exposure, or undefined
                        
                        setTimeout(function() {
                            oModel.setProperty("/state", "COMPLETED");
                            oModel.setProperty("/agent2_status", "COMPLETED");
                            oModel.setProperty("/agent3_status", "COMPLETED");
                            that.getOwnerComponent().getModel("app").setProperty("/caseStatus", "DECISION_PENDING");
                        }, 2500);
                        // Intentionally do NOT set stageStep to 6 here. The user must click "Proceed to Decision"
                        // to logically complete this stage in the UI, or it will be updated by App.controller.js on route change.
                    })
                    .catch(function (err) {
                        var sMessage = err.message;
                        if (sMessage === "Load failed" || sMessage === "Failed to fetch" || sMessage.indexOf("NetworkError") !== -1) {
                            sMessage = "Cannot reach the server";
                        }
                        oModel.setProperty("/state", "FAILED");
                        oModel.setProperty("/agent3_status", "FAILED");
                        oModel.setProperty("/errorMessage", sMessage);
                    })
                    .finally(function() {
                        that._inFlight[sCaseId] = false;
                    });
            })
            .catch(function (err) {
                if (err.message === "SILENT_ABORT") {
                    return;
                }
                var sMessage = err.message;
                if (sMessage === "Load failed" || sMessage === "Failed to fetch" || sMessage.indexOf("NetworkError") !== -1) {
                    sMessage = "Cannot reach the server";
                }
                oModel.setProperty("/state", "FAILED");
                oModel.setProperty("/errorMessage", sMessage);
                that._inFlight[sCaseId] = false;
            });
        },

        onRefreshPlans: function () {
            // Clear the inFlight flag so the refresh fetch actually runs
            this._inFlight[this._sCurrentCaseId] = false;
            this.loadRecoveryData(this._sCurrentCaseId);
        },

        onSelectPlan: function (oEvent) { console.log("[CARD-UI] onSelectPlan triggered");
            var oContext = oEvent.getSource().getBindingContext("rec");
            if (!oContext) return;
            var planObj = oContext.getObject();
            var oModel = this.getView().getModel("rec");
            var currentSelected = oModel.getProperty("/selectedPlanId");

            if (currentSelected === planObj.plan_id) {
                oModel.setProperty("/selectedPlanId", null);
            } else {
                oModel.setProperty("/selectedPlanId", planObj.plan_id);
            }
        },

        onInspectPlan: function (oEvent) {
            var oContext = oEvent.getSource().getBindingContext("rec");
            if (!oContext) return;
            var planObj = oContext.getObject();

            // Inject target_quantity from the parent rec model so the dialog has it
            var oRecModel = this.getView().getModel("rec");
            planObj.target_quantity = planObj.target_quantity || oRecModel.getProperty("/target_quantity") || 0;

            var oInspectModel = this.getView().getModel("inspect");
            oInspectModel.setData(planObj);

            var oView = this.getView();
            if (!this._pInspectDialog) {
                this._pInspectDialog = Fragment.load({
                    id: oView.getId(),
                    name: "com.quads.supplychain.view.InspectPlanDialog",
                    controller: this
                }).then(function (oDialog) {
                    oView.addDependent(oDialog);
                    return oDialog;
                });
            }
            this._pInspectDialog.then(function (oDialog) {
                oDialog.open();
            });
        },

        onCloseInspectDialog: function () {
            if (this._pInspectDialog) {
                this._pInspectDialog.then(function (oDialog) {
                    oDialog.close();
                });
            }
        },

        onProceedToDecision: function () {
            var sCaseId = this._sCurrentCaseId;
            var oModel = this.getView().getModel("rec");
            var selectedPlanId = oModel.getProperty("/selectedPlanId");

            if (!selectedPlanId) {
                MessageToast.show("Select a recovery plan before proceeding");
                return;
            }

            var sNormalizedId = selectedPlanId.split(" ")[0];
            window.localStorage.setItem("quads_selected_plan_" + sCaseId, sNormalizedId);

            WorkflowNavHelper.completeStage(sCaseId, 4, 5);
            this.getOwnerComponent().getRouter().navTo("decision", { caseId: sCaseId });
        },

        onBackToPriority: function () {
            this.getOwnerComponent().getRouter().navTo("checkpoint1", { caseId: this._sCurrentCaseId });
        },

        onWorkflowStagePress: function (oEvent) {
            WorkflowNavHelper.onWorkflowStagePress(oEvent, this);
        },

        // Formatters
        formatCount: function(val) {
            if (Array.isArray(val)) return val.length;
            if (typeof val === "number") return val;
            return 0;
        },

        formatCurrency: function(val) {
            if (!val && val !== 0) return "—";
            return "$" + Number(val).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
        },

        formatDate: function(sDate) {
            if (!sDate) return "—";
            var oDate = new Date(sDate);
            if (isNaN(oDate.getTime())) return sDate;
            var aMonths = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            var day = String(oDate.getDate()).padStart(2, '0');
            return day + " " + aMonths[oDate.getMonth()];
        },

        formatPluralPlans: function(val) {
            var count = 0;
            if (Array.isArray(val)) {
                count = val.length;
            } else if (typeof val === "number") {
                count = val;
            }
            return count === 1 ? "1 Plan" : count + " Plans";
        },
        
        formatPlanTitle: function(planId) {
            if (!planId) return "—";
            // Strip any version suffix if present in the ID itself, e.g. "PLAN-02 (v1)" -> "PLAN-02"
            return planId.split(" ")[0];
        },
        
        formatPlanNumberBadge: function(sPlanId) {
            if (!sPlanId) return "";
            var num = sPlanId.replace(/[^0-9]/g, "");
            return "P" + (num ? parseInt(num, 10) : "");
        },

        formatPlanBadgeClass: function(bFeasible) {
            return bFeasible ? "quadsPlanBadgeBlue quadsPlanNumberBadge" : "quadsPlanBadgeRed quadsPlanNumberBadge";
        },
        
        isPlanSelected: function(planId, selectedPlanId) {
            if (!planId || !selectedPlanId) return false;
            return planId.split(" ")[0] === selectedPlanId.split(" ")[0];
        },
        
        formatFeasibilityText: function(bFeasible) {
            if (bFeasible === undefined || bFeasible === null) return "PRE-EVALUATION";
            return bFeasible ? "FEASIBLE" : "NOT FEASIBLE";
        },
        
        formatFeasibilityState: function(bFeasible) {
            if (bFeasible === undefined || bFeasible === null) return "None";
            return bFeasible ? "Success" : "Error";
        },

        formatFulfilmentPercent: function(fulfilled, required) {
            if (!required || required === 0) return 0;
            return Math.round((fulfilled / required) * 100);
        },

        formatFulfilmentColor: function(fulfilled, required) {
            if (!required || required === 0) return "Error";
            var pct = (fulfilled / required) * 100;
            if (pct >= 95) return "Success";
            if (pct >= 70) return "Warning";
            return "Error";
        },

        formatCostDiff: function(cost, baseline) {
            if (cost === undefined || cost === null || baseline === undefined || baseline === null || baseline === 0) return "";
            var diff = ((cost - baseline) / baseline) * 100;
            var sign = diff > 0 ? "+" : "";
            return sign + Math.round(diff) + "% vs normal";
        },

        formatCostDiffColor: function(cost, baseline) {
            if (!cost || !baseline) return "None";
            return cost > baseline ? "Error" : "Success";
        },
        
        formatSeverityState: function(risk) {
            if (!risk) return "None";
            var r = risk.toUpperCase();
            if (r.indexOf("LOW") !== -1) return "Success";
            if (r.indexOf("MEDIUM") !== -1 || r.indexOf("AMBER") !== -1) return "Warning";
            if (r.indexOf("HIGH") !== -1 || r.indexOf("CRITICAL") !== -1 || r.indexOf("RED") !== -1) return "Error";
            return "None";
        },

        formatRiskState: function(risk) {
            if (!risk) return "None";
            var r = risk.toUpperCase();
            if (r === "LOW") return "Success";
            if (r === "MEDIUM") return "Warning";
            if (r === "HIGH" || r === "CRITICAL") return "Error";
            return "None";
        },

        formatCostL: function(val) {
            if (val === undefined || val === null || val === "") return "—";
            var n = Number(val);
            if (isNaN(n)) return "—";
            // Format as ₹X.XXL (lakhs notation like the reference)
            if (n >= 100000) {
                return "₹" + (n / 100000).toFixed(2) + "L";
            }
            return "₹" + n.toLocaleString();
        },

        formatStrategyLabel: function(s) {
            if (!s) return "—";
            return s.replace(/_/g, " ");
        }
    });
});
