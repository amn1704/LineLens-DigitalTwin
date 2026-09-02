# LineLens Phase 3 reproducible demo

Use the frontend and backend URLs in `docs/DEVELOPMENT.md`. The values evolve from the Twin, so exact decimals can differ slightly with selection timing.

1. Open **Dashboard**, click **Reset simulation**, set speed to **8×**, and leave the view in **Twin**.
2. Select **Chassis Marriage**. Show its current Twin estimate, station-specific expected cycle, residual, confidence, and low Bottleneck Risk.
3. Briefly switch **Observed → Twin** to explain the progression from available evidence to the assimilated current-state estimate. Return to **Twin**.
4. In the Chassis Marriage inspector, click **Simulate process drift**. This injects only a gradual fixture-alignment delay into the physical process.
5. Watch the estimated cycle and residual rise over roughly 20–35 real seconds at 8×. Point out that risk follows persistent Twin evidence; a single slow cycle does not immediately create a severe alert.
6. Before obvious line disruption, show rising Bottleneck Risk and separate Forecast Confidence. Expand **Why risk is rising** to show actual cycle, residual/trend, takt pressure, incoming queue growth, and completion-rate evidence.
7. Switch to **Forecast**. Confirm the banner says **Forecast view · No intervention · simulation-derived** so future and current state cannot be confused.
8. Select **+5m**. Show the thin amber predicted route/rings, ghost queue occupancy at Chassis Marriage/Trim where projected, and downstream starvation impacts for Wheel & Torque and later stations. Existing solid status rings remain the current state.
9. Select **+10m**. Show current-to-projected throughput, peak queue/WIP, upstream blocking, downstream starvation, and End-of-Line/line output loss where produced by this particular snapshot.
10. Open **Analytics**. Show the selected station's Observed/Twin/Expected history, residual, Bottleneck Risk trend, and dashed no-action queue trajectory.
11. Open **Alerts**. Show deduplicated FORECAST threshold/impact events. INFO initializes validation; NOTICE/WARNING are used before CRITICAL.
12. Return to **Dashboard → Twin**. Leave the scenario running. The live factory continues independently; the Forecast view never mutated it.
13. Allow the simulation to pass the +2m validation checkpoint. Open **Alerts** and show queue MAE, accumulator MAE, throughput error, and state accuracy. Longer checkpoints fill at +5m and +10m.
14. When sustained Trim blocking or downstream starvation occurs, show the measured prediction lead time and impact-ETA error in the validation summary.
15. Optionally test resilience: reset, select Chassis Marriage, click **Drop**, and compare its lower prediction confidence while a Twin estimate and forecast remain available. Select Legacy **Trim Station** to show risk accepts inferred Twin state with appropriately lower confidence.
16. Finish by clicking **Reset simulation**, restoring **Twin** mode, and confirming the factory is healthy with no injected noise or dropout.

The intended story is: observations update the evolving Twin; persistent station-specific deviation raises an interpretable risk; a disposable clone of that same Twin reveals the likely no-action future; live operation later provides synthetic validation.
