#!/usr/bin/env python3
"""Generates activity-graph.svg and trophies.svg in the repo root.

Uses only the Python standard library + the GitHub GraphQL API.
Token: GITHUB_TOKEN or GH_TOKEN env var (Codespaces and Actions provide one).
Run locally:  GH_TOKEN=$(gh auth token) python3 scripts/generate_images.py
"""
import datetime as dt
import json
import os
import sys
import urllib.request

LOGIN = "Rathio12"
# Repos owned by orgs/other accounts whose stars/forks should count too:
EXTRA_REPOS = [("VanillaPlusPlus", "VPP-Admin-Tools")]
DAYS = 31
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

BG, BORDER, TEXT, MUTED = "#0a0612", "#4c1d95", "#e9d5ff", "#8b7bb5"
ACCENT, ACCENT2, TITLE = "#a855f7", "#7c3aed", "#c084fc"
FONT = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"


def gql(query, variables):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN or GH_TOKEN (e.g. GH_TOKEN=$(gh auth token))")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch():
    if os.environ.get("MOCK"):
        today = dt.date.today()
        import random
        random.seed(4)
        days = [((today - dt.timedelta(days=DAYS - 1 - i)).isoformat(), random.choice([0, 0, 1, 2, 3, 5, 8])) for i in range(DAYS)]
        return dict(days=days, followers=12, stars=135, repos=9, commits=420, prs=17, issues=6, top=131)

    today = dt.date.today()
    start = today - dt.timedelta(days=DAYS - 1)
    extra = "".join(
        f'x{i}: repository(owner:"{o}", name:"{n}") {{ stargazerCount }}\n'
        for i, (o, n) in enumerate(EXTRA_REPOS)
    )
    q = """
    query($login:String!,$from:DateTime!,$to:DateTime!,$year:DateTime!){
      user(login:$login){
        followers{totalCount}
        repositories(ownerAffiliations:OWNER,isFork:false,first:100){
          totalCount nodes{stargazerCount}
        }
        pullRequests{totalCount}
        issues{totalCount}
        month: contributionsCollection(from:$from,to:$to){
          contributionCalendar{weeks{contributionDays{date contributionCount}}}
        }
        year: contributionsCollection(from:$year,to:$to){ totalCommitContributions }
      }
      %s
    }""" % extra
    res = gql(q, {
        "login": LOGIN,
        "from": f"{start}T00:00:00Z",
        "to": f"{today}T23:59:59Z",
        "year": f"{today - dt.timedelta(days=364)}T00:00:00Z",
    })
    if "data" not in res or not res["data"] or not res["data"].get("user"):
        sys.exit(f"GraphQL error: {json.dumps(res)[:500]}")
    d = res["data"]
    u = d["user"]
    cal = {}
    for w in u["month"]["contributionCalendar"]["weeks"]:
        for x in w["contributionDays"]:
            cal[x["date"]] = x["contributionCount"]
    days = []
    for i in range(DAYS):
        day = (start + dt.timedelta(days=i)).isoformat()
        days.append((day, cal.get(day, 0)))
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    top = max([n["stargazerCount"] for n in u["repositories"]["nodes"]] or [0])
    for i in range(len(EXTRA_REPOS)):
        r = d.get(f"x{i}")
        if r:
            stars += r["stargazerCount"]
            top = max(top, r["stargazerCount"])
    return dict(
        days=days, followers=u["followers"]["totalCount"], stars=stars,
        repos=u["repositories"]["totalCount"], commits=u["year"]["totalCommitContributions"],
        prs=u["pullRequests"]["totalCount"], issues=u["issues"]["totalCount"], top=top,
    )


