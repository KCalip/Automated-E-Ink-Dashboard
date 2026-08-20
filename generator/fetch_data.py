"""
fetch_data.py - live values for the RBC dashboard.

Sources (ALL FREE, NO API KEY, NO SIGNUP):
  - Weather:    Open-Meteo (current + daily high/low + hourly)   open-meteo.com
  - Park hours: ThemeParks.wiki                                  api.themeparks.wiki
  - History:    local disney_history.json

Nothing here needs a key. If the network is unavailable (e.g. a locked-down
sandbox), each fetcher falls back to clearly-marked SAMPLE data so the image
pipeline still renders for layout testing.
"""
import os, json, datetime, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# Show a raindrop on an hourly slot only when precip probability is at least this.
# Tune to taste: lower = more raindrops. 30 keeps Florida's constant low chances quiet.
RAIN_POP_THRESHOLD = 20

# RBC / Runaway Beach Club, Kissimmee FL (Disney area)
LAT, LON = 28.3086, -81.4326
TZ = "America/New_York"

WDW_PARKS = [
    ("Magic Kingdom",     "75ea578a-adc8-4116-a54d-dccb60765ef9"),
    ("EPCOT",             "47f90d2c-e191-4239-a466-5892ef59a88b"),
    ("Hollywood Studios", "288747d1-8b4f-4a64-867e-ea7c9b27bad8"),
    ("Animal Kingdom",    "1c84a229-8862-4648-9c71-378ddd2c7693"),
]
UA = {"User-Agent": "RBC-Dashboard/2.0 (personal guest display)"}

def _get_json(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

# ---------- WEATHER (Open-Meteo) ----------
def fetch_weather():
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={LAT}&longitude={LON}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,apparent_temperature"
            "&hourly=temperature_2m,weather_code,precipitation_probability"
            "&daily=temperature_2m_max,temperature_2m_min,uv_index_max,sunrise,sunset"
            f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone={TZ.replace('/','%2F')}"
            "&forecast_days=1"
        )
        d = _get_json(url)
        cur = d["current"]; daily = d["daily"]; hourly = d["hourly"]

        # sunrise/sunset hour (local) for day/night icon logic
        try:
            sr = int(daily["sunrise"][0][11:13])
            ss = int(daily["sunset"][0][11:13])
        except Exception:
            sr, ss = 7, 20  # sensible Florida fallback

        # pick 9,11,13,15,17,19,21 local from hourly arrays
        want = [9, 11, 13, 15, 17, 19, 21]
        times = hourly["time"]           # e.g. "2026-08-14T09:00"
        temps = hourly["temperature_2m"]
        codes = hourly["weather_code"]
        pops  = hourly.get("precipitation_probability", [0]*len(times))
        by_hour = {}
        for t, tp, cd, pp in zip(times, temps, codes, pops):
            hh = int(t[11:13])
            by_hour[hh] = (round(tp), _wmo(cd), pp if pp is not None else 0)
        hrly = []
        for h in want:
            if h in by_hour:
                tp, cond, pop = by_hour[h]
                is_night = (h < sr) or (h >= ss)
                # show a raindrop only when rain is worth noting
                rain = pop >= RAIN_POP_THRESHOLD
                hrly.append({"label": _fmt_hour(h), "temp": tp, "cond": cond,
                             "night": is_night, "pop": pop, "rain": rain})

        return {
            "high": round(daily["temperature_2m_max"][0]),
            "low":  round(daily["temperature_2m_min"][0]),
            "current": round(cur["temperature_2m"]),
            "feels_like": round(cur["apparent_temperature"]),
            "condition": _wmo(cur["weather_code"]),
            "humidity": f'{round(cur["relative_humidity_2m"])}%',
            "wind": f'{round(cur["wind_speed_10m"])} mph',
            "uv": _uv_label(daily["uv_index_max"][0]),
            "hourly": hrly,
        }
    except Exception as e:
        return _sample_weather(f"weather fetch failed: {e}")

# WMO weather code -> short label / icon family
def _wmo(code):
    c = int(code)
    if c == 0: return "Clear"
    if c in (1, 2): return "Partly Cloudy"
    if c == 3: return "Cloudy"
    if c in (45, 48): return "Fog"
    if c in (51, 53, 55, 56, 57): return "Drizzle"
    if c in (61, 63, 65, 66, 67, 80, 81, 82): return "Rain"
    if c in (71, 73, 75, 77, 85, 86): return "Snow"
    if c in (95, 96, 99): return "Storm"
    return "Cloudy"

def _fmt_hour(h):
    ap = "a" if h < 12 else "p"; hh = h if h <= 12 else h-12
    if hh == 0: hh = 12
    return f"{hh}{ap.upper()}M" if False else f"{hh} {ap.upper()}M"

def _uv_label(uvi):
    uvi = round(uvi or 0)
    r = "Low" if uvi<=2 else "Mod" if uvi<=5 else "High" if uvi<=7 else "V.High" if uvi<=10 else "Extreme"
    return f"{uvi} {r}"

