#!/usr/bin/env python3
"""Generate a hexagon (FIFA-style) radar chart of your GitHub language distribution.

Usage:
  python generate_radar.py                 # uses GITHUB_REPOSITORY_OWNER / GITHUB_TOKEN
  python generate_radar.py --user NAME     # explicit username
  python generate_radar.py --demo          # sample data, no network
Output: language-radar.svg
"""
import argparse, json, math, os, urllib.request
from collections import Counter

API = "https://api.github.com"

def get(url, token):
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "language-radar"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def collect(user, token):
    totals, repos, page = Counter(), 0, 1
    while True:
        batch = get(f"{API}/users/{user}/repos?per_page=100&type=owner&page={page}", token)
        if not batch:
            break
        for repo in batch:
            if repo.get("fork") or repo.get("archived"):
                continue
            langs = get(repo["languages_url"], token)
            if langs:
                repos += 1
                totals.update(langs)
        page += 1
    return totals, repos

def render(totals, repos, user, out="language-radar.svg"):
    top = totals.most_common(6)
    while len(top) < 6:
        top.append(("-", 0))
    grand = sum(totals.values()) or 1
    mx = max(v for _, v in top) or 1
    # score 0-100 relative to the strongest language, floor so the shape stays readable
    scores = [max(26, round(v / mx * 100)) if v else 6 for _, v in top]
    pct = [v / grand * 100 for _, v in top]

    W, H, cx, cy, R = 560, 560, 280, 300, 150
    ang = lambda i: math.radians(-90 + 60 * i)
    pt = lambda i, f: (cx + R * f * math.cos(ang(i)), cy + R * f * math.sin(ang(i)))
    poly = lambda f: " ".join("%.1f,%.1f" % pt(i, f) for i in range(6))

    s = []
    s.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Segoe UI, Helvetica, Arial, sans-serif">')
    s.append('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1117"/><stop offset="1" stop-color="#0b1f17"/></linearGradient>
<linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00e676" stop-opacity="0.65"/><stop offset="1" stop-color="#00c853" stop-opacity="0.25"/></linearGradient>
<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>''')
    s.append(f'<rect width="{W}" height="{H}" rx="22" fill="url(#bg)" stroke="#1f6f4a" stroke-width="1.5"/>')
    s.append(f'<text x="{W/2}" y="44" text-anchor="middle" fill="#00e676" font-size="22" font-weight="700" letter-spacing="3">LANGUAGE ATTRIBUTES</text>')
    s.append(f'<text x="{W/2}" y="66" text-anchor="middle" fill="#7d8590" font-size="13">@{user} · {repos} repositories analysed</text>')
    # rings
    for k, f in enumerate((0.2, 0.4, 0.6, 0.8, 1.0)):
        op = 0.9 if f == 1.0 else 0.45
        sw = 2 if f == 1.0 else 1
        s.append(f'<polygon points="{poly(f)}" fill="{"#0f2a1f" if k % 2 == 0 else "none"}" fill-opacity="0.5" stroke="#1f6f4a" stroke-opacity="{op}" stroke-width="{sw}"/>')
    # circle inside the hexagon (inscribed)
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{R*math.cos(math.radians(30)):.1f}" fill="none" stroke="#00e676" stroke-opacity="0.35" stroke-dasharray="4 5"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{R*0.5:.1f}" fill="none" stroke="#1f6f4a" stroke-opacity="0.5"/>')
    # axes
    for i in range(6):
        x, y = pt(i, 1)
        s.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#1f6f4a" stroke-opacity="0.6"/>')
    # data polygon
    dpts = " ".join("%.1f,%.1f" % pt(i, scores[i] / 100) for i in range(6))
    s.append(f'<polygon points="{dpts}" fill="url(#fill)" stroke="#00e676" stroke-width="2.5" stroke-linejoin="round" filter="url(#glow)"/>')
    for i in range(6):
        x, y = pt(i, scores[i] / 100)
        s.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#0d1117" stroke="#00e676" stroke-width="2.5"/>')
    # centre badge
    s.append(f'<circle cx="{cx}" cy="{cy}" r="20" fill="#0d1117" stroke="#00e676" stroke-width="2"/>')
    s.append(f'<text x="{cx}" y="{cy+4}" text-anchor="middle" fill="#00e676" font-size="13" font-weight="800">{len([1 for n,v in top if v])}</text>')
    s.append(f'<text x="{cx}" y="{cy+13}" text-anchor="middle" fill="#7d8590" font-size="6" letter-spacing="1">LANGS</text>')
    # labels
    for i, (name, v) in enumerate(top):
        lx, ly = pt(i, 1.2)
        a = math.degrees(ang(i)) % 360
        anchor = "middle" if a in (270.0,) or abs(a - 90) < 1 else ("start" if math.cos(ang(i)) > 0 else "end")
        s.append(f'<text x="{lx:.1f}" y="{ly-2:.1f}" text-anchor="{anchor}" fill="#e6edf3" font-size="16" font-weight="700">{name}</text>')
        s.append(f'<text x="{lx:.1f}" y="{ly+16:.1f}" text-anchor="{anchor}" fill="#00e676" font-size="14" font-weight="600">{pct[i]:.1f}%</text>')
    s.append('</svg>')
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(s))
    print("wrote", out, [(n, round(p, 1)) for (n, _), p in zip(top, pct)])

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER"))
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default="language-radar.svg")
    a = ap.parse_args()
    if a.demo:
        render(Counter({"Go": 52000, "Python": 31000, "TypeScript": 24000, "Java": 21000, "JavaScript": 16000, "C": 9000}), 9, a.user or "your-username", a.out)
    else:
        if not a.user:
            raise SystemExit("Provide --user or set GITHUB_REPOSITORY_OWNER")
        tot, n = collect(a.user, os.environ.get("GITHUB_TOKEN"))
        render(tot, n, a.user, a.out)
