# RBC Daily Dashboard (The Bonfire Bulletin)

Generates a 1200x1600 PNG for the SwitchBot 13.3" E-Ink Art Frame:
weather + hourly forecast, live WDW park hours, and Today in Disney History,
composited onto your static MCM background.

## One-time setup
    pip install pillow
    export OPENWEATHER_API_KEY=your_key_here   # One Call API 3.0

## Run it
    python3 compose.py            # writes output/dashboard.png
    python3 compose.py --eink     # also writes a 6-color preview

Without an API key it renders with SAMPLE weather so you can test offline.
Park hours use ThemeParks.wiki (no key).

## Files
    assets/background.png   your static art (fields left blank)
    layout.json             ALL text positions/sizes/colors — tweak here, no code
    disney_history.json     MM-DD keyed history; add your own entries
    fetch_data.py           pulls weather + park hours + history
    compose.py              draws data onto the background
    fonts/                  Poppins

## Adjusting positions
Everything is in layout.json in the background's native 1086x1448 space.
Move a number by editing its "xy". Re-run compose.py to see the change.

## Next: push to the frame
See push_to_frame.py (stub) for the SwitchBot upload call once you have
your SwitchBot API token + device ID.
