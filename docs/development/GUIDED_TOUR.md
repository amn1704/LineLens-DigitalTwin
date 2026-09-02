# LineLens Guided Tour

The Phase 6 Quick Tour is a seven-step spotlight walkthrough designed for a first-time judge. It starts only after live application state has loaded. Completing or skipping it stores `linelens.phase6.tour-seen=1`; subsequent refreshes remain unobstructed. The permanent **Tour** header button replays it. `?tour=welcome` is a deterministic review entry point that displays the welcome without deleting the user's saved preference.

## The seven steps

1. **Your live factory** — Dashboard and the 3D factory; drag and zoom interaction.
2. **Even when data is limited** — Trim Station and its Basic data Twin estimate and confidence.
3. **See trouble before it spreads** — Chassis Marriage, normal/current cycle, and Forecast control.
4. **See what may happen next** — a real quick bottleneck demo and the +5 minute expected impact.
5. **Every vehicle has a memory** — Quality and a valid vehicle Digital Build Record.
6. **Find what the affected vehicles share** — a real weld-drift demo and its Common Pattern.
7. **From warning to action** — the relevant Incident, its evidence, checks, and human workflow.

Every card stays to two or three short sentences and includes Back, Next, and Skip. The spotlight follows its target with `ResizeObserver`; missing targets never produce a broken rectangle.

## Scenario behavior and integrity

The tour controller owns the current step, target page, station, optional scenario, and loading state. It contains no timeout chain and runs each required scenario at most once per tour.

The bottleneck sequence resets and pauses the plant, activates the existing Chassis Fixture Alignment physical drift, and advances 380 simulated seconds through `AssemblyLineSimulator._advance` in bounded increments. Predictions and downstream impacts are then requested from the normal Prediction Service.

The quality sequence resets and pauses the plant, activates the existing Weld Drift physical scenario, advances 1,800 simulated seconds through the same production pipeline, and requests the normal Quality Twin, genealogy, validation, and Incident data. Neither sequence assigns a risk, forecast, vehicle outcome, station state, or incident in the frontend.

While a sequence runs, the card says **Running a short factory simulation…**. If a preferred vehicle is unavailable, the tour selects another high-risk vehicle or a vehicle with enough completed build history. Tour targets render safe empty states when data is temporarily unavailable.

## Completion, skip, and reset

Completing the tour offers **Explore LineLens**, **Run Bottleneck Demo**, and **Run Quality Demo**. Explore resets to a healthy running Dashboard. The two demo choices intentionally leave their named synthetic state active for inspection. Skip records the preference and leaves normal exploration available; the application never depends on tour state.

## Acceptance script

1. Open `http://localhost:5176/?tour=welcome` at 1440×900 and wait for live data.
2. Start the tour and complete all seven spotlight steps.
3. Confirm the real scenario loading state, predicted impact, build record, common pattern, and incident response.
4. Finish with Explore and verify the healthy baseline.
5. Replay with Tour, skip, then refresh without the query and confirm the welcome does not return.
6. Open every primary route, the More menu, Demo drawer, and About / Validation.
7. Repeat at a common laptop viewport and confirm the browser console is clean.

## Measured new-user run

The browser acceptance run at 1440×900 completed in **80.9 seconds**, inside the 60–90 second target. At **60 seconds**, the user was on Step 6 looking at the Common Pattern: the live factory, sensor gap, early warning, future impact, and vehicle history had already been explained; human incident response followed as the final step. The bottleneck preparation took 2.5 seconds and the quality preparation took 3.7 seconds on the acceptance machine.
