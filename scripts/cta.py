"""
Adds one Padhle box (link to Padhle) to pages that have no real Padhle link.
The author-name link in the byline does not count as a real link.

- add_cta(html, domain): returns html with the box (idempotent, skips pages
  that already link to Padhle properly).
- sweep(root, domain): runs add_cta on every .html page in the site.
"""
import os
import re

MARKER = "<!-- padhle-cta -->"
BYLINE = re.compile(
    r'<a href="https?://(neet\.)?padhle\.in/?" style="color:#[0-9A-Fa-f]{6};'
    r'text-decoration:none;font-weight:600;">'
)
REAL_LINK = re.compile(r'href="https?://([a-z0-9-]+\.)?padhle\.in', re.I)

COPY = {
    "neet": {
        "heading": "Preparing for NEET?",
        "text": "Padhle AIM720 is a full NEET course with live classes and a personal "
                "mentor who plans your week and checks your test scores.",
        "button": "See Padhle AIM720",
        "url": "https://neet.padhle.in/",
    },
    "cbse10": {
        "heading": "Class 10 boards coming up?",
        "text": "Padhle's Vijay batch covers the full Class 10 syllabus with weekly "
                "tests and daily practice questions.",
        "button": "See the Vijay batch",
        "url": "https://padhle.in/home/vijay",
    },
    "cbse9": {
        "heading": "Studying for Class 9?",
        "text": "Padhle has lectures, notes and practice questions for Class 9 "
                "Science, Maths and SST.",
        "button": "Study with Padhle",
        "url": "https://padhle.in/",
    },
}


def _kind(domain):
    if "cbseclass10" in domain:
        return "cbse10"
    if "cbseclass9" in domain:
        return "cbse9"
    return "neet"


def box_html(domain):
    c = COPY[_kind(domain)]
    src = domain.replace("www.", "")
    url = f"{c['url']}?utm_source={src}&utm_medium=blog&utm_campaign=seo_cta"
    return (
        MARKER
        + '<div style="max-width:760px;margin:40px auto;padding:24px 28px;border-radius:14px;'
        'background:#FFF4EC;border:1px solid #FFD2B0;font-family:system-ui,-apple-system,'
        'Segoe UI,Roboto,sans-serif;color:#1F1F1F;box-sizing:border-box">'
        f'<div style="font-size:20px;font-weight:700;margin-bottom:8px">{c["heading"]}</div>'
        f'<p style="margin:0 0 16px;font-size:16px;line-height:1.55">{c["text"]}</p>'
        f'<a href="{url}" style="display:inline-block;background:#FF6B00;color:#fff;'
        'padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:600;'
        f'font-size:16px">{c["button"]}</a></div>'
    )


def has_real_link(html):
    return bool(REAL_LINK.search(BYLINE.sub("", html)))


def add_cta(html, domain):
    if MARKER in html or has_real_link(html):
        return html
    box = box_html(domain)
    lower = html.lower()
    # put it above the footer if there is one, else just before the end of the page
    for anchor in ("<footer", "<!-- padhle-tracker -->", "</body>"):
        idx = lower.rfind(anchor.lower()) if anchor != "<footer" else lower.find("<footer")
        if idx != -1:
            return html[:idx] + box + "\n" + html[idx:]
    return html + box


def sweep(root, domain):
    changed = 0
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "scripts"]
        for name in files:
            if not name.endswith(".html") or name.startswith("google"):
                continue
            path = os.path.join(folder, name)
            with open(path, encoding="utf-8", errors="ignore") as f:
                html = f.read()
            new = add_cta(html, domain)
            if new != html:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
                changed += 1
    return changed


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "CNAME")) as f:
        dom = f.read().strip()
    print(f"Padhle box added to {sweep(here, dom)} pages")
