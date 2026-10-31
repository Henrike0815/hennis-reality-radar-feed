"""Read-only diagnostics of Joyn episode links for all tracked Joyn shows."""
import json
import html as html_module
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

SLUGS = {
    "Das große Promi-Büßen": "das-grosse-promi-buessen",
    "Forsthaus Rampensau Germany": "forsthaus-rampensau-germany",
    "The Power": "the-power",
    "Club der Reality Detektive": "club-der-reality-detektive",
}

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()
    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        if href:
            self.links.add(href)

def main():
    data = json.loads(Path("feed.json").read_text(encoding="utf-8"))
    shows = data if isinstance(data, list) else data["shows"]
    for name, slug in SLUGS.items():
        show = next((s for s in shows if s.get("name") == name), None)
        if show is None:
            print(f"JOYN WARNUNG: {name}: Nicht im Feed")
            continue
        url = f"https://www.joyn.de/serien/{slug}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                html = response.read().decode("utf-8", "replace")
                final_url = response.geturl()
        except Exception as exc:
            print(f"JOYN FEHLER: {name}: {type(exc).__name__}: {exc}")
            continue
        parser = Links()
        parser.feed(html)
        pattern = re.compile(rf"(?:https?://www\.joyn\.de)?/serien/{re.escape(slug)}/(\d+)-(\d+)-", re.I)
        matches = set()
        for href in parser.links:
            match = pattern.search(href)
            if match:
                matches.add((int(match.group(1)), int(match.group(2))))
        # Site HTML may also contain JSON-embedded episode URLs.
        for match in pattern.finditer(html.replace("\/", "/")):
            matches.add((int(match.group(1)), int(match.group(2))))
        season_match = re.search(r"[0-9]+", str(show.get("season", "")))
        season_number = int(season_match.group()) if season_match else None
        season_matches = sorted(number for season, number in matches if season == season_number)
        feed_numbers = {int(ep["number"]) for ep in show.get("episodes", [])}
        new_numbers = [number for number in season_matches if number not in feed_numbers]
        # Compare existing planned dates with what the landing page actually exposes.
        missing = sorted(feed_numbers - set(season_matches))
        print(f"JOYN ABDECKUNG: {name}: Auf-Seite={len(season_matches)}, "
              f"Nur-im-Feed={missing}, "
              f"Hinweis=Folgenlinks-belegen-keine-JoynPlus-Verfuegbarkeit")
        if season_matches:
            sample = season_matches[-1]
            urls = sorted(h for h in parser.links
                          if re.search(rf"/serien/{re.escape(slug)}/{season_number}-{sample}-", h))
            if urls:
                print(f"JOYN BEISPIEL: {name}: Staffel={season_number}, Folge={sample}, "
                      f"Link={urls[0][:240]}")
        if season_matches:
            sample = season_matches[-1]
            episode_links = sorted(h for h in parser.links
                                   if re.search(rf"/serien/{re.escape(slug)}/{season_number}-{sample}-", h))
            if episode_links:
                episode_url = urllib.request.urljoin("https://www.joyn.de", episode_links[0])
                try:
                    episode_req = urllib.request.Request(
                        episode_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(episode_req, timeout=20) as response:
                        episode_html = response.read().decode("utf-8", "replace")
                    scripts = re.findall(
                        r'<script[^>]*type=["\\\']application/ld\\+json["\\\'][^>]*>(.*?)</script>',
                        episode_html, flags=re.I | re.S)
                    metadata = []
                    for raw in scripts:
                        try:
                            parsed = json.loads(html_module.unescape(raw))
                            nodes = parsed if isinstance(parsed, list) else [parsed]
                            for node in nodes:
                                if isinstance(node, dict):
                                    metadata.append({
                                        "type": node.get("@type"),
                                        "datePublished": node.get("datePublished"),
                                        "uploadDate": node.get("uploadDate"),
                                        "availabilityStarts": node.get("availabilityStarts"),
                                        "episodeNumber": node.get("episodeNumber"),
                                    })
                        except (ValueError, TypeError):
                            continue
                    keywords = {
                        key: len(re.findall(key, episode_html, re.I))
                        for key in ("availabilityStarts", "datePublished", "uploadDate",
                                    "publicationDate", "Joyn PLUS+", "joynPlus")
                    }
                    # Show small, bounded snippets only; do not dump entire HTML.
                    for key in ("datePublished", "uploadDate", "application/ld+json"):
                        match = re.search(re.escape(key), episode_html, re.I)
                        if match:
                            start = max(0, match.start() - 130)
                            end = min(len(episode_html), match.end() + 220)
                            excerpt = re.sub(r"\\s+", " ", episode_html[start:end])
                            print(f"JOYN DATUMSKONTEXT: {name}: Feld={key}, "
                                  f"Ausschnitt={excerpt[:380]!r}")
                    print(f"JOYN DETAIL: {name}: Staffel={season_number}, Folge={sample}, "
                          f"JSONLD={metadata[:6]}, Datumsfelder={keywords}")
                except Exception as exc:
                    print(f"JOYN DETAILFEHLER: {name}: {type(exc).__name__}: {exc}")
        print(f"JOYN STAFFEL: {name}: Staffel={season_number}, "
              f"Joyn-Folgen={season_matches}, Feed-Folgen={sorted(feed_numbers)}, "
              f"Neue-Nummern-Kandidaten={new_numbers}")
        print(f"JOYN DIAGNOSE: {name}: URL={final_url}, HTML-Zeichen={len(html)}, "
              f"Staffel/Folge-Kandidaten={len(matches)}, "
              f"Feed-Folgen={len(show.get('episodes', []))}")
    print("JOYN: Nur Diagnose; feed.json unveraendert.")

if __name__ == "__main__":
    main()
