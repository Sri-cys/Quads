import sys

xml = """
                    <!-- No Plan Selected Message -->
                    <VBox visible="{= !${dec>/selectedPlan/plan_id} }" class="sapUiSmallMarginTop">
                        <VBox class="sapChoiceCard quadsDecisionSummaryCard sapUiSmallMarginBottom" style="padding: 24px;">
                            <HBox alignItems="Center">
                                <core:Icon src="sap-icon://message-information" size="24px" class="sapUiSmallMarginEnd" color="#0B63A8" />
                                <VBox>
                                    <Title text="No recovery plan selected." level="H2" class="bold textDark" />
                                    <Text text="Go back to Recovery Planning and select a plan." class="textMuted" />
                                </VBox>
                            </HBox>
                        </VBox>
                    </VBox>

                    <!-- Confirm Recovery Plan Cards (Visible once a plan is chosen) -->
                    <VBox visible="{= !!${dec>/selectedPlan/plan_id} }" class="sapUiSmallMarginTop">
                        <!-- Card 1: Plan Header Card -->
                        <VBox class="quadsDecisionHeaderCard sapUiSmallMarginBottom">
                            <HBox class="sapUiTinyMarginBottom" wrap="Wrap">
                                <Label text="{= ${dec>/selectedPlan/version} ? ${dec>/selectedPlan/plan_id} + ' (' + ${dec>/selectedPlan/version} + ')' : ${dec>/selectedPlan/plan_id} }" class="quadsDecisionPlanChip sapUiTinyMarginEnd" />
                                <Label text="{= ${dec>/selectedPlan/is_feasible} ? 'FEASIBLE' : 'NOT FEASIBLE' }" class="{= ${dec>/selectedPlan/is_feasible} ? 'quadsDecisionFeasibleChip' : 'quadsDecisionInfeasibleChip' } sapUiTinyMarginEnd">
                                    <layoutData><FlexItemData growFactor="0"/></layoutData>
                                </Label>
                                <Label text="{= ${dec>/selectedPlan/operational_risk} ? ${dec>/selectedPlan/operational_risk} + ' RISK' : '—' }" class="quadsDecisionRiskChip" />
                            </HBox>
                            <Title text="{path: 'dec>/selectedPlan/strategy', formatter: '.formatStrategy'}" level="H2" class="bold textDark sapUiTinyMarginBottom" />
                            
                            <!-- Source to Destination Flow -->
                            <HBox alignItems="Center" class="quadsDecisionRouteBox sapUiSmallMarginTop">
                                <VBox class="quadsFlowNode">
                                    <Text text="SOURCE" class="quadsDecisionRouteLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/source_name', formatter: '.formatMissing'}" class="quadsDecisionRouteValue" />
                                </VBox>
                                <VBox class="quadsFlowArrow sapUiSmallMarginBeginEnd">
                                    <core:Icon src="sap-icon://shipping-status" size="1.2rem" color="#0B63A8" />
                                </VBox>
                                <VBox class="quadsFlowNode">
                                    <Text text="DESTINATION" class="quadsDecisionRouteLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/target_plant_name', formatter: '.formatMissing'}" class="quadsDecisionRouteValue" />
                                </VBox>
                            </HBox>
                        </VBox>

                        <!-- Card 2: Recovery Summary Card -->
                        <VBox class="quadsDecisionSummaryCard sapUiSmallMarginBottom">
                            <HBox alignItems="Center" class="sapUiSmallMarginBottom">
                                <core:Icon src="sap-icon://list" size="1rem" class="sapUiTinyMarginEnd textDark" />
                                <Title text="RECOVERY SUMMARY" level="H3" class="bold textDark" />
                            </HBox>
                            <layout:Grid defaultSpan="XL4 L4 M6 S12" hSpacing="1" vSpacing="1">
                                <VBox class="quadsDecisionSummaryTile">
                                    <Text text="Transfer Quantity" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/recovered_quantity', formatter: '.formatMissing'} units" class="bold textLarge textDark" />
                                </VBox>
                                <VBox class="quadsDecisionSummaryTile">
                                    <Text text="Recovery Time" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/recovery_days', formatter: '.formatMissing'} Days" class="bold textLarge textDark" />
                                </VBox>
                                <VBox class="quadsDecisionSummaryTile">
                                    <Text text="Expected ETA" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/expected_arrival_date', formatter: '.formatDate'}" class="bold textLarge textDark" />
                                </VBox>
                                <VBox class="quadsDecisionSummaryTile">
                                    <Text text="Total Cost" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/total_cost', formatter: '.formatCurrency2Decimals'}" class="bold textLarge textDark" />
                                </VBox>
                                <VBox class="quadsDecisionSummaryTile">
                                    <Text text="Customer Delay" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/selectedPlan/customer_delay_days', formatter: '.formatMissing'} Days" class="bold textLarge quadsDelayText_{path: 'dec>/selectedPlan/customer_delay_days', formatter: '.formatDelayState'}" />
                                </VBox>
                                <VBox />
                            </layout:Grid>
                        </VBox>

                        <!-- Card 3: Impact Cards (Side by Side) -->
                        <layout:Grid defaultSpan="XL6 L6 M12 S12" hSpacing="1" vSpacing="1" class="sapUiSmallMarginBottom">
                            <!-- Production Impact -->
                            <VBox class="quadsDecisionImpactCard quadsDecisionImpactLeft" style="height: 100%;">
                                <HBox alignItems="Center" justifyContent="SpaceBetween" class="sapUiSmallMarginBottom">
                                    <HBox alignItems="Center">
                                        <core:Icon src="sap-icon://factory" size="1rem" class="sapUiTinyMarginEnd textDark" />
                                        <Title text="PRODUCTION IMPACT" level="H3" class="bold textDark" />
                                    </HBox>
                                    <ObjectStatus text="{parts: [{path: 'dec>/selectedPlan/recovered_quantity'}, {path: 'dec>/caseData/affected_quantity'}], formatter: '.formatProductionText'}" state="{parts: [{path: 'dec>/selectedPlan/recovered_quantity'}, {path: 'dec>/caseData/affected_quantity'}], formatter: '.formatProductionState'}" class="bold" inverted="true" />
                                </HBox>
                                <Toolbar height="1px" class="sapUiTinyMarginBottom" style="background:#E2E8F0;border:none;" />
                                <HBox justifyContent="SpaceBetween" class="sapUiTinyMarginBottom">
                                    <Text text="Production ID:" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/caseData/material_id', formatter: '.formatMissing'}" class="bold textDark" style="font-family: monospace;" />
                                </HBox>
                                <HBox justifyContent="SpaceBetween">
                                    <Text text="Quantity Restored:" class="sapContextItemLabel" />
                                    <ObjectStatus text="{path: 'dec>/selectedPlan/recovered_quantity', formatter: '.formatMissing'} units" state="{parts: [{path: 'dec>/selectedPlan/recovered_quantity'}, {path: 'dec>/caseData/affected_quantity'}], formatter: '.formatQtyColor'}" class="bold" />
                                </HBox>
                            </VBox>
                            <!-- Customer Impact -->
                            <VBox class="quadsDecisionImpactCard quadsDecisionImpactRight" style="height: 100%;">
                                <HBox alignItems="Center" justifyContent="SpaceBetween" class="sapUiSmallMarginBottom">
                                    <HBox alignItems="Center">
                                        <core:Icon src="sap-icon://customer" size="1rem" class="sapUiTinyMarginEnd textDark" />
                                        <Title text="CUSTOMER IMPACT" level="H3" class="bold textDark" />
                                    </HBox>
                                    <ObjectStatus text="{parts: [{path: 'dec>/selectedPlan/recovered_quantity'}, {path: 'dec>/caseData/affected_quantity'}], formatter: '.formatCustomerText'}" state="{parts: [{path: 'dec>/selectedPlan/recovered_quantity'}, {path: 'dec>/caseData/affected_quantity'}], formatter: '.formatCustomerState'}" class="bold" inverted="true" />
                                </HBox>
                                <Toolbar height="1px" class="sapUiTinyMarginBottom" style="background:#E2E8F0;border:none;" />
                                <HBox justifyContent="SpaceBetween" class="sapUiTinyMarginBottom">
                                    <Text text="Customer ID:" class="sapContextItemLabel" />
                                    <Text text="{path: 'dec>/caseData/customer_id', formatter: '.formatMissing'}" class="bold textDark" style="font-family: monospace;" />
                                </HBox>
                                <HBox justifyContent="SpaceBetween">
                                    <Text text="Quantity Fulfilled:" class="sapContextItemLabel" />
                                    <ObjectStatus text="{path: 'dec>/selectedPlan/recovered_quantity', formatter: '.formatMissing'} units" state="{parts: [{path: 'dec>/selectedPlan/recovered_quantity'}, {path: 'dec>/caseData/affected_quantity'}], formatter: '.formatQtyColor'}" class="bold" />
                                </HBox>
                            </VBox>
                        </layout:Grid>

                        <!-- Card 4: Pre-conditions Card -->
                        <VBox class="quadsDecisionPreconditionsCard">
                            <HBox alignItems="Center" justifyContent="SpaceBetween" class="sapUiSmallMarginBottom">
                                <HBox>
                                    <core:Icon src="sap-icon://paste" size="1.5rem" class="sapUiSmallMarginEnd textDark" />
                                    <VBox>
                                        <Title text="{= ${dec>/selectedPlan/is_feasible} ? 'ALL PRE-CONDITIONS SATISFIED' : 'PRE-CONDITIONS NOT MET' }" level="H3" class="bold textDark" />
                                        <Text text="{= ${dec>/selectedPlan/is_feasible} ? 'All operational checks have passed verification.' : ${dec>/selectedPlan/failed_constraints_count} + ' checks failed' }" class="textMuted" />
                                    </VBox>
                                </HBox>
                                <ObjectStatus text="{= ${dec>/selectedPlan/is_feasible} ? 'READY TO EXECUTE' : 'NOT READY' }" state="{= ${dec>/selectedPlan/is_feasible} ? 'Success' : 'Error' }" icon="{= ${dec>/selectedPlan/is_feasible} ? 'sap-icon://accept' : 'sap-icon://decline' }" inverted="true" class="bold" />
                            </HBox>
                            <Toolbar height="1px" class="sapUiSmallMarginBottom" style="background:#E2E8F0;border:none;" />
                            
                            <layout:Grid defaultSpan="XL6 L6 M12 S12" hSpacing="1" vSpacing="1">
                                <!-- Row 1: Source inventory available -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_SOURCE_INVENTORY_AVAILABLE'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_SOURCE_INVENTORY_AVAILABLE'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="Source inventory available" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_SOURCE_INVENTORY_AVAILABLE'}" />
                                </HBox>
                                <!-- Row 2: Safety stock maintained -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_SOURCE_SAFETY_STOCK'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_SOURCE_SAFETY_STOCK'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="Safety stock maintained" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_SOURCE_SAFETY_STOCK'}" />
                                </HBox>
                                <!-- Row 3: Destination capacity available -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_DESTINATION_CAPACITY_LIMIT'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_DESTINATION_CAPACITY_LIMIT'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="Destination capacity available" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_DESTINATION_CAPACITY_LIMIT'}" />
                                </HBox>
                                <!-- Row 4: Transportation capacity available -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_TRANSPORT_CAPACITY_LIMIT'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_TRANSPORT_CAPACITY_LIMIT'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="Transportation capacity available" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_TRANSPORT_CAPACITY_LIMIT'}" />
                                </HBox>
                                <!-- Row 5: Required quantity covered -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_RECOVERY_QTY_TARGET'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_RECOVERY_QTY_TARGET'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="Required quantity covered" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_RECOVERY_QTY_TARGET'}" />
                                </HBox>
                                <!-- Row 6: Recovery within allowed stockout window -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_STOCKOUT_ARRIVAL_LIMIT'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_STOCKOUT_ARRIVAL_LIMIT'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="Recovery within allowed stockout window" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_STOCKOUT_ARRIVAL_LIMIT'}" />
                                </HBox>
                                <!-- Row 7: No governing rule breached (spans both) -->
                                <HBox alignItems="Center" class="quadsDecisionCheckRow">
                                    <layoutData><layout:GridData span="XL12 L12 M12 S12" /></layoutData>
                                    <core:Icon src="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintIcon_GOVERNING_RULE_BREACHED'}" color="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintColor_GOVERNING_RULE_BREACHED'}" size="1rem" class="sapUiSmallMarginEnd" />
                                    <Text text="No governing rule breached" class="{path: 'dec>/selectedPlan/constraints', formatter: '.formatConstraintTextClass_GOVERNING_RULE_BREACHED'}" />
                                </HBox>
                            </layout:Grid>
                        </VBox>
                    </VBox>
"""
with open('new_cards.xml', 'w') as f:
    f.write(xml)
print("Saved to new_cards.xml")
