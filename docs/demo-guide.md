# LineLens Demo Guide

This guide outlines how to demonstrate LineLens to evaluators. The application is designed to be interactive and heavily visual, guiding the user from a healthy factory to predictive disruption and quality containment.

## Prerequisites
- Backend running on port `8102` (`cd backend && uvicorn app.main:app --port 8102`)
- Frontend running on port `5176` (`cd frontend && npm run dev`)

> **Important**: Always use the **Reset Simulation** button in the Demo drawer between scenarios to clear history and return to a clean, warm baseline.

## Demo 1: Healthy Factory
1. Open the **Dashboard**. Verify the 3D factory is running smoothly.
2. Orbit the camera and use the **Walk** mode to explore the facility.
3. Select any station (e.g., *Paint Booth*).
4. In the right panel, expand **Why? / Details**. 
5. Show how the Twin Estimate compares to the observed cycle, note the Confidence score, and point out the Sensor Maturity tier (Full, Limited, or Basic).

## Demo 2: Bottleneck Detection
1. Reset the simulation.
2. Select **Chassis Marriage** from the station list.
3. Open the Demo drawer and click **Simulate process drift**.
4. Set the simulation speed to **10x** in the Demo drawer.
5. Watch the station risk rise. Point out the clear evidence (residual time increasing).
6. When the early warning triggers, show the **Forecast** impacts.
7. Wait for the +5m and +10m simulated time to pass, then open the **About / Validation** drawer to show the actual vs. predicted metrics (Queue MAE, State Accuracy).

## Demo 3: Vehicle Quality
1. Reset the simulation.
2. Navigate to the **Quality** tab.
3. Open the Demo drawer and click **Simulate weld drift**. Set speed to **10x**.
4. Watch vehicles exit the Robotic Weld Cell. As they drift out of tolerance, a subtle quality indicator ring will appear around them in the 3D view.
5. Select a high-risk vehicle from the **WATCH** or **INSPECT** list.
6. Show the **Digital Build Record**, pointing out the specific weld evidence (e.g., energy deviation).
7. Look at the **Genealogy** panel to show how LineLens identifies common factors (e.g., a specific electrode lot).
8. Wait for vehicles to reach End-of-Line to show the Quality Validation metrics update as ground truth is revealed.

## Demo 4: Incident Response
1. Following either the Bottleneck or Quality demo, navigate to the **Incidents** tab.
2. Select the active incident.
3. Show the human-in-the-loop workflow: click **Acknowledge**, check off playbook items, and click **Start investigation**.
4. Explain that this acts as decision support and does not autonomously command the line.
5. Return to the Demo drawer and click **Restore normal process**, then resolve the incident.

## Demo 5: Sensor Loss and Recovery
1. Reset the simulation.
2. Select any active station.
3. In the Demo drawer, toggle **Drop telemetry** for that station.
4. Expand the station details. Show how the station falls back to an imputed estimate while the Confidence score decays exponentially.
5. Restore telemetry and show how confidence recovers smoothly over time.

## Demo 6: Guided Tour
For an automated executive overview:
1. Reset the simulation.
2. Click the **Tour** button in the top navigation bar (or append `?tour=welcome` to the URL).
3. The tour will step through 7 key highlights, moving the camera and pausing the simulation automatically.
