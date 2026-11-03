#!/usr/bin/env python3
"""
Generate a high-quality, animated Halloween-themed GitHub contribution graph SVG.

Usage:
    python scripts/generate_halloween_graph.py --username soul-abhi --token $GITHUB_TOKEN
    python scripts/generate_halloween_graph.py --sample   # offline preview

Output: halloween-contribution-graph.svg
"""

import argparse
import math
import os
import random
import sys
from datetime import date, datetime, timedelta

try:
    import requests
    from dateutil import parser as dtparser
except ImportError:  # sample mode still works without them
    requests = None
    dtparser = None


# ─────────────────────────────── Palette ────────────────────────────────
BG        = "#0d1117"   # GitHub dark background
BORDER    = "#2b3440"   # card border (more visible)
TEXT_DIM  = "#8b949e"   # labels
TEXT_MID  = "#c9d1d9"
ACCENT    = "#ff7a18"   # pumpkin orange
# Solid, high-contrast Halloween ramp (easily distinguishable at a glance)
LEVELS = [
    "#1c2129",  # 0 – empty cell (clearly visible against the background)
    "#6b2a00",  # 1 – deep ember
    "#b83e00",  # 2 – burnt orange
    "#f66100",  # 3 – pumpkin
    "#ff9500",  # 4 – blazing
]
GLOW = [None, None, None, "#ff7a10", "#ffb340"]

# ─────────────────────────────── Geometry ───────────────────────────────
CELL   = 13      # cell edge (bigger = clearer)
GAP    = 3       # gap between cells
RADIUS = 3       # cell corner radius
ROWS    = 7

PAD_L  = 44      # room for day labels
PAD_T  = 28      # room for month labels
PAD_R  = 20
PAD_B  = 46      # room for legend

FONT   = "'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif"


def level_for(count: int, thresholds) -> int:
    """Map a contribution count to a 0-4 level using quartile thresholds."""
    if count <= 0:
        return 0
    q1, q2, q3 = thresholds
    if count <= q1:
        return 1
    if count <= q2:
        return 2
    if count <= q3:
        return 3
    return 4


def quartiles(values):
    """Return (q1, q2, q3) for positive counts, with safe fallbacks."""
    vals = sorted(v for v in values if v > 0)
    if not vals:
        return (1, 3, 6)
    n = len(vals)
    return (
        vals[n // 4],
        vals[n // 2],
        vals[(3 * n) // 4],
    )


def fetch_weeks(username: str, token: str):
    """Fetch the last year of contribution data from the GitHub GraphQL API."""
    if requests is None or dtparser is None:
        raise RuntimeError("requests/python-dateutil are required for live mode")

    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"username": username}},
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"GitHub API HTTP {resp.status_code}: {resp.text[:300]}")
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GitHub API error: {payload['errors']}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["weeks"], cal["totalContributions"]


def sample_weeks(seed: int = 7):
    """Build deterministic sample data so the SVG can be previewed offline."""
    rng = random.Random(seed)
    today = date.today()
    # Walk back to the most recent Sunday, then keep exactly 53 weeks.
    end = today + timedelta(days=(6 - today.weekday()) % 7)
    start = end - timedelta(days=7 * 53 - 1)

    weeks, total = [], 0
    for w in range(53):
        days = []
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            if day > today:
                count = 0
            else:
                # Weekend dips + occasional zero days, loosely realistic.
                base = 0.0 if rng.random() < 0.42 else rng.gammavariate(1.7, 3.2)
                if day.weekday() >= 5:
                    base *= 0.55
                count = min(int(base), 22)
            total += count
            days.append({"date": day.isoformat(), "contributionCount": count})
        weeks.append({"contributionDays": days})
    return weeks, total


