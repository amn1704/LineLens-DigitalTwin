# Phase 4 Quality Twin Demo Guide

## Overview

Phase 4 transforms each vehicle's digital thread into an evolving quality twin that can identify defect risk before the defect is discovered at the normal late inspection point.

## Core Architecture

### Quality Prediction Flow

```
Physical Process
→ Observations
→ Vehicle Digital Thread  
→ Quality Feature Builder
→ Quality Predictor
→ Predicted Risk
```

### Ground Truth Separation

```
Physical Process
→ Latent Quality Ground Truth (hidden)
→ Eventual Inspection Result
→ Ground Truth Label
```

**Critical**: The predictor never receives:
- `quality_drift_active`
- `scenario_name` 
- `injected_fault`
- `defect_truth`
- Future inspection result
- Future process data

## Demo Sequence

### 1. Reset to Healthy Baseline

1. Click the **Reset** button in the simulation controls
2. Verify the factory starts in a healthy 20-minute warm state
3. Check that most vehicles show low quality risk (quality indicators absent or subtle)

### 2. Open Quality Workspace

1. Navigate to the **Quality** tab in the primary navigation
2. Observe the healthy monitoring state:
   - The **ALL** vehicle list contains active recent units, sorted by current risk.
   - The newest active unit is selected automatically; its Quality Twin, retained risk progression, and Digital Build Record are visible immediately.
   - **Inspection required: 0** is a status summary, not an empty workspace.
   - Genealogy explicitly reports that no enriched common factor is detected and names the monitored factor families.

### 3. Show Healthy Vehicle Digital Thread

1. Select any vehicle from the Dashboard 3D scene
2. View its compact **Digital Build Record** in the center Quality panel.
3. Expand **Robotic Weld** to inspect vehicle-owned cell, gun, electrode lot, energy deviation, and Twin confidence evidence.
4. Note the low current risk, independent confidence, normal state, and standard EOL recommendation.

### 4. Activate Weld Process Drift Scenario

1. Navigate to the **Quality** workspace
2. Click **"Simulate weld drift"** button
3. Observe the scenario state and its physical evidence begin changing in the right panel: energy deviation, process variability, tool condition, and exposed-unit count.
4. Physical scenario: Weld Gun WG-04, Electrode Cap Lot EC-17 experiencing gradual wear

### 5. Focus Robotic Weld Cell in 3D

1. Return to **Dashboard** tab
2. Select **BIW-02 Robotic Weld Cell** from the station list
3. Observe the station inspector showing weld process telemetry
4. Note the process signals will begin drifting over time:
   - Weld power becomes less consistent
   - Process variance increases
   - Occasional cycle extensions

### 6. Observe Vehicles Leaving Robotic Weld

1. Watch vehicles exiting the Robotic Weld Cell
2. Some vehicles will begin accumulating quality risk
3. The quality indicator (subtle ring) appears around risky vehicles
4. Risk levels vary based on drift severity and vehicle sensitivity

### 7. Select Downstream High-Risk Vehicle

1. Click on a vehicle showing quality indicators
2. Open the Vehicle Inspector
3. Navigate to **Quality** tab for detailed view

### 8. Show Quality Risk Evidence

For a high-risk vehicle, observe:

**Quality Twin Information:**
- Risk: 60-85% (depending on drift exposure)
- Confidence: 70-90% (based on signal quality)
- Likely issue: "Body geometry / weld integrity"
- Likely origin: "Robotic Weld Cell"
- Recommended inspection: "Body Shop Exit"

**Evidence Panel:**
- Weld energy deviation: +X.X%
- Weld variance: X.X× baseline
- Robot cell: RW-CELL-02
- Weld gun: WG-04
- Station residual: +X.X s

### 9. Show Multiple Vehicles with Similar Risk

1. Remain in the **Quality** workspace.
2. Observe WATCH and INSPECT vehicles rise naturally to the top of the ALL list while healthy units remain visible.
3. Multiple vehicles show elevated risk (60-85%)
4. All share "Body geometry / weld integrity" as likely issue
5. All trace back to "Robotic Weld Cell" as likely origin

### 10. Open Quality Genealogy Analysis

1. In the **Quality** workspace, observe the Genealogy panel
2. Common factors emerge showing:

**Typical Genealogy Results:**
```
WG-04
Present in: 8/10 risky units
Baseline: 18%
Risk lift: 4.4×

RW-CELL-02  
Present in: 9/10
Baseline: 42%
Risk lift: 2.1×

Electrode Cap Lot EC-17
Present in: 7/10
Baseline: 22%
Risk lift: 3.2×
```

