"""compose.py - draw live data onto the new template. python3 compose.py [--eink]"""
import os, sys, json, math
from PIL import Image, ImageDraw, ImageFont
from fetch_data import gather

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE,"layout.json"), encoding="utf-8"))
PAL = L["palette"]
FA = {"heavy":"Poppins-Bold","semi":"Poppins-SemiBold","body":"Poppins-Regular","script":"Pacifico-Regular"}
FF = {"Poppins-Bold":"fonts/Poppins-Bold.ttf","Poppins-SemiBold":"fonts/Poppins-SemiBold.ttf","Poppins-Regular":"fonts/Poppins-Regular.ttf","Pacifico-Regular":"fonts/Pacifico-Regular.ttf"}

def hexrgb(h): h=h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def col(n): return hexrgb(PAL[n])
_fc={}
def font(alias,size):
    fam=FA.get(alias,alias); k=(fam,size)
    if k not in _fc: _fc[k]=ImageFont.truetype(os.path.join(HERE,FF[fam]),size)
    return _fc[k]
def txt(d,spec,s):
    d.text(tuple(spec["xy"]), str(s), font=font(spec["font"],spec["size"]),
           fill=col(spec["color"]), anchor=spec.get("anchor","la"))
def wrap(d,s,f,w):
    # Honor explicit line breaks (\n or literal backslash-n from JSON), then
    # word-wrap each segment to the width.
    s=s.replace("\\n","\n")           # in case JSON stored a literal backslash-n
    out=[]
    for segment in s.split("\n"):
        cur=""
        for word in segment.split():
            t=(cur+" "+word).strip()
            if d.textlength(t,font=f)<=w: cur=t
            else:
                if cur: out.append(cur)
                cur=word
        out.append(cur)              # keep the segment's last line (even if empty)
    return out

# sample the cream background so icon-cover discs blend in
def bg_sample(img,x,y): return img.getpixel((max(0,min(x,img.width-1)),max(0,min(y,img.height-1))))

def draw_moon(d,cx,cy,r,ink,gold,bg):
    # Clean crescent: solid dark-ink shape built as (full disc) minus (offset disc).
    # Drawn on a mask so the crescent is a crisp filled shape, not a carve that
    # depends on matching the background color.
    from PIL import Image, ImageDraw
    size=int(r*2.6); 
    m=Image.new("L",(size,size),0); md=ImageDraw.Draw(m)
    R=r*0.82
    ox,oy=size/2, size/2
    # full disc
    md.ellipse([ox-R,oy-R,ox+R,oy+R],fill=255)
    # subtract an offset disc to carve the crescent (offset up-right)
    off=R*0.62
    md.ellipse([ox-R+off,oy-R-off*0.45,ox+R+off,oy+R-off*0.45],fill=0)
    # paste solid ink through the mask
    swatch=Image.new("RGB",(size,size),(20,40,90))  # dark navy moon
    d._image.paste(swatch,(int(cx-size/2),int(cy-size/2)),m)

def draw_cloud(d,cx,cy,w,fill,ink,ow=3):
    # Compact fair-weather cloud with ONE clean outer outline (no internal seams).
    # Built by filling a silhouette mask, then deriving the outline as the
    # difference between a dilated mask and the mask itself.
    from PIL import Image, ImageDraw, ImageFilter
    pad=ow+4
    W=int(w); H=int(w*0.66)
    S=(W+pad*2, H+pad*2)
    m=Image.new("L",S,0); md=ImageDraw.Draw(m)
    ox,oy=pad,pad
    bumps=[(ox+W*0.02,oy+H*0.32,ox+W*0.44,oy+H*0.95),   # left
           (ox+W*0.22,oy+H*0.02,ox+W*0.78,oy+H*0.82),   # center (tallest)
           (ox+W*0.54,oy+H*0.28,ox+W*0.99,oy+H*0.95)]   # right
    for b in bumps: md.ellipse(b,fill=255)
    md.rectangle([ox+W*0.12,oy+H*0.58,ox+W*0.88,oy+H*0.95],fill=255)  # flat base
    # outline = (dilated mask) - (mask), so only the OUTER edge is stroked
    dil=m.filter(ImageFilter.MaxFilter(ow*2+1))
    from PIL import ImageChops
    outline=ImageChops.subtract(dil,m)
    px,py=int(cx-S[0]/2),int(cy-S[1]/2)
    d._image.paste(Image.new("RGB",S,fill),(px,py),m)       # fill first
    d._image.paste(Image.new("RGB",S,ink),(px,py),outline)  # clean outer outline

