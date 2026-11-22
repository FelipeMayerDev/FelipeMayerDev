"""Render the profile's SVG assets (section bars, contribution heatmap, footer).

Run by .github/workflows/render.yml every day; needs GITHUB_TOKEN.
"""
import json
import os
import urllib.request
from pathlib import Path

USER = "FelipeMayerDev"
OUT = Path(__file__).resolve().parent.parent / "assets"
FONT = 'ui-monospace,"JetBrains Mono","Cascadia Code",SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace'

# Tokyo Night / Tokyo Night Day, same palette as the header.
THEMES = {
    "dark": dict(bg="#1a1b26", fg="#a9b1d6", dim="#565f89", accent="#7aa2f7", title="#bb9af7", border="#292e42",
                 heat=["#1f2335", "#2a3a66", "#3d59a1", "#5a7ee0", "#7aa2f7"]),
    "light": dict(bg="#e1e2e7", fg="#3760bf", dim="#8990b3", accent="#2e7de9", title="#9854f1", border="#b4b5b9",
                  heat=["#d0d5e3", "#a8c0f0", "#7aa2f7", "#2e7de9", "#1a5fc0"]),
}

SECTIONS = {
    "desktop": "Omarchy &amp; Hyprland",  # SVG is XML: keep entities escaped
    "self-hosted": "my own server",
    "agents": "daily driver: Orca",
    "plugins": "small tools for apps I use",
    "upstream": "open source I've contributed to",
}


def gql(query):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}"},
    )
    with urllib.request.urlopen(req) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def svg(w, h, label, body, t):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{label}">'
            f'<style>text{{font-family:{FONT};font-size:13px;fill:{t["fg"]}}}</style>{body}</svg>\n')


def section_bar(name, sub, t):
    body = (f'<rect x="1" y="1" width="838" height="32" rx="7" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<rect x="1" y="1" width="4" height="32" rx="2" fill="{t["accent"]}"/>'
            f'<text x="18" y="22" style="fill:{t["title"]};font-weight:700">{name}/</text>'
            f'<text x="822" y="22" text-anchor="end" style="fill:{t["dim"]}">{sub}</text>')
    return svg(840, 34, f"{name}: {sub}", body, t)


def heatmap(cal, t):
    weeks = cal["weeks"][-53:]
    top = max((d["contributionCount"] for w in weeks for d in w["contributionDays"]), default=0) or 1
    cells = []
    for x, week in enumerate(weeks):
        for d in week["contributionDays"]:
            n = d["contributionCount"]
            # ponytail: linear buckets; switch to quartiles if one huge day flattens the rest
            lvl = 0 if n == 0 else min(4, 1 + 3 * n // top)
            cells.append(f'<rect x="{49 + x * 14}" y="{36 + d["weekday"] * 14}" width="11" height="11" rx="2" fill="{t["heat"][lvl]}"/>')
    total = cal["totalContributions"]
    body = (f'<rect x="1" y="1" width="838" height="148" rx="8" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<text x="18" y="24" style="fill:{t["title"]};font-weight:700">activity/</text>'
            f'<text x="822" y="24" text-anchor="end" style="fill:{t["dim"]}">{total} contributions in the last year</text>'
            + "".join(cells))
    return svg(840, 150, f"{total} contributions in the last year", body, t)


def footer(last_push, merged, t):
    body = (f'<rect x="1" y="1" width="838" height="26" rx="7" fill="{t["bg"]}" stroke="{t["border"]}"/>'
            f'<text x="16" y="19" style="fill:{t["dim"]}">last push <tspan style="fill:{t["accent"]}">{last_push}</tspan></text>'
            f'<text x="420" y="19" text-anchor="middle" style="fill:{t["dim"]}">felipe@omarchy</text>'
            f'<text x="824" y="19" text-anchor="end" style="fill:{t["dim"]}"><tspan style="fill:{t["accent"]}">{merged}</tspan> PRs merged upstream</text>')
    return svg(840, 28, f"Last push {last_push}; {merged} PRs merged upstream", body, t)


def main():
    data = gql(f'''{{
      user(login: "{USER}") {{
        contributionsCollection {{ contributionCalendar {{ totalContributions weeks {{ contributionDays {{ contributionCount weekday }} }} }} }}
        repositories(first: 1, privacy: PUBLIC, orderBy: {{field: PUSHED_AT, direction: DESC}}) {{ nodes {{ pushedAt }} }}
      }}
      search(query: "author:{USER} is:pr is:merged -user:{USER}", type: ISSUE, first: 0) {{ issueCount }}
    }}''')
    user = data["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    last_push = user["repositories"]["nodes"][0]["pushedAt"][:10]
    merged = data["search"]["issueCount"]
    for name, t in THEMES.items():
        for sec, sub in SECTIONS.items():
            (OUT / f"section-{sec}-{name}.svg").write_text(section_bar(sec, sub, t))
        (OUT / f"activity-{name}.svg").write_text(heatmap(cal, t))
        (OUT / f"footer-{name}.svg").write_text(footer(last_push, merged, t))


if __name__ == "__main__":
    main()
