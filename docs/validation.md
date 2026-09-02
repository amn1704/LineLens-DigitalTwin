# Validation Methodology

LineLens includes built-in validation to measure how well the predictive Digital Twin performs. Because this is a prototype, validation compares the Digital Twin's predictions against the actual outcomes of the **synthetic simulator**, demonstrating that the architecture works rather than proving real-world plant calibration.

## Bottleneck Validation

When a station shows elevated risk, the system spawns a disposable Forward Twin to predict outcomes at +2m, +5m, and +10m horizons assuming no human intervention. As the physical simulator continues running, LineLens compares those saved predictions against what actually happens.

Metrics recorded include:
- **Queue MAE**: Mean absolute error of physical vehicle queues and accumulators compared to the forecast.
- **Throughput Error**: Difference between the forecasted production rate and actual rolling throughput.
- **State Accuracy**: Percentage of stations where the predicted state (running, blocked, starved) matched the physical reality.
- **Prediction Lead Time**: The time elapsed between when LineLens generated the alert and when sustained disruption (starvation/blocking) actually occurred.

## Quality Validation

The Vehicle Quality Twin predicts defect risks based on process telemetry long before the vehicle reaches the final inspection point. The physical simulator maintains a hidden "ground truth" for each vehicle that is only revealed when the unit completes End-of-Line (EOL) inspection.

Metrics recorded include:
- **Precision / Recall**: Calculated only after EOL outcomes arrive. Precision measures how many predicted defects were actual defects; recall measures how many actual defects were successfully flagged.
- **False Positives**: Vehicles flagged for inspection that passed EOL.
- **Early Interception Opportunity**: The percentage of actual defects that LineLens detected while the vehicle was still in early shops (e.g., Body Shop or Paint), allowing for cheaper rework.
- **Prediction Lead Time**: The time gained between the early quality prediction and the standard EOL discovery.

## Confidence Interpretation

Confidence is tracked separately from Risk. 
- **Twin Confidence** indicates how much the system trusts its state estimate. It drops when sensor telemetry is lost (data gaps) or if the station relies on inferred legacy signals.
- **Prediction Confidence** decays over time. A 10-minute forecast has lower confidence than a 2-minute forecast because slight variations compound.

During a data gap, the Twin retains its last known estimate while confidence decays exponentially. When sensors recover, confidence restores smoothly rather than snapping violently.

## Running Validation in the Prototype

Validation requires time to elapse so predictions can be compared to actual outcomes.

1. **For Bottlenecks**: Open the Demo menu, select *Simulate process drift* for Chassis Marriage. Wait for the +5m and +10m checkpoints to pass. The validation metrics will populate in the right panel and the About/Validation drawer.
2. **For Quality**: Open the Quality tab, start *Simulate weld drift*, and wait for the exposed vehicles to reach the End-of-Line station. Validation metrics will appear in the Quality metrics panel once ground truth is revealed.
