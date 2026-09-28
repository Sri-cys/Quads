import os

css_content = '''

/* --- QUADS CUSTOM IMPACT ANALYSIS DESIGN (MOCKUP MATCH) --- */
.quadsPageBg { background-color: #F5F6F8 !important; }
.quadsPagePadding { padding: 24px; max-width: 1400px; margin: 0 auto; }

/* Breadcrumbs */
.quadsBreadcrumbRow { margin-bottom: 16px; }
.quadsBreadcrumbLink { color: #0A6ED1; cursor: pointer; font-size: 14px; font-weight: 500; }
.quadsBreadcrumbText { color: #556B82; font-size: 14px; margin: 0 4px; }
.quadsBreadcrumbActive { color: #1D2D3E; font-size: 14px; font-weight: 600; }

/* Global Cards */
.quadsWhiteCard {
    background: #FFFFFF;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    border: 1px solid #E5E7EB;
    padding: 20px;
}
.quadsWhiteCard.borderCritical {
    border: 1px solid #FECACA;
}

/* Header Card */
.quadsHeaderCard { padding: 16px 24px; }
.quadsHeaderWarningIconBox {
    background: #FEF2F2;
    border-radius: 6px;
    width: 48px; height: 48px;
}
.quadsHeaderWarningIcon { font-size: 24px !important; color: #DC2626 !important; }
.quadsHeaderTitle { font-size: 20px !important; font-weight: 700; color: #111827; margin: 0; }
.quadsHeaderBadgeCritical {
    background: #FEF2F2; color: #DC2626; border-radius: 12px;
    padding: 2px 8px; font-size: 12px; font-weight: 600; border: 1px solid #FECACA;
}
.quadsHeaderSubtitle { font-size: 13px; color: #4B5563; margin-top: 4px; }

.quadsHeaderRight { gap: 24px; }
.quadsHeaderMetaBox { display: flex; flex-direction: column; }
.quadsHeaderMetaDivider { width: 1px; background: #E5E7EB; height: 32px; margin: 0 8px; align-self: center; }
.quadsMetaLabel { font-size: 11px; color: #6B7280; margin-bottom: 2px; }
.quadsMetaValueMain { font-size: 13px; font-weight: 600; color: #111827; }
.quadsMetaValueSub { font-size: 12px; color: #6B7280; }
.quadsMetaIcon { font-size: 14px !important; color: #0A6ED1 !important; }
.quadsStatusBadgeWarning { background: #FFFBEB; color: #B45309; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; text-align: center; }
.quadsStatusIconSuccess { font-size: 14px !important; color: #10B981 !important; }
.quadsStatusText { font-size: 13px; font-weight: 600; color: #111827; }

/* 4 KPI Grid */
.quadsImpact4Grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.quadsKpiCard { padding: 16px; }
.quadsKpiIconBox { width: 40px; height: 40px; border-radius: 8px; }
.quadsKpiIconBox.blue { background: #EFF6FF; color: #2563EB; }
.quadsKpiIconBox.blue .sapUiIcon { font-size: 20px !important; color: #2563EB !important; }
.quadsKpiIconBox.red { background: #FEF2F2; color: #DC2626; }
.quadsKpiIconBox.red .sapUiIcon { font-size: 20px !important; color: #DC2626 !important; }
.quadsKpiTitle { font-size: 12px; font-weight: 600; color: #374151; margin-bottom: 4px; }
.quadsKpiValueCritical { font-size: 18px; font-weight: 700; color: #DC2626; }
.quadsKpiValueDark { font-size: 18px; font-weight: 700; color: #111827; }
.quadsKpiSub { font-size: 12px; color: #6B7280; margin-top: 2px; }
.quadsKpiArrow { color: #9CA3AF !important; font-size: 14px !important; }

/* Timeline */
.quadsSectionIcon { font-size: 16px !important; }
.quadsSectionIcon.blue { color: #2563EB !important; }
.quadsSectionTitle { font-size: 15px !important; font-weight: 700; color: #111827; }
.quadsSectionSub { font-size: 13px; color: #6B7280; }
.quadsBtnOutline { border: 1px solid #D1D5DB; color: #0A6ED1; border-radius: 4px; }

.quadsCustomTimelineContainer { position: relative; width: 100%; margin: 32px 0 16px; display: flex; justify-content: space-between; }
.quadsTimelineNode { width: 120px; z-index: 2; position: relative; }
.quadsTlLabel { font-size: 11px; color: #6B7280; margin-bottom: 2px; }
.quadsTlLabel.bold { font-weight: 700; color: #111827; }
.quadsTlLabel.critical { color: #DC2626; }
.quadsTlLabel.future { color: #4B5563; }
.quadsTlDate { font-size: 12px; font-weight: 600; color: #111827; margin-bottom: 12px; }
.quadsTlDate.critical { color: #DC2626; }
.quadsTlDate.future { color: #4B5563; }

.quadsTlIcon { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; }
.quadsTlIcon.done { background: #10B981; color: #FFF; font-size: 12px !important; }
.quadsTlIcon.done .sapUiIcon { color: #FFF !important; }
.quadsTlIcon.currentBox { background: #2563EB; }
.quadsTlIconCurrent { color: #FFF !important; font-size: 12px !important; }
.quadsTlIcon.criticalBox { background: #DC2626; }
.quadsTlIconCritical { color: #FFF !important; font-size: 12px !important; }
.quadsTlIcon.futureBoxCritical { background: #DC2626; }
.quadsTlIcon.futureBox { background: #9CA3AF; }

.quadsTlLabelBoxCritical { background: #FECACA; padding: 2px 8px; border-radius: 4px; margin-bottom: 4px; }
.quadsTlLabelBoxText { color: #B91C1C; font-size: 11px; font-weight: 600; }

.quadsTlLine { flex: 1; height: 2px; position: relative; top: 18px; margin: 0 -40px; z-index: 1; }
.quadsTlLine.done { background: #10B981; }
.quadsTlLine.current { background: #10B981; }
.quadsTlLine.future { background: #E5E7EB; }
.delayDashedLine { border-bottom: 2px dashed #DC2626; width: 100%; position: absolute; top: 50%; }
.delayLineBox { flex: 2; height: 40px; position: relative; margin: 0 -30px; top: -2px;}
.delayLineText { color: #DC2626; font-size: 12px; font-weight: 600; background: #FFF; padding: 0 4px; position: relative; z-index: 2; top: 20px;}

/* 3-Column Details */
.quadsImpact3Grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: start; }
.quadsDetailCard { padding: 24px; }
.quadsDetailRow { margin-bottom: 8px; width: 100%; }
.quadsDetailLabel { font-size: 13px; color: #6B7280; }
.quadsDetailValue { font-size: 13px; font-weight: 600; color: #111827; }
.quadsDetailValueCritical { font-size: 13px; font-weight: 700; color: #DC2626; }
.quadsAlertBanner { background: #FEF2F2; color: #DC2626; border: 1px solid #FECACA; padding: 10px; border-radius: 4px; font-size: 12px; font-weight: 500; width: 100%; }
.quadsAlertBanner .sapUiIcon { color: #DC2626 !important; }
.quadsBadgeWarning { background: #FEF3C7; color: #D97706; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.quadsBadgeCritical { background: #FEE2E2; color: #DC2626; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.quadsBadgeCriticalBox { background: #FEF2F2; border: 1px solid #FECACA; color: #DC2626; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }

/* 2-Column Details */
.quadsImpact2Grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.quadsPlantGrid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
.quadsFinancial3Grid { display: grid; grid-template-columns: 1fr auto 1fr auto 1fr; gap: 16px; align-items: center; }
.quadsFinBox { display: flex; flex-direction: column; align-items: center; text-align: center; }
.quadsFinLabel { font-size: 12px; color: #6B7280; margin-bottom: 4px; }
.quadsFinValue { font-size: 16px; font-weight: 700; color: #111827; }
.quadsFinSub { font-size: 11px; color: #9CA3AF; margin-top: 2px; }
.quadsFinDivider { width: 1px; background: #E5E7EB; height: 40px; }
.quadsFinTotalBox { background: #FEF2F2; border-radius: 6px; padding: 12px 16px; margin-top: 16px; }
.quadsFinTotalLabel { font-size: 14px; font-weight: 700; color: #111827; }
.quadsFinTotalIcon { color: #DC2626 !important; font-size: 18px !important; }
.quadsFinTotalValue { font-size: 18px; font-weight: 700; color: #DC2626; }
.quadsFinTotalArrow { color: #DC2626 !important; font-size: 14px !important; }

/* Propagation */
.quadsPropagationContainer { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 16px; justify-content: space-between; }
.quadsPropNode { display: flex; align-items: center; flex: 1; }
.quadsPropIconBox { width: 32px; height: 32px; background: #FFF; border-radius: 6px; border: 1px solid #E2E8F0; display: flex; align-items: center; justify-content: center; }
.quadsPropIconBox .sapUiIcon { color: #2563EB !important; font-size: 16px !important; }
.quadsPropLabel { font-size: 11px; color: #6B7280; }
.quadsPropValue { font-size: 13px; font-weight: 700; color: #111827; }
.quadsPropArrow { color: #94A3B8 !important; font-size: 14px !important; margin: 0 16px; }

/* Buttons */
.quadsProceedBtn { min-width: 200px; height: 36px; font-weight: 600; }
'''

with open('c:/Users/jasan/Quads-saran/Quads/frontend/webapp/css/style.css', 'a') as f:
    f.write(css_content)

print("CSS appended.")
