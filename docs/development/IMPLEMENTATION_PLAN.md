# LineLens Phase 1 plan

## NexusTwin audit — 31 August 2026

The supplied NexusTwin material is a public showcase, not an application source distribution. It contains a detailed `README.md`, attribution record, architecture illustration, social preview, and five screenshots. The README expressly says proprietary source code, data, deployment configuration, and implementation details are not included. No pre-existing reusable frontend, backend, dependency manifest, HTML, JavaScript, or application configuration was found in this workspace.

The reference materials remain untouched in the repository root and `assets/`. Their industrial visual direction will inform this prototype; no NexusTwin source is copied. Existing attribution is retained in `ATTRIBUTIONS.md`.

### What can be reused

- The visible design direction: graphite surfaces, compact operational panels, color-coded status, an isometric factory-first view, and a contextual inspector.
- The supplied screenshots and architecture diagram as visual and interaction references only.

### What must be recreated

- The complete client, 3D scene, data model, sensor simulation, data API, navigation, assets, and interactions from the public demo. These are absent from the download.

## Delivery sequence

1. **Foundation** — recreate the factory-first NexusTwin experience with Vite + React, FastAPI, an 11-station automotive floor, live synthetic values, and an interactive Three.js scene.
2. **Production flow** — add vehicle and buffer movement from a realistic assembly-line simulation.
3. **Operational prediction** — add bottleneck detection and downstream propagation.
4. **Quality intelligence** — add vehicle-level quality evidence and defect genealogy.
5. **Decision Lab** — introduce safe what-if evaluation and human-approved recommendations.
6. **Optimisation** — evaluate whether PPO provides enough demonstrable value to warrant inclusion.
7. **Demo readiness** — validation, business evidence, responsive refinement, and a polished walkthrough.

## Phase 1 acceptance checks

- The API returns 11 typed automotive assets across Body, Paint, and Final Assembly zones.
- State advances from elapsed wall-clock time with no persistence dependency.
- The app renders an isometric factory view with orbit, zoom, click-to-select, status indicators, vehicle flow, and selected-asset inspector data.
- Frontend and backend each start independently and are exercised through the browser.
