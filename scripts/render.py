#!/usr/bin/env python3
"""Render generated files from config/profile.json + data/stats.json.

  assets/generated/terminal.svg   neofetch-style centrepiece (portrait + info)
  assets/generated/activity.svg   stat tiles + contribution heatmap
  README.md                       assembled from config

Pure standard library. SVGs use only shapes, text and system monospace fonts,
so GitHub's image proxy renders them unchanged (no scripts, CSS files,
external fonts or remote images).
"""
import json, pathlib, datetime
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config/profile.json").read_text())
try:
    STATS = json.loads((ROOT / "data/stats.json").read_text())
except Exception:
    STATS = {}
GEN = ROOT / "assets/generated"

FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"
BG, PANEL, BORDER = "#0d1117", "#161b22", "#30363d"
FG, MUTED, BLUE, GREEN = "#c9d1d9", "#8b949e", "#58a6ff", "#3fb950"

def t(x, y, s, fill=FG, size=12.5, cw=7.5, anchor="start", weight="normal"):
    """Text with an exact width (textLength) so every font lays out identically."""
    w = len(s) * cw
    if anchor == "end":
        x -= w
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" font-weight="{weight}" '
            f'textLength="{w:.1f}" lengthAdjust="spacingAndGlyphs" xml:space="preserve">{escape(s)}</text>')

def svg_wrap(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(title)}" font-family="{FONT}">\n'
            f'<title>{escape(title)}</title>\n{body}\n</svg>\n')

def num(v):
    return f"{v:,}" if isinstance(v, int) else "n/a"

# ------------------------------------------------------------------ terminal
def terminal():
    W = 1000
    ascii_lines = (GEN / "ascii.txt").read_text().rstrip("\n").split("\n")
    acw, alh = 4.2, 8.3                       # ascii char width / line height
    top = 84
    H = int(top + len(ascii_lines) * alh + 40)
    o = [f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>',
         f'<path d="M0 10a10 10 0 0 1 10-10h{W-20}a10 10 0 0 1 10 10v26H0z" fill="{PANEL}"/>',
         f'<line x1="0" y1="36" x2="{W}" y2="36" stroke="{BORDER}"/>']
    for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        o.append(f'<circle cx="{22+i*20}" cy="18" r="6" fill="{c}"/>')
    h = CFG["handle"]
    o.append(t(W/2, 23, f"{h}@github: ~", MUTED, 12, 7.2, "middle" if False else "start").replace(
        f'x="{W/2:.1f}"', f'x="{W/2 - len(h+"@github: ~")*3.6:.1f}"'))
    o.append(t(24, 62, f"{h}@github", GREEN, 13, 7.8, weight="bold"))
    o.append(t(24 + 9*7.8, 62, ":", FG, 13, 7.8))
    o.append(t(24 + 10*7.8, 62, "~", BLUE, 13, 7.8))
    o.append(t(24 + 11*7.8, 62, "$ neofetch", FG, 13, 7.8))
    # portrait
    for i, line in enumerate(ascii_lines):
        if line.strip():
            o.append(t(24, top + i*alh + 6, line, "#b6c2cf", 7, acw))
    # info panel
    x0, x1, cw, lh = 470, W - 28, 7.5, 17.5
    y = top + 8
    def header(label):
        nonlocal y
        rule = "─" * int((x1 - x0) / cw - len(label) - 3)
        o.append(t(x0, y, label, BLUE, 12.5, cw, weight="bold"))
        o.append(t(x0 + (len(label)+1)*cw, y, rule, BORDER, 12.5, cw))
        y += lh
    def row(k, v, vc=FG):
        nonlocal y
        o.append(t(x0, y, k, GREEN, 12.5, cw))
        vw = len(v) * cw
        dots = int((x1 - vw - x0 - len(k)*cw) / cw) - 2
        if dots > 0:
            o.append(t(x0 + (len(k)+1)*cw, y, "." * dots, "#484f58", 12.5, cw))
        o.append(t(x1, y, v, vc, 12.5, cw, "end"))
        y += lh
    header(f"{h}@github")
    for k, v in CFG["terminal"]["info"]: row(k, v)
    y += 8; header("Stack")
    for k, v in CFG["terminal"]["stack"]: row(k, v)
    y += 8; header("Contact")
    L = CFG["links"]
    row("Email", L["email"]); row("LinkedIn", L["linkedin"].split("//")[1])
    row("GitHub", L["github"].split("//")[1])
    y += 8; header("GitHub Stats")
    row("Repos", num(STATS.get("repos"))); row("Stars", num(STATS.get("stars")))
    row("Followers", num(STATS.get("followers")))
    row("Contributions (12 mo)", num(STATS.get("contributions")))
    o.append(t(x0, H - 22, f"updated {STATS.get('updated', 'pending first workflow run')}", "#484f58", 11, 6.9))
    (GEN / "terminal.svg").write_text(svg_wrap(W, H, "\n".join(o), f"{CFG['name']} terminal profile"))

