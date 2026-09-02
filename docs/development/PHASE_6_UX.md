# Phase 6 UX

Phase 6 makes LineLens judge-first without removing the engineering depth built in Phases 1–5. The default experience now tells one story: see the live factory, notice the one issue that matters, understand what may happen next, trace affected vehicles, and hand the evidence to a person.

## Information hierarchy

The primary navigation is **Dashboard**, **Quality**, and **Incidents**. **More** keeps Machines, Analytics, Alerts, and About / Validation available for deeper investigation. No separate Trust workspace was added.

The Dashboard remains 3D-first. Its first layer is the live factory, selected station, four factory metrics, and at most one active warning. The station inspector shows station, status, vehicle, current versus normal cycle, difference, confidence, and queue. Sensor maturity, raw observations, freshness, and model calculations live under **Why? / Details**.

Quality keeps its three-column layout, but the default list contains only vehicles that need review. Each row is reduced to vehicle, location, risk, and status. The selected-vehicle story is expressed as **Why**, **Likely origin**, and **What to do**, followed by a simple build history. Model inputs, confidence, process evidence, and outcome validation are under **View technical evidence**. Healthy operation is deliberately calm.

Incidents leads with what happened, expected next impact, why, what to check, ownership, and outcome. Forecast validation and extended playbook evidence remain under expandable details.

## Simple-language rules

- Expected baseline → Normal cycle
- Residual → Difference from normal
- Residual rising → Getting worse
- State-estimation confidence → Confidence
- Quality genealogy → Common pattern
- Propagation forecast → Expected impact
- Sensor classes → Direct data, Partial data, or Basic data

Observed, Twin, Forecast, Confidence, and Quality Risk each have a short explanation at the point of use. Technical terms remain available where an engineer expects them, but do not compete with the judge-facing story.

## Demo and validation controls

All synthetic controls moved to the header **Demo** drawer. It contains the bottleneck, weld quality issue, sensor loss, speed, and reset controls and labels them as a synthetic demonstration. Active scenarios use only a small badge in operational views.

About / Validation is a secondary drawer. It summarizes warnings checked, correct warnings, time gained, vehicles detected before end-of-line, and data coverage. The full metrics remain in an expandable technical section.

Reset Demo calls the normal simulator reset, clears prediction and incident services, and returns the app to a running healthy baseline.

## Responsive behavior

The desktop target is 1440×900. On narrower laptops, Quality moves its analysis cards below the vehicle story; at compact widths all three sections stack. The tour card remains inside the viewport and the primary application remains usable independently of the tour.
