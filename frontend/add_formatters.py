with open('/Users/srisaran/Quads/frontend/webapp/controller/Decision.controller.js', 'r') as f:
    content = f.read()

formatters = """
        formatConstraintIcon_SOURCE_INVENTORY_AVAILABLE: function(constraints) { return this._getConstraintIcon(constraints, "SOURCE_INVENTORY_AVAILABLE"); },
        formatConstraintColor_SOURCE_INVENTORY_AVAILABLE: function(constraints) { return this._getConstraintColor(constraints, "SOURCE_INVENTORY_AVAILABLE"); },
        formatConstraintTextClass_SOURCE_INVENTORY_AVAILABLE: function(constraints) { return this._getConstraintTextClass(constraints, "SOURCE_INVENTORY_AVAILABLE"); },

        formatConstraintIcon_SOURCE_SAFETY_STOCK: function(constraints) { return this._getConstraintIcon(constraints, "SOURCE_SAFETY_STOCK"); },
        formatConstraintColor_SOURCE_SAFETY_STOCK: function(constraints) { return this._getConstraintColor(constraints, "SOURCE_SAFETY_STOCK"); },
        formatConstraintTextClass_SOURCE_SAFETY_STOCK: function(constraints) { return this._getConstraintTextClass(constraints, "SOURCE_SAFETY_STOCK"); },

        formatConstraintIcon_DESTINATION_CAPACITY_LIMIT: function(constraints) { return this._getConstraintIcon(constraints, "DESTINATION_CAPACITY_LIMIT"); },
        formatConstraintColor_DESTINATION_CAPACITY_LIMIT: function(constraints) { return this._getConstraintColor(constraints, "DESTINATION_CAPACITY_LIMIT"); },
        formatConstraintTextClass_DESTINATION_CAPACITY_LIMIT: function(constraints) { return this._getConstraintTextClass(constraints, "DESTINATION_CAPACITY_LIMIT"); },

        formatConstraintIcon_TRANSPORT_CAPACITY_LIMIT: function(constraints) { return this._getConstraintIcon(constraints, "TRANSPORT_CAPACITY_LIMIT"); },
        formatConstraintColor_TRANSPORT_CAPACITY_LIMIT: function(constraints) { return this._getConstraintColor(constraints, "TRANSPORT_CAPACITY_LIMIT"); },
        formatConstraintTextClass_TRANSPORT_CAPACITY_LIMIT: function(constraints) { return this._getConstraintTextClass(constraints, "TRANSPORT_CAPACITY_LIMIT"); },

        formatConstraintIcon_RECOVERY_QTY_TARGET: function(constraints) { return this._getConstraintIcon(constraints, "RECOVERY_QTY_TARGET"); },
        formatConstraintColor_RECOVERY_QTY_TARGET: function(constraints) { return this._getConstraintColor(constraints, "RECOVERY_QTY_TARGET"); },
        formatConstraintTextClass_RECOVERY_QTY_TARGET: function(constraints) { return this._getConstraintTextClass(constraints, "RECOVERY_QTY_TARGET"); },

        formatConstraintIcon_STOCKOUT_ARRIVAL_LIMIT: function(constraints) { return this._getConstraintIcon(constraints, "STOCKOUT_ARRIVAL_LIMIT"); },
        formatConstraintColor_STOCKOUT_ARRIVAL_LIMIT: function(constraints) { return this._getConstraintColor(constraints, "STOCKOUT_ARRIVAL_LIMIT"); },
        formatConstraintTextClass_STOCKOUT_ARRIVAL_LIMIT: function(constraints) { return this._getConstraintTextClass(constraints, "STOCKOUT_ARRIVAL_LIMIT"); },

        formatConstraintIcon_GOVERNING_RULE_BREACHED: function(constraints) { return this._getConstraintIcon(constraints, "GOVERNING_RULE_BREACHED"); },
        formatConstraintColor_GOVERNING_RULE_BREACHED: function(constraints) { return this._getConstraintColor(constraints, "GOVERNING_RULE_BREACHED"); },
        formatConstraintTextClass_GOVERNING_RULE_BREACHED: function(constraints) { return this._getConstraintTextClass(constraints, "GOVERNING_RULE_BREACHED"); },

        _getConstraint: function(constraints, name) {
            if (!constraints) return null;
            for (var i = 0; i < constraints.length; i++) {
                if (constraints[i].constraint_name === name) return constraints[i];
            }
            return null;
        },
        _getConstraintIcon: function(constraints, name) {
            var c = this._getConstraint(constraints, name);
            if (!c) return "sap-icon://minuend";
            return c.satisfied ? "sap-icon://accept" : "sap-icon://decline";
        },
        _getConstraintColor: function(constraints, name) {
            var c = this._getConstraint(constraints, name);
            if (!c) return "#8f9ea8";
            return c.satisfied ? "#2b7d2b" : "#bb0000";
        },
        _getConstraintTextClass: function(constraints, name) {
            var c = this._getConstraint(constraints, name);
            if (!c) return "textMuted";
            return c.satisfied ? "textDark" : "textCritical";
        },
"""

# Insert right before formatCurrency
content = content.replace('formatCurrency: function(val) {', formatters + '\n        formatCurrency: function(val) {')

# Also wait! "production icon and uppercase title PRODUCTION IMPACT, a status badge on the right FULFILLED green when production quantity restored is at least the required quantity, otherwise PARTIAL amber"
# I should update formatProductionText/State!
content = content.replace('''
        formatProductionState: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "None";
            return fulfilled >= target ? "Success" : (fulfilled > 0 ? "Warning" : "Error");
        },
        formatProductionText: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "—";
            return fulfilled >= target ? "PROTECTED" : "IMPACTED";
        },
''', '''
        formatProductionState: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "None";
            return fulfilled >= target ? "Success" : "Warning";
        },
        formatProductionText: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "—";
            return fulfilled >= target ? "FULFILLED" : "PARTIAL";
        },
''')

content = content.replace('''
        formatCustomerState: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "None";
            return fulfilled >= target ? "Success" : (fulfilled > 0 ? "Warning" : "Error");
        },
        formatCustomerText: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "—";
            return fulfilled >= target ? "PROTECTED" : "IMPACTED";
        },
''', '''
        formatCustomerState: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "None";
            return fulfilled >= target ? "Success" : "Error";
        },
        formatCustomerText: function(fulfilled, target) {
            if (fulfilled === undefined || target === undefined || fulfilled === null || target === null) return "—";
            return fulfilled >= target ? "PROTECTED" : "AT RISK";
        },
''')

with open('/Users/srisaran/Quads/frontend/webapp/controller/Decision.controller.js', 'w') as f:
    f.write(content)

print("Formatters updated!")
