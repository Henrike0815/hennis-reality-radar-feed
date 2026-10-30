
import json
import re
import urllib.request
from html.parser import HTMLParser

URL = "https://plus.rtl.de/love-island-vip-p_3030"


class DataFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

        self.in_script = False
        self.script_type = ""
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attributes = dict(attrs)
            self.in_script = True
            self.script_type = attributes.get("type", "")
            self.current = []

    def handle_data(self, data):
        if self.in_script:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.in_script:
            self.scripts.append((
                self.script_type,
                "".join(self.current)
            ))
            self.in_script = False


def main():
    print("REALITY RADAR - RTL+ DATENANALYSE")
    print("--------------------------------")

    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(
        request, timeout=20
    ) as response:
        html = response.read().decode(
            "utf-8", errors="replace"
        )
        print("HTTP-Status:", response.status)

    finder = DataFinder()
    finder.feed(html)

    print("Gefundene Script-Bloecke:", len(finder.scripts))

    keywords = [
        "episodeNumber",
        "seasonNumber",
        "releaseDate",
        "publicationDate",
        "availableFrom",
        "episodes",
    ]

    for keyword in keywords:
        count = len(re.findall(
            re.escape(keyword),
            html,
            flags=re.IGNORECASE
        ))
        print(f"{keyword}: {count} Treffer")

    print("\nJSON-Script-Bloecke:")

    for script_type, content in finder.scripts:
        if "json" not in script_type.lower():
            continue

        try:
            data = json.loads(content)
        except (ValueError, TypeError):
            continue

        print("JSON-Typ:", script_type)
        print("Oberste Struktur:", type(data).__name__)

        if isinstance(data, dict):
            print("Felder:", list(data.keys())[:15])

    print("\nAnalyse abgeschlossen.")
    print("Keine Dateien wurden veraendert.")


if __name__ == "__main__":
    main()
