"""
compose.py - draw live data onto the static background, output frame-ready PNG.

Usage:
  python3 compose.py            # uses live data (or sample fallback), writes output/
  python3 compose.py --eink     # also writes a 6-color quantized preview

Outputs:
  output/dashboard.png       (1200x1600, what you upload to the frame)
  output/dashboard_eink.png  (6-color simulated preview, only with --eink)
"""
import os, sys, json
from PIL import Image, ImageDraw, ImageFont
from fetch_data import gather

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT = json.load(open(os.path.join(HERE, "layout.json")))
PAL = LAYOUT["palette"]
FONT_FILES = {
    "Poppins-Bold": "fonts/Poppins-Bold.ttf",
    "Poppins-SemiBold": "fonts/Poppins-SemiBold.ttf",
    "Poppins-Regular": "fonts/Poppins-Regular.ttf",
}
FONT_ALIAS = {"heavy":"Poppins-Bold","semi":"Poppins-SemiBold","body":"Poppins-Regular"}

def hexrgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def col(name): return hexrgb(PAL[name])
_font_cache={}
def font(alias, size):
    fam = FONT_ALIAS.get(alias, alias)
    key=(fam,size)
    if key not in _font_cache:
        p=os.path.join(HERE, FONT_FILES.get(fam,"fonts/Poppins-Regular.ttf"))
        _font_cache[key]=ImageFont.truetype(p,size)
    return _font_cache[key]

def draw_text(d, spec, text):
    f=font(spec["font"], spec["size"])
    anchor=spec.get("anchor","la")
    d.text(tuple(spec["xy"]), str(text), font=f, fill=col(spec["color"]), anchor=anchor)

def wrap(d, text, f, max_w):
    words=text.split(); lines=[]; cur=""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textlength(t,font=f)<=max_w: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

# ---- weather icon glyphs, drawn as flat shapes (no baked art, e-ink safe) ----
def draw_icon(d, cx, cy, r, cond):
    c = cond.lower()
    gold=col("gold"); teal=col("muted_teal"); sage=hexrgb("#A2AB9F"); ink=col("ink")
    if "clear" in c or "sun" in c:
        d.ellipse([cx-r*0.55,cy-r*0.55,cx+r*0.55,cy+r*0.55], fill=gold)
        import math
        for a in range(0,360,45):
            x=cx+math.cos(math.radians(a))*r; y=cy+math.sin(math.radians(a))*r
            x2=cx+math.cos(math.radians(a))*r*0.72; y2=cy+math.sin(math.radians(a))*r*0.72
            d.line([x2,y2,x,y], fill=gold, width=4)
    elif "cloud" in c or "part" in c:
        d.ellipse([cx-r*0.5,cy-r*0.7,cx+r*0.2,cy], fill=gold)  # peeking sun
        d.ellipse([cx-r*0.9,cy-r*0.1,cx-r*0.1,cy+r*0.7], fill=sage)
        d.ellipse([cx-r*0.2,cy-r*0.3,cx+r*0.7,cy+r*0.6], fill=sage)
        d.ellipse([cx-r*0.5,cy+r*0.1,cx+r*0.9,cy+r*0.8], fill=sage)
    elif "rain" in c or "storm" in c or "drizzle" in c:
        d.ellipse([cx-r*0.9,cy-r*0.5,cx+r*0.9,cy+r*0.4], fill=teal)
        for dx in (-r*0.4,0,r*0.4):
            d.line([cx+dx,cy+r*0.5,cx+dx-4,cy+r*0.95], fill=col("teal"), width=4)
    elif "snow" in c:
        d.ellipse([cx-r*0.9,cy-r*0.5,cx+r*0.9,cy+r*0.4], fill=sage)
        for dx in (-r*0.4,0,r*0.4):
            d.ellipse([cx+dx-3,cy+r*0.6,cx+dx+3,cy+r*0.9], fill=teal)
    else:  # default cloud
        d.ellipse([cx-r*0.9,cy-r*0.2,cx+r*0.9,cy+r*0.7], fill=sage)

