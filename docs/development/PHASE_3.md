# LineLens Phase 3 — predictive digital twin

Phase 3 extends the locked Phase 2.75 pipeline without bypassing it:

`Physical simulator → StationObservation → TwinStateEstimator → TwinState → risk features → bottleneck risk → disposable Forward Twin → no-action forecast → UI`

The prediction package accepts `TwinState`. It does not import or inspect simulator runtime objects. Physical ground truth is used only by automated tests and forecast-vs-actual validation.

## Risk model

For station feature vector `x`, the prototype uses an interpretable weighted logistic score:

`risk = clamp(sigmoid(z), 0.01, 0.96)`

where:

`z = -3.55 + 2.00·residual_pressure·(0.35 + 0.65·persistence) + 1.15·rolling_pressure + 0.85·takt_pressure + 0.75·rising_trend·persistence + 0.55·completion_loss + 0.48·queue_growth + 0.28·variability + 0.35·blocked_ratio`

Each pressure term is normalized and clamped to `[0,1]`. The negative intercept keeps healthy operation low-risk. A residual must be large relative to the station-specific baseline envelope and persist across recent Twin history before it receives its full weight. Takt is evidence, not a single threshold. Levels are LOW `<25%`, ELEVATED `<50%`, HIGH `<75%`, and SEVERE `≥75%`.

Exact evaluated features are:

- cycle-to-takt ratio
- Twin health residual and station-specific normalized residual
- residual trend and evidence persistence
- rolling Twin-cycle mean and variance
- station completion rate and change from healthy expected rate
- incoming queue/accumulator growth
- downstream arrival rate
- utilization
- blocked and starved observation ratios
- accumulator fill rate

Every assessment carries deterministic evidence strings using current values: estimated versus expected cycle, residual/trend, cycle-to-takt ratio, queue growth, and completion-rate change.

Risk and confidence are separate. Risk estimates the likelihood of material flow disruption in the forecast horizon. Evidence confidence combines current Twin confidence (68%), accumulated history depth (16%), cycle stability (12%), and persistence (4%), clamped to 18–97%. It therefore falls during telemetry dropout and is appropriately lower for inferred Legacy stations.

## Forward Twin

`snapshot_from_twin()` serializes only the evolving public Twin state into typed station, topology, and accumulator records. `ForwardTwinSimulator.simulate(snapshot, horizon, source, seed)` constructs disposable station and transfer objects, advances them at deterministic two-second steps, records 30-second trajectory points, returns outcome metrics, and discards the clone. The live simulator and input snapshot are never mutated.

Supported horizons are 120, 300, 600, and 900 simulated seconds. Seed `275` makes the same snapshot, assumptions, and horizon reproducible. `ForwardScenario.action` is deliberately `None` and the assumption is `NO_INTERVENTION`; no actions, reward, Gymnasium environment, PPO, or optimizer are present.

The forward flow respects direct-coupled one-position staging and only the two physical major accumulators: Body Shop Exit Accumulator and Painted Body Storage. Completions, transfers, capacity constraints, blocked state, starvation, WIP, and output evolve from the cloned topology. Impacts are derived from trajectory events—not plant-distance rules—and currently include queue growth, upstream blocking, downstream starvation, and line throughput loss. ETA is the first sustained simulation crossing; queue ETAs align with a stored trajectory sample. ETA ranges widen with horizon and reduced forecast confidence.

Forecast confidence is a prototype indicator, not a real-world calibrated probability:

`confidence = clamp(mean Twin confidence × horizon decay × variability decay, 0.25, 0.94)`

with horizon decay `1 - horizon/4200` and variability decay `1/(1 + mean cycle standard deviation/45)`. Longer horizons and uncertain/noisy Twin estimates reduce confidence.

## Runtime, alerts, and validation

The service caches all four forecasts by selected station, an eight-simulated-second time bucket, and material snapshot fields. Healthy risk below 25% suppresses forecast impacts, avoiding phantom propagation. Alerts use one-time crossing keys for 35%, 60%, and 82% risk and deduplicate each predicted entity/impact pair.

When Chassis Marriage first crosses 45%, the service preserves its +2m/+5m/+10m no-action forecasts. As live simulation continues, it evaluates:

- station queue mean absolute error
- physical accumulator occupancy mean absolute error
- rolling throughput absolute error
- station-state classification accuracy
- first material-impact ETA error
- prediction lead time from risk trigger to sustained actual blocking/starvation

These values are synthetic simulator validation only. They do not establish plant accuracy.

## Deterministic verification snapshot

On the documented seed and a 15-second evaluation cadence, a 10-minute healthy run produced maximum station risk `6.2%`, zero forecast alerts, live output `57 veh/h`, and forecast output `54 veh/h` (5.3% error). Under Chassis Marriage fixture-alignment drift, sampled risk rose from `2.9%` to `33.0%`, `43.1%`, `52.8%`, `66.2%`, `75.7%`, and `80.1%` as the residual grew from `+2.6s` to `+14.4s`. The stored run measured 345 seconds of lead time before sustained actual disruption.

One full synthetic checkpoint run produced queue MAE `0.091/0.273/0.364` vehicles at +2m/+5m/+10m. Throughput absolute error was `28/33/20 veh/h`, and state accuracy was `63.6%/90.9%/81.8%`. Throughput error is intentionally reported honestly: the small deterministic forward model compares horizon-average completions with the live simulator's rolling throughput and is not production-calibrated. Accumulator and ETA errors are now also stored and shown for new runs.

## Limitations

- This is a deterministic synthetic prototype, not plant-validated probability or accuracy.
- A single seed is used for fast, comparable forecasts; ETA ranges are analytical uncertainty bands, not Monte Carlo confidence intervals.
- The compact forward model approximates the richer live simulator, so short-horizon throughput error can be high.
- Risk weights are simulator-calibrated and interpretable, not learned from real production labels.
- Validation is held in process memory and resets with the simulation.
- No control action, intervention ranking, quality/defect model, PLC write, RL reward, or PPO exists in Phase 3.

