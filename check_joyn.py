"""Daily read-only Joyn monitoring. Never infer Joyn+ release from upload dates."""
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

SLUGS = {
    "Das große Promi-Büßen": "das-grosse-promi-buessen",
    "Forsthaus Rampensau Germany": "forsthaus-rampensau-germany",
    "The Power": "the-power",
    "Club der Reality Detektive": "club-der-reality-detektive",
}
SCRIPT = re.compile(r'<script\\b[^>]*\\btype\\s*=\\s*["\\x27]application/ld\\+json["\\x27][^>]*>(.*?)</script\\s*>', re.I | re.S)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.add(href)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", "replace")

def episode_info(url, season, number):
    page = fetch(url)
    for raw in SCRIPT.findall(page):
        try:
            parsed = json.loads(html.unescape(raw))
        except (ValueError, TypeError):
            continue
        nodes = parsed if isinstance(parsed, list) else [parsed]
        for node in nodes:
            if not isinstance(node, dict) or node.get("@type") != "TVEpisode":
                continue
            part = node.get("partOfSeason") or {}
            if not isinstance(part, dict):
                continue
            try:
                if int(part.get("seasonNumber")) != season or int(node.get("episodeNumber")) != number:
                    continue
            except (TypeError, ValueError):
                continue
            video = node.get("video")
            video = video if isinstance(video, dict) else {}
            return node.get("datePublished"), video.get("uploadDate")
    return None

def main():
    feed = json.loads(Path("feed.json").read_text(encoding="utf-8"))
    shows = feed if isinstance(feed, list) else feed["shows"]
    today = date.today()
    print(f"JOYN MONITOR: Stand={today}, Modus=Nur-Meldung, keine Feed-Aenderungen")
    for name, slug in SLUGS.items():
        show = next((s for s in shows if s.get("name") == name), None)
        if not show:
            print(f"JOYN WARNUNG: {name}: Nicht im Feed")
            continue
        season_match = re.search(r"[0-9]+", str(show.get("season", "")))
        if not season_match:
            print(f"JOYN WARNUNG: {name}: Staffel nicht lesbar")
            continue
        season = int(season_match.group())
        existing = {int(ep["number"]) for ep in show.get("episodes", [])}
        try:
            page = fetch(f"https://www.joyn.de/serien/{slug}")
            parser = Links()
            parser.feed(page)
            pattern = re.compile(rf"/serien/{re.escape(slug)}/{season}-([0-9]+)-", re.I)
            links = {}
            for href in parser.links:
                match = pattern.search(href)
                if match:
                    number = int(match.group(1))
                    links.setdefault(number, urllib.parse.urljoin("https://www.joyn.de", href))
            new = sorted(set(links) - existing)
            print(f"JOYN STATUS: {name}: Staffel={season}, Joyn-Links={len(links)}, "
                  f"Feed-Folgen={len(existing)}, Neue-Kandidaten={new}")
            # Only fetch previously unseen episodes: bounded to avoid hammering Joyn.
            for number in new[:5]:
                try:
                    info = episode_info(links[number], season, number)
                    if info is None:
                        print(f"JOYN PRUEFEN: {name}: Folge={number}, Metadaten=unbestaetigt")
                        continue
                    published, uploaded = info
                    print(f"JOYN PRUEFEN: {name}: Folge={number}, "
                          f"datePublished={published}, video.uploadDate={uploaded}, "
                          f"JoynPlus-Start=NICHT_BESTAETIGT, Link={links[number]}")
                except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                    print(f"JOYN FEHLER: {name}: Folge={number}, {type(exc).__name__}: {exc}")
            if len(new) > 5:
                print(f"JOYN HINWEIS: {name}: {len(new)-5} weitere Kandidaten nicht im Detail geprueft")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print(f"JOYN FEHLER: {name}: {type(exc).__name__}: {exc}")
    print("JOYN MONITOR: feed.json unveraendert; Joyn+-Freischaltung nicht aus JSON-LD ableitbar")

if __name__ == "__main__":
    main()
