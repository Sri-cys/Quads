with open('/Users/srisaran/Quads/frontend/webapp/css/style.css', 'a') as f:
    f.write('''

/* ---- quadsDecision New Layout ---- */
.quadsDecisionHeaderCard {
    background: #FFFFFF !important;
    border-radius: 6px !important;
    border-left: 4px solid #0B63A8 !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    padding: 1.25rem !important;
    border: 1px solid #E2E8F0;
}

.quadsDecisionSummaryCard, .quadsDecisionImpactCard, .quadsDecisionPreconditionsCard {
    background: #FFFFFF !important;
    border-radius: 6px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    padding: 1.25rem !important;
    border: 1px solid #E2E8F0;
}

.quadsDecisionPlanChip {
    background-color: #e6f2f9 !important;
    color: #0B63A8 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-family: monospace !important;
    font-size: 0.875rem !important;
}

.quadsDecisionFeasibleChip {
    background-color: #e8f5e9 !important;
    color: #2b7d2b !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 0.875rem !important;
    font-weight: bold !important;
}

.quadsDecisionInfeasibleChip {
    background-color: #ffebee !important;
    color: #c62828 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 0.875rem !important;
    font-weight: bold !important;
}

.quadsDecisionRiskChip {
    background-color: #f5f5f5 !important;
    color: #616161 !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 0.875rem !important;
    font-weight: bold !important;
}

.quadsDecisionRouteBox {
    background: #F8FAFC !important;
    border-radius: 8px !important;
    padding: 1rem !important;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid #E2E8F0;
}

.quadsDecisionRouteLabel {
    font-size: 0.75rem !important;
    color: #64748B !important;
    letter-spacing: 0.05rem;
    margin-bottom: 0.25rem;
}

.quadsDecisionRouteValue {
    font-size: 1.1rem !important;
    font-weight: bold !important;
    color: #1D2D3E !important;
}

.quadsDecisionSummaryTile {
    background: #F8FAFC !important;
    border-radius: 6px !important;
    padding: 1rem !important;
    border: 1px solid #E2E8F0;
}

.quadsDecisionImpactLeft {
    margin-right: 0.5rem;
}

.quadsDecisionImpactRight {
    margin-left: 0.5rem;
}

@media (max-width: 600px) {
    .quadsDecisionImpactLeft { margin-right: 0; margin-bottom: 1rem; }
    .quadsDecisionImpactRight { margin-left: 0; }
}

.quadsDecisionCheckRow {
    background: #F8FAFC !important;
    border-radius: 6px !important;
    padding: 0.75rem !important;
    border: 1px solid #E2E8F0;
}

''')
