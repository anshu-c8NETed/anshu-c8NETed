#!/usr/bin/env python3
"""
Generates assets/readout.svg - a custom blueprint-style "system status" panel
built from real GitHub data: a 26-week commit waveform + a language radar.
No third-party badge service involved - every pixel is drawn here.
"""
import os
import sys
import json
import datetime
import urllib.request
import math

USERNAME = os.environ.get("GH_USERNAME", "anshu-c8NETed")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

API = "https://api.github.com/graphql"
REST = "https://api.github.com"

ACCENT = "#2DD4BF"
ACCENT2 = "#F5A623"
INK = "#EAEAE6"
DIM = "#5a615f"
BG = "#0a0c0b"
LINE = "#2a302e"


def gh_request(url, data=None, headers=None):
    h = {"User-Agent": "readout-generator"}
    if TOKEN:
        h["Authorization"] = f"bearer {TOKEN}"
    if headers:
        h.update(headers)
    if data is not None:
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=h, method="POST")
    else:
        req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def fetch_contributions(username):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks { contributionDays { contributionCount date } }
          }
        }
      }
    }"""
    try:
        res = gh_request(API, {"query": query, "variables": {"login": username}})
        weeks = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
        return weekly
    except Exception as e:
        print(f"contributions fetch failed: {e}", file=sys.stderr)
        return [0] * 52


def fetch_languages(username):
    try:
        repos = gh_request(f"{REST}/users/{username}/repos?per_page=100&type=owner")
        totals = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            try:
                langs = gh_request(repo["languages_url"])
            except Exception:
                continue
            for lang, count in langs.items():
                totals[lang] = totals.get(lang, 0) + count
        if not totals:
            raise ValueError("no language data")
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:6]
        total = sum(v for _, v in ranked) or 1
        return [(name, v / total) for name, v in ranked]
    except Exception as e:
        print(f"languages fetch failed: {e}", file=sys.stderr)
        return [("JavaScript", 0.4), ("TypeScript", 0.25), ("C++", 0.15),
                ("Python", 0.1), ("CSS", 0.06), ("HTML", 0.04)]


def render_waveform(weekly, x0, y0, w, h):
    n = len(weekly)
    if n == 0:
        return ""
    mx = max(weekly) or 1
    step = w / max(n - 1, 1)
    points = []
    for i, v in enumerate(weekly):
        x = x0 + i * step
        y = y0 + h - (v / mx) * h
        points.append((x, y))
    path = f"M {points[0][0]:.1f} {y0+h:.1f} "
    for px, py in points:
        path += f"L {px:.1f} {py:.1f} "
    path += f"L {points[-1][0]:.1f} {y0+h:.1f} Z"
    line = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in points)
    svg = f'<path d="{path}" fill="{ACCENT}" opacity="0.12"/>'
    svg += f'<path d="{line}" fill="none" stroke="{ACCENT}" stroke-width="1.6"/>'
    return svg


def render_radar(langs, cx, cy, r):
    n = len(langs)
    if n == 0:
        return ""
    angle_step = 2 * math.pi / n
    maxf = max(f for _, f in langs) or 1
    pts = []
    for i, (name, frac) in enumerate(langs):
        a = -math.pi / 2 + i * angle_step
        rr = r * (0.25 + 0.75 * frac / maxf)
        x = cx + rr * math.cos(a)
        y = cy + rr * math.sin(a)
        pts.append((x, y, name, frac))
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, _, _ in pts)
    svg = ""
    for ring in (0.33, 0.66, 1.0):
        rp = []
        for i in range(n):
            a = -math.pi / 2 + i * angle_step
            rp.append((cx + r * ring * math.cos(a), cy + r * ring * math.sin(a)))
        svg += f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x,y in rp)}" fill="none" stroke="{LINE}" stroke-width="1"/>'
    for x, y, _, _ in pts:
        svg += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{LINE}" stroke-width="1"/>'
    svg += f'<polygon points="{poly}" fill="{ACCENT2}" fill-opacity="0.15" stroke="{ACCENT2}" stroke-width="1.6"/>'
    for x, y, name, frac in pts:
        svg += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{ACCENT2}"/>'
        anchor = "start" if x > cx + 2 else ("end" if x < cx - 2 else "middle")
        label_x = x + (16 if x > cx else (-16 if x < cx else 0))
        svg += f'<text x="{label_x:.1f}" y="{y:.1f}" fill="{DIM}" font-size="10" text-anchor="{anchor}">{name.upper()} {round(frac*100)}%</text>'
    return svg


def main():
    weekly = fetch_contributions(USERNAME)
    langs = fetch_languages(USERNAME)
    today = datetime.date.today().isoformat()
    total_year = sum(weekly)

    waveform_svg = render_waveform(weekly[-26:], 60, 110, 480, 90)
    radar_svg = render_radar(langs, 880, 160, 90)

    svg = f'''<svg viewBox="0 0 1200 320" xmlns="http://www.w3.org/2000/svg" font-family="'JetBrains Mono','Courier New',monospace">
  <defs>
    <pattern id="g" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#161b1a" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="1200" height="320" fill="{BG}"/>
  <rect width="1200" height="320" fill="url(#g)"/>

  <text x="30" y="34" fill="{INK}" font-size="14" letter-spacing="3" font-weight="700">SYSTEM STATUS - LIVE READOUT</text>
  <text x="1170" y="34" fill="{DIM}" font-size="11" text-anchor="end">LAST SYNCED {today}</text>
  <line x1="30" y1="46" x2="1170" y2="46" stroke="{LINE}" stroke-width="1"/>

  <text x="60" y="90" fill="{DIM}" font-size="11" letter-spacing="2">COMMIT ACTIVITY - LAST 26 WEEKS</text>
  {waveform_svg}
  <line x1="60" y1="200" x2="540" y2="200" stroke="{LINE}" stroke-width="1"/>
  <text x="60" y="220" fill="{ACCENT}" font-size="12">{total_year} contributions tracked this year</text>

  <text x="800" y="60" fill="{DIM}" font-size="11" letter-spacing="2">LANGUAGE DISTRIBUTION</text>
  {radar_svg}

  <line x1="30" y1="280" x2="1170" y2="280" stroke="{LINE}" stroke-width="1"/>
  <text x="30" y="300" fill="{DIM}" font-size="10" letter-spacing="2">AUTO-REGENERATED VIA GITHUB ACTIONS - github.com/{USERNAME}</text>
  <text x="1170" y="300" fill="{DIM}" font-size="10" letter-spacing="2" text-anchor="end">NO THIRD-PARTY BADGE SERVICE</text>
</svg>'''

    os.makedirs("assets", exist_ok=True)
    with open("assets/readout.svg", "w") as f:
        f.write(svg)
    print("wrote assets/readout.svg")


if __name__ == "__main__":
    main()
