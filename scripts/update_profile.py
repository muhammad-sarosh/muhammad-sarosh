"""Generate profile SVGs from public GitHub data (standard library only)."""

from collections import Counter
from datetime import date, timedelta
from html import escape
from pathlib import Path
import json
import os
import re
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
USER = "muhammad-sarosh"
BG = "#1a1b27"
CARD = "#222436"
TEXT = "#c0caf5"
MUTED = "#9aa5ce"
CYAN = "#7dcfff"
COLORS = ["#7aa2f7", "#9ece6a", "#e0af68", "#bb9af7", "#f7768e", "#73daca"]


def fetch(url):
    headers = {"User-Agent": "profile-readme-generator"}
    if url.startswith("https://api.github.com/") and os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8")


def svg(width, height, body, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">'
        f'<title>{escape(title)}</title>'
        f'<rect width="{width}" height="{height}" rx="12" fill="{BG}"/>'
        f'<style>text{{font-family:Segoe UI,Arial,sans-serif}}</style>{body}</svg>\n'
    )


def txt(x, y, value, size=15, color=TEXT, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def write(name, content):
    (ROOT / name).write_text(content, encoding="utf-8")


def main():
    update_summary_stats()
    update_profile_details()
    profile = json.loads(fetch(f"https://api.github.com/users/{USER}"))
    repos = json.loads(fetch(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner"))
    repos = [repo for repo in repos if not repo["fork"] and repo["name"] != USER]
    languages = Counter(repo["language"] for repo in repos if repo["language"])
    total_stars = sum(repo["stargazers_count"] for repo in repos)

    contribution_html = fetch(f"https://github.com/users/{USER}/contributions")
    match = re.search(r'id="js-contribution-activity-description"[^>]*>\s*([\d,]+)', contribution_html)
    yearly_total = int(match.group(1).replace(",", "")) if match else None
    days = {
        date.fromisoformat(day): int(level)
        for day, level in re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"', contribution_html)
    }
    if not days:
        raise RuntimeError("GitHub contribution calendar could not be parsed")

    # Language distribution: each repository contributes once, by its primary language.
    count = sum(languages.values())
    overview = txt(30, 38, "Primary languages", 20, CYAN, 700)
    overview += txt(30, 62, "Across public, non-fork repositories", 12, MUTED)
    angle = 0
    for index, (language, amount) in enumerate(languages.most_common(6)):
        fraction = amount / count
        overview += (f'<circle cx="130" cy="144" r="56" fill="none" stroke="{COLORS[index]}" '
                     f'stroke-width="23" stroke-dasharray="{fraction * 351.86:.2f} 351.86" '
                     f'transform="rotate({angle - 90:.2f} 130 144)"/>')
        angle += fraction * 360
        y = 91 + index * 25
        overview += f'<circle cx="255" cy="{y - 5}" r="5" fill="{COLORS[index]}"/>'
        overview += txt(269, y, language, 14)
        overview += txt(530, y, f"{amount} repos", 14, MUTED, anchor="end")
    overview += txt(130, 139, count, 24, TEXT, 700, "middle")
    overview += txt(130, 159, "repos", 12, MUTED, anchor="middle")
    write("overview.svg", svg(560, 245, overview, "Public repositories by primary language"))

    cards = [
        ("PUBLIC REPOSITORIES", profile["public_repos"]),
        ("STARS EARNED", total_stars),
        ("FOLLOWERS", profile["followers"]),
        ("CONTRIBUTIONS · LAST YEAR", yearly_total if yearly_total is not None else "—"),
    ]
    stats = txt(28, 38, "Muhammad Sarosh · GitHub stats", 20, CYAN, 700)
    for index, (label, value) in enumerate(cards):
        x = 28 + index * 190
        stats += f'<rect x="{x}" y="58" width="176" height="90" rx="9" fill="{CARD}"/>'
        stats += txt(x + 14, 86, label, 10, MUTED, 700)
        stats += txt(x + 14, 129, value, 30, COLORS[index], 700)
    stats += txt(28, 175, "Public profile snapshot · updated " + date.today().isoformat(), 12, MUTED)
    write("stats.svg", svg(820, 195, stats, "Public GitHub profile statistics"))

    first = min(days)
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    graph = txt(30, 36, "Contribution activity", 20, CYAN, 700)
    graph += txt(30, 57, f"{yearly_total:,} contributions in the last year" if yearly_total is not None else "Last year", 12, MUTED)
    palette = ["#292e42", "#0e4429", "#006d32", "#26a641", "#39d353"]
    for day, level in days.items():
        week = (day - start).days // 7
        weekday = (day.weekday() + 1) % 7
        x, y = 57 + week * 14, 88 + weekday * 14
        graph += f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="{palette[level]}"/>'
    for weekday, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        graph += txt(43, 97 + weekday * 14, label, 10, MUTED, anchor="end")
    last_month = None
    for week in range(54):
        current = start + timedelta(days=week * 7)
        if current.month != last_month and current >= first:
            graph += txt(57 + week * 14, 78, current.strftime("%b"), 10, MUTED)
            last_month = current.month
    graph += txt(57, 207, "Less", 11, MUTED)
    for level, color in enumerate(palette):
        graph += f'<rect x="90" y="198" width="11" height="11" rx="2" fill="{color}" transform="translate({level * 14} 0)"/>'
    graph += txt(171, 207, "More", 11, MUTED)
    write("contributions.svg", svg(825, 225, graph, "GitHub contribution calendar for the last year"))


def update_profile_details():
    """Use a clean title and keep the contact row clear of the chart."""
    root = ET.fromstring(fetch(
        f"https://github-profile-summary-cards.vercel.app/api/cards/profile-details"
        f"?username={USER}&theme=tokyonight&name={USER}"
    ))
    title_found = False
    for element in root.iter():
        if element.tag.endswith("}text") and element.get("y") == "40":
            element.text = USER
            title_found = True
        if element.tag.endswith("}text") and element.text and "@" in element.text:
            element.set("style", element.get("style", "").replace("font-size: 14px", "font-size: 11px"))
    if not title_found:
        raise RuntimeError("Upstream profile title changed")
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    write("profile-details.svg", ET.tostring(root, encoding="unicode") + "\n")


def update_summary_stats():
    """Show last-year calendar contributions, with PR and issue rows omitted."""
    calendar = fetch(f"https://github.com/users/{USER}/contributions")
    match = re.search(
        r'id="js-contribution-activity-description"[^>]*>\s*([\d,]+)', calendar
    )
    if not match:
        raise RuntimeError("GitHub last-year contribution total could not be parsed")
    yearly_total = int(match.group(1).replace(",", ""))
    root = ET.fromstring(fetch(
        f"https://github-profile-summary-cards.vercel.app/api/cards/stats?username={USER}&theme=tokyonight"
    ))
    removed_labels = {"Total PRs:", "Total Issues:"}
    labels = {element.text for element in root.iter()}
    if not removed_labels.issubset(labels):
        raise RuntimeError("Upstream stats card changed; cannot identify rows to remove")
    commit_label_found = False
    commit_value_found = False
    for element in root.iter():
        if element.text == "Total Commits:":
            element.text = "Contributions (1y):"
            commit_label_found = True
        elif (element.tag.endswith("}text") and element.get("x") == "130"
              and re.search(r"--gpsc-i:\s*1(?:;|$)", element.get("style", ""))):
            element.text = f"{yearly_total:,}"
            commit_value_found = True
    if not (commit_label_found and commit_value_found):
        raise RuntimeError("Upstream commit row changed; cannot replace it safely")
    # Give the longer contribution label room while keeping all values aligned.
    for element in root.iter():
        if element.tag.endswith("}text") and element.get("x") == "130":
            element.set("x", "155")
    for parent in root.iter():
        for element in list(parent):
            style = element.get("style", "")
            if re.search(r"--gpsc-i:\s*[23](?:;|$)", style):
                parent.remove(element)
            elif re.search(r"--gpsc-i:\s*4(?:;|$)", style):
                element.set("y", "64.4") if element.get("y") else None
                for child in element:
                    if child.get("transform") == "translate(0,100.8)":
                        child.set("transform", "translate(0,50.4)")
    if any(element.text in removed_labels for element in root.iter()):
        raise RuntimeError("PR and issue rows were not removed")
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    write("summary-stats.svg", ET.tostring(root, encoding="unicode") + "\n")


if __name__ == "__main__":
    main()