3. Likely process origin: "Robotic Weld Cell"
4. Analysis confidence: 0.65-0.85 (meaningful correlation detected)

### 11. Follow Risky Vehicle Downstream

1. Select a high-risk vehicle from the Quality list
2. Watch it move through Paint Shop and Final Assembly
3. Despite being downstream, the vehicle retains:
   - Original quality prediction
   - Risk attribution to Robotic Weld Cell
   - Recommended inspection point (Body Shop Exit)
4. This demonstrates the digital thread value - risk travels with the vehicle

### 12. Observe EOL Inspection Results

1. Wait for vehicles to reach **FA-05 End-of-Line Inspection**
2. Some vehicles will fail inspection with:
   - Result: "FAIL - Body geometry / weld integrity"
   - Defect family: Body geometry / weld integrity
3. Compare the preserved risk-progression history with the revealed result. The validation panel reports measured lead time only after a confirmed result; it does not manufacture an early outcome.

### 13. Show Prediction Lead Time

In the Quality metrics panel, observe measured precision, recall, false-positive rate, lead time, and early-interception opportunity after EOL results arrive. Before that point the panel explicitly says **Awaiting EOL outcomes** and uses `—` for undefined values.

### 14. Show Quality Validation Metrics

The Quality workspace right panel shows:

**Quality Validation Metrics:**
- Total predictions: X vehicles
- Defect rate: X% (synthetic baseline during drift)
- True positives: X (correctly predicted defects)
- False positives: X (predicted but passed)
- Precision: XX% (how many predictions were correct)
- Recall: XX% (how many actual defects were caught)
- Early interception: XX% (defects caught before EOL)

### 15. Demonstrate Healthy Operation

1. Click **"Stop drift"** to end the weld scenario
2. Reset simulation to healthy baseline
3. Run for several minutes without scenarios
4. Verify:
   - Quality risk remains low (<15% for most vehicles)
   - Genealogy shows no strong false clusters
   - Quality metrics show low defect rate
   - No unnecessary inspection recommendations

### 16. Demonstrate Telemetry Dropout Resilience

1. Start a healthy simulation
2. Go to **Machines** tab
3. Select **BIW-02 Robotic Weld Cell**
4. Enable **"Drop telemetry"** for the station
5. Observe:
   - Quality predictions continue using Twin estimates
   - Prediction confidence decreases appropriately
   - Risk estimates remain (with lower confidence)
   - System remains functional despite missing direct signals

## Key Design Principles Demonstrated

### 1. Temporal Leakage Prevention

- Quality features contain only information available at prediction time
- Future stations never appear in earlier snapshots
- EOL results never leak into earlier predictions
- Scenario flags never influence the predictor

### 2. Ground Truth Separation

- Latent defect truth exists only in simulator
- Quality predictor uses only observable evidence
- Inspection results revealed only after actual inspection
- Prediction records remain immutable after outcomes

### 3. Interpretable Evidence

- Risk is explained by actual process evidence
- Feature contributions are calculated from model coefficients
- No "AI magic" - transparent attribution
- Humans can understand why a vehicle is flagged

### 4. Genealogy Correlation vs Causation

- Genealogy finds correlated common factors
- UI explicitly labels as "Suspected common factor"
- Never claims "Root cause confirmed" without validation
- Support/lift statistics provided for transparency

### 5. Digital Thread Value

- Vehicle quality state evolves with production
- Risk attribution travels with the vehicle downstream
- Process history provides complete evidence trail
- Early detection enables targeted intervention

## Technical Architecture Summary

### Backend Components

**Quality Module (`backend/app/quality/`):**
- `features.py`: VehicleQualitySnapshot and QualityFeatureBuilder
- `model.py`: Logistic regression with fallback
- `service.py`: QualityService for predictions and metrics
- `genealogy.py`: GenealogyAnalyzer for common factor detection

**Simulation Extensions:**
- Latent quality state in VehicleRuntime
- Weld process drift scenario in simulator
- Extended process metadata in digital thread
- EOL inspection with ground truth revelation

**API Endpoints:**
- `GET /api/quality/vehicles` - High-risk vehicles list
- `GET /api/quality/vehicles/{id}` - Vehicle quality detail
- `GET /api/quality/genealogy` - Common factor analysis
- `GET /api/quality/metrics` - Quality validation metrics
- `POST /api/simulation/scenarios/weld-drift` - Scenario control

### Frontend Components

