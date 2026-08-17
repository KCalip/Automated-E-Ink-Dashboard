# CHANGELOG — RBC Dashboard (as of 08/16/2026)

Summary of everything changed since the earlier code snapshot that was in the
repository. Use this while committing.

---

## ⚠️ HOW TO COMMIT (read first)

The files previously in the repo had **newer save-dates but OLDER content** than
the current versions. Do **not** merge file-by-file by date — that keeps stale
versions and breaks things.

1. Extract `rbc_dashboard_FINAL.zip` **over** the repo folder, replacing everything.
2. Run `git diff` before committing. The only pre-existing change of note was the
   output path (`../output/`), and the current `compose.py` already contains it.
   If `git diff` shows any *other* intentional change that's now missing, stop and
   flag it before committing.
3. Confirm the **fonts actually appear** in the `fonts/` folder on github.com in
   the browser (binary files can get silently skipped by .gitignore). All four
   must be there: Pacifico-Regular.ttf, Poppins-Bold.ttf, Poppins-SemiBold.ttf,
   Poppins-Regular.ttf.

---

## compose.py
- **PRESERVED:** the `../output/` output-path change from the earlier repo version.
- Outlined weather-cloud icons — the plain white clouds were vanishing into the
  pale background on the actual frame; dark outline + gray fill fixes that.
- Pacifico **script header** for the trivia block.
- **Dynamic header:** shows "This Day in Disney History" on days with a real
  dated entry, "Did You Know?" on evergreen days.
- Dated entries now render as: header → date ("January 15, 1975") → event text.
  The redundant auto-headline was dropped (it echoed the event text).
- **Template switching:** loads the scheduled background for the date; falls back
  to the default if none is set or a file is missing.

## fetch_data.py
- **Weather source switched to Open-Meteo** (was OpenWeather). No API key, no
  signup, no credit card — nothing sensitive to store in a public repo.
- Added daily HIGH/LOW fetch.
- **Dateless-evergreen fallback:** days without an entry show a generic "Did You
  Know?" fact that makes NO date claim (fixes the bug where a missing day borrowed
  another day's dated fact and looked wrong).
- Added `kind` flag (history vs evergreen) so the header knows which to show.
- Added `resolve_template()` — reads schedule.json to pick a template by date.
  NOTE: this is the only function that knows where the schedule lives; swapping to
  a Google Sheet later changes only this function.

## layout.json
- Date centered on the orange dot (x=362).
- Weather block repositioned; hourly icons + temps moved down to clear the time
  labels.
- Park hours centered on true card centers and enlarged (so a changed closing
  time stays balanced).
- Trivia block with the larger script header.

## disney_history.json
- Expanded from 8 seed entries to **88 dated entries**: the HISTORY tab of
  Walt_Disney_World_park_data.xlsx (best event per day, WDW/Florida preferred)
  merged with verified milestone entries.
- Days not listed fall back to the evergreen "Did You Know?" facts.
- To add more: add a line `"MM-DD": {"year":"YYYY","headline":"...","blurb":"..."}`.
  (For dated entries the headline isn't shown, so it can be brief.)

## NEW FILES — must be committed
- **schedule.json** — date → template map you edit. Any date not listed uses the
  default. See SCHEDULE_HOWTO.md.
- **assets/templates/** — disney.png (live default), universal.png + resort.png
  (placeholders to replace with real art; keep 1086×1448, blank data areas).
- **fonts/Pacifico-Regular.ttf** — the script header font. Header errors without it.
- **SCHEDULE_HOWTO.md** — how to schedule a template for a date.
- **CHANGELOG_08162026.md** — this file.

---

## Credentials / setup reminders
- Weather + park hours need **no keys** (Open-Meteo + ThemeParks.wiki).
- The only credential anywhere is the **SwitchBot token + secret**, used solely
  by the push-to-frame step (your son's piece), stored as GitHub Actions secrets —
  never in the code or committed files.
