"""Builds assets/stats.svg and assets/langs.svg from the GitHub API.

Runs inside GitHub Actions with the built-in GITHUB_TOKEN, so no extra secrets
are needed. Only uses public data for the user.
"""
import json
import os
import urllib.parse
import urllib.request
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "kenza11-star")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"

LANG_COLORS = {
    "Kotlin": "#A97BFF", "Java": "#B07219", "TypeScript": "#3178C6",
    "JavaScript": "#F1E05A", "HTML": "#E34C26", "CSS": "#563D7C",
    "Python": "#3572A5", "Shell": "#89E051", "Swift": "#F05138",
    "C++": "#F34B7D", "C": "#555555", "Dart": "#00B4AB",
}
DEFAULT_COLOR = "#78BED7"


def get(path, accept="application/vnd.github+json"):
    req = urllib.request.Request(API + path)
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def all_pages(path):
    items, page = [], 1
    while True:
        sep = "&" if "?" in path else "?"
        batch = get(f"{path}{sep}per_page=100&page={page}")
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items


def collect():
    user = get(f"/users/{USER}")
    repos = [r for r in all_pages(f"/users/{USER}/repos?type=owner&sort=updated") if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in repos)

    totals = {}
    for r in repos:
        try:
            langs = get(f"/repos/{r['full_name']}/languages")
        except Exception:
            continue
        for name, size in langs.items():
            totals[name] = totals.get(name, 0) + size

    commits = None
    try:
        q = urllib.parse.quote(f"author:{USER}")
        commits = get(f"/search/commits?q={q}&per_page=1",
                      accept="application/vnd.github.cloak-preview+json").get("total_count")
    except Exception:
        commits = None

    return {
        "repos": len(repos),
        "stars": stars,
        "followers": user.get("followers", 0),
        "commits": commits,
        "langs": totals,
    }


def fmt(n):
    if n is None:
        return "—"
    return f"{n:,}"


def stats_svg(d):
    rows = [
        ("Public repositories", fmt(d["repos"])),
        ("Total stars earned", fmt(d["stars"])),
        ("Followers", fmt(d["followers"])),
        ("Commits (all time)", fmt(d["commits"])),
    ]
    items = ""
    for i, (label, value) in enumerate(rows):
        y = 92 + i * 36
        items += (
            f'  <g class="row" style="animation-delay:{0.15 + i * 0.12:.2f}s">'
            f'<text x="36" y="{y}" class="label">{escape(label)}</text>'
            f'<text x="464" y="{y}" class="value" text-anchor="end">{escape(value)}</text></g>\n'
        )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="250" viewBox="0 0 500 250">
  <style>
    .card {{ animation: pop .8s cubic-bezier(.2,.8,.2,1) both; transform-origin: center; transform-box: fill-box; }}
    @keyframes pop {{ from {{ opacity: 0; transform: translateY(10px) scale(.98); }} to {{ opacity: 1; transform: none; }} }}
    .row {{ opacity: 0; animation: fade .7s cubic-bezier(.2,.8,.2,1) forwards; }}
    @keyframes fade {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
    .title {{ font: 700 22px Poppins, 'Segoe UI', Arial, sans-serif; fill: #2e6186; }}
    .label {{ font: 600 17px Poppins, 'Segoe UI', Arial, sans-serif; fill: #3d7196; }}
    .value {{ font: 700 17px Poppins, 'Segoe UI', Arial, sans-serif; fill: #2e6186; }}
    .sep {{ stroke: #cfeef7; stroke-width: 1.5; }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; opacity: 1 !important; }} }}
  </style>
  <g class="card">
    <rect x="2" y="2" width="496" height="246" rx="22" fill="#ffffff" stroke="#78bed7" stroke-width="1.5"/>
    <text x="36" y="50" class="title">GitHub stats</text>
    <line x1="36" y1="66" x2="464" y2="66" class="sep"/>
{items}  </g>
</svg>
'''


def langs_svg(d):
    totals = d["langs"]
    total = sum(totals.values()) or 1
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
    width = 500
    bars = ""
    for i, (name, size) in enumerate(top):
        pct = size / total * 100
        y = 92 + i * 30
        color = LANG_COLORS.get(name, DEFAULT_COLOR)
        bar_w = max(4, 300 * pct / 100)
        bars += (
            f'  <g class="row" style="animation-delay:{0.15 + i * 0.1:.2f}s">'
            f'<circle cx="40" cy="{y - 5}" r="6" fill="{color}"/>'
            f'<text x="56" y="{y}" class="label">{escape(name)}</text>'
            f'<rect x="170" y="{y - 12}" width="300" height="12" rx="6" fill="#eaf7fb"/>'
            f'<rect class="bar" style="animation-delay:{0.3 + i * 0.1:.2f}s" x="170" y="{y - 12}" width="{bar_w:.1f}" height="12" rx="6" fill="{color}"/>'
            f'<text x="{width - 36}" y="{y}" class="value" text-anchor="end">{pct:.1f}%</text></g>\n'
        )
    height = 110 + max(len(top), 1) * 30
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .card {{ animation: pop .8s cubic-bezier(.2,.8,.2,1) both; transform-origin: center; transform-box: fill-box; }}
    @keyframes pop {{ from {{ opacity: 0; transform: translateY(10px) scale(.98); }} to {{ opacity: 1; transform: none; }} }}
    .row {{ opacity: 0; animation: fade .7s cubic-bezier(.2,.8,.2,1) forwards; }}
    @keyframes fade {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
    .bar {{ transform-origin: left center; transform-box: fill-box; animation: grow 1s cubic-bezier(.2,.8,.2,1) both; }}
    @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
    .title {{ font: 700 22px Poppins, 'Segoe UI', Arial, sans-serif; fill: #2e6186; }}
    .label {{ font: 600 16px Poppins, 'Segoe UI', Arial, sans-serif; fill: #3d7196; }}
    .value {{ font: 700 15px Poppins, 'Segoe UI', Arial, sans-serif; fill: #2e6186; }}
    .sep {{ stroke: #cfeef7; stroke-width: 1.5; }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; opacity: 1 !important; }} }}
  </style>
  <g class="card">
    <rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="22" fill="#ffffff" stroke="#78bed7" stroke-width="1.5"/>
    <text x="36" y="50" class="title">Top languages</text>
    <line x1="36" y1="66" x2="{width - 36}" y2="66" class="sep"/>
{bars}  </g>
</svg>
'''


def main():
    data = collect()
    os.makedirs("assets", exist_ok=True)
    with open("assets/stats.svg", "w", encoding="utf-8") as f:
        f.write(stats_svg(data))
    with open("assets/langs.svg", "w", encoding="utf-8") as f:
        f.write(langs_svg(data))
    print("repos", data["repos"], "stars", data["stars"], "langs", len(data["langs"]))


if __name__ == "__main__":
    main()
