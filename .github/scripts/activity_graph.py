"""Render the README's contribution graph (last 31 days) as an SVG.

Run by .github/workflows/profile-cards.yml. Needs GITHUB_TOKEN and
GITHUB_USER in the environment; writes the SVG to the path given as argv[1].
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

DAYS = 31
W, H = 1000, 340
LEFT, RIGHT, TOP, BOTTOM = 70, 30, 72, 62
BG, TITLE, TEXT, LINE, POINT = "#18132A", "#E0BDAB", "#B5A8E6", "#7C67CA", "#E0BDAB"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Sans-Serif"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    name
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


def fetch(login, token):
    now = dt.datetime.now(dt.timezone.utc)
    start = (now - dt.timedelta(days=DAYS - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    body = json.dumps({"query": QUERY, "variables": {
        "login": login, "from": start.isoformat(), "to": now.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors"):
        sys.exit(f"GraphQL error: {data['errors']}")
    user = data["data"]["user"]
    weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return user["name"] or login, days[-DAYS:]


def nice_max(value):
    """Smallest 'round' number >= value that splits evenly into 4 gridlines."""
    for step in (1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 50, 100, 250, 500, 1000):
        if value <= step * 4:
            return step * 4
    return value


def render(name, days):
    counts = [c for _, c in days]
    ymax = nice_max(max(counts + [1]))
    pw, ph = W - LEFT - RIGHT, H - TOP - BOTTOM
    x = lambda i: LEFT + pw * i / (len(days) - 1)
    y = lambda c: TOP + ph * (1 - c / ymax)
    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    base = TOP + ph

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
        f"  <title>{escape(name)}'s contributions in the last {DAYS} days</title>",
        '  <defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1">',
        f'    <stop offset="0" stop-color="{LINE}" stop-opacity="0.55"/>',
        f'    <stop offset="1" stop-color="{LINE}" stop-opacity="0.05"/>',
        "  </linearGradient></defs>",
        f'  <rect width="{W}" height="{H}" rx="10" fill="{BG}"/>',
        f'  <g font-family="{FONT}">',
        f'    <text x="{W / 2}" y="40" text-anchor="middle" font-size="20" font-weight="600" fill="{TITLE}">{escape(name)}\'s Contribution Graph</text>',
    ]
    for k in range(5):
        v = ymax * k // 4
        gy = y(v)
        out.append(f'    <line x1="{LEFT}" x2="{W - RIGHT}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="{TEXT}" stroke-opacity="0.12"/>')
        out.append(f'    <text x="{LEFT - 12}" y="{gy + 4:.1f}" text-anchor="end" font-size="12" fill="{TEXT}">{v}</text>')
    for i, (date, _) in enumerate(days):
        out.append(f'    <text x="{x(i):.1f}" y="{base + 20}" text-anchor="middle" font-size="11" fill="{TEXT}">{int(date[8:])}</text>')
    out += [
        f'    <text x="{LEFT + pw / 2}" y="{H - 12}" text-anchor="middle" font-size="13" fill="{TEXT}">Days</text>',
        f'    <text transform="translate(20 {TOP + ph / 2}) rotate(-90)" text-anchor="middle" font-size="13" fill="{TEXT}">Contributions</text>',
        "  </g>",
        f'  <polygon points="{LEFT},{base} {line} {W - RIGHT},{base}" fill="url(#area)"/>',
        f'  <polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round"/>',
    ]
    for (px, py), (date, c) in zip(pts, days):
        out.append(f'  <circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{POINT}"><title>{date}: {c}</title></circle>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    name, days = fetch(os.environ["GITHUB_USER"], os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(sys.argv[1]) or ".", exist_ok=True)
    with open(sys.argv[1], "w") as f:
        f.write(render(name, days))
    print(f"Wrote {sys.argv[1]} ({len(days)} days, max {max(c for _, c in days)})")
