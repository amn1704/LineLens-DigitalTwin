# LineLens Phase 2.75 — Evolving Twin Foundation

LineLens uses a synthetic automotive production simulator as its **physical factory** for this prototype. It does not label the data as real plant telemetry, real sensors, or a trained factory model.

## Data boundary

```
Synthetic simulator (ground truth)
          ↓ emits only plant-facing signals
Observation layer
          ↓ assimilates at a controlled cadence
Twin state estimator
          ↓
Evolving twin state for the UI and future Phase 3 modules
```

The estimator receives `StationObservation` objects rather than simulator runtime objects. Observations expose only realistic PLC/MES-style fields: state, event timestamps, occupancy, selected tool signals, and vehicle identity where instrumentation supports it. Simulator-only state remains private to simulation, testing, and future forecast validation.

## Sensor maturity

- **Full telemetry**: direct cycle observation, PLC state, vehicle identity, and available tool telemetry.
- **Limited telemetry**: PLC state, entry/exit timestamps, conveyor occupancy, and selected signals; no direct cycle sensor.
- **Legacy / basic signals**: arrival/departure events, basic PLC state, and conveyor occupancy; no direct cycle reading is fabricated.

## Baselines and estimation

Each station starts with its own warm-shift synthetic observation history and then learns an individual healthy fingerprint. The fingerprint uses an interpretable exponentially weighted mean and variance for cycle time, plus expected utilization and normal queue level.

Only healthy completed observations with quality of at least 0.72 update a baseline. Blocked, starved, warning, and offline periods are excluded. A 3σ-style envelope (with a four-second minimum margin) rejects abnormal values so telemetry noise, dropouts, and excursions do not redefine healthy operation.

The estimator is a lightweight adaptive filter:

- Full telemetry gives the latest observed cycle the strongest weight, with moderate smoothing to suppress short sensor noise.
- Limited and legacy stations combine completion timestamps when available, entry age, queue/conveyor evidence, topology continuity, and their own historical baseline.
- The resulting twin estimate is stored with a range, residual from expected healthy behavior, normalized deviation, and a stable/rising/falling residual trend.

Residuals are descriptive deviations only. Phase 2.75 does not call them bottlenecks, failures, or defects and includes no forecasting, defect model, PPO/RL, or what-if interventions.

## Confidence and data gaps

Estimated confidence is a bounded weighted score: sensor maturity 50%, signal coverage 13%, freshness 13%, baseline consistency 11%, healthy-history depth 5%, and current observation quality 3%. The terms overlap intentionally and the result is constrained to 0.18–0.99. During a data gap, the previous estimate is retained, confidence decays exponentially with age, the station source changes to **Estimated after data gap**, and the current-observations endpoint no longer lists that station. On recovery, confidence moves 38% toward the fresh-data target per assimilation, preventing a violent snap.

Residual is always `Twin Estimate − Expected healthy baseline`. Its trend compares the recent three residuals with the earlier window and uses a station-variance-based tolerance (at least 0.35 seconds), preventing tiny poll-to-poll changes from flipping the label.

## Physical topology

Stations, connections, queues, and accumulation buffers are separate concepts. Direct-coupled and short-conveyor links have one incoming staging position and do not create buffer entities. The only explicit accumulation buffers are:

- **Body Shop Exit Accumulator** (`BODY-ACC`), Underbody → Pretreatment, capacity 4.
- **Painted Body Storage** (`PBS`), Curing Oven → Trim, capacity 5.

Both are returned in `TwinState.buffers`; vehicle records carry `buffer_id` and `queue_kind`, and the 3D positions use the same occupancy. A station becomes blocked only when its actual downstream queue or accumulator is full, and starved only when its actual incoming source is empty.

The confidence values and estimate ranges are prototype estimates; they are not calibrated real-world confidence intervals.

## Digital build records

Each vehicle retains a bounded in-memory digital build record. Completed steps include ordered entry/exit times, cycle duration, result, equipment/tool ID, and compact station-specific process metadata such as a weld robot cell, paint batch, fixture, torque tool, or calibration rig. The last 240 completed vehicle records are retained in memory. A backend restart resets the synthetic shift and the in-memory archive.

## APIs

- `GET /api/twin/state`
- `GET /api/twin/stations`
- `GET /api/twin/stations/{station_id}`
- `GET /api/twin/observations`
- `GET /api/twin/synchronization`
- `GET /api/vehicles/{vehicle_id}/thread`

The test-only synthetic observation condition endpoint supports controlled missing-data and noise validation:

- `POST /api/twin/testing/stations/{station_id}/observation-condition`
- JSON fields: `drop: boolean` and/or `noise: number` (seconds, 0–8)

## Known limitations

- All observations are synthetic and local to the prototype.
- Baselines and build records are in memory and reset with the backend.
- Estimated ranges are explainable spread indicators, not statistically calibrated plant confidence intervals.
- This phase intentionally stops before Phase 3 prediction and decisioning work.
