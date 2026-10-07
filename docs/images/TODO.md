# Screenshot refresh — TODO

The existing captures (`live-*.png`) predate the impact and sustainability panels. Screenshots could not be saved from the environment that made these changes, so these captures are still needed. Use a locally running build (`npm run build`, then `uvicorn app.main:app --port 8102` from `backend/`, open `http://127.0.0.1:8102`) at 1440 × 900, browser zoom 100 %, with the impact assumptions at their illustrative defaults.

| File | How to capture | Must show |
| --- | --- | --- |
| `live-dashboard.png` (replace) | Demo → **Bottleneck**, then Dashboard in Twin view with Chassis Marriage selected. | Factory overview with **Energy / vehicle** and **Value at risk / shift** (₹, lakh grouping), the "Assumption-based · synthetic data" caption, and the Chassis Marriage inspector. |
| `live-sustainability.png` (new) | Same state; scroll the right panel to the **Energy & CO₂** card. | Idle-energy share, top idle-energy station, CO₂ so far, the "If the bottleneck persists" line, and the "Synthetic power profile · illustrative" caption. |
| `live-incidents.png` (replace) | After Bottleneck, open Incidents and select the production incident. | The **Impact if nothing changes** block (vehicles / shift, ₹ contribution, idle kWh) with "Assumption-based estimate · edit assumptions". |
| `live-quality.png` (replace) | Demo → **Weld quality issue**, Quality → **Inspect** filter, select a flagged body. | The vehicle card and the **Common pattern** card listing Weld Gun WG-04, Electrode Cap Lot EC-17, **Supplier SUP-T2-03 (Tier-2, synthetic)**, and the rework-avoided ₹ figure. |
| `live-assumptions.png` (new) | More → **Impact assumptions**. | All six editable assumptions and the illustrative-placeholder note. |
| `live-pitch-demo.png` (new) | Press **Pitch demo** and advance to step 4. | The pitch card ("Pitch demo · 04 / 09") spotlighting the impact metrics. |

`live-activity.png` and `live-trends.png` can stay as they are. After capturing, add the two new dashboard captures to the README's **Live product captures** table and to the fallback slide list in [the pitch script](../hackathon/PITCH-SCRIPT.md).
