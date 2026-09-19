#!/usr/bin/env python3
"""
Daily NEET article generator for neetsuccess.com
Generates a complete HTML article using Claude API and saves it to the repo.
Run via GitHub Actions on a daily schedule.
"""

import anthropic
import os
import sys
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
import seo_utils as su

DOMAIN = "neetsuccess.com"
SITE_NAME = "NEETSuccess"

AUTHORS = ["Ananya Sharma", "Rohan Verma", "Priya Nair", "Arjun Mehta", "Sneha Iyer", "Karan Malhotra", "Divya Reddy", "Aditya Joshi"]

def add_byline(html, today_display):
    author = random.choice(AUTHORS)
    byline = (
        '<div style="max-width:800px;margin:20px auto 0;padding:0 24px;'
        'font-family:-apple-system,sans-serif;font-size:0.88rem;color:#6b7280;">'
        f'By <a href="https://neet.padhle.in" style="color:#E8A020;text-decoration:none;font-weight:600;">{author}</a>'
        f' &middot; \U0001F4C5 {today_display}</div>'
    )
    idx = html.find("<body")
    if idx == -1:
        return byline + html
    end = html.find(">", idx)
    if end == -1:
        return byline + html
    end += 1
    return html[:end] + byline + html[end:]

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
    {"slug": "neet-biology-molecular-basis-inheritance", "title": "Molecular Basis of Inheritance for NEET: DNA, RNA and Gene Expression Explained", "subject": "Biology"},
    {"slug": "neet-biology-body-fluids-circulation", "title": "Body Fluids and Circulation for NEET: Blood, Lymph and the Cardiac Cycle", "subject": "Biology"},
    {"slug": "neet-biology-excretory-products", "title": "Excretory Products for NEET: Kidney Function and Osmoregulation Simplified", "subject": "Biology"},
    {"slug": "neet-biology-neural-control", "title": "Neural Control and Coordination for NEET: The Nervous System Made Clear", "subject": "Biology"},
    {"slug": "neet-biology-chemical-coordination", "title": "Chemical Coordination for NEET: Endocrine Glands and Hormones Explained", "subject": "Biology"},
    {"slug": "neet-biology-breathing-exchange-gases", "title": "Breathing and Exchange of Gases for NEET: Respiratory System Chapter Guide", "subject": "Biology"},
    {"slug": "neet-biology-microbes-human-welfare", "title": "Microbes in Human Welfare for NEET: A High-Yield NCERT Chapter", "subject": "Biology"},
    {"slug": "neet-biology-health-disease-immunity", "title": "Human Health and Disease for NEET: Immunity, Pathogens and Vaccines", "subject": "Biology"},
    {"slug": "neet-biology-organisms-populations", "title": "Organisms and Populations for NEET: Ecology Concepts You Cannot Skip", "subject": "Biology"},
    {"slug": "neet-biology-biodiversity-conservation", "title": "Biodiversity and Conservation for NEET: Key Terms and Exam Patterns", "subject": "Biology"},
    {"slug": "neet-physics-units-measurements", "title": "Units and Measurements for NEET: The Chapter Everyone Underestimates", "subject": "Physics"},
    {"slug": "neet-physics-laws-of-motion", "title": "Laws of Motion for NEET: Newton's Laws and Common Numerical Traps", "subject": "Physics"},
    {"slug": "neet-physics-work-energy-power", "title": "Work, Energy and Power for NEET: Formulas and Frequently Asked Questions", "subject": "Physics"},
    {"slug": "neet-physics-gravitation", "title": "Gravitation for NEET: Kepler's Laws and Satellite Motion Explained", "subject": "Physics"},
    {"slug": "neet-physics-oscillations", "title": "Oscillations for NEET: SHM Concepts That Show Up Every Year", "subject": "Physics"},
    {"slug": "neet-physics-electromagnetic-induction", "title": "Electromagnetic Induction for NEET: Faraday's Laws Made Simple", "subject": "Physics"},
    {"slug": "neet-physics-alternating-current", "title": "Alternating Current for NEET: RMS Values and Circuit Analysis", "subject": "Physics"},
    {"slug": "neet-physics-dual-nature-matter", "title": "Dual Nature of Matter and Radiation for NEET: Photoelectric Effect Deep Dive", "subject": "Physics"},
    {"slug": "neet-chemistry-mole-concept", "title": "Mole Concept for NEET: The Foundation Chapter Most Students Rush Through", "subject": "Chemistry"},
    {"slug": "neet-chemistry-structure-of-atom", "title": "Structure of Atom for NEET: Quantum Numbers and Electronic Configuration", "subject": "Chemistry"},
    {"slug": "neet-chemistry-periodic-classification", "title": "Periodic Classification for NEET: Trends You Must Memorize Correctly", "subject": "Chemistry"},
    {"slug": "neet-chemistry-bonding-molecular-structure", "title": "Chemical Bonding for NEET: VSEPR Theory and Hybridization Explained", "subject": "Chemistry"},
    {"slug": "neet-chemistry-redox-reactions", "title": "Redox Reactions for NEET: Balancing Equations Without Confusion", "subject": "Chemistry"},
    {"slug": "neet-chemistry-aldehydes-ketones", "title": "Aldehydes, Ketones and Carboxylic Acids for NEET: Reaction Mechanisms Simplified", "subject": "Chemistry"},
    {"slug": "neet-exam-day-strategy-checklist", "title": "NEET Exam Day Checklist: What Toppers Do Differently on the Final Day", "subject": "Strategy"},
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
        "- 1 dark CTA box linking to https://neet.padhle.in mentioning Padhle AIM720\n"
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
    html = add_byline(html, datetime.now().strftime("%B %d, %Y"))

    url = f"https://{DOMAIN}/{filename}"
    title = topic["title"]
    description = su.extract_description(html, title)

    tagged_html = su.publish_article(
        article_html=html, site_name=SITE_NAME, domain=DOMAIN,
        canonical_url=url, title=title, description=description,
        date_iso=today_str, category=topic["subject"],
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(tagged_html)
    print(f"Saved {filename} ({len(tagged_html):,} bytes)")
    print("SEO tags injected, manifest/sitemap/homepage/archive rebuilt")
    print("Done!")


if __name__ == "__main__":
    main()
