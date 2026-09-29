sap.ui.define([
    "sap/ui/core/UIComponent",
    "sap/ui/Device",
    "com/quads/supplychain/model/models",
    "com/quads/supplychain/controller/WorkflowNavHelper"
], function (UIComponent, Device, models, WorkflowNavHelper) {
    "use strict";

    return UIComponent.extend("com.quads.supplychain.Component", {
        metadata: {
            manifest: "json"
        },

        init: function () {
            // call the base component's init function
            UIComponent.prototype.init.apply(this, arguments);

            // set the device model
            this.setModel(models.createDeviceModel(), "device");

            // set the app model
            this.setModel(models.createAppModel(), "app");

            // attach workflow route guard
            WorkflowNavHelper.initRouteGuard(this.getRouter());

            // enable routing
            this.getRouter().initialize();
        }
    });
});
