# CHANGELOG — RBC Dashboard (08/19/2026)

Changes made in this session, on top of CHANGELOG_081726.md.

---

## Hourly rain icons (new)

Rainy hours in the hourly forecast now show a **cloud with a single blue
teardrop**, so guests can see at a glance when showers are likely.

**fetch_data.py**
- Open-Meteo request now also pulls hourly `precipitation_probability`.
- Each hourly slot carries `pop` (percent) and a `rain` flag.
- New tunable constant near the top: `RAIN_POP_THRESHOLD = 20`.
  A slot gets the raindrop only when its chance is at least this value.
  Raise it for fewer drops, lower it for more. (Set to 20% per request.)
- Sample/offline data updated with pop + rain flags so test renders show rain.

**compose.py**
- `draw_icon()` takes a `rain` flag. When set:
  - Day: **cloud + teardrop only** (no sun).
  - Night: cloud + teardrop (instead of the moon) if it's raining; otherwise moon.
- New `draw_drop()` helper draws a real teardrop shape (pointed top, round
  bottom) — replaces the earlier short line that read like a tally mark.

---

## Icon set summary (current visual language)
- Plain sun ............ clear, daytime
- Sun behind cloud ..... partly cloudy, daytime
- Cloud + teardrop ..... rain likely (chance >= threshold)
- Crescent moon ....... after sunset, no rain

Day vs. night is decided by real sunrise/sunset from Open-Meteo (see 08/17 log).

---

## Commit notes
- No new files or dependencies.
- Threshold lives in fetch_data.py (`RAIN_POP_THRESHOLD`) — change one number.
- Everything still writes to ../output/ (unchanged).