**Quality Workspace:**
- All/Watch/Inspect/Confirmed monitored vehicle list with risk levels
- Default selected healthy Quality Twin with evidence and retained risk progression
- Expandable Digital Build Record based on vehicle-owned MES/Twin evidence
- Genealogy analysis with factor enrichment
- Quality metrics dashboard
- Scenario control for weld drift

**3D Scene Indicators:**
- Subtle quality rings around risky vehicles
- Color-coded by risk level (amber/red)
- Only shown for vehicles above WATCH threshold

**Vehicle Inspector Extensions:**
- Quality risk overlay in vehicle display
- Quality detail in dedicated workspace
- Build thread with quality evidence

## Model Validation

### Synthetic Dataset

- **Training size**: 2,400 deterministic synthetic historical vehicles
- **Defect prevalence**: generated from observable weld/process features; it is not a live-simulator label
- **Features**: 10 normalized quality features
- **Prediction checkpoint**: After Robotic Weld (BIW-02)
- **Use**: demonstration calibration only; the live simulator is never used to train or refit the model

### Model Performance (Synthetic)

- **Model**: logistic regression (`quality-logreg-v1`)
- Runtime precision, recall, false positives, lead time, and early-interception opportunity are calculated only after EOL outcomes arrive.
- The application does not present fabricated PR-AUC, Brier, or real-world claims. Those are evaluation work for a held-out production dataset, not a synthetic UI metric.

### Calibration

Vehicles predicted around 70% risk fail more often than vehicles predicted around 20% risk (synthetic validation).

**Important**: This is synthetic calibration for demonstration, not real-world performance.

## Limitations

1. **Synthetic Data**: All metrics are from synthetic production, not real manufacturing
2. **Simplified Physics**: Weld drift model is approximate, not actual welding physics
3. **Single Defect Family**: Primary focus on body/weld integrity, limited paint/fastener modeling
4. **No Real Sensor Data**: All telemetry is synthetic, not connected to actual equipment
5. **Deterministic Randomness**: Seeded randomness for reproducibility, not true process randomness
6. **No Actual Intervention**: System recommends inspection but doesn't perform actions
7. **Simplified Genealogy**: Correlation analysis without causal inference
8. **Temporal Scope**: Demo focuses on immediate production, not long-term quality trends

## Acceptance Checklist

✅ Latent synthetic quality ground truth exists separately from prediction
✅ Predictor cannot access hidden truth  
✅ Weld-process drift changes physical/process evidence only
✅ Each vehicle has an evolving quality state
✅ Feature snapshots contain only information available at prediction time
✅ Deterministic synthetic historical training data exists
✅ Interpretable vehicle-quality model exists (logistic regression)
✅ Quality risk is vehicle-specific
✅ Risk and confidence are separate
✅ Likely defect family is provided
✅ Likely process origin is provided  
✅ Deterministic evidence is provided
✅ Targeted early inspection is recommended
✅ Quality risk can be predicted before EOL
✅ Quality prediction lead time is measured
✅ Multiple exposed vehicles create a cohort
✅ Genealogy analyzes actual digital-thread metadata
✅ Genealogy uses support/lift rather than hardcoded source
✅ Genealogy distinguishes correlation from proven cause
✅ Healthy production does not produce spurious strong genealogy
✅ EOL ground truth eventually becomes available
✅ Stored predictions are compared to later outcomes
✅ Precision/recall/false positives are measured
✅ Synthetic calibration is documented
✅ Telemetry dropout reduces confidence without destroying prediction
✅ Legacy/missing signals are handled honestly
✅ Vehicle 3D quality markers work
✅ Quality workspace works
✅ Dashboard remains uncluttered
✅ Automated backend tests pass
✅ Frontend type-check and production build pass
✅ Phase 3 predictive Twin remains intact
✅ No PPO/RL has been implemented
✅ No autonomous intervention has been implemented

### Acceptance walkthrough

1. Reset, open **Quality**, and inspect the automatically selected healthy vehicle.
2. Expand its Robotic Weld record to show its individual process evidence.
3. Start **Simulate weld drift**. Watch the physical-evidence panel update before the model recommendation appears.
4. Use ALL, WATCH, and INSPECT filters to follow exposed vehicles downstream.
5. Confirm the first INSPECT recommendation is at Body Shop Exit when still reachable, otherwise the next quality hold.
6. Confirm the Genealogy panel identifies suspected common factors only, with support and risk lift.
7. Wait for EOL: inspect the immutable history, actual result, and measured validation metrics.

## Scope boundary

Phase 4 stops at transparent forecasting, inspection recommendation, and retrospective validation. It does not implement autonomous control, PLC integration, reinforcement learning, or intervention optimization.