def compose(data, eink=False):
    bg=Image.open(os.path.join(HERE,"assets/background.png")).convert("RGB")
    d=ImageDraw.Draw(bg)
    w=data["weather"]

    # weather block
    draw_text(d, LAYOUT["weather"]["temp"], f'{w["temp"]}\u00b0')
    draw_text(d, LAYOUT["weather"]["condition"], w["condition"])
    draw_text(d, LAYOUT["weather"]["feels_like"], f'Feels Like {w["feels_like"]}\u00b0')
    draw_text(d, LAYOUT["weather"]["humidity"], w["humidity"])
    draw_text(d, LAYOUT["weather"]["wind"], w["wind"])
    draw_text(d, LAYOUT["weather"]["uv"], w["uv"])

    # hourly
    H=LAYOUT["hourly"]; cream=col("cream")
    for i, hr in enumerate(w["hourly"][:7]):
        cx=H["cols_center_x"][i]
        # time
        d.text((cx,H["time_y"]), hr["label"], font=font("body",H["time_size"]),
               fill=col(H["time_color"]), anchor="ma")
        # cover baked icon with a cream disc, then draw live icon
        r=H["icon_r"]
        d.ellipse([cx-r-4,H["icon_cy"]-r-4,cx+r+4,H["icon_cy"]+r+4], fill=cream)
        draw_icon(d, cx, H["icon_cy"], r, hr["cond"])
        # temp
        d.text((cx,H["temp_y"]), f'{hr["temp"]}\u00b0', font=font("semi",H["temp_size"]),
               fill=col(H["temp_color"]), anchor="ma")

    # park hours
    P=LAYOUT["parks"]
    for i, t in enumerate(data["parks"][:4]):
        d.text((P["time_x"],P["rows_y"][i]), t, font=font(P["font"],P["size"]),
               fill=col(P["color"]), anchor=P["anchor"])

    # history
    hi=data["history"]; Hh=LAYOUT["history"]
    draw_text(d, Hh["date"], hi["date"])
    # headline wrap
    hs=Hh["headline"]; hf=font(hs["font"],hs["size"])
    hx,hy=hs["xy"]
    hlines=wrap(d, hi["headline"], hf, hs["max_w"])
    for ln in hlines[:2]:
        d.text((hx,hy), ln, font=hf, fill=col(hs["color"])); hy+=hs["leading"]
    # blurb starts below the (possibly 2-line) headline
    bs=Hh["blurb"]; f=font(bs["font"],bs["size"])
    lines=wrap(d, hi["blurb"], f, bs["max_w"])
    x=bs["xy"][0]; y=max(bs["xy"][1], hy+6)
    for ln in lines[:4]:
        d.text((x,y), ln, font=f, fill=col(bs["color"])); y+=bs["leading"]

    # scale to frame resolution
    out=bg.resize((LAYOUT["canvas"]["out_w"],LAYOUT["canvas"]["out_h"]), Image.LANCZOS)
    os.makedirs(os.path.join(HERE,"output"), exist_ok=True)
    out_path=os.path.join(HERE,"output/dashboard.png")
    out.save(out_path)

    if eink:
        palette=[(255,255,255),(20,20,20),(210,31,38),(242,183,5),(30,125,79),(27,79,160)]
        pim=Image.new("P",(1,1)); flat=[]
        for c in palette: flat+=list(c)
        flat+=[0]*(768-len(flat)); pim.putpalette(flat)
        q=out.quantize(palette=pim, dither=Image.FLOYDSTEINBERG).convert("RGB")
        q.save(os.path.join(HERE,"output/dashboard_eink.png"))
    return out_path

if __name__=="__main__":
    eink="--eink" in sys.argv
    data=gather()
    if data["weather"].get("_sample"):
        print("[note] weather sample data:", data["weather"]["_sample"])
    p=compose(data, eink=eink)
    print("wrote", p)
