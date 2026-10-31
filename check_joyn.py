"""Read-only diagnostics of Joyn episode links for all tracked Joyn shows."""
import json
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
        print(f"JOYN DIAGNOSE: {name}: URL={final_url}, HTML-Zeichen={len(html)}, "
              f"Staffel/Folge-Kandidaten={sorted(matches)[:35]}, "
              f"Feed-Folgen={len(show.get('episodes', []))}")
    print("JOYN: Nur Diagnose; feed.json unveraendert.")

if __name__ == "__main__":
    main()