def activity_svg(days):
    W, H = 900, 300
    L, R, T, B = 56, 24, 64, 48
    pw, ph = W - L - R, H - T - B
    vals = [v for _, v in days]
    mx = max(max(vals), 4)
    # round max up to a nice step
    step = max(1, -(-mx // 4))
    mx = step * 4
    xs = [L + pw * i / (len(days) - 1) for i in range(len(days))]
    ys = [T + ph - ph * v / mx for v in vals]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{L},{T+ph} " + pts + f" {L+pw},{T+ph}"
    grid = ""
    for i in range(5):
        y = T + ph - ph * i / 4
        grid += f'<line x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}" stroke="{BORDER}" stroke-opacity=".45" stroke-dasharray="3 5"/>'
        grid += f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" font-size="11" fill="{MUTED}">{step*i}</text>'
    labels = ""
    for i in range(0, len(days), 5):
        d = dt.date.fromisoformat(days[i][0])
        labels += f'<text x="{xs[i]:.1f}" y="{T+ph+22}" text-anchor="middle" font-size="11" fill="{MUTED}">{d.strftime("%b %d").replace(" 0", " ")}</text>'
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#f3e8ff" stroke="{ACCENT}" stroke-width="1.5"><title>{d}: {v}</title></circle>'
        for (d, v), x, y in zip(days, xs, ys) if v > 0
    )
    total = sum(vals)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<defs><linearGradient id="a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{ACCENT2}" stop-opacity=".55"/><stop offset="1" stop-color="{ACCENT2}" stop-opacity="0"/></linearGradient></defs>
<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="8" fill="{BG}" stroke="{BORDER}"/>
<text x="{W/2}" y="34" text-anchor="middle" font-size="18" font-weight="600" fill="{TITLE}">{LOGIN}'s Contribution Graph</text>
<text x="{W/2}" y="52" text-anchor="middle" font-size="11" fill="{MUTED}">last {DAYS} days · {total} contributions</text>
{grid}
<polygon points="{area}" fill="url(#a)"/>
<polyline points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
{dots}
{labels}
</svg>
'''


def tier(value, steps):
    """steps = thresholds for C, B, A, S (ascending)."""
    names = ["-", "C", "B", "A", "S"]
    t = sum(1 for s in steps if value >= s)
    return names[t], t


def trophies_svg(s):
    items = [
        ("Stars", s["stars"], (1, 10, 50, 100)),
        ("Top repo", s["top"], (1, 10, 50, 100)),
        ("Commits", s["commits"], (50, 200, 500, 1000)),
        ("Followers", s["followers"], (1, 10, 50, 100)),
        ("Pull requests", s["prs"], (1, 10, 30, 100)),
        ("Issues", s["issues"], (1, 5, 20, 50)),
        ("Repos", s["repos"], (1, 5, 15, 30)),
    ]
    cw, ch, gap = 118, 150, 10
    W = len(items) * cw + (len(items) - 1) * gap
    H = ch
    cards = ""
    for i, (label, val, steps) in enumerate(items):
        name, t = tier(val, steps)
        x = i * (cw + gap)
        glow = [0.15, 0.3, 0.5, 0.75, 1][t]
        col = ["#4c1d95", "#6d28d9", "#7c3aed", "#a855f7", "#d8b4fe"][t]
        cards += f'''<g transform="translate({x},0)">
<rect x=".5" y=".5" width="{cw-1}" height="{ch-1}" rx="8" fill="{BG}" stroke="{col}" stroke-opacity="{max(glow,.4)}"/>
<text x="{cw/2}" y="22" text-anchor="middle" font-size="12" font-weight="600" fill="{TITLE}">{label}</text>
<g transform="translate({cw/2},58)" fill="{col}" fill-opacity="{max(glow,.35)}" stroke="{col}" stroke-width="1.6">
<path d="M-12 -16 H12 V-5 A12 12 0 0 1 -12 -5 Z"/>
<path d="M-12 -12 H-19 V-8 A7 7 0 0 0 -12 -2" fill="none"/>
<path d="M12 -12 H19 V-8 A7 7 0 0 1 12 -2" fill="none"/>
<rect x="-3" y="7" width="6" height="7" stroke="none"/>
<rect x="-10" y="14" width="20" height="4" rx="1.5" stroke="none"/>
</g>
<text x="{cw/2}" y="104" text-anchor="middle" font-size="22" font-weight="700" fill="{TEXT}">{val}</text>
<text x="{cw/2}" y="128" text-anchor="middle" font-size="12" font-weight="700" fill="{col}" letter-spacing="2">RANK {name}</text>
</g>'''
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
{cards}
</svg>
'''


def main():
    s = fetch()
    with open(os.path.join(OUT, "activity-graph.svg"), "w") as f:
        f.write(activity_svg(s["days"]))
    with open(os.path.join(OUT, "trophies.svg"), "w") as f:
        f.write(trophies_svg(s))
    print("wrote activity-graph.svg and trophies.svg", {k: v for k, v in s.items() if k != "days"})


if __name__ == "__main__":
    main()