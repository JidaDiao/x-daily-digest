import json, os, re, base64, hashlib, html, time, zipfile, datetime
ROOT = "/srv/daily"
SITE = ROOT + "/site"
DATA = ROOT + "/data"
FAV = ROOT + "/favorites"
WWW = ROOT + "/www"
STORE = DATA + "/feedback.json"
LIB = DATA + "/library.json"
TOKENS = DATA + "/design-tokens.json"

def load(p, d):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return d

def save(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)

def slug(date, site):
    a = re.sub(r"[^a-z0-9]+", "-", site.lower()).strip("-")[:40] or "item"
    h = hashlib.sha1(site.encode()).hexdigest()[:6]
    return f"{date}-{a}-{h}"

def qualifies(r):
    return r.get("site") != "test" and not r.get("test") and (r.get("fav") is True or (r.get("rating") or 0) >= 4)

def segments(page_html):
    """Yield (site, url, segment_html) for each data-site block in a design page."""
    ms = list(re.finditer(r'data-site="([^"]*)"(?:\s+data-url="([^"]*)")?', page_html))
    out = {}
    for i, m in enumerate(ms):
        start = page_html.rfind("<", 0, m.start())
        end = ms[i + 1].start() if i + 1 < len(ms) else len(page_html)
        site = html.unescape(m.group(1))
        if site in out: out[site] = (out[site][0], out[site][1] + page_html[start:end]); continue
        out[site] = (html.unescape(m.group(2) or ""), page_html[start:end])
    return out

def text_of(seg, n=400):
    seg = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", seg)
    seg = re.sub(r"data:[a-z]+/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=]+", "", seg)
    t = html.unescape(re.sub(r"<[^>]+>", " ", seg))
    return re.sub(r"\s+", " ", t).strip()[:n]

def tokens_for(site, url):
    toks = load(TOKENS, {}).get("tokens", [])
    key = site.split("·")[0].strip().lower()
    host = re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0].lower()
    res = []
    for t in toks:
        src = (t.get("source") or "").lower(); tu = (t.get("url") or "").lower()
        if (key and (key == src or key in t.get("id", "").lower().split("-")[0:1])) or (host and host not in ("mobbin.com",) and host in tu):
            res.append({k: t.get(k) for k in ("id", "title", "description", "css", "js", "status")})
    return res

def extract_media(date, site, dest):
    """Copy Mobbin originals (videos/images) from the mirrored design page into dest."""
    page = os.path.join(SITE, "design", f"{date}.html")
    if not os.path.exists(page): return [], "", ""
    src = open(page, encoding="utf-8", errors="ignore").read()
    segs = segments(src)
    if site not in segs: return [], "", ""
    url, seg = segs[site]
    os.makedirs(dest, exist_ok=True)
    media = []
    for i, p in enumerate(dict.fromkeys(re.findall(r'data-b64="([^"]+)"', seg))):
        fp = os.path.join(SITE, "design", p)
        if os.path.exists(fp):
            raw = open(fp, "rb").read().strip()
            if raw.startswith(b"data:"): raw = raw.split(b",", 1)[1]
            name = os.path.basename(p).replace(".b64", "")
            open(os.path.join(dest, name), "wb").write(base64.b64decode(raw))
            media.append(name)
    for i, (kind, ext, b) in enumerate(re.findall(r"data:(image|video)/([a-z0-9+]+);base64,([A-Za-z0-9+/=]+)", seg)):
        if len(b) < 2000: continue  # skip tiny icons
        ext = {"svg+xml": "svg", "jpeg": "jpg"}.get(ext, ext)
        name = f"{kind}-{i+1}.{ext}"
        open(os.path.join(dest, name), "wb").write(base64.b64decode(b))
        media.append(name)
    for p in dict.fromkeys(re.findall(r'(?:src|poster)="(assets/[^"]+\.(?:mp4|webm|png|jpe?g|webp|gif))"', seg)):
        fp = os.path.join(SITE, "design", p)
        if os.path.exists(fp):
            name = os.path.basename(p); open(os.path.join(dest, name), "wb").write(open(fp, "rb").read()); media.append(name)
    return media, url, text_of(seg)

def materialize(r):
    """Ensure favorites/<slug>/ has media + meta.json for a qualifying record."""
    s = r.get("slug") or slug(r["date"], r["site"])
    dest = os.path.join(FAV, s)
    os.makedirs(dest, exist_ok=True)
    media, purl, notes = extract_media(r["date"], r["site"], dest) if r.get("date") else ([], "", "")
    existing = sorted((f for f in os.listdir(dest) if f != "meta.json"), key=lambda f: (not f.startswith("hero"), f))
    meta = dict(r)
    meta.update(slug=s, media=existing, page_url=f"/design/{r['date']}.html" if r.get("date") and not r.get("library") else "")
    if not meta.get("url") and purl: meta["url"] = purl
    if not meta.get("notes") and notes: meta["notes"] = notes
    if not meta.get("tokens"): meta["tokens"] = tokens_for(r["site"], meta.get("url", ""))
    save(os.path.join(dest, "meta.json"), meta)
    return meta
