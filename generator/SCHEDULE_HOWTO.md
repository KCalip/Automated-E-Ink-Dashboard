# How to Show a Different Template on Certain Dates

## The idea
Most days show the default Disney template. On dates you choose, the frame shows
a different one (Universal, Resort Day, etc.). You control this by editing ONE file.

## To schedule a template for a date
1. Open **schedule.json**
2. In the "dates" block, add a line:  `"YYYY-MM-DD": "templatename",`
   - Example: `"2026-09-14": "universal",`
   - The template name is the image filename in assets/templates/ WITHOUT ".png"
3. Save. Done. That date now uses that template; every other date uses the default.

## To add a NEW template design
1. Make a 1086 x 1448 PNG (same size/layout as the Disney one, blank data areas).
2. Drop it in **assets/templates/** with a simple name, e.g. `beach.png`.
3. Reference it in schedule.json by that name (without .png): `"beach"`.

## Current templates
- `disney`   (the default)
- `universal` (placeholder - replace with real art)
- `resort`    (placeholder - replace with real art)

## Notes
- Any date not listed automatically uses the "default" (currently "disney").
- If a template name is misspelled or the file is missing, it safely falls back
  to the default - it won't crash.
- The data (weather, park hours, trivia) is drawn in the same spots on every
  template, so all templates must share the same 1086x1448 layout.

## Later: if editing JSON gets annoying
This can be upgraded to read a Google Sheet instead, so you edit a spreadsheet
from your phone. Only one function (resolve_template in fetch_data.py) changes;
the rest stays the same.