def draw_icon(d,cx,cy,r,cond,cover,night=False,bg=(230,232,220)):
    c=cond.lower()
    gold=hexrgb("#E8A21E"); cloud=hexrgb("#F2EFE2"); ink=hexrgb("#12333B"); teal=hexrgb("#3E6B6B")
    ow=2  # outline width (lighter, closer to template cloud)
    if cover:
        d.ellipse([cx-r-6,cy-r-6,cx+r+6,cy+r+6], fill=cover)

    # ---- NIGHT: sun is down. Always just a moon (no clouds, no sun). ----
    if night:
        draw_moon(d,cx,cy,r,ink,gold,bg)
        return

    # ---- DAY ----
    if "clear" in c:
        d.ellipse([cx-r*0.6,cy-r*0.6,cx+r*0.6,cy+r*0.6],fill=gold,outline=ink,width=ow)
        for a in range(0,360,45):
            x1=cx+math.cos(math.radians(a))*r*0.78; y1=cy+math.sin(math.radians(a))*r*0.78
            x2=cx+math.cos(math.radians(a))*r*1.05; y2=cy+math.sin(math.radians(a))*r*1.05
            d.line([x1,y1,x2,y2],fill=gold,width=4)
    elif "part" in c or ("cloud" in c and "very" not in c):
        # sun in upper-left, fair-weather cloud overlapping its lower-right (like reference)
        d.ellipse([cx-r*0.85,cy-r*0.9,cx-r*0.0,cy-r*0.05],fill=gold,outline=ink,width=ow)
        for a in range(0,360,45):
            sx=cx-r*0.42; sy=cy-r*0.48
            x1=sx+math.cos(math.radians(a))*r*0.52; y1=sy+math.sin(math.radians(a))*r*0.52
            x2=sx+math.cos(math.radians(a))*r*0.72; y2=sy+math.sin(math.radians(a))*r*0.72
            d.line([x1,y1,x2,y2],fill=gold,width=3)
        draw_cloud(d,cx+r*0.22,cy+r*0.42,r*1.75,cloud,ink,ow)
    elif "rain" in c or "drizzle" in c or "storm" in c:
        draw_cloud(d,cx,cy-r*0.2,r*1.7,cloud,ink,ow)
        for dx in (-r*0.35,0,r*0.35):
            d.line([cx+dx,cy+r*0.5,cx+dx-3,cy+r*0.95],fill=teal,width=5)
    elif "snow" in c:
        draw_cloud(d,cx,cy-r*0.2,r*1.7,cloud,ink,ow)
        for dx in (-r*0.35,0,r*0.35): d.ellipse([cx+dx-3,cy+r*0.55,cx+dx+3,cy+r*0.85],fill=teal)
    else:
        draw_cloud(d,cx,cy,r*1.8,cloud,ink,ow)

def compose(data,eink=False):
    # pick the scheduled template; fall back to the plain background if missing
    tpl = data.get("template", "disney")
    tpl_path = os.path.join(HERE, "assets", "templates", f"{tpl}.png")
    if not os.path.exists(tpl_path):
        tpl_path = os.path.join(HERE, "assets", "background.png")  # safety net
    bg=Image.open(tpl_path).convert("RGB")
    d=ImageDraw.Draw(bg)
    w=data["weather"]

    # date header
    txt(d,L["date"]["weekday"],data["date"]["weekday"])
    txt(d,L["date"]["full"],data["date"]["full"])

    # forecast high / low
    txt(d,L["forecast"]["high"],f'{w["high"]}\u00b0')
    txt(d,L["forecast"]["low"], f'{w["low"]}\u00b0')

    # hourly temps + live icons
    H=L["hourly"]
    for i,hr in enumerate(w["hourly"][:7]):
        cx=H["cols_center_x"][i]
        cover=bg_sample(bg,cx,H["icon_cy"]) if H.get("cover_icons") else None
        bgcol=bg_sample(bg,cx,H["icon_cy"]-int(H["icon_r"]*0.5))
        draw_icon(d,cx,H["icon_cy"],H["icon_r"],hr["cond"],cover,hr.get("night",False),bgcol)
        d.text((cx,H["temp_y"]),f'{hr["temp"]}\u00b0',font=font("heavy",H["temp_size"]),
               fill=col(H["temp_color"]),anchor="mm")

    # park times under each card
    P=L["parks"]
    for i,t in enumerate(data["parks"][:4]):
        d.text((P["cards_center_x"][i],P["time_y"]),t,font=font(P["font"],P["size"]),
               fill=col(P["colors"][i]),anchor=P["anchor"])

    # history / trivia block with dynamic header
    hi=data["history"]; Hh=L["history"]
    header = "This Day in Disney History" if hi.get("kind")=="history" else "Did You Know?"
    txt(d, Hh["header"], header)
    # Sub-line: for dated entries show the DATE (headline would just echo the blurb);
    # for evergreen show the topic headline.
    if hi.get("kind")=="history":
        line = hi["date"]
    else:
        line = hi.get("headline","")
    txt(d, Hh["date"], line)
    # blurb / event text
    bs=Hh["body"]; f=font(bs["font"],bs["size"])
    x,y=bs["xy"]
    for ln in wrap(d,hi["blurb"],f,bs["max_w"])[:3]:
        d.text((x,y),ln,font=f,fill=col(bs["color"])); y+=bs["leading"]

    out=bg.resize((L["canvas"]["out_w"],L["canvas"]["out_h"]),Image.LANCZOS)
    OUT_DIR = os.path.join(HERE, "..", "output")
    os.makedirs(OUT_DIR, exist_ok=True)
    p=os.path.join(OUT_DIR, "dashboard.png"); out.save(p)
    if eink:
        pal=[(255,255,255),(20,20,20),(210,31,38),(242,183,5),(30,125,79),(27,79,160)]
        pim=Image.new("P",(1,1)); flat=[]
        for c in pal: flat+=list(c)
        flat+=[0]*(768-len(flat)); pim.putpalette(flat)
        out.quantize(palette=pim,dither=Image.FLOYDSTEINBERG).convert("RGB").save(os.path.join(OUT_DIR,"dashboard_eink.png"))
    return p

if __name__=="__main__":
    data=gather()
    if data["weather"].get("_sample"): print("[note] SAMPLE weather:",data["weather"]["_sample"])
    print("wrote",compose(data,eink="--eink" in sys.argv))
