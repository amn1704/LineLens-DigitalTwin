# LineLens — submission text

Copy-paste text for the Maruti Suzuki Innovation Hackathon 2026 form. Every number below comes from this repository. Numbers marked *illustrative* come from the synthetic simulator and placeholder assumptions; none are Maruti Suzuki or plant figures.

> Independent student concept for the Maruti Suzuki Innovation Hackathon 2026. Not affiliated with or endorsed by Maruti Suzuki India Ltd. No Maruti Suzuki data is used.

## One-line pitch

LineLens is an explainable digital twin that warns supervisors about developing bottlenecks and weld-quality drift before they spread, and shows what doing nothing would cost in vehicles, ₹, and kWh.

## Abstract (150 words)

Assembly lines lose output in small, compounding ways: one station drifts a few seconds slower, a weld gun's electrode caps wear, and the problem surfaces only as a queue or an End-of-Line failure. LineLens is an explainable digital twin that closes this gap. It estimates the state of every station, including legacy stations with only basic signals, and states its confidence. An interpretable risk model flags developing bottlenecks, and a no-intervention forecast shows what happens next. Each vehicle's build record links risky bodies to a shared weld gun, consumable lot, and Tier-2 supplier while they are still on the line. Every warning is translated into assumption-based vehicles, rupees, and kilowatt-hours at risk, including the idle energy that starved ovens and paint booths still draw. Supervisors act through playbooks; LineLens never controls equipment and checks its own predictions against later outcomes. The prototype runs on synthetic data, on a laptop.

## Problem

High-volume, mixed-model lines run close to takt. A slowdown of a few seconds at one station repeats every cycle, fills buffers, starves downstream stations, and becomes visible only once output has already been lost. Quality drift is similar: a worn electrode cap can affect many bodies before End-of-Line inspection confirms the first defect, when rework is most expensive. Brownfield plants make both harder, because modern cells sit beside legacy stations that report little more than arrival and departure. Supervisors therefore have data, but not an early, trustworthy, prioritised view of where to look, or of what waiting will cost.

## Solution

LineLens is decision support for the line supervisor:

1. **See now.** A Twin state estimator keeps a live estimate of all 11 stations of a synthetic line across Body Shop, Paint Shop, and Final Assembly, from Full, Limited, or Basic signals, with explicit confidence.
2. **Predict next.** An interpretable bottleneck-risk score flags persistent drift; a disposable Forward Twin projects queues, starvation, blocking, and throughput 2–15 minutes ahead if nothing changes.
3. **Know the cost.** Forecasts, quality cohorts, and a synthetic energy meter become assumption-based vehicles and ₹ at risk per shift, rework avoidable in-line, kWh per vehicle, idle energy, and CO₂.
4. **Trace quality.** A Digital Build Record per vehicle feeds a logistic-regression quality model and a genealogy analysis that points to the shared weld gun, electrode-cap lot, and Tier-2 supplier.
5. **Respond with evidence.** Persistent risks become incidents with playbooks (including a supplier quality alert) and response tracking. People decide; LineLens never writes back to the line.
6. **Earn trust.** Forecasts and quality warnings are validated against later outcomes, with misses and false alarms kept visible.

## Focus domain and sub-topics

**Manufacturing & Industrial Innovation — Engineer the factory of tomorrow.**

| Sub-topic | Covered by |
| --- | --- |
| Smart manufacturing | Twin state estimation with confidence, interpretable bottleneck risk, no-intervention forecasting |
| Industry 4.0 | Per-vehicle digital thread, mixed sensor-maturity observation layer, read-only OPC UA / MQTT integration path |
| Process improvement | Incidents and playbooks, genealogy to tool / lot / supplier, value-at-risk, prediction validation |
| Sustainability | kWh per vehicle, idle-energy share and cost, CO₂ with a configurable grid factor, idle energy at risk, rework avoided |

## Innovation

- **Works with incomplete and legacy signals.** Every station is estimated, and each estimate says how strong its evidence is. Most twins assume rich telemetry; brownfield lines rarely have it.
- **Explainable end to end.** A weighted logistic risk score over named features, a 10-feature logistic regression with per-feature contributions, and enrichment-based genealogy. A supervisor can see why each warning appeared.
- **Cost, energy, and quality on one screen.** The same forecast that predicts a bottleneck also prices it in vehicles and ₹ and shows the idle energy starved thermal processes keep drawing.
- **Supplier-aware genealogy.** Risky bodies are traced to a consumable lot and its Tier-2 supplier before End-of-Line, turning an internal quality issue into an actionable supplier alert.
- **Self-validating.** The twin records its own predictions and scores them against later outcomes.
- **Lightweight.** One container, no database, no licences: cheap to pilot beside existing systems.

