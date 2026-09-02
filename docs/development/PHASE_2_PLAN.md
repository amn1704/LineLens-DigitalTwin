# LineLens Phase 2 — live production flow

## Audit summary

Phase 1 provides a strong visual shell, 11 station assets, client-side decorative vehicles, and a FastAPI endpoint that emits smooth but independent station telemetry. It does not yet have vehicle entities, process sequencing, queues, buffers, history, events, or shared live state.

## Implementation plan

1. Build one background, wall-clock-driven backend simulator with a fixed 11-station route, 60-second configurable takt, accelerated simulation time, and synchronized vehicle/station/buffer/event/history state.
2. Provide concise REST endpoints for state, stations, vehicles, events, history, and simulation controls.
3. Adapt the existing Phase 1 pages and 3D scene to render only API state; retain the visual system and interaction patterns.
4. Validate normal mixed-model flow, lifecycle controls, browser refresh behavior, selection synchronization, and responsive layouts.

## Explicitly deferred

Bottleneck prediction, defect intelligence, what-if simulation, PPO/RL, and any prescriptive logic remain out of Phase 2.
