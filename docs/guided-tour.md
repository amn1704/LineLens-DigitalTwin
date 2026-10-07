# Guided Product Tour

LineLens has one Full Product Tour, available from **Help**. It is designed for a first-time evaluator and takes about five minutes. The tour can be exited with its close button or Escape at any time.

## Story

1. Whole factory and line sections
2. Station selection and station evidence
3. Observed telemetry, Twin estimate, and Forecast
4. Limited sensor coverage and confidence
5. Viewport exploration: Orbit, Walk, and Flythrough
6. Real Bottleneck demonstration and computed forecast
7. Incident creation, evidence, and human-led checks
8. Real Weld quality demonstration and vehicle Digital Build Record
9. Early quality warning and Common Pattern
10. Stations, Trends, and outcome validation

The Bottleneck and Weld steps call the same local simulator and backend pipelines as the Demo controls. No operational values, alerts, vehicles, or common factors are invented by the tour.

## Pitch Demo

The **Pitch demo** button in the top bar runs a separate nine-step presenter story through the same `GuidedTour` component and scenario mechanics. It resets the demo first, so it needs no manual setup.

1. The line
2. A developing bottleneck (real Bottleneck scenario)
3. Why it was flagged
4. What happens if nothing changes (Forecast view and the impact metrics)
5. From warning to action (incident impact and playbook)
6. Greener line (Energy & CO₂ card)
7. Quality early warning (real Weld quality scenario)
8. The root cause lead (weld gun, cap lot, Tier-2 supplier, rework avoided)
9. Trust (validation summary)

The greener-line step comes straight after the incident, while the bottleneck is still live, so the energy card shows the bottleneck's idle-energy cost; the quality scenario starts from a reset line. The tour tests check that every pitch target exists in the app, that each scenario is valid, that step text stays at 25 words or fewer, and that each impact step sits between its scenario and the next.

## Page Guides

Dashboard, Quality, Incidents, Activity, Stations, and Trends each provide a **Guide this page** button. These short guides explain the controls and evidence visible in their current workspace.
