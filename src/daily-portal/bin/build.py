#!/usr/bin/env python3
import os, re, json, html, zipfile, datetime, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import *

def title_of(p):
    try: t = re.search(r"<title>([^<]*)", open(p, encoding="utf-8", errors="ignore").read(20000)).group(1)
    except Exception: return ""
    parts = [x.strip() for x in html.unescape(t).split("·")]
    return parts[-1] if len(parts) >= 3 else ""

def design_items(p):
    try: s = open(p, encoding="utf-8", errors="ignore").read()
    except Exception: return []
    return [k.split("·")[0].strip() for k in segments(s)][:6]

def favorites():
    store = load(STORE, {})
    recs = [r for r in store.values() if qualifies(r)]
    recs += [r for r in load(LIB, []) if qualifies(r)]
    out = []
    for r in recs:
        s = r.get("slug") or slug(r["date"], r["site"])
        mp = os.path.join(FAV, s, "meta.json")
        m = load(mp, None) or materialize(r)
        m["rating"], m["fav"] = r.get("rating"), r.get("fav")
        out.append(m)
    out.sort(key=lambda m: (m.get("library", False), m.get("date") or ""), reverse=True)
    return out

def status_snapshot():
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("api", os.path.join(os.path.dirname(__file__), "api.py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
        return m.status()
    except Exception: return {}

def main():
    os.makedirs(WWW, exist_ok=True)
    dates = set()
    for f in os.listdir(SITE):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f): dates.add(f[:10])
    for f in os.listdir(os.path.join(SITE, "design")):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.html", f): dates.add(f[:10])
    days = []
    for d in sorted(dates, reverse=True):
        xp, dp = os.path.join(SITE, d + ".html"), os.path.join(SITE, "design", d + ".html")
        days.append({"date": d, "x": f"/x/{d}.html" if os.path.exists(xp) else None,
                     "xtitle": title_of(xp) if os.path.exists(xp) else "",
                     "design": f"/design/{d}.html" if os.path.exists(dp) else None,
                     "designs": design_items(dp) if os.path.exists(dp) else []})
    favs = favorites()
    save(os.path.join(WWW, "favorites.json"), favs)
    zp = os.path.join(WWW, "favorites.zip")
    with zipfile.ZipFile(zp + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("favorites.json", json.dumps(favs, ensure_ascii=False, indent=1))
        for m in favs:
            d = os.path.join(FAV, m["slug"])
            for f in os.listdir(d): z.write(os.path.join(d, f), f"{m['slug']}/{f}")
    os.replace(zp + ".tmp", zp)
    tpl = open(os.path.join(os.path.dirname(__file__), "portal.html"), encoding="utf-8").read()
    data = json.dumps({"days": days, "favs": favs, "status": status_snapshot(), "built": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M") + " (UTC+8)"}, ensure_ascii=False).replace("</", "<\\/")
    with open(os.path.join(WWW, "index.html.tmp"), "w", encoding="utf-8") as f: f.write(tpl.replace("/*DATA*/null", data))
    os.replace(os.path.join(WWW, "index.html.tmp"), os.path.join(WWW, "index.html"))
    print(f"built {len(days)} days, {len(favs)} favorites")

if __name__ == "__main__": main()
