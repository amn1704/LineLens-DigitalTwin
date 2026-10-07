# LineLens — Q&A preparation

Twelve likely jury questions with short, honest answers for the 5-minute Q&A. Lead with the direct answer, then one supporting fact. If you don't know, say so and say how a pilot would find out.

> Independent student concept for the Maruti Suzuki Innovation Hackathon 2026. Not affiliated with or endorsed by Maruti Suzuki India Ltd. No Maruti Suzuki data is used.

### 1. Is this real plant data?

No. Every signal, vehicle, defect, and energy reading comes from our own synthetic 11-station simulator, and every ₹ figure uses placeholder assumptions you can edit on screen. We did that on purpose: it lets us demonstrate the full loop honestly without claiming plant access. The pilot's first phase exists to replace the synthetic data with one line's historical logs.

### 2. How is this different from Siemens Tecnomatix or Dassault DELMIA?

Those are comprehensive digital-manufacturing suites, strong for designing, simulating, and validating lines in detail. LineLens answers a narrower daily question for a supervisor on an existing line: what is drifting now, what will it cost if we wait, and where do we look first. It works with incomplete, legacy signals and shows its confidence, it is explainable end to end, and it runs on a laptop. It could complement such a suite, for example by using a line model from it as its topology.

### 3. What about false alarms?

We designed against them in three ways. A warning needs a persistent pattern: cycle against normal, a trend, and the queue, sustained over time, before it becomes an incident. Risk and confidence are separate, so a low-evidence station is shown as uncertain rather than alarming. And every warning is validated: false positives are counted and shown, not hidden. In a pilot we would tune thresholds against measured precision. One honest gap: in our synthetic run the warning was early, which is good, but the forecast's timing for the first downstream impact was too pessimistic, so ETA calibration is pilot work.

### 4. How would you connect to legacy machines with no sensors?

Most "no-sensor" stations still have something: a PLC state, a photo-eye or conveyor bit at entry and exit. That is our **Basic** tier. LineLens infers cycle time from arrival and departure timestamps and neighbouring flow, and lowers its confidence accordingly. Where there's truly nothing, a low-cost retrofit sensor at entry and exit is enough. All of it is read through a read-only OPC UA or MQTT gateway.

### 5. What does a pilot cost, and what does it need from Maruti?

Phase A needs no hardware and no plant connection: one line's historical station cycle logs as a CSV or historian export, plus a process-engineering contact for a few hours a week. It runs on a laptop or a single VM. Phase B adds read-only historian access approved by plant IT and safety, with no write-back. We haven't priced it, because the main cost is people's time, which we'd agree together.

### 6. Why not let the system act automatically?

Because the cost of a wrong automatic action on a running line is much higher than the cost of a supervisor reading a good warning. Supervisors are accountable for the line, and trust has to be earned with measured precision first. So LineLens recommends and records; it has no control path at all. Once a pilot has shown reliable precision, closed-loop suggestions could be discussed, but with people approving them.

### 7. How accurate is the quality model?

On held-out synthetic test data, the model's PR-AUC is about **0.52**, with a Brier score of about 0.16. Defects make up about 12 % of that test set, so a random ranking would score about 0.12; the model is roughly four times better than random at ranking risky bodies. That makes it useful for deciding which bodies to inspect first, not for declaring a body defective. It is a 10-feature logistic regression, trained on 2,400 synthetic rows with a 70/15/15 split, and its weights are frozen in `quality_model_artifact.json`. Real accuracy is unknown until we train and validate on real inspection labels in the pilot.

### 8. How does it scale to hundreds of stations?

The design scales roughly linearly: each station has its own baseline and estimator, and the forecast is a simple discrete-time simulation whose cost grows with stations and horizon. A real deployment would split by shop or line, add a persistent time-series store, and ingest events rather than polling. But we haven't benchmarked hundreds of stations or high-frequency telemetry, and we won't claim we have.

### 9. What is your business model?

Our working hypothesis is a paid pilot followed by a per-line annual subscription, plus integration services for the read-only connection. The low infrastructure footprint keeps the cost per line small. That's a hypothesis to validate with plant and IT stakeholders, not a tested model.

### 10. What did you build, and what did you reuse?

We built the simulator, the observation layer, the Twin estimator, the bottleneck risk model and Forward Twin, the quality model and its synthetic training data, the genealogy analysis, the incident workflow, the impact and energy model, and the frontend including the 3D factory scene. We reused standard open-source libraries: React, Three.js, React Three Fiber, Drei, FastAPI, Pydantic, NumPy, scikit-learn, and others. Initial visual design direction came from a public showcase repository that contained only screenshots and a README, no code. Everything is listed in `ATTRIBUTIONS.md`.

### 11. Where do the rupee figures come from?

From placeholders we chose to be clearly illustrative: an 8-hour shift, ₹50,000 contribution margin per vehicle, ₹1,500 to fix a body in-line against ₹6,000 after End-of-Line, and ₹8 per kWh. The formulas are simple and shown in the app and README. For example, vehicles at risk equal the forecast throughput drop times shift hours, counted only while bottleneck risk is elevated. You can change any figure live in **More → Impact assumptions** and watch the estimates update.

### 12. How realistic is the energy and CO₂ model?

It is a synthetic power profile: each station has a running and an idle draw, and we meter it in simulated seconds. The pattern is plausible, with paint and curing the biggest loads and the oven drawing nearly full power when starved, but the numbers are not measured. CO₂ uses 0.71 kg per kWh as an approximate Indian grid average, to be verified against the latest CEA CO₂ Baseline Database. In a pilot, we would replace the profile with sub-meter data or rated power multiplied by PLC state.
