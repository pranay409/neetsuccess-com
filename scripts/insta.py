"""
Instagram hub for a blog site: the link-in-bio page (/ig/), one page per reel
(/ig/<slug>.html) and a "Follow us on Instagram" strip on every page.

Config: ig/config.json  {"handle": "neet.inside", "name": "NEET Inside", "tagline": "..."}
Posts:  ig/posts.json   [{"slug","title","date","reel_url","summary","body_md"}]  newest last

  python scripts/insta.py add --title "..." --reel "https://www.instagram.com/reel/..." \
         --summary "one line" --body-file notes.md [--date 2026-11-27]
  python scripts/insta.py build        # rebuild /ig pages, follow strip, sitemap entries

body_md is simple text: blank line = new paragraph, "## " = heading, "- " = bullet,
"1. " = numbered point, **bold** works. Links: [text](https://...).
"""
import argparse
import html as H
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGDIR = os.path.join(ROOT, "ig")
STRIP_MARKER = "<!-- padhle-insta -->"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _read(p):
    with open(p, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _write(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(t)


def config():
    p = os.path.join(IGDIR, "config.json")
    return json.loads(_read(p)) if os.path.exists(p) else None


def posts():
    p = os.path.join(IGDIR, "posts.json")
    return json.loads(_read(p)) if os.path.exists(p) else []


def domain():
    return _read(os.path.join(ROOT, "CNAME")).strip().replace("www.", "")


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:70].strip("-")


def md(text):
    """Tiny markdown: paragraphs, ## headings, - bullets, 1. lists, **bold**, [links](url)."""
    def inline(s):
        s = H.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2" style="color:#C2410C">\1</a>', s)
        return s
    out, lst = [], None
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        lines = [l.rstrip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        bullet, number = re.compile(r"^\s*[-*] "), re.compile(r"^\s*\d+[.)] ")
        if all(bullet.match(l) for l in lines):
            out.append("<ul>" + "".join("<li>" + inline(bullet.sub("", l)) + "</li>" for l in lines) + "</ul>")
        elif all(number.match(l) for l in lines):
            out.append("<ol>" + "".join("<li>" + inline(number.sub("", l)) + "</li>" for l in lines) + "</ol>")
        elif lines[0].startswith("## "):
            out.append(f"<h2>{inline(lines[0][3:])}</h2>")
            if lines[1:]:
                out.append(f"<p>{inline(' '.join(lines[1:]))}</p>")
        else:
            out.append(f"<p>{inline(' '.join(lines))}</p>")
    return "\n".join(out)


STYLE = """<style>
:root{--o:#FF6B00;--ink:#1F1F1F;--mut:#5F5F5F;--bg:#FFFBF7;--line:#F1E3D6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.6}
.wrap{max-width:720px;margin:0 auto;padding:24px 18px 48px}a{color:#C2410C}
.top{display:flex;align-items:center;gap:14px;margin-bottom:18px}.av{width:64px;height:64px;border-radius:50%;background:linear-gradient(135deg,#FEDA75,#FA7E1E,#D62976,#962FBF);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:24px;flex:none}
.top h1{font-size:22px;margin:0}.top p{margin:2px 0 0;color:var(--mut);font-size:14px}
.btn{display:inline-block;background:var(--o);color:#fff!important;text-decoration:none;font-weight:600;padding:11px 18px;border-radius:10px;font-size:15px}
.btn.ghost{background:#fff;color:var(--ink)!important;border:1px solid var(--line)}
.card{display:block;background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:12px 0;text-decoration:none;color:var(--ink)}
.card b{display:block;font-size:17px;margin-bottom:2px}.card span{color:var(--mut);font-size:14px}
h2{font-size:19px;margin:28px 0 8px}.muted{color:var(--mut);font-size:14px}
.reel{margin:18px 0}.reel blockquote{margin:0 auto!important}
article p,article li{font-size:17px}
</style>"""


def _page(title, desc, canonical, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{H.escape(title)}</title><meta name="description" content="{H.escape(desc)}"><link rel="canonical" href="{canonical}">
<meta property="og:title" content="{H.escape(title)}"><meta property="og:description" content="{H.escape(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:type" content="article">
{STYLE}</head><body><div class="wrap">{body}</div></body></html>"""


def _header(cfg):
    h = cfg["handle"]
    return f"""<div class="top"><div class="av">{H.escape(cfg['name'][:1])}</div><div><h1>{H.escape(cfg['name'])}</h1><p>@{H.escape(h)} · {H.escape(cfg.get('tagline',''))}</p></div></div>
<p><a class="btn" href="https://www.instagram.com/{h}/" rel="me">Follow @{H.escape(h)} on Instagram</a></p>"""


def build():
    cfg = config()
    if not cfg:
        return 0
    dom, items = domain(), sorted(posts(), key=lambda p: p.get("date", ""), reverse=True)
    import cta, tracker, seo_boost
    # one page per reel
    for p in items:
        url = f"https://{dom}/ig/{p['slug']}.html"
        embed = (f'<div class="reel"><blockquote class="instagram-media" data-instgrm-permalink="{H.escape(p["reel_url"])}" '
                 f'data-instgrm-version="14" style="max-width:420px;width:100%"><a href="{H.escape(p["reel_url"])}">Watch this reel on Instagram</a></blockquote>'
                 '<script async src="https://www.instagram.com/embed.js"></script></div>') if p.get("reel_url") else ""
        body = (_header(cfg) + f'<p class="muted"><a href="/ig/">All reel notes</a> · {H.escape(p.get("date",""))}</p>'
                f'<article><h1 style="font-size:26px;line-height:1.25">{H.escape(p["title"])}</h1>'
                f'<p class="muted">{H.escape(p.get("summary",""))}</p>{embed}{md(p.get("body_md",""))}</article>')
        page = _page(f"{p['title']} | {cfg['name']}", p.get("summary") or p["title"], url, body)
        page = seo_boost.add_related(page, url)
        page = cta.add_cta(page, dom)
        page = tracker.add_tracker(page)
        _write(os.path.join(IGDIR, f"{p['slug']}.html"), page)
    # link-in-bio page
    cards = "".join(f'<a class="card" href="/ig/{p["slug"]}.html"><b>{H.escape(p["title"])}</b><span>{H.escape(p.get("summary",""))}</span></a>' for p in items)
    if not cards:
        cards = '<p class="muted">Notes from our reels will appear here.</p>'
    arts = sorted(seo_boost.manifest(), key=lambda a: a.get("date", ""), reverse=True)[:5]
    art_cards = "".join(f'<a class="card" href="{a["url"]}"><b>{H.escape(a["title"])}</b><span>{H.escape((a.get("description") or "")[:120])}</span></a>' for a in arts)
    reels = []
    rp = os.path.join(IGDIR, "reels.json")
    if os.path.exists(rp):
        reels = json.loads(_read(rp))[:8]
    reel_cards = "".join(f'<a class="card" href="{H.escape(r["url"])}" rel="noopener"><b>{H.escape(r.get("title") or "Watch on Instagram")}</b><span>Watch on Instagram</span></a>' for r in reels)
    body = (_header(cfg) + '<h2>Notes from our reels</h2><p class="muted">Every reel that says "link in bio" has its notes here.</p>' + cards +
            (('<h2>Latest reels</h2>' + reel_cards) if reel_cards else '') +
            f'<h2>Latest guides on {H.escape(dom)}</h2>' + art_cards +
            f'<p style="margin-top:20px"><a class="btn ghost" href="/">Visit {H.escape(dom)}</a></p>')
    hub = _page(f"{cfg['name']} (@{cfg['handle']}) reel notes | {dom}", f"Notes, PDFs and links from @{cfg['handle']} reels.", f"https://{dom}/ig/", body)
    hub = cta.add_cta(hub, dom)
    hub = tracker.add_tracker(hub)
    _write(os.path.join(IGDIR, "index.html"), hub)
    follow_strip()
    add_to_sitemap(dom, items)
    return len(items)


def strip_html(cfg):
    h = cfg["handle"]
    return (STRIP_MARKER + '<div style="max-width:760px;margin:24px auto;padding:14px 18px;border-radius:12px;background:#fff;'
            'border:1px solid #F1E3D6;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;display:flex;flex-wrap:wrap;'
            'align-items:center;justify-content:space-between;gap:10px;box-sizing:border-box">'
            f'<span style="font-size:15px;color:#1F1F1F">Short NEET reels by <b>{H.escape(cfg["name"])}</b> on Instagram</span>'
            f'<span><a href="https://www.instagram.com/{h}/" rel="me" style="color:#C2410C;font-weight:600;text-decoration:none;margin-right:14px">Follow @{H.escape(h)}</a>'
            '<a href="/ig/" style="color:#C2410C;font-weight:600;text-decoration:none">Reel notes</a></span></div>')


TOP_MARKER = "<!-- padhle-insta-top -->"
NAV_MARKER = "<!-- padhle-insta-nav -->"


def topbar_html(cfg):
    h = cfg["handle"]
    return (TOP_MARKER + '<div style="background:linear-gradient(90deg,#962FBF,#D62976,#FA7E1E);color:#fff;'
            'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;line-height:1.4;'
            'text-align:center;padding:8px 12px">'
            f'<a href="https://www.instagram.com/{h}/" rel="me" style="color:#fff;text-decoration:none;font-weight:600">'
            f'&#128247; Follow @{H.escape(h)} on Instagram</a>'
            '<span style="opacity:.7"> &nbsp;·&nbsp; </span>'
            '<a href="/ig/" style="color:#fff;text-decoration:underline">Reel notes</a></div>')


def add_header(html_text, cfg=None):
    """Instagram bar at the very top of the page + an Instagram item in the menu if there is one."""
    cfg = cfg or config()
    if not cfg:
        return html_text
    if TOP_MARKER not in html_text:
        m = re.search(r"<body[^>]*>", html_text, re.I)
        if m:
            html_text = html_text[:m.end()] + "\n" + topbar_html(cfg) + html_text[m.end():]
    if NAV_MARKER not in html_text:
        m = re.search(r'(<ul class="nav-links"[^>]*>)(.*?)(</ul>)', html_text, re.S)
        if m:
            item = (f'{NAV_MARKER}<li><a href="https://www.instagram.com/{cfg["handle"]}/" rel="me" '
                    'target="_blank">Instagram</a></li>')
            html_text = html_text[:m.end(2)] + item + html_text[m.end(2):]
    return html_text


def add_strip(html_text, cfg=None):
    cfg = cfg or config()
    if not cfg:
        return html_text
    html_text = add_header(html_text, cfg)
    if STRIP_MARKER in html_text:
        return html_text
    low = html_text.lower()
    for anchor in ("<footer", "<!-- padhle-tracker -->", "</body>"):
        i = low.find(anchor) if anchor == "<footer" else low.rfind(anchor)
        if i != -1:
            return html_text[:i] + strip_html(cfg) + "\n" + html_text[i:]
    return html_text + strip_html(cfg)


def follow_strip():
    cfg = config()
    n = 0
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("scripts", "ig")]
        for f in files:
            if f.endswith(".html") and not f.startswith("google"):
                p = os.path.join(folder, f)
                t = _read(p)
                nt = add_strip(t, cfg)
                if nt != t:
                    _write(p, nt)
                    n += 1
    return n


def add_to_sitemap(dom, items):
    p = os.path.join(ROOT, "sitemap.xml")
    if not os.path.exists(p):
        return
    sm = _read(p)
    urls = [f"https://{dom}/ig/"] + [f"https://{dom}/ig/{x['slug']}.html" for x in items]
    add = "".join(f"<url><loc>{u}</loc></url>" for u in urls if f"<loc>{u}</loc>" not in sm)
    if add:
        _write(p, sm.replace("</urlset>", add + "</urlset>"))


def add(title, reel, summary, body, date=None):
    ps = posts()
    slug = slugify(title)
    if any(x["slug"] == slug for x in ps):
        slug = f"{slug}-{len(ps)+1}"
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    ps.append({"slug": slug, "title": title, "date": date or ist, "reel_url": reel or "", "summary": summary or "", "body_md": body or ""})
    _write(os.path.join(IGDIR, "posts.json"), json.dumps(ps, indent=2, ensure_ascii=False))
    build()
    return f"https://{domain()}/ig/{slug}.html"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["add", "build"])
    ap.add_argument("--title"); ap.add_argument("--reel"); ap.add_argument("--summary")
    ap.add_argument("--body-file"); ap.add_argument("--date")
    a = ap.parse_args()
    if a.cmd == "build":
        print("reel pages:", build())
    else:
        body = _read(a.body_file) if a.body_file else ""
        print(add(a.title, a.reel, a.summary, body, a.date))