# ------------------------------------------------------------------ activity
def activity():
    W, H = 1000, 250
    cal = STATS.get("calendar") or [[0]*7 for _ in range(53)]
    have = bool(STATS.get("calendar"))
    o = [f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>']
    tiles = [("Repositories", STATS.get("repos")), ("Stars", STATS.get("stars")),
             ("Followers", STATS.get("followers")), ("Contributions, last year", STATS.get("contributions"))]
    tw = (W - 48 - 3*12) / 4
    for i, (lab, val) in enumerate(tiles):
        x = 24 + i*(tw+12)
        o.append(f'<rect x="{x:.1f}" y="20" width="{tw:.1f}" height="58" rx="6" fill="{PANEL}" stroke="{BORDER}"/>')
        o.append(t(x+14, 44, num(val), GREEN, 20, 12, weight="bold"))
        o.append(t(x+14, 66, lab, MUTED, 11, 6.6))
    flat = [c for w in cal for c in w]
    mx = max(flat) or 1
    pal = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    cell, gap = 13, 3
    gx, gy = 24 + (W - 48 - len(cal)*(cell+gap) + gap)//2, 116
    for wi, w in enumerate(cal):
        for di, c in enumerate(w):
            lvl = 0 if c == 0 else min(4, 1 + int(c / mx * 3.999))
            o.append(f'<rect x="{gx+wi*(cell+gap)}" y="{gy+di*(cell+gap)}" width="{cell}" height="{cell}" rx="2" fill="{pal[lvl]}"/>')
    if have:
        d0 = datetime.date.fromisoformat(STATS["first_day"]); last = None
        for wi in range(len(cal)):
            d = d0 + datetime.timedelta(weeks=wi)
            if d.month != last and d.day <= 7:
                o.append(t(gx+wi*(cell+gap), 106, d.strftime("%b"), MUTED, 10.5, 6.3)); last = d.month
    else:
        o.append(t(W/2 - 190, 106, "contribution data appears after the first workflow run", MUTED, 11, 6.9))
    o.append(t(24, H - 12, "Source: GitHub GraphQL API, refreshed by GitHub Actions", "#484f58", 10.5, 6.3))
    (GEN / "activity.svg").write_text(svg_wrap(W, H, "\n".join(o), "GitHub activity"))

# ------------------------------------------------------------------ README
def readme():
    L, name = CFG["links"], CFG["name"]
    code = lambda xs: " ".join(f"`{x}`" for x in xs)
    md = [f'<div align="center">\n\n# {name}\n\n**{CFG["tagline"]}**\n\n'
          f'[LinkedIn]({L["linkedin"]}) · [Email](mailto:{L["email"]}) · [GitHub]({L["github"]})\n\n</div>\n',
          f'<p align="center">\n  <img src="assets/generated/terminal.svg" alt="neofetch-style terminal profile of {name}" width="100%">\n</p>\n',
          "## About\n\n" + CFG["about"] + "\n",
          "## Technical Skills\n\n| Area | Tools |\n| :-- | :-- |\n" +
          "\n".join(f"| **{a}** | {code(b)} |" for a, b in CFG["skills"]) + "\n",
          "## Featured Projects\n"]
    cells = []
    for p in CFG["projects"]:
        title = f'<a href="{p["url"]}"><b>{p["name"]}</b></a>' if p.get("url") else f'<b>{p["name"]}</b>'
        cells.append(f'{title}<br>{p["desc"]}<br><sub>{" · ".join(p["tech"])}</sub>')
    rows = "".join(f"<tr>{''.join(f'<td valign=\"top\" width=\"50%\">{c}</td>' for c in cells[i:i+2])}</tr>\n"
                   for i in range(0, len(cells), 2))
    md.append(f"<table>\n{rows}</table>\n")
    md.append('## GitHub Activity\n\n<p align="center">\n  <img src="assets/generated/activity.svg" alt="GitHub statistics and contribution graph" width="100%">\n</p>\n')
    md.append("## Experience & Learning\n\n" + "\n".join(f"- {e}" for e in CFG["experience"] + CFG["certifications"]) + "\n")
    md.append(f'## Contact\n\n- Email: [{L["email"]}](mailto:{L["email"]})\n- LinkedIn: [{L["linkedin"].split("//")[1]}]({L["linkedin"]})\n- Location: Lucknow, India\n')
    (ROOT / "README.md").write_text("\n".join(md))

if __name__ == "__main__":
    terminal(); activity(); readme(); print("rendered terminal.svg, activity.svg, README.md")
