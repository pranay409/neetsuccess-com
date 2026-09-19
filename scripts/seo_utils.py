"""
Shared SEO + article-listing utilities for the Padhle NEET satellite sites.
Copied identically into each repo's scripts/ folder. Deterministic post-processing —
never relies on the model reliably following prompt instructions.
"""
import os
import re
import json
import html as html_lib
from datetime import datetime

ARTICLES_MARKER_START = "<!-- ARTICLES:START -->"
ARTICLES_MARKER_END = "<!-- ARTICLES:END -->"


def load_manifest(path="articles.json"):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_manifest(manifest, path="articles.json"):
    manifest = sorted(manifest, key=lambda a: a["date"], reverse=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)


def guess_category(title):
    t = title.lower()
    if "physics" in t:
        return "Physics"
    if "chemistry" in t:
        return "Chemistry"
    if "biology" in t or "biotechnology" in t:
        return "Biology"
    if "dropper" in t or "strategy" in t or "revision" in t or "mock test" in t:
        return "Strategy"
    if "counsel" in t or "quota" in t or "college" in t or "cutoff" in t:
        return "Counselling"
    return "NEET"


def extract_title(article_html, fallback):
    m = re.search(r"<title>(.*?)</title>", article_html, re.I | re.S)
    if m:
        t = re.sub(r"\s*[|–-]\s*[^|–-]+$", "", m.group(1)).strip()
        t = html_lib.unescape(t)
        if t:
            return t
    return fallback


def extract_description(article_html, fallback):
    # Match content="..." or content='...' without stopping at an apostrophe
    # inside a double-quoted value (e.g. "Whittaker's").
    m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content="([^"]+)"',
        article_html, re.I,
    )
    if not m:
        m = re.search(
            r"<meta[^>]+name=[\"']description[\"'][^>]+content='([^']+)'",
            article_html, re.I,
        )
    if m:
        return html_lib.unescape(m.group(1)).strip()
    return fallback


def inject_seo_tags(article_html, *, site_name, canonical_url, title, description,
                     date_iso, category=None):
    """Guarantee canonical + OG + JSON-LD Article schema in <head>, regardless of
    what the model produced. Strips any pre-existing ones first to avoid dupes."""
    out = article_html
    out = re.sub(r'<link[^>]+rel=["\']canonical["\'][^>]*>\s*', "", out, flags=re.I)
    out = re.sub(r'<meta[^>]+property=["\']og:[^"\']+["\'][^>]*>\s*', "", out, flags=re.I)
    out = re.sub(r'<meta[^>]+name=["\']twitter:[^"\']+["\'][^>]*>\s*', "", out, flags=re.I)
    out = re.sub(
        r'<script[^>]+application/ld\+json[^>]*>.*?</script>\s*', "", out,
        flags=re.I | re.S,
    )

    esc_title = html_lib.escape(title, quote=True)
    esc_desc = html_lib.escape(description, quote=True)

    tags = (
        f'<link rel="canonical" href="{canonical_url}">\n'
        f'<meta property="og:title" content="{esc_title}">\n'
        f'<meta property="og:description" content="{esc_desc}">\n'
        f'<meta property="og:type" content="article">\n'
        f'<meta property="og:url" content="{canonical_url}">\n'
        f'<meta property="og:site_name" content="{html_lib.escape(site_name, quote=True)}">\n'
        f'<meta name="twitter:card" content="summary">\n'
        f'<meta name="twitter:title" content="{esc_title}">\n'
        f'<meta name="twitter:description" content="{esc_desc}">\n'
    )

    jsonld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "description": description,
        "datePublished": date_iso,
        "dateModified": date_iso,
        "author": {"@type": "Organization", "name": site_name},
        "publisher": {"@type": "Organization", "name": site_name},
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
    }
    if category:
        jsonld["articleSection"] = category
    tags += f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>\n'

    idx = out.lower().find("</head>")
    if idx == -1:
        return tags + out
    return out[:idx] + tags + out[idx:]


