# Sensor Alert Thresholds and Interpretation

## Overview
This document describes how to interpret sensor readings in the context of INDUSTRIA-X
predictive-maintenance alerts. Thresholds below are generic guidelines; always verify against
the specific equipment manufacturer's specifications and established site baselines.

---

## Vibration (RMS velocity, mm/s)
Based on general rotating machinery guidance:

| Zone | RMS velocity | Interpretation |
|---|---|---|
| A | 0–2.3 mm/s | Newly commissioned — excellent |
| B | 2.3–4.5 mm/s | Acceptable for long-term operation |
| C | 4.5–7.1 mm/s | Alarm — investigate; schedule correction |
| D | > 7.1 mm/s | Danger — immediate action required |

- Values are for machines ≤ 15 kW on rigid mounting. Higher values apply to larger machines;
  consult ISO 20816-3 for machine-class-specific limits.
- Trend change (rate of rise) is often more important than absolute level; a sudden doubling
  warrants investigation regardless of the absolute zone.

---

## Temperature (°C)
**Bearing housings (general):**
- Normal: ≤ 70 °C for most standard bearings.
- Warning: 70–90 °C — check lubrication; reduce load if possible.
- Alarm: > 90 °C — schedule inspection; prepare replacement.
- Critical: > 110 °C — immediate shutdown to prevent seizure.

**Motor windings:**
- Class F insulation limit: 155 °C.
- Class H insulation limit: 180 °C.
- Operating at or above class limit halves remaining insulation life per 10 °C excess.

**Pump casing (fluid-specific — these are generic examples):**
- High casing temperature may indicate cavitation or reduced flow; check process conditions.

---

## Acoustic / Ultrasonic (dB increase over baseline)
- +6 dB: early warning — increase lubrication and monitoring frequency.
- +12 dB: moderate deterioration — schedule inspection within 500 hours.
- +16 dB or more: advanced deterioration — plan replacement at next opportunity.

---

## Rotational Speed Deviation (%)
- Within ± 1% of setpoint: normal.
- ± 1–3%: investigate mechanical load variation or drive settings.
- > ± 3%: shutdown and diagnose; possible coupling failure or load shed.

---

## Current (% over nameplate full-load current)
- 0–100%: normal operating range.
- 100–115%: permissible short-term overload — investigate load; reduce if sustained.
- > 115%: persistent overload — thermal protection should trip; investigate before restart.

---

## Interpreting Compound Alerts
When multiple sensors trigger simultaneously, consider compound causes:

| Combination | Likely Cause |
|---|---|
| High vibration (1×) + high temperature | Unbalance or misalignment with lubrication stress |
| High vibration at bearing frequencies + high ultrasonic | Bearing surface fatigue |
| High temperature + normal vibration | Lubrication starvation (early stage) or winding thermal issue |
| Speed deviation + high current | Mechanical obstruction or coupling slip |
| High vibration (2×) + high axial vibration | Angular misalignment |
