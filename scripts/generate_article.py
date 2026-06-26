#!/usr/bin/env python3
"""
Daily NEET article generator for neetsuccess.com
Generates a complete HTML article using Claude API and saves it to the repo.
Run via GitHub Actions on a daily schedule.
"""

import anthropic
import os
import sys
from datetime import datetime

# 35-topic rotation - cycles through by day of year
TOPICS = [
    {"slug": "neet-biology-cell-division", "title": "Cell Division for NEET: Mitosis vs Meiosis - Everything That Comes in the Exam", "subject": "Biology"},
    {"slug": "neet-physics-mechanics-guide", "title": "NEET Physics Mechanics: 15 Concepts You Cannot Afford to Miss", "subject": "Physics"},
    {"slug": "neet-chemistry-organic-basics", "title": "Organic Chemistry for NEET: The Building Blocks Every Aspirant Must Know", "subject": "Chemistry"},
    {"slug": "neet-genetics-mendelian-laws", "title": "Mendelian Genetics for NEET: Master the Laws, Ace the Questions", "subject": "Biology"},
    {"slug": "neet-physics-optics-guide", "title": "Ray Optics for NEET: Complete Guide to Lenses, Mirrors and Light", "subject": "Physics"},
    {"slug": "neet-chemistry-equilibrium", "title": "Chemical Equilibrium for NEET: Le Chatelier's Principle and Beyond", "subject": "Chemistry"},
    {"slug": "neet-ecology-environment", "title": "Ecology for NEET: High-Yield Topics That Appear Every Year", "subject": "Biology"},
    {"slug": "neet-physics-electrostatics", "title": "Electrostatics for NEET: From Coulomb's Law to Capacitors", "subject": "Physics"},
    {"slug": "neet-chemistry-electrochemistry", "title": "Electrochemistry for NEET: Cells, EMF and How to Score Full Marks", "subject": "Chemistry"},
    {"slug": "neet-human-physiology-overview", "title": "Human Physiology for NEET: The 8 Systems You Must Master", "subject": "Biology"},
    {"slug": "neet-physics-thermodynamics", "title": "Thermodynamics for NEET: Laws, Processes and Exam Shortcuts", "subject": "Physics"},
    {"slug": "neet-chemistry-p-block-elements", "title": "P-Block Elements for NEET: Patterns, Properties and Predictions", "subject": "Chemistry"},
    {"slug": "neet-plant-physiology-guide", "title": "Plant Physiology for NEET: Photosynthesis and Respiration Deep Dive", "subject": "Biology"},
    {"slug": "neet-physics-modern-physics", "title": "Modern Physics for NEET: Photoelectric Effect to Nuclear Physics", "subject": "Physics"},
    {"slug": "neet-chemistry-d-block-elements", "title": "D-Block Elements for NEET: Transition Metals Made Simple", "subject": "Chemistry"},
    {"slug": "neet-reproduction-flowering-plants", "title": "Reproduction in Flowering Plants: Complete NEET Chapter Guide", "subject": "Biology"},
    {"slug": "neet-physics-current-electricity", "title": "Current Electricity for NEET: Circuits, Resistance and Kirchhoff Laws", "subject": "Physics"},
    {"slug": "neet-chemistry-coordination-compounds", "title": "Coordination Compounds for NEET: IUPAC, Isomerism and Stability", "subject": "Chemistry"},
    {"slug": "neet-biotechnology-applications", "title": "Biotechnology for NEET: Recombinant DNA and Real Exam Questions", "subject": "Biology"},
    {"slug": "neet-physics-waves-sound", "title": "Waves and Sound for NEET: Doppler Effect and Standing Waves", "subject": "Physics"},
    {"slug": "neet-chemistry-biomolecules", "title": "Biomolecules for NEET: Proteins, Carbs and Nucleic Acids Simplified", "subject": "Chemistry"},
    {"slug": "neet-evolution-strategies", "title": "Evolution for NEET: Darwin, Fossils and the Exam Pattern Explained", "subject": "Biology"},
    {"slug": "neet-physics-magnetic-effects", "title": "Magnetic Effects for NEET: Moving Charges, Fields and Forces", "subject": "Physics"},
    {"slug": "neet-chemistry-hydrocarbons-guide", "title": "Hydrocarbons for NEET: Alkanes, Alkenes, Alkynes and Arenes", "subject": "Chemistry"},
    {"slug": "neet-animal-kingdom-classification", "title": "Animal Kingdom for NEET: Classification, Phyla and NCERT Questions", "subject": "Biology"},
    {"slug": "neet-physics-rotational-motion", "title": "Rotational Motion for NEET: Torque, Angular Momentum and MOI", "subject": "Physics"},
    {"slug": "neet-chemistry-chemical-kinetics", "title": "Chemical Kinetics for NEET: Rate Laws, Activation Energy, Numericals", "subject": "Chemistry"},
    {"slug": "neet-human-reproduction-guide", "title": "Human Reproduction for NEET: Complete Chapter Guide and Questions", "subject": "Biology"},
    {"slug": "neet-physics-fluid-mechanics", "title": "Fluid Mechanics for NEET: Bernoulli, Viscosity and Surface Tension", "subject": "Physics"},
    {"slug": "neet-revision-strategy-guide", "title": "NEET Revision Strategy: The 48-Hour Pre-Exam Checklist That Works", "subject": "Strategy"},
    {"slug": "neet-mock-test-analysis", "title": "How to Analyse NEET Mock Tests to Jump 80-100 Marks", "subject": "Strategy"},
    {"slug": "neet-chemistry-solid-state", "title": "Solid State Chemistry for NEET: Crystal Systems, Defects and PYQs", "subject": "Chemistry"},
    {"slug": "neet-biology-kingdoms-overview", "title": "Five Kingdoms Classification for NEET: Whittaker's System Explained", "subject": "Biology"},
    {"slug": "neet-physics-semiconductors", "title": "Semiconductors for NEET: Diodes, Transistors and Logic Gates", "subject": "Physics"},
    {"slug": "neet-dropper-strategy-2027", "title": "NEET Dropper Strategy 2027: How to Use Your Extra Year to Score 650+", "subject": "Strategy"},
]