def rebuild_sitemap(manifest, domain, path="sitemap.xml"):
    """Regenerate sitemap.xml from scratch from this site's own manifest only —
    eliminates any cross-domain contamination from string-append bugs."""
    entries = [
        f"  <url>\n    <loc>https://{domain}/</loc>\n"
        f"    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>"
    ]
    for a in manifest:
        entries.append(
            f"  <url>\n    <loc>{a['url']}</loc>\n    <lastmod>{a['date']}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries) + "\n</urlset>\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(xml)


def _render_cards(entries):
    cards = []
    for a in entries:
        try:
            date_display = datetime.strptime(a["date"], "%Y-%m-%d").strftime("%B %d, %Y")
        except ValueError:
            date_display = a["date"]
        cat = html_lib.escape(a.get("category") or "NEET")
        cards.append(
            '\n      <article class="pk-article-card">'
            f'<span class="pk-article-tag">{cat}</span>'
            f'<h3><a href="{a["url"]}">{html_lib.escape(a["title"])}</a></h3>'
            f'<p>{html_lib.escape(a["description"])}</p>'
            f'<time datetime="{a["date"]}">{date_display}</time>'
            '</article>'
        )
    return "".join(cards)


PK_CSS = """
<style>
  .pk-articles-section{padding:56px 0;background:#F7F8FA;}
  .pk-articles-section .pk-inner{max-width:1100px;margin:0 auto;padding:0 24px;}
  .pk-articles-section h2{font-size:1.6rem;color:#0C1B33;margin-bottom:28px;text-align:center;}
  .pk-articles-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:20px;}
  .pk-article-card{background:#fff;border:1px solid #E8E9ED;border-radius:12px;padding:20px;display:block;}
  .pk-article-tag{display:inline-block;background:rgba(232,160,32,0.15);color:#b8860b;padding:3px 10px;border-radius:12px;font-size:0.72rem;font-weight:700;margin-bottom:10px;letter-spacing:.03em;text-transform:uppercase;}
  .pk-article-card h3{margin:0 0 8px;font-size:1.02rem;line-height:1.4;}
  .pk-article-card h3 a{color:#0C1B33;text-decoration:none;}
  .pk-article-card h3 a:hover{text-decoration:underline;}
  .pk-article-card p{color:#5a6273;font-size:0.88rem;line-height:1.5;margin:0 0 10px;}
  .pk-article-card time{color:#9aa1af;font-size:0.78rem;}
  .pk-view-all{text-align:center;margin-top:32px;}
  .pk-view-all a{color:#0C1B33;font-weight:700;text-decoration:none;border-bottom:2px solid #E8A020;padding-bottom:2px;}
</style>
""".strip()


def build_articles_section(manifest, limit=9, archive_href="/articles.html"):
    latest = sorted(manifest, key=lambda a: a["date"], reverse=True)[:limit]
    return (
        ARTICLES_MARKER_START + "\n"
        + PK_CSS + "\n"
        '<section class="pk-articles-section" id="articles">\n'
        '  <div class="pk-inner">\n'
        "    <h2>Latest NEET Articles</h2>\n"
        f'    <div class="pk-articles-grid">{_render_cards(latest)}\n    </div>\n'
        f'    <div class="pk-view-all"><a href="{archive_href}">View All Articles ({len(manifest)}) &rarr;</a></div>\n'
        "  </div>\n</section>\n"
        + ARTICLES_MARKER_END
    )


def _find_balanced_span(text, tag_name, open_tag_start):
    """Given the index of '<' for an opening tag, return (start, end) spanning
    through its matching closing tag, accounting for nested same-name tags."""
    open_re = re.compile(rf"<{tag_name}\b", re.I)
    close_re = re.compile(rf"</{tag_name}>", re.I)
    gt = text.find(">", open_tag_start)
    if gt == -1:
        return None
    pos = gt + 1
    depth = 1
    while depth > 0:
        next_close = close_re.search(text, pos)
        if not next_close:
            return None
        next_open = open_re.search(text, pos, next_close.start())
        if next_open:
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
    return open_tag_start, pos


def strip_existing_articles_block(index_html):
    """Remove a pre-existing hand-authored id="articles" block (stale,
    hardcoded article list with no dates) so it isn't left duplicated
    alongside the new auto-generated section."""
    m = re.search(r'<(div|section)\b[^>]*\bid=["\']articles["\'][^>]*>', index_html, re.I)
    if not m:
        return index_html
    span = _find_balanced_span(index_html, m.group(1), m.start())
    if span is None:
        return index_html
    start, end = span
    return index_html[:start] + index_html[end:]


def rebuild_homepage(index_html, manifest, limit=9, archive_href="/articles.html"):
    section = build_articles_section(manifest, limit=limit, archive_href=archive_href)
    if ARTICLES_MARKER_START in index_html and ARTICLES_MARKER_END in index_html:
        pattern = re.escape(ARTICLES_MARKER_START) + r".*?" + re.escape(ARTICLES_MARKER_END)
        return re.sub(pattern, lambda _m: section, index_html, flags=re.S)
    index_html = strip_existing_articles_block(index_html)
    lower = index_html.lower()
    idx = lower.rfind("<footer")
    if idx == -1:
        idx = lower.rfind("</body>")
    if idx == -1:
        return index_html + "\n" + section
    return index_html[:idx] + section + "\n" + index_html[idx:]


def rebuild_archive_page(manifest, site_name, domain):
    all_sorted = sorted(manifest, key=lambda a: a["date"], reverse=True)
    cards = _render_cards(all_sorted)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>All Articles | {html_lib.escape(site_name)}</title>
<meta name="description" content="Browse all {len(manifest)} NEET preparation articles from {html_lib.escape(site_name)}.">
<link rel="canonical" href="https://{domain}/articles.html">
{PK_CSS}
<style>
  body{{margin:0;font-family:-apple-system,"Segoe UI",Arial,sans-serif;background:#fff;color:#1a2233;}}
  header{{background:#0C1B33;padding:20px 0;}}
  header .pk-inner{{max-width:1100px;margin:0 auto;padding:0 24px;}}
  header a.pk-logo{{color:#fff;font-weight:700;font-size:1.2rem;text-decoration:none;}}
  h1.pk-h1{{max-width:1100px;margin:40px auto 6px;padding:0 24px;color:#0C1B33;}}
  .pk-articles-section{{background:#fff;padding-top:10px;}}
</style>
</head>
<body>
<header><div class="pk-inner"><a class="pk-logo" href="/">{html_lib.escape(site_name)}</a></div></header>
<h1 class="pk-h1">All Articles ({len(manifest)})</h1>
{ARTICLES_MARKER_START}
<section class="pk-articles-section" id="articles">
  <div class="pk-inner">
    <div class="pk-articles-grid">{cards}
    </div>
  </div>
</section>
{ARTICLES_MARKER_END}
</body>
</html>
"""


def publish_article(*, article_html, site_name, domain, canonical_url, title,
                     description, date_iso, category, manifest_path="articles.json",
                     sitemap_path="sitemap.xml", index_path="index.html",
                     archive_path="articles.html"):
    """One call that does the full guaranteed post-processing pipeline for a
    freshly generated article: inject SEO tags, update manifest, rebuild
    sitemap/homepage/archive. Returns the SEO-tagged article HTML to save."""
    tagged = inject_seo_tags(
        article_html, site_name=site_name, canonical_url=canonical_url,
        title=title, description=description, date_iso=date_iso, category=category,
    )

    manifest = load_manifest(manifest_path)
    manifest = [a for a in manifest if a["url"] != canonical_url]
    manifest.append({
        "title": title, "url": canonical_url, "date": date_iso,
        "description": description, "category": category,
    })
    save_manifest(manifest, manifest_path)

    rebuild_sitemap(manifest, domain, sitemap_path)

    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
        index_html = rebuild_homepage(index_html, manifest)
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_html)

    with open(archive_path, "w", encoding="utf-8") as f:
        f.write(rebuild_archive_page(manifest, site_name, domain))

    return tagged
