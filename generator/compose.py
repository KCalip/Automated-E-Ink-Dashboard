"""compose.py - draw live data onto the new template. python3 compose.py [--eink]"""
import os, sys, json, math
from PIL import Image, ImageDraw, ImageFont
from fetch_data import gather

HERE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(HERE,"layout.json")))
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
    out=[]; cur=""
    for word in s.split():
        t=(cur+" "+word).strip()
        if d.textlength(t,font=f)<=w: cur=t
        else: out.append(cur); cur=word
    if cur: out.append(cur)
    return out

# sample the cream background so icon-cover discs blend in
def bg_sample(img,x,y): return img.getpixel((max(0,min(x,img.width-1)),max(0,min(y,img.height-1))))

def draw_icon(d,cx,cy,r,cond,cover):
    c=cond.lower()
    gold=hexrgb("#E8A21E"); cloud=hexrgb("#C7CBB8"); ink=hexrgb("#12333B"); teal=hexrgb("#3E6B6B")
    ow=3  # outline width
    if cover:
        d.ellipse([cx-r-6,cy-r-6,cx+r+6,cy+r+6], fill=cover)
    if "clear" in c:
        d.ellipse([cx-r*0.6,cy-r*0.6,cx+r*0.6,cy+r*0.6],fill=gold,outline=ink,width=ow)
        for a in range(0,360,45):
            x1=cx+math.cos(math.radians(a))*r*0.78; y1=cy+math.sin(math.radians(a))*r*0.78
            x2=cx+math.cos(math.radians(a))*r*1.05; y2=cy+math.sin(math.radians(a))*r*1.05
            d.line([x1,y1,x2,y2],fill=gold,width=4)
    elif "part" in c or ("cloud" in c and "very" not in c):
        # sun peeking, THEN cloud with dark outline + gray fill so it reads on e-ink
        d.ellipse([cx-r*0.5,cy-r*0.8,cx+r*0.2,cy-r*0.1],fill=gold,outline=ink,width=ow)
        # cloud as merged puffs with a single outline: draw fill then stroke the silhouette
        puffs=[(cx-r*0.85,cy-r*0.05,cx-r*0.05,cy+r*0.72),
               (cx-r*0.3,cy-r*0.25,cx+r*0.7,cy+r*0.62),
               (cx-r*0.6,cy+r*0.05,cx+r*0.9,cy+r*0.78)]
        for p in puffs: d.ellipse(p,fill=cloud)
        for p in puffs: d.ellipse(p,outline=ink,width=ow)
        # cover interior seams by refilling centers (keeps outline only on outer edge visually)
        d.ellipse([cx-r*0.55,cy+r*0.15,cx+r*0.6,cy+r*0.6],fill=cloud)
    elif "rain" in c or "drizzle" in c or "storm" in c:
        d.ellipse([cx-r*0.85,cy-r*0.55,cx+r*0.85,cy+r*0.35],fill=cloud,outline=ink,width=ow)
        for dx in (-r*0.4,0,r*0.4):
            d.line([cx+dx,cy+r*0.45,cx+dx-4,cy+r*0.95],fill=teal,width=5)
    elif "snow" in c:
        d.ellipse([cx-r*0.85,cy-r*0.55,cx+r*0.85,cy+r*0.35],fill=cloud,outline=ink,width=ow)
        for dx in (-r*0.4,0,r*0.4): d.ellipse([cx+dx-3,cy+r*0.55,cx+dx+3,cy+r*0.85],fill=teal)
    else:
        d.ellipse([cx-r*0.85,cy-r*0.3,cx+r*0.85,cy+r*0.6],fill=cloud,outline=ink,width=ow)

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
        draw_icon(d,cx,H["icon_cy"],H["icon_r"],hr["cond"],cover)
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
