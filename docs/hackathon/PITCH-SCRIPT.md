# LineLens — 5:00 pitch script

Seven slides, with the live **Pitch demo** as slide 4. Every number on screen comes from the synthetic simulator and illustrative assumptions; say so once, early, and the jury will trust the rest.

> Independent student concept for the Maruti Suzuki Innovation Hackathon 2026. Not affiliated with or endorsed by Maruti Suzuki India Ltd. No Maruti Suzuki data is used.

## Before you walk on

- [ ] Open the hosted link **about 2 minutes before** your slot; free tiers sleep and need a cold start.
- [ ] Load the Dashboard once and dismiss the welcome dialog. Leave the browser zoom at 100 % and close other tabs.
- [ ] Do not press **Pitch demo** yet; it resets the line itself.
- [ ] Keep the fallback screenshots (below) open in a second window.
- [ ] Assumptions are at their illustrative defaults (**More → Impact assumptions → Restore illustrative defaults**).

## Timing at a glance

| # | Slide | Time | Ends at |
| --- | --- | --- | --- |
| 1 | Hook / problem | 0:30 | 0:30 |
| 2 | Why now / India context | 0:30 | 1:00 |
| 3 | Solution in one sentence | 0:20 | 1:20 |
| 4 | **Live Pitch demo** | 2:15 | 3:35 |
| 5 | Impact | 0:30 | 4:05 |
| 6 | Pilot plan and ask | 0:35 | 4:40 |
| 7 | Close | 0:20 | 5:00 |

## Slide 1 — Hook / problem (0:00–0:30)

**On slide:** "A few seconds. Every cycle. Every shift."

> "On a line running close to takt, one station slowing by a few seconds doesn't look like an emergency. But it repeats every cycle. Buffers fill, the next station starves, and by the time anyone sees the queue, output for the shift is already lost. Quality works the same way: a worn electrode cap can touch dozens of bodies before End-of-Line inspection finds the first defect, where rework costs the most."

## Slide 2 — Why now / India context (0:30–1:00)

**On slide:** four icons: mixed-model volume · brownfield sensors · supplier base · energy and CO₂.

> "Indian plants make this harder and more valuable to solve. High-volume, mixed-model lines. Brownfield shops where a modern robot cell sits beside a conveyor that only reports arrival and departure. A deep Tier-1 and Tier-2 supplier base, where one bad consumable lot spreads fast. And rising energy cost with CO₂ commitments, where a starved paint oven still draws power. Supervisors have data. What they lack is an early, trustworthy view of where to look and what waiting will cost."

## Slide 3 — Solution in one sentence (1:00–1:20)

**On slide:** "LineLens: an explainable digital twin that sees problems early, prices them in vehicles, ₹ and kWh, and leaves the decision to people."

> "LineLens is an explainable digital twin. It sees a problem early, tells you what doing nothing would cost in vehicles, rupees and kilowatt-hours, and leaves every decision to the supervisor. Let me show you, live. Everything you'll see is synthetic data and illustrative assumptions."

## Slide 4 — Live Pitch demo (1:20–3:35)

Switch to the browser and press **Pitch demo**. Advance with **Next** at each cue. About 15 seconds per step; steps 2 and 7 wait briefly while the real simulator runs, so keep talking.

| Step | Time | On screen | Say |
| --- | --- | --- | --- |
| 1. The line | 1:20 | Factory canvas | "Eleven stations, three shops, and mixed sensor maturity: some stations have rich telemetry, some only basic signals. LineLens estimates all of them and says how confident it is." |
| 2. A developing bottleneck | 1:35 | Chassis Marriage inspector | "Now a fixture at Chassis Marriage starts drifting. This is the real simulator running, not a canned animation." |
| 3. Why it was flagged | 1:50 | Inspector | "Why flag it? Current cycle against normal, a growing difference, and the queue. A persistent pattern, not one slow cycle." |
| 4. What happens if nothing changes | 2:05 | Forecast + Value at risk | "The no-intervention forecast says throughput falls from about 59 to 42 vehicles an hour. Over a shift, that's roughly 136 vehicles, and at a placeholder margin, about ₹68 lakh at risk. You can edit every assumption." |
| 5. From warning to action | 2:20 | Incident · Impact if nothing changes | "That becomes an incident: impact, evidence, and a playbook. The supervisor acknowledges and investigates. LineLens never touches the line." |
| 6. Greener line | 2:35 | Energy & CO₂ card | "Here's the hidden cost. Starved and blocked stations still draw power, the curing oven most of all. LineLens puts kWh, rupees and CO₂ next to every bottleneck." |
| 7. Quality early warning | 2:50 | Quality · flagged vehicle | "Second story: weld-gun drift. This body was flagged right after the weld cell, long before End-of-Line inspection would catch it." |
| 8. The root cause lead | 3:05 | Common pattern | "The risky bodies share one weld gun, one electrode-cap lot, and one Tier-2 supplier. Catching the bodies still on the line avoids about ₹18,000 of End-of-Line rework. The playbook raises a supplier quality alert." |
| 9. Trust | 3:20 | Validation | "And we check ourselves. Every warning is compared with what actually happened later, false alarms included." |

Press **Finish demo** at about 3:35.

## Slide 5 — Impact (3:35–4:05)

**On slide:** three tiles: Vehicles & ₹ at risk · Rework avoided · kWh & CO₂ — footer "Assumption-based estimates over synthetic data."

> "So, three kinds of value from one screen. Lost output, priced per shift. Rework avoided by catching bodies in-line instead of at End-of-Line. And energy: kilowatt-hours per vehicle, the idle share, and CO₂. Today these are assumption-based estimates over synthetic data. The point of a pilot is to replace every placeholder with a real figure and measure it."

## Slide 6 — Pilot plan and ask (4:05–4:40)

**On slide:** A → B → C timeline.

> "We'd pilot in three steps, with no risk to production. Phase A, four weeks: we replay one line's historical cycle logs offline. Phase B, eight weeks: read-only shadow mode through an OPC UA or MQTT gateway from the historian, with no write-back. Phase C: supervisors use it on one line, and we measure alert lead time, precision, and avoided rework. Our ask is one line's historical cycle data and a process-engineering contact."

## Slide 7 — Close (4:40–5:00)

**On slide:** "See it early. Know the cost. Act with evidence."

> "LineLens doesn't replace your engineers or your control systems. It gives the supervisor an earlier, explainable, honest view of the line, with a price on waiting. See it early, know the cost, act with evidence. Thank you."

## Fallback if the live demo fails (30 seconds)

If the link does not load within about 10 seconds, or the demo stalls, say "Let me show you a recording of the same run" and switch to the screenshots. Then narrate:

| Screenshot | Say (≈ 5 s each) |
| --- | --- |
| Dashboard with Value at risk | "A drifting Chassis Marriage station, flagged early; about ₹68 lakh a shift at risk on placeholder figures." |
| Incident · Impact if nothing changes | "It becomes an incident with impact, evidence and a playbook; the supervisor decides." |
| Energy & CO₂ card | "Starved and blocked stations still burn energy; LineLens shows the idle-energy cost." |
| Quality · flagged body | "A weld drift flagged right after the weld cell, before End-of-Line." |
| Common pattern | "Traced to one weld gun, cap lot and Tier-2 supplier; catching it in-line avoids rework." |
| Validation drawer | "And every warning is checked against what happened next." |

Then continue with slide 5. The captures needed are listed in [docs/images/TODO.md](../images/TODO.md).