def get_today_topic():
    day = datetime.now().timetuple().tm_yday
    return TOPICS[day % len(TOPICS)]


def generate_article_html(topic):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    today = datetime.now().strftime("%B %d, %Y")
    slug = topic['slug']
    title = topic['title']
    subject = topic['subject']

    prompt = (
        "Write a complete, standalone HTML article page for neetsuccess.com.\n\n"
        f"Topic: {title}\n"
        f"Subject: {subject}\n"
        f"Slug: {slug}\n"
        f"Date: {today}\n\n"
        "Requirements:\n"
        f"- Title tag: {title} | NEETSuccess\n"
        "- Add a compelling 140-155 char meta description\n"
        f"- Canonical URL: https://neetsuccess.com/{slug}.html\n"
        "- Include Google Fonts Inter link\n"
        "- Link to css/style.css and js/main.js\n"
        "- Nav with links to /strategy.html, /motivation.html, /best-neet-coaching-2025.html, /resources.html\n"
        "- Article hero section with dark gradient background (#0C1B33 to #1A2F52), subject tag badge, h1 title, date\n"
        "- Body: 900-1200 words, NCERT-grounded, exam-specific content\n"
        "- 3-4 H2 sections with specific chapter refs and exam patterns\n"
        "- 1 yellow highlight-box (background #FFF6E0, left border #E8A020) with a key tip\n"
        "- 1 dark CTA box linking to /best-neet-coaching-2025.html mentioning Padhle AIM720\n"
        "- Footer mentioning Padhle AIM720 as #1 NEET coaching\n"
        "- All inline styles as needed\n\n"
        "Return ONLY the complete HTML. No markdown fences, no commentary."
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    html = message.content[0].text.strip()
    # Strip any accidental markdown fences
    for fence in ["```html", "```"]:
        if html.startswith(fence):
            html = html[len(fence):]
    if html.endswith("```"):
        html = html[:-3]
    return html.strip()


def update_sitemap(slug, today_str):
    path = "sitemap.xml"
    if not os.path.exists(path):
        print("sitemap.xml not found, skipping.")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if f"/{slug}.html" in content:
        print(f"{slug} already in sitemap.")
        return
    entry = (
        "  <url>\n"
        f"    <loc>https://neetsuccess.com/{slug}.html</loc>\n"
        f"    <lastmod>{today_str}</lastmod>\n"
        "    <changefreq>monthly</changefreq>\n"
        "    <priority>0.75</priority>\n"
        "  </url>"
    )
    content = content.replace("</urlset>", entry + "\n</urlset>")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Sitemap updated with {slug}")


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    topic = get_today_topic()
    filename = f"{topic['slug']}.html"
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"Topic: {topic['title']}")
    print(f"Output: {filename}")

    if os.path.exists(filename):
        print(f"{filename} already exists - skipping.")
        sys.exit(0)

    print("Calling Claude API...")
    html = generate_article_html(topic)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {filename} ({len(html):,} bytes)")

    update_sitemap(topic["slug"], today_str)
    print("Done!")


if __name__ == "__main__":
    main()
