# CHANGELOG — RBC Dashboard (08/17/2026)

Changes made in this session, on top of CHANGELOG_08162026.md.

---

## compose.py

**Day/night-aware weather icons**
- Hourly icons now switch on real sunrise/sunset (pulled from Open-Meteo per
  date/location), not a fixed hour.
- After sunset: a clean crescent **moon** (dark navy, drawn as a filled
  circle-difference shape via a mask — crisp on e-ink, no muddy carve).
- Before sunset: normal day icons (sun, or sun-behind-cloud) regardless of hour.
  So in summer a 7 PM still shows a sun; as sunset creeps earlier through the
  year, 7 PM (then 5 PM) flips to a moon automatically.
- No moon-behind-cloud and no sun at night — night is always just a moon.

**Rebuilt cloud icons (fair-weather, not rain-cloud)**
- New `draw_cloud()` helper: compact silhouette with a flat-ish base and one
  CLEAN outer outline (built by dilating a fill mask and subtracting it, so
  there are no internal seams). Warm-white fill instead of gray.
- Partly-cloudy: sun upper-left with the cloud overlapping its lower-right,
  matching the reference concept.
- Rain/snow reuse the same clean cloud shape as their base.
- Outline weight set to `ow=2` (lighter, closer to the template's "Today's
  Forecast" cloud, while still surviving the panel's dithering). `ow=1` would
  match the template even more but risks breaking up on e-ink.

**Trivia block: explicit line breaks + spacing**
- `wrap()` now honors `\n` in a blurb (splits on newline first, then word-wraps
  each segment). Also handles a literal backslash-n stored in JSON.
- NOTE: the block fits ~3 lines. `\n` gives manual control but does not hard-cap
  line count — keep entries short enough to fit, or use `\n` to make lines
  shorter, not to add a long extra line.

## layout.json
- Trivia text block shifted left (x≈285) and wrap widened (max_w 740) so more
  words fit per line and the block centers between the starburst and the block's
  right edge.

## fetch_data.py
- Open-Meteo request now also pulls daily `sunrise,sunset` for the day/night
  icon logic.
- Sample-data hourly entries carry a `night` flag (7 PM = day, 9 PM = night) so
  offline test renders reflect current-season sunset (~8 PM).

## disney_history.json
- Grown to 164 dated entries (verified additions from the screenshot-sourcing
  work). Includes an 08-18 line-break test entry — safe to remove once testing
  is done.

---

## Commit notes
- No new dependencies or files beyond this changelog.
- Fonts unchanged (Pacifico already committed last session — confirm it's still
  present in fonts/).
- Everything still writes to ../output/ (unchanged).