## Impact (assumption-based)

All figures below are *illustrative*: synthetic simulator output combined with editable placeholder assumptions (8-hour shift, ₹50,000 contribution margin per vehicle, ₹1,500 in-line vs ₹6,000 End-of-Line rework, ₹8/kWh, 0.71 kg CO₂/kWh).

- **Production.** In the synthetic Chassis Marriage bottleneck demo (cycle ≈ 75 s against a 60 s normal), the 10-minute no-intervention forecast drops throughput from about 59 to 42 vehicles per hour. Extrapolated to a shift, that is ≈ 136 vehicles and ≈ ₹68,00,000 of contribution at risk. In a measured synthetic run, the elevated warning came about 15 minutes before the first sustained (≥ 30 s) downstream starvation. The forecast's own timing for that impact was pessimistic by a similar margin, which a pilot would need to calibrate.
- **Quality.** In the synthetic weld-drift demo, LineLens flags 7 bodies; 4 are still on the line and catchable, avoiding ≈ ₹18,000 of End-of-Line rework at ₹4,500 per body. In that run, 5 warnings were later confirmed at End-of-Line, on average about 9.6 minutes before End-of-Line inspection.
- **Energy.** The synthetic line uses roughly 9–12 kWh per vehicle in the demo. During the bottleneck the oven and booth keep drawing power while blocked or starved; the forecast puts ≈ 24 kWh per shift of extra idle energy at risk at the affected stations.

Exact values vary slightly with simulation timing. The value of a pilot is to replace every placeholder with a real one and measure alert lead time, precision, and avoided rework.

## Feasibility

- **Stack.** Python (FastAPI, Pydantic, NumPy, scikit-learn) backend; React 18, Vite, and React Three Fiber (Three.js) frontend; a multi-stage Dockerfile serving UI and API from one URL.
- **What works today.** The full loop runs end to end on synthetic data: simulator → observation layer → Twin → risk and forecast → quality model and genealogy → impact and energy → incidents → validation. A three-minute **Pitch demo** button runs the whole story without manual setup.
- **Quality.** 66 automated backend tests and 9 frontend tour tests pass; the TypeScript production build passes.
- **Integration path.** The observation layer is already separated from the simulator, so a real source (historian export, OPC UA, or MQTT) replaces the synthetic one without changing the Twin, models, or UI.

## Pilot plan

| Phase | Duration | What happens | Success measure |
| --- | --- | --- | --- |
| **A — Offline replay** | 4 weeks | Replay one line's historical station cycle logs (CSV / historian export) through LineLens to learn station baselines and replay past disruptions. No plant connection. | Would LineLens have warned earlier than the team noticed? Alert lead time and false-alarm rate on known events. |
| **B — Read-only shadow mode** | 8 weeks | Connect read-only through an OPC UA / MQTT gateway from the PLC / MES historian. No write-back of any kind. LineLens runs beside the line; supervisors are not yet asked to act on it. | Live alert lead time, precision, and twin confidence by station. |
| **C — Supervisor workflow pilot** | After B | Supervisors use incidents and playbooks on one line, with the plant's own cost and energy figures in the assumptions. | Alert lead time, precision, avoided rework, and supervisor feedback on usefulness. |

**What we would need:** one line's historical cycle logs, a process-engineering contact, and, for Phase B, read-only historian access approved by plant IT and safety.

## Team

*TODO: add team name, members, roles, and institute before submitting.*

| Name | Role |
| --- | --- |
| *TODO* | *TODO* |

## Honest limitations

- All data is synthetic; nothing has been calibrated on a real line.
- The line is a simplified, linear 11-station model; real plants have hundreds of stations, parallel lines, and rework loops.
- ₹, vehicles-at-risk, and CO₂ figures are assumption-based; the defaults are placeholders, and shift-level figures extrapolate a 10-minute forecast.
- The energy model is a synthetic power profile, not metered data.
- The quality model reaches a test PR-AUC of about 0.52 on synthetic data: useful for ranking which bodies to inspect first, not a defect verdict.
- State is in memory; there is no persistent store or multi-user access control yet.
- Performance at hundreds of stations or high-frequency telemetry has not been benchmarked.
