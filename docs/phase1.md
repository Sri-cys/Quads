# Quads Phase 1 Scope & Boundary Specification

## 1. Absolute Phase 1 Boundary

QUADS Phase 1 focuses exclusively on Disruption Ingestion, Triage, and **Agent 1 (Impact Analysis)**, concluding at **Human Checkpoint 1**.

```
DISRUPTION
    ↓
INGESTION
    ↓
CASE CREATION
    ↓
TRIAGE
    ↓
AGENT 1 — IMPACT ANALYSIS
    ↓
DETERMINISTIC BUSINESS CALCULATIONS
    ↓
GEMINI EXPLANATION
    ↓
HUMAN CHECKPOINT 1
    ↓
[ TIME / COST / RISK / BALANCED ]
    ↓
STOP (Phase 1 Complete)
```

## 2. Hard Governance Rule: Stopping at Checkpoint 1

After Checkpoint 1 is approved by the human planner:
- **NO** candidate recovery plans are generated.
- **NO** recovery options are ranked.
- **NO** transport optimization or lane re-routing is executed.
- **NO** calls to Agent 2 or Agent 3 are triggered.
- **NO** purchase orders or freight bookings are modified.
- **NO** shipment monitoring or reinforcement learning occurs.

The UI displays:
> **"Checkpoint 1 approved."**  
> **"Recovery Planning is ready for Phase 2."**  
> *"Phase 1 complete — Recovery Planning is available in Phase 2."*

## 3. Supported Scenarios & Demo Data
Phase 1 provides 8 fully-worked mock supply chain cases spanning all four severity tiers:

| Tier | Case ID | Supplier | Material | Plant | Primary Trigger | Days of Cover |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `CASE-0001` | Global Chips (SUP-001) | Microcontroller MCU-32 (MAT-001) | Munich Hub (PLANT-001) | DoC &le; 3 Days & Safety Buffer Breached | 2.0 Days |
| **CRITICAL** | `CASE-0002` | Apex Battery (SUP-002) | Li-Ion Cell Pack 48V (MAT-002) | Austin Plant (PLANT-002) | Zero Available Inventory & Supply Gap | 0.0 Days |
| **HIGH** | `CASE-0003` | Rhine Forgings (SUP-003) | Titanium Drive Shaft (MAT-003) | Munich Hub (PLANT-001) | Safety Stock Breached & DoC &le; 7 Days | 5.0 Days |
| **HIGH** | `CASE-0004` | Nordic Hydraulic (SUP-004) | Hydraulic Valve H-90 (MAT-004) | Curitiba Plant (PLANT-003) | Safety Stock Breached & DoC &le; 7 Days | 6.0 Days |
| **MEDIUM** | `CASE-0005` | Pacific Harness (SUP-005) | Automotive Wiring Loom (MAT-005) | Austin Plant (PLANT-002) | Buffer Intact, DoC &le; 14 Days | 10.0 Days |
| **MEDIUM** | `CASE-0006` | Global Chips (SUP-001) | LiDAR Sensor Array (MAT-006) | Munich Hub (PLANT-001) | Transit Gap Risk, DoC &le; 14 Days | 12.0 Days |
| **LOW** | `CASE-0007` | Bavaria Fasteners (SUP-006) | Hex Bolt Assembly (MAT-007) | Munich Hub (PLANT-001) | Abundant Stock Buffer | 30.0 Days |
| **LOW** | `CASE-0008` | Nordic Hydraulic (SUP-004) | Silicone Seal Gasket (MAT-008) | Curitiba Plant (PLANT-003) | Healthy Stock Buffer | 25.0 Days |

---

## 4. End-to-End Section 29 Verification Scenario

1. Open Quads Control Tower.
2. Navigate to **New Disruption**.
3. Enter:
   - Supplier: `SUP-001`
   - Material: `MAT-001`
   - Plant: `PLANT-001`
   - Description: `"Supplier shipment delayed by 5 days."`
4. Click **ANALYZE DISRUPTION**.
5. Automated LangGraph workflow ingests, triages, and computes deterministic impact (DoC = 2.0 days, Severity = CRITICAL).
6. Gemini generates executive briefing grounded strictly in deterministic numbers.
7. User arrives at **Checkpoint 1**.
8. User selects **TIME** priority.
9. System records decision and writes immutable audit log entry.
10. System displays: *"Checkpoint 1 approved. Recovery Planning is ready for Phase 2."*
11. Execution explicitly terminates.
