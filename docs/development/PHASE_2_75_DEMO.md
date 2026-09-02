# LineLens Phase 2.75 reproducible demo

This sequence uses only visible controls. Start with the backend and frontend URLs shown in `docs/DEVELOPMENT.md`.

1. On Dashboard, click **Reset simulation** and leave speed at **8×**.
2. Select **Chassis Marriage**. In Twin mode, point out Estimated, Expected, Residual, Confidence, data age, source, sensor maturity, and Current feed.
3. Under **Testing · synthetic**, move **Inject noise** to **5.0s**. Leave it there for about 12–15 seconds so several assimilations reach history.
4. Open **Analytics**. The dark Observed line fluctuates, the teal Twin estimate is filtered, and the dashed Expected baseline stays nearly flat. The deterministic estimator regression sequence measures variance **17.607 s² observed**, **0.447 s² Twin**, and **0.000 s² Expected**.
5. Return to Dashboard, Chassis Marriage, and set noise to **0.0s**.
6. Click **Drop**. Switch to **Observed**: Current feed reads Unavailable, direct cycle and vehicle data are unavailable, while Sensor maturity remains Full telemetry.
7. Switch to **Twin**: the last valid estimate remains, source becomes **Estimated after data gap**, data age increases, and confidence falls. In Analytics the Observed line has a real gap while Twin and Expected continue.
8. Click **Restore**. The source returns to Full telemetry, data age becomes fresh, the estimate converges without snapping, and confidence recovers progressively. The deterministic regression curve is **68.9% stale → 80.4% → 82.1% → 83.1% → 83.7%** over four restored assimilations.
9. Select **Trim Station** and switch to Observed. Confirm Observed cycle is **No direct signal** / indirect timing. Switch to Twin and show its numeric estimate and lower confidence.
10. Click any visible vehicle in the 3D factory. The right inspector shows its ID, variant, current station, line progress, time in line, and ordered Digital Build Record with equipment metadata.
11. Enter **Walk mode**. Click the scene, use WASD, hold Shift for faster movement, and press Esc to return to Orbit. Confirm station signs are small physical nameplates and the camera remains inside the factory bounds.
12. Open **Alerts** and note that it is explicitly an **Operational log · Live events**; healthy operation does not fabricate predictive alerts.

Before handing off, click Reset once more so the factory is left at the healthy baseline with noise off and telemetry restored.
