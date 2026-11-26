"""
Picks a topic that has NOT been published on this site yet.

Why this exists: the old logic was TOPICS[day_of_year % len(TOPICS)]. Once every
topic in the fixed list had been written, sites either skipped silently every day
(green tick, no article) or re-published the same title again and again
(duplicate content). This picker:

  1. uses today's rotation topic if it is still unpublished,
  2. otherwise the first unpublished topic left in the list,
  3. otherwise asks Claude for a brand-new title that does not overlap anything
     already on the site.

If step 3 fails the script exits with an error, so the GitHub run turns red and
someone notices, instead of "succeeding" while publishing nothing.
"""
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "claude-haiku-4-5-20251001"


def _norm(text):
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def slugify(text, max_len=70):
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s[:max_len].strip("-")


def _title_of(t):
    return t["title"] if isinstance(t, dict) else str(t)


def published_titles():
    """Every title already on the site (articles.json + page <title>s as backup)."""
    titles = []
    try:
        with open(os.path.join(ROOT, "articles.json"), encoding="utf-8") as f:
            for a in json.load(f):
                if a.get("title"):
                    titles.append(a["title"])
    except Exception:
        pass
    for folder in (ROOT, os.path.join(ROOT, "articles")):
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if not name.endswith(".html"):
                continue
            try:
                with open(os.path.join(folder, name), encoding="utf-8", errors="ignore") as f:
                    m = re.search(r"<title>(.*?)</title>", f.read(20000), re.S | re.I)
                if m:
                    titles.append(re.split(r"\s+\|\s+", m.group(1).strip())[0])
            except Exception:
                pass
    return titles


def _is_used(topic, used_norm):
    if _norm(_title_of(topic)) in used_norm:
        return True
    if isinstance(topic, dict) and topic.get("slug"):
        if os.path.exists(os.path.join(ROOT, f"{topic['slug']}.html")):
            return True
    return False


def _new_topic_from_claude(topics, published, site_name, domain):
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    sample = [_title_of(t) for t in topics[:15]]
    subjects = sorted({t.get("subject") for t in topics if isinstance(t, dict) and t.get("subject")})
    recent = published[-200:]
    prompt = f"""You plan articles for the website {domain} ({site_name}).
Typical topics on this site:
{json.dumps(sample, ensure_ascii=False, indent=1)}

Titles ALREADY published (do not repeat or closely overlap any of them):
{json.dumps(recent, ensure_ascii=False, indent=1)}

Suggest ONE new article title for the same audience that a student would really search
on Google. It must cover a different angle, chapter, question or problem from all of the
published titles. Keep it specific and under 90 characters.
{"Pick its subject from: " + ", ".join(subjects) if subjects else ""}

Reply with JSON only: {{"title": "...", "subject": "..."}}"""

    for _ in range(3):
        msg = client.messages.create(
            model=MODEL, max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            continue
        data = json.loads(m.group(0))
        title = data.get("title", "").strip()
        if not title or _norm(title) in {_norm(p) for p in published}:
            continue
        subject = data.get("subject") or (subjects[0] if subjects else "Strategy")
        return title, subject
    raise RuntimeError("Could not get a fresh topic from Claude")


def pick_topic(topics, site_name, domain):
    """Return an unpublished topic in the same shape as the TOPICS list items."""
    published = published_titles()
    used = {_norm(t) for t in published}

    day = datetime.now().timetuple().tm_yday
    rotation = topics[day % len(topics)]
    if not _is_used(rotation, used):
        return rotation
    for t in topics:
        if not _is_used(t, used):
            return t

    print("All listed topics are already published - asking Claude for a new one.")
    try:
        title, subject = _new_topic_from_claude(topics, published, site_name, domain)
    except Exception as e:
        print(f"ERROR: could not pick a new topic: {e}")
        sys.exit(1)
    print(f"New topic: {title}")
    if isinstance(topics[0], dict):
        prefix = ""
        first_slug = topics[0].get("slug", "")
        m = re.match(r"^(cbse\d+-)", first_slug)
        if m:
            prefix = m.group(1)
        slug = prefix + slugify(title)
        if os.path.exists(os.path.join(ROOT, f"{slug}.html")):
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d')}"
        return {"slug": slug, "title": title, "subject": subject}
    return title