def build_svg(weeks, total: int, username: str = "you", year: int | None = None) -> str:
    year = year or datetime.now().year
    week_count = len(weeks)

    grid_w = week_count * (CELL + GAP) - GAP
    grid_h = ROWS * (CELL + GAP) - GAP
    svg_w = PAD_L + grid_w + PAD_R
    svg_h = PAD_T + grid_h + PAD_B

    thresholds = quartiles(
        d["contributionCount"] for wk in weeks for d in wk["contributionDays"]
    )

    # Days with the most contributions get a jack-o'-lantern.
    # Pick the top ~10% of active days (min 4, max 40) so it always looks good.
    active_days = sorted(
        (
            (d["contributionCount"], d["date"])
            for wk in weeks
            for d in wk["contributionDays"]
            if d["contributionCount"] > 0
        ),
        reverse=True,
    )
    k = min(40, max(4, len(active_days) // 10)) if active_days else 0
    pumpkin_dates = {date for _, date in active_days[:k]}

    out = []
    a = out.append

    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
      f'viewBox="0 0 {svg_w} {svg_h}" role="img" '
      f'aria-label="Halloween contribution graph for {username}">')

    # ── defs: glow filter + keyframes ──────────────────────────────────
    a('<defs>')
    a('<filter id="glow" x="-80%" y="-80%" width="260%" height="260%">')
    a('<feGaussianBlur stdDeviation="1.6" result="b"/>')
    a('<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>')
    a('</filter>')
    a('<style><![CDATA[')
    a('@keyframes drift {0%,100%{transform:translateY(0)}50%{transform:translateY(-1.6px)}}')
    a('@keyframes twinkle {0%,100%{opacity:.15}50%{opacity:.7}}')
    a('@keyframes pop {0%{transform:scale(0) rotate(-25deg);opacity:0}'
      '55%{transform:scale(1.28) rotate(10deg);opacity:1}'
      '75%{transform:scale(.9) rotate(-4deg)}'
      '100%{transform:scale(1) rotate(0)}')
    a('@keyframes bob {0%,100%{transform:translateY(0)}50%{transform:translateY(-1.4px)}}')
    a('@keyframes flicker {0%,100%{opacity:.9}50%{opacity:1}}')
    a('.p{animation:drift 3.2s ease-in-out infinite}')
    a('.s{animation:twinkle 4s ease-in-out infinite}')
    a('.pop{animation:pop .75s cubic-bezier(.34,1.56,.64,1) both;'
      'transform-box:fill-box;transform-origin:center}')
    a('.bob{animation:bob 2.4s ease-in-out infinite;'
      'transform-box:fill-box;transform-origin:center}')
    a('.fl{animation:flicker 1.8s ease-in-out infinite}')
    a(']]></style>')
    a('</defs>')

    # ── card background ────────────────────────────────────────────────
    a(f'<rect x="0.5" y="0.5" width="{svg_w-1}" height="{svg_h-1}" rx="10" '
      f'fill="{BG}" stroke="{BORDER}" stroke-width="1"/>')

    # ── month labels ───────────────────────────────────────────────────
    seen = set()
    for wi, wk in enumerate(weeks):
        first = wk["contributionDays"][0]["date"]
        month = int(first[5:7])
        label = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][month-1]
        if label in seen:
            continue
        seen.add(label)
        x = PAD_L + wi * (CELL + GAP)
        a(f'<text x="{x}" y="18" fill="{TEXT_DIM}" font-family="{FONT}" '
          f'font-size="10.5" font-weight="600">{label}</text>')

    # ── day labels (Mon / Wed / Fri – matches GitHub) ──────────────────
    for di, name in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        y = PAD_T + di * (CELL + GAP) + CELL - 4
        a(f'<text x="{PAD_L-11}" y="{y}" fill="{TEXT_DIM}" font-family="{FONT}" '
          f'font-size="10" font-weight="600" text-anchor="end">{name}</text>')

    # ── cells ──────────────────────────────────────────────────────────
    pump_order = 0
    for wi, wk in enumerate(weeks):
        for di, day in enumerate(wk["contributionDays"]):
            count = day["contributionCount"]
            lvl = level_for(count, thresholds)
            x = PAD_L + wi * (CELL + GAP)
            y = PAD_T + di * (CELL + GAP)

            if lvl == 0:
                a(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                  f'rx="{RADIUS}" fill="{LEVELS[0]}"/>')
                continue

            glow = ' filter="url(#glow)"' if lvl >= 3 else ''

            # ── High-contribution day → jack-o'-lantern that pops in ──
            if day["date"] in pumpkin_dates:
                # Dark rounded tile so the bright pumpkin pops with high contrast
                a(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RADIUS}" '
                  f'fill="#2b1405"/>')

                cx = x + CELL / 2
                cy = y + CELL / 2
                s = round(CELL * 1.18 / 24, 4)
                pop_delay = round(0.15 + (pump_order * 0.06) % 1.9, 2)
                pump_order += 1

                a(f'<g transform="translate({cx},{cy})">')
                a(f'<g class="pop" style="animation-delay:{pop_delay}s">')
                a(f'<g class="bob" style="animation-delay:{round(pop_delay + 0.75, 2)}s">')
                a(f'<g transform="scale({s}) translate(-12,-12)">')
                a(f'<title>{count} contributions on {day["date"]} 🎃</title>')
                a('<circle cx="12" cy="13.5" r="11.5" fill="#ff7a10" opacity="0.30"/>')
                a('<ellipse cx="12" cy="13.6" rx="9.4" ry="8.5" fill="#ff9500"/>')
                a('<path d="M7.4 6.8 Q5 13.6 7.4 20.4" stroke="#c25a00" '
                  'stroke-width="1.2" fill="none" opacity=".85"/>')
                a('<path d="M16.6 6.8 Q19 13.6 16.6 20.4" stroke="#c25a00" '
                  'stroke-width="1.2" fill="none" opacity=".85"/>')
                a('<path d="M12 5.2 Q12 13.6 12 22" stroke="#c25a00" '
                  'stroke-width="1.1" fill="none" opacity=".6"/>')
                a('<path d="M11.2 5.6 q0.2 -2.2 2.3 -2.6" stroke="#4caf50" '
                  'stroke-width="2" fill="none" stroke-linecap="round"/>')
                a('<path d="M7.2 12.4 L10.7 9.8 L11 13.6 Z" fill="#1a0a00"/>')
                a('<path d="M16.8 12.4 L13.3 9.8 L13 13.6 Z" fill="#1a0a00"/>')
                a('<path d="M7.6 16.9 L9.3 15.5 L10.7 16.9 L12 15.5 '
                  'L13.3 16.9 L14.7 15.5 L16.4 16.9" stroke="#1a0a00" '
                  'stroke-width="1.5" fill="none" stroke-linejoin="round" '
                  'stroke-linecap="round"/>')
                a('<ellipse cx="8.6" cy="9" rx="2.2" ry="1.3" fill="#ffd08a" '
                  'opacity=".5"/>')
                a('</g></g></g></g>')
                continue

            a(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RADIUS}" '
              f'fill="{LEVELS[lvl]}"{glow}>'
              f'<title>{count} contribution{"s" if count != 1 else ""} on {day["date"]}</title>'
              f'</rect>')

    # ── legend (bottom-left) ───────────────────────────────────────────
    legend_baseline = svg_h - 18
    a(f'<text x="{PAD_L}" y="{legend_baseline}" fill="{TEXT_DIM}" font-family="{FONT}" '
      f'font-size="10">Less</text>')
    lx0 = PAD_L + 34
    for i in range(5):
        lx = lx0 + i * (CELL + 3)
        a(f'<rect x="{lx}" y="{legend_baseline-10}" width="{CELL}" height="{CELL}" '
          f'rx="{RADIUS}" fill="{LEVELS[i]}"/>')
    a(f'<text x="{lx0 + 5*(CELL+3) + 4}" y="{legend_baseline}" fill="{TEXT_DIM}" '
      f'font-family="{FONT}" font-size="10">More</text>')

    # ── total (bottom-right) with a little pumpkin ─────────────────────
    total_text = f"{total:,} contributions in {year}"
    # Rough width estimate so the pumpkin sits just left of the text.
    text_w = len(total_text) * 6.2
    tx = svg_w - PAD_R
    a(f'<text x="{tx}" y="{legend_baseline}" fill="{ACCENT}" '
      f'font-family="{FONT}" font-size="11" font-weight="600" text-anchor="end">'
      f'{total_text}</text>')

    pxi = tx - text_w - 14
    a(f'<g transform="translate({pxi},{legend_baseline-4})"><g class="p">')
    a(f'<circle r="5.4" fill="{ACCENT}" opacity="0.95"/>')
    a(f'<path d="M0,-5.4 q1.2,-2 2.6,-1.4" stroke="#2e7d32" '
      f'stroke-width="1.3" fill="none" stroke-linecap="round"/>')
    a(f'<ellipse cx="-1.8" cy="-1.4" rx="1" ry="1.2" fill="{BG}"/>')
    a(f'<ellipse cx="1.8" cy="-1.4" rx="1" ry="1.2" fill="{BG}"/>')
    a(f'<path d="M-2.2,1.4 Q0,2.9 2.2,1.4" stroke="{BG}" '
      f'stroke-width="1.1" fill="none" stroke-linecap="round"/>')
    a('</g></g>')

    # ── faint twinkling stars ──────────────────────────────────────────
    rng = random.Random(13)
    for _ in range(10):
        sx = rng.randint(PAD_L, svg_w - PAD_R)
        sy = rng.randint(PAD_T, PAD_T + grid_h)
        r = rng.choice([0.6, 0.8, 1.0])
        delay = round(rng.uniform(0, 4), 1)
        a(f'<circle cx="{sx}" cy="{sy}" r="{r}" fill="#ffb066" opacity="0.2" '
          f'class="s" style="animation-delay:{delay}s"/>')

    a('</svg>')
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--username", default=os.environ.get("USERNAME", "soul-abhi"))
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--out", default="halloween-contribution-graph.svg")
    ap.add_argument("--sample", action="store_true", help="render offline sample data")
    args = ap.parse_args()

    if args.sample:
        weeks, total = sample_weeks()
        print("Rendering sample preview (no API call).")
    else:
        if not args.token:
            print("ERROR: --token/ GITHUB_TOKEN is required (or pass --sample).", file=sys.stderr)
            return 1
        weeks, total = fetch_weeks(args.username, args.token)

    svg = build_svg(weeks, total, username=args.username)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(svg)

    print(f"Wrote {args.out} — {len(weeks)} weeks, {total:,} contributions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
