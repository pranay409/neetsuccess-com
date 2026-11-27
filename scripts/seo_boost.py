"""
SEO helpers shared by all Padhle blog sites.

  python scripts/seo_boost.py all            # one-off: everything below, whole site
  python scripts/seo_boost.py llms           # rebuild llms.txt from articles.json
  python scripts/seo_boost.py related        # add "Related articles" links to articles
  python scripts/seo_boost.py dedupe         # point duplicate articles at their original
  python scripts/seo_boost.py indexnow-new   # tell Bing/IndexNow about pages from the last 2 days
  python scripts/seo_boost.py indexnow-all   # tell Bing/IndexNow about every page in the sitemap

publish_article (seo_utils) calls refresh_after_publish() so new posts get related
links, llms.txt stays current, and duplicates never re-enter the sitemap.
"""
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEXNOW_KEY = "2a2afbbf9febabe2144f9f0ff4608038"
RELATED_MARKER = "<!-- padhle-related -->"


def _read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def domain():
    return _read(os.path.join(ROOT, "CNAME")).strip().replace("www.", "")


def manifest():
    try:
        return json.loads(_read(os.path.join(ROOT, "articles.json")))
    except Exception:
        return []


def _norm(t):
    return re.sub(r"[^a-z0-9]+", "", str(t).lower())


def _path_for(url, dom):
    p = re.sub(r"^https?://(www\.)?" + re.escape(dom), "", url).lstrip("/") or "index.html"
    return os.path.join(ROOT, p)


# ---------------------------------------------------------------- duplicates
def dedupe():
    """Keep the first copy of each title. Later copies stay online but point their
    canonical at the original and leave articles.json (so sitemap/home/archive)."""
    dom = domain()
    items = sorted(manifest(), key=lambda a: (a.get("date", ""), a.get("url", "")))
    first, keep, moved = {}, [], 0
    for a in items:
        k = _norm(a.get("title", ""))
        if k in first:
            path = _path_for(a["url"], dom)
            if os.path.exists(path):
                html = _read(path)
                tag = f'<link rel="canonical" href="{first[k]}">'
                if re.search(r'<link[^>]+rel="canonical"[^>]*>', html):
                    html = re.sub(r'<link[^>]+rel="canonical"[^>]*>', tag, html, count=1)
                else:
                    html = html.replace("</head>", tag + "\n</head>", 1)
                _write(path, html)
            moved += 1
        else:
            first[k] = a["url"]
            keep.append(a)
    if moved:
        keep.sort(key=lambda a: a.get("date", ""))
        _write(os.path.join(ROOT, "articles.json"), json.dumps(keep, indent=2, ensure_ascii=False))
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import seo_utils as su
        su.rebuild_sitemap(keep, dom, os.path.join(ROOT, "sitemap.xml"))
        idx = os.path.join(ROOT, "index.html")
        if os.path.exists(idx):
            _write(idx, su.rebuild_homepage(_read(idx), keep))
        name = re.sub(r"\.(com|org)$", "", dom)
        _write(os.path.join(ROOT, "articles.html"), su.rebuild_archive_page(keep, name, dom))
    return moved


# ---------------------------------------------------------------- llms.txt
def llms():
    dom = domain()
    path = os.path.join(ROOT, "llms.txt")
    head = ""
    if os.path.exists(path):
        head = _read(path).split("## Key Pages")[0].split("## All Articles")[0].rstrip()
    if not head:
        idx = _read(os.path.join(ROOT, "index.html")) if os.path.exists(os.path.join(ROOT, "index.html")) else ""
        t = re.search(r"<title>(.*?)</title>", idx, re.S | re.I)
        d = re.search(r'<meta name="description" content="([^"]*)"', idx, re.I)
        head = f"# {(t.group(1).strip() if t else dom)}\n\n> {(d.group(1) if d else '')}\n\n" \
               f"Independent study guidance from {dom}. For structured coaching, see Padhle: https://padhle.in"
    arts = sorted(manifest(), key=lambda a: a.get("date", ""), reverse=True)
    lines = [head, "", "## Key Pages", "", f"- [Home](https://{dom}/)", f"- [All articles](https://{dom}/articles.html)", "",
             "## All Articles", ""]
    for a in arts:
        desc = (a.get("description") or "").strip().replace("\n", " ")
        lines.append(f"- [{a['title']}]({a['url']}): {desc}" if desc else f"- [{a['title']}]({a['url']})")
    _write(path, "\n".join(lines) + "\n")
    return len(arts)


