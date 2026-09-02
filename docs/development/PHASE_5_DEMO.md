# LineLens Phase 5 — Incident response demo

Phase 5 turns existing production and vehicle-quality predictions into a human-in-the-loop response workspace. Incident actions record workflow progress only; they never write to PLCs, stop machines, or alter the physical simulator.

## Production incident

1. Reset LineLens, select **Chassis Marriage**, and start **Simulate process drift**.
2. Select **10×** and wait for the early warning.
3. Open **Incidents**. The single deduplicated Chassis Marriage incident shows live cycle evidence, forecast-based response window, expected downstream impact, owner, and configured checks.
4. Use **Acknowledge**, **Start investigation**, **Mark check complete**, or **Add note**. These add timeline events and response timing only.
5. Use **Restore normal process** (explicitly labelled simulation control), then resolve the workflow incident when ready.

## Quality incident

1. Reset LineLens, open **Quality**, and start **Simulate weld drift**.
2. At **10×**, wait for an inspection-level cohort with an enriched shared pattern.
3. Open **Incidents**. Quality containment shows the actual affected vehicles, weld genealogy factor, configured Body Shop checks, and the expected lead before normal End-of-Line discovery.
4. From a listed vehicle, open its **Digital Build Record** or use the quality-incident link to return to the incident.

## Deterministic rules

- Production: Chassis Marriage risk must remain at or above 45% for at least 12 simulated seconds.
- Quality: at least two vehicles must reach the 60% inspection threshold and share real genealogy evidence.
- An active incident is updated rather than duplicated. Resolved incidents remain in bounded in-memory history.
