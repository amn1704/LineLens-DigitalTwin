# LineLens — 2:30 demo video script

A screen recording that follows the in-app **Pitch demo** (`PITCH_STEPS` in `frontend/src/tour.ts`). Record at 1440 × 900 or 1920 × 1080, browser zoom 100 %, with a single tab open. Keep the lower-third caption **"Synthetic data · illustrative assumptions"** on screen for the whole video.

> Independent student concept for the Maruti Suzuki Innovation Hackathon 2026. Not affiliated with or endorsed by Maruti Suzuki India Ltd. No Maruti Suzuki data is used.

## Setup

1. Start LineLens (hosted link or `docker run -p 8000:8000 linelens`), open the Dashboard, and dismiss the welcome dialog.
2. In **More → Impact assumptions**, press **Restore illustrative defaults**.
3. Start recording on the Dashboard, then press **Pitch demo**.

Steps 2 and 7 run the real simulator for a moment. Keep recording through the short wait and trim it in the edit if needed.

## Shot list

| Time | Pitch step | On-screen action | Voice-over |
| --- | --- | --- | --- |
| 0:00–0:10 | — (title) | Title card: "LineLens — an explainable digital twin for smarter, greener automotive assembly" and the disclaimer line. | "This is LineLens, an explainable digital twin for automotive assembly. Everything you'll see runs on synthetic data." |
| 0:10–0:25 | 1. The line | Press **Pitch demo**. The factory canvas is spotlighted. | "Eleven stations across Body Shop, Paint Shop and Final Assembly, with mixed sensor maturity. LineLens estimates every station and says how confident it is." |
| 0:25–0:42 | 2. A developing bottleneck | **Next.** Wait for the scenario; the Chassis Marriage inspector is spotlighted. | "A fixture at Chassis Marriage starts drifting. The real simulator runs, and LineLens flags the slowdown before the queue is obvious." |
| 0:42–0:55 | 3. Why it was flagged | **Next.** Inspector with current vs normal cycle. | "Current cycle against normal, a growing difference, and the queue. A persistent pattern, not one slow cycle." |
| 0:55–1:12 | 4. What happens if nothing changes | **Next.** Forecast view; Energy / vehicle and Value at risk / shift are spotlighted. Hold on the ₹ figure. | "If nothing changes, throughput falls from about 59 to 42 vehicles an hour. Over a shift that's roughly 136 vehicles, about ₹68 lakh at a placeholder margin. Every assumption is editable." |
| 1:12–1:27 | 5. From warning to action | **Next.** Incident page; "Impact if nothing changes" is spotlighted. Scroll briefly to the checks. | "The warning becomes an incident with its impact, evidence and a playbook. The supervisor decides; LineLens never controls the line." |
| 1:27–1:42 | 6. Greener line | **Next.** Energy & CO₂ card. | "Starved and blocked stations still draw power, the curing oven most of all. LineLens shows kWh, rupees and CO₂ next to the bottleneck." |
| 1:42–1:58 | 7. Quality early warning | **Next.** Wait for the weld scenario; the flagged vehicle card is spotlighted. | "Now a weld-gun drift. This body was flagged right after the weld cell, long before End-of-Line inspection would catch it." |
| 1:58–2:14 | 8. The root cause lead | **Next.** Common pattern card: weld gun, cap lot, supplier, rework avoided. | "The risky bodies share a weld gun, an electrode-cap lot and a Tier-2 supplier. Catching them in-line avoids about ₹18,000 of End-of-Line rework, and the playbook raises a supplier quality alert." |
| 2:14–2:24 | 9. Trust | **Next.** Validation drawer. | "And LineLens checks itself: every warning is compared with what happened later, false alarms included." |
| 2:24–2:30 | — (end card) | **Finish demo.** End card: "See it early. Know the cost. Act with evidence." | "See it early. Know the cost. Act with evidence." |

## Editing notes

- Add a small caption at 0:55 and 1:58: "₹ values: assumption-based estimates; placeholders editable in the app."
- Do not add logos or trademarks of Maruti Suzuki or Suzuki.
- If a figure on screen differs slightly from the voice-over (simulation timing varies a little), re-record the line to match the screen rather than editing the screen.