# ---------------------------------------------------------------- related links
def _related_html(current_url, items):
    cur = next((a for a in items if a["url"] == current_url), None)
    cat = (cur or {}).get("category")
    others = [a for a in items if a["url"] != current_url and _norm(a["title"]) != _norm((cur or {}).get("title", ""))]
    same = [a for a in others if cat and a.get("category") == cat]
    rest = [a for a in others if a not in same]
    picks = (sorted(same, key=lambda a: a.get("date", ""), reverse=True)[:4] +
             sorted(rest, key=lambda a: a.get("date", ""), reverse=True))[:4]
    if not picks:
        return ""
    li = "".join(f'<li style="margin:6px 0"><a href="{a["url"]}" style="color:#C2410C;text-decoration:none">{a["title"]}</a></li>' for a in picks)
    return (RELATED_MARKER + '<nav aria-label="Related articles" style="max-width:760px;margin:32px auto;padding:0 20px;'
            'font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif">'
            '<div style="font-size:18px;font-weight:700;margin-bottom:8px;color:#1F1F1F">Related articles</div>'
            f'<ul style="margin:0;padding-left:18px;font-size:16px;line-height:1.5">{li}</ul></nav>')


def add_related(html, current_url, items=None):
    if RELATED_MARKER in html:
        return html
    block = _related_html(current_url, items if items is not None else manifest())
    if not block:
        return html
    low = html.lower()
    for anchor in ("<!-- padhle-cta -->", "<footer", "<!-- padhle-tracker -->", "</body>"):
        i = low.find(anchor.lower()) if anchor in ("<!-- padhle-cta -->", "<footer") else low.rfind(anchor.lower())
        if i != -1:
            return html[:i] + block + "\n" + html[i:]
    return html + block


def related():
    dom, items, n = domain(), manifest(), 0
    for a in items:
        p = _path_for(a["url"], dom)
        if os.path.exists(p):
            h = _read(p)
            nh = add_related(h, a["url"], items)
            if nh != h:
                _write(p, nh)
                n += 1
    return n


# ---------------------------------------------------------------- IndexNow (Bing, Yandex, etc.)
def ensure_key_file():
    p = os.path.join(ROOT, f"{INDEXNOW_KEY}.txt")
    if not os.path.exists(p):
        _write(p, INDEXNOW_KEY)


def indexnow(urls):
    urls = [u for u in dict.fromkeys(urls) if u]
    if not urls:
        print("IndexNow: nothing to send")
        return 0
    dom = domain()
    body = json.dumps({"host": dom, "key": INDEXNOW_KEY, "keyLocation": f"https://{dom}/{INDEXNOW_KEY}.txt",
                       "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: sent {len(urls)} URLs, HTTP {r.status}")
            return r.status
    except urllib.error.HTTPError as e:
        print(f"IndexNow: HTTP {e.code} {e.read()[:200]!r}")
        return e.code
    except Exception as e:
        print(f"IndexNow: failed {e}")
        return 0


def sitemap_urls():
    try:
        return re.findall(r"<loc>(.*?)</loc>", _read(os.path.join(ROOT, "sitemap.xml")))
    except Exception:
        return []


def indexnow_new(days=2):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    dom = domain()
    urls = [a["url"] for a in manifest() if a.get("date", "") >= cutoff]
    urls += [f"https://{dom}/", f"https://{dom}/articles.html", f"https://{dom}/sitemap.xml"]
    return indexnow(urls)


# ---------------------------------------------------------------- called by publish_article
def refresh_after_publish(article_html, canonical_url):
    """Return article_html with related links; rebuild llms.txt."""
    try:
        ensure_key_file()
        html = add_related(article_html, canonical_url)
        llms()
        try:
            import insta  # only on sites with an Instagram hub
            if insta.config():
                html = insta.add_strip(html)
                insta.add_to_sitemap(domain(), insta.posts())
        except ImportError:
            pass
        return html
    except Exception as e:  # never block publishing
        print(f"seo_boost: skipped ({e})")
        return article_html


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("all", "dedupe"):
        print("duplicates pointed at originals:", dedupe())
    if cmd in ("all", "llms"):
        print("llms.txt articles:", llms())
    if cmd in ("all", "related"):
        print("related links added:", related())
    if cmd == "all":
        ensure_key_file()
    if cmd == "indexnow-new":
        indexnow_new()
    if cmd == "indexnow-all":
        indexnow(sitemap_urls())