def _sample_weather(reason):
    return {"_sample": reason, "high": 88, "low": 68, "current": 84,
            "feels_like": 88, "condition": "Partly Cloudy", "humidity": "62%",
            "wind": "10 mph", "uv": "7 High",
            "hourly": [
                {"label":"9 AM","temp":72,"cond":"Partly Cloudy","night":False,"pop":10,"rain":False},
                {"label":"11 AM","temp":78,"cond":"Clear","night":False,"pop":10,"rain":False},
                {"label":"1 PM","temp":84,"cond":"Partly Cloudy","night":False,"pop":40,"rain":True},
                {"label":"3 PM","temp":88,"cond":"Rain","night":False,"pop":60,"rain":True},
                {"label":"5 PM","temp":87,"cond":"Rain","night":False,"pop":50,"rain":True},
                {"label":"7 PM","temp":82,"cond":"Clear","night":False,"pop":20,"rain":True},
                {"label":"9 PM","temp":76,"cond":"Clear","night":True,"pop":10,"rain":False},
            ]}

# ---------- PARK HOURS ----------
def _fmt_time(iso):
    t = datetime.datetime.fromisoformat(iso)
    h = t.hour; ap = "AM" if h < 12 else "PM"; hh = h if h <= 12 else h-12
    if hh == 0: hh = 12
    return f"{hh}:{t.minute:02d} {ap}"

def fetch_park_hours():
    today = datetime.date.today().isoformat()
    out = []
    for name, pid in WDW_PARKS:
        try:
            d = _get_json(f"https://api.themeparks.wiki/v1/entity/{pid}/schedule")
            op = [s for s in d.get("schedule", []) if s.get("date")==today and s.get("type")=="OPERATING"]
            if op:
                s = op[0]
                out.append(f"{_fmt_time(s['openingTime'])} \u2013 {_fmt_time(s['closingTime'])}")
            else:
                out.append("Closed")
        except Exception:
            out.append(_sample_hours(name))
    return out

def _sample_hours(name):
    return {"Magic Kingdom":"9:00 AM \u2013 11:00 PM","EPCOT":"9:00 AM \u2013 9:00 PM",
            "Hollywood Studios":"9:00 AM \u2013 9:00 PM","Animal Kingdom":"8:00 AM \u2013 7:00 PM"}.get(name,"--")

# ---------- HISTORY ----------
# Evergreen, DATELESS lines for days with no specific entry.
# These make NO "on this day" claim, so they're never wrong. Rotates daily.
_EVERGREEN = [
    {"date": "Did You Know?", "headline": "Four Parks, One Resort", "blurb": "Walt Disney World is home to Magic Kingdom, EPCOT, Hollywood Studios, and Animal Kingdom \u2013 plus two water parks."},
    {"date": "Disney Fact", "headline": "Bigger Than a City", "blurb": "Walt Disney World spans about 25,000 acres near Orlando \u2013 roughly the size of San Francisco."},
    {"date": "Did You Know?", "headline": "The Original Park", "blurb": "Disneyland opened in California in 1955 and inspired the far larger Walt Disney World in Florida."},
    {"date": "Disney Fact", "headline": "Cinderella Castle", "blurb": "Magic Kingdom's Cinderella Castle stands 189 feet tall and has anchored the park since opening day in 1971."},
    {"date": "Did You Know?", "headline": "A Mouse Named Mickey", "blurb": "Walt's wife Lillian suggested the name 'Mickey' after Walt first called his mouse character 'Mortimer.'"},
    {"date": "Disney Fact", "headline": "Spaceship Earth", "blurb": "EPCOT's iconic geodesic sphere weighs over 15,000 tons and has been the park's symbol since 1982."},
    {"date": "Did You Know?", "headline": "Audio-Animatronics", "blurb": "Disney pioneered lifelike robotic figures, debuting the technology in Disneyland's Enchanted Tiki Room in 1963."},
]

def fetch_history():
    with open(os.path.join(HERE,"disney_history.json")) as f:
        data = json.load(f)
    today = datetime.date.today()
    key = today.strftime("%m-%d")
    if key in data:
        e = data[key]
        return {"kind": "history",
                "date": today.strftime("%B ") + str(today.day) + f", {e['year']}",
                "headline": e["headline"], "blurb": e["blurb"]}
    # No entry for today -> dateless evergreen line (never claims a wrong date)
    ev = _EVERGREEN[today.timetuple().tm_yday % len(_EVERGREEN)]
    return {"kind": "evergreen", **ev}

def gather():
    today = datetime.date.today()
    return {
        "date": {"weekday": today.strftime("%A").upper(),
                 "full": today.strftime("%B ").upper() + str(today.day) + today.strftime(", %Y")},
        "weather": fetch_weather(),
        "parks": fetch_park_hours(),
        "history": fetch_history(),
        "template": resolve_template(),
    }

def resolve_template(for_date=None):
    """Return the template NAME for a given date (default: today).

    Reads schedule.json. Any date not listed falls back to 'default'.
    NOTE: This is the ONLY function that knows *where* the schedule lives.
    To switch to a Google Sheet later, replace just this function's body
    with a fetch of the sheet -- nothing else in the pipeline changes.
    """
    d = (for_date or datetime.date.today()).isoformat()
    try:
        with open(os.path.join(HERE, "schedule.json")) as f:
            sched = json.load(f)
    except Exception:
        return "disney"  # safe fallback if schedule missing/broken
    default = sched.get("default", "disney")
    return sched.get("dates", {}).get(d, default)

if __name__ == "__main__":
    print(json.dumps(gather(), indent=2))
