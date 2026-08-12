"""
fetch_data.py - pulls the live values for the RBC dashboard.

Sources:
  - Weather + hourly: OpenWeather One Call 3.0  (needs OPENWEATHER_API_KEY)
  - Park hours:        ThemeParks.wiki (no key required)
  - Disney history:    local disney_history.json

If OPENWEATHER_API_KEY is unset, weather falls back to SAMPLE data so you can
test the image pipeline offline. Park hours will still try the live (keyless) API;
if the network is unavailable it falls back to sample too.
"""
import os, json, datetime, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))

# Kissimmee, FL (RBC / Runaway Beach Club area)
LAT, LON = 28.3086, -81.4326

# ThemeParks.wiki entity IDs for the four WDW parks (stable UUIDs).
WDW_PARKS = [
    ("Magic Kingdom",     "75ea578a-adc8-4116-a54d-dccb60765ef9"),
    ("EPCOT",             "47f90d2c-e191-4239-a466-5892ef59a88b"),
    ("Hollywood Studios", "288747d1-8b4f-4a64-867e-ea7c9b27bad8"),
    ("Animal Kingdom",    "1c84a229-8862-4648-9c71-378ddd2c7693"),
]

UA = {"User-Agent": "RBC-Dashboard/1.0 (personal STR guest display)"}

def _get_json(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

# ---------- WEATHER ----------
def fetch_weather():
    key = os.environ.get("OPENWEATHER_API_KEY")
    if not key:
        return _sample_weather("no OPENWEATHER_API_KEY set")
    try:
        url = (f"https://api.openweathermap.org/data/3.0/onecall"
               f"?lat={LAT}&lon={LON}&units=imperial&exclude=minutely,daily,alerts&appid={key}")
        d = _get_json(url)
        cur = d["current"]
        # hourly: pick 9a,11a,1p,3p,5p,7p,9p local
        tz_off = d.get("timezone_offset", -14400)
        want_hours = [9, 11, 13, 15, 17, 19, 21]
        picks = []
        for h in d["hourly"]:
            lt = datetime.datetime.utcfromtimestamp(h["dt"] + tz_off)
            if lt.hour in want_hours and lt.date() == datetime.datetime.utcfromtimestamp(cur["dt"]+tz_off).date():
                picks.append((lt.hour, round(h["temp"]), h["weather"][0]["main"]))
        # dedupe by hour, keep order of want_hours
        by_hour = {p[0]: p for p in picks}
        hourly = []
        for wh in want_hours:
            if wh in by_hour:
                _, t, cond = by_hour[wh]
                hourly.append({"label": _fmt_hour(wh), "temp": t, "cond": cond})
        return {
            "temp": round(cur["temp"]),
            "condition": cur["weather"][0]["description"].title(),
            "feels_like": round(cur["feels_like"]),
            "humidity": f'{cur["humidity"]}%',
            "wind": f'{round(cur["wind_speed"])} mph',
            "uv": _uv_label(cur.get("uvi", 0)),
            "hourly": hourly,
        }
    except Exception as e:
        return _sample_weather(f"weather fetch failed: {e}")

def _fmt_hour(h):
    ap = "a" if h < 12 else "p"
    hh = h if h <= 12 else h-12
    if hh == 0: hh = 12
    return f"{hh}{ap}"

def _uv_label(uvi):
    uvi = round(uvi)
    if uvi <= 2: risk = "Low"
    elif uvi <= 5: risk = "Mod"
    elif uvi <= 7: risk = "High"
    elif uvi <= 10: risk = "V.High"
    else: risk = "Extreme"
    return f"{uvi} {risk}"

def _sample_weather(reason):
    return {
        "_sample": reason,
        "temp": 88, "condition": "Partly Sunny", "feels_like": 92,
        "humidity": "62%", "wind": "E 10 mph", "uv": "7 High",
        "hourly": [
            {"label":"9a","temp":82,"cond":"Clear"},
            {"label":"11a","temp":87,"cond":"Clouds"},
            {"label":"1p","temp":90,"cond":"Clouds"},
            {"label":"3p","temp":89,"cond":"Rain"},
            {"label":"5p","temp":85,"cond":"Rain"},
            {"label":"7p","temp":81,"cond":"Clouds"},
            {"label":"9p","temp":78,"cond":"Clear"},
        ],
    }

# ---------- PARK HOURS ----------
def _fmt_time(iso):
    # iso like 2026-08-06T09:00:00-04:00
    t = datetime.datetime.fromisoformat(iso)
    h = t.hour; ap = "a" if h < 12 else "p"
    hh = h if h <= 12 else h-12
    if hh == 0: hh = 12
    m = t.minute
    return f"{hh}:{m:02d}{ap}" if m else f"{hh}{ap}"

def fetch_park_hours():
    today = datetime.date.today().isoformat()
    out = []
    for name, pid in WDW_PARKS:
        try:
            d = _get_json(f"https://api.themeparks.wiki/v1/entity/{pid}/schedule")
            op = [s for s in d.get("schedule", [])
                  if s.get("date") == today and s.get("type") == "OPERATING"]
            if op:
                s = op[0]
                out.append(f"{_fmt_time(s['openingTime'])} \u2013 {_fmt_time(s['closingTime'])}")
            else:
                out.append("--")
        except Exception:
            out.append(_sample_hours(name))
    return out

def _sample_hours(name):
    return {"Magic Kingdom":"9a \u2013 10p","EPCOT":"9a \u2013 9p",
            "Hollywood Studios":"9a \u2013 9p","Animal Kingdom":"8a \u2013 7p"}.get(name,"--")

# ---------- DISNEY HISTORY ----------
def fetch_history():
    with open(os.path.join(HERE, "disney_history.json")) as f:
        data = json.load(f)
    key = datetime.date.today().strftime("%m-%d")
    if key in data:
        e = data[key]
        d = datetime.date.today()
        return {"date": d.strftime("%B %-d, ") + e["year"],
                "headline": e["headline"], "blurb": e["blurb"]}
    # fallback: rotate through available real entries by day-of-year
    entries = [(k,v) for k,v in data.items() if not k.startswith("_")]
    entries.sort()
    v = entries[datetime.date.today().timetuple().tm_yday % len(entries)][1]
    return {"date": f"On This Day \u00b7 {v['year']}", "headline": v["headline"], "blurb": v["blurb"]}

def gather():
    return {"weather": fetch_weather(),
            "parks": fetch_park_hours(),
            "history": fetch_history()}

if __name__ == "__main__":
    print(json.dumps(gather(), indent=2))
