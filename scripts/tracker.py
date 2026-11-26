"""
Adds the Padhle Blog Tracker snippet to pages, so the tracker dashboard can count
page views, unique visitors and clicks to padhle.in. No cookies, no IPs.

- add_tracker(html): returns html with the snippet (idempotent).
- sweep(root): adds it to every .html page in the site (run on each publish).
Run directly (python scripts/tracker.py) to sweep the repo once.
"""
import os

ENDPOINT = "https://padhle-blog-tracker.lovable.app/api/public/track"
MARKER = "<!-- padhle-tracker -->"

SNIPPET = MARKER + """<script>(function(){var E="%s";var s=location.hostname.replace(/^www\\./,"");var v="anon";try{v=localStorage.getItem("pt_vid");if(!v){v=Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem("pt_vid",v)}}catch(e){}function send(d){d.site=s;d.path=location.pathname;d.visitor_id=v;d.referrer=document.referrer||"";var b=JSON.stringify(d);try{if(navigator.sendBeacon&&navigator.sendBeacon(E,b))return}catch(e){}try{fetch(E,{method:"POST",body:b,keepalive:true,headers:{"Content-Type":"text/plain"}})}catch(e){}}send({event:"view"});document.addEventListener("click",function(e){var a=e.target&&e.target.closest?e.target.closest("a[href]"):null;if(a&&/(^|\\.)padhle\\.in$/i.test(a.hostname)){send({event:"click",target:a.href})}},true)})();</script>""" % ENDPOINT

SKIP_PREFIXES = ("google",)  # Search Console verification files


def add_tracker(html):
    if MARKER in html:
        return html
    idx = html.lower().rfind("</body>")
    if idx == -1:
        return html + SNIPPET
    return html[:idx] + SNIPPET + "\n" + html[idx:]


def sweep(root="."):
    changed = 0
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "scripts"]
        for name in files:
            if not name.endswith(".html") or name.startswith(SKIP_PREFIXES):
                continue
            path = os.path.join(folder, name)
            with open(path, encoding="utf-8", errors="ignore") as f:
                html = f.read()
            new = add_tracker(html)
            if new != html:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
                changed += 1
    return changed


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Tracker added to {sweep(here)} pages")
