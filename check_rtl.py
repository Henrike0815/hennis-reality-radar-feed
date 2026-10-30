
import json
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

URL = "https://plus.rtl.de/love-island-vip-p_3030"


class LinkFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(urljoin(URL, href))


def main():
    print("REALITY RADAR - RTL+ FOLGENVERGLEICH")
    print("-----------------------------------")

    with open("feed.json", encoding="utf-8") as file:
        feed = json.load(file)

    shows = feed if isinstance(feed, list) else feed["shows"]

    show = next(
        (
            item for item in shows
            if item.get("name") == "Love Island VIP"
            and item.get("season") == "Staffel 3"
        ),
        None,
    )

    if show is None:
        raise ValueError("Love Island VIP Staffel 3 fehlt")

    existing = {
        episode["number"]
        for episode in show["episodes"]
    }

    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    with urllib.request.urlopen(
        request, timeout=20
    ) as response:
        html = response.read().decode(
            "utf-8", errors="replace"
        )
        print("HTTP-Status:", response.status)
    print("HTML-Laenge:", len(html))
    print("Datum 2026-11-11 vorhanden:", "2026-11-11" in html)
    print("Datum 2026-11-25 vorhanden:", "2026-11-25" in html)
    finder = LinkFinder()
    finder.feed(html)

    discovered = {}

    for link in finder.links:
        parsed = urlparse(link)

        if parsed.hostname != "plus.rtl.de":
            continue

        if "/love-island-vip-p_3030/video/" not in parsed.path:
            continue

        match = re.search(
            r"/folge-(\d+)-2026-c_",
            parsed.path,
            flags=re.IGNORECASE,
        )

        if match:
            number = int(match.group(1))
            discovered[number] = link

        print("Gefundene RTL+-Folgenlinks:", len(discovered))

    for number in sorted(discovered):
        print("RTL+ gefunden: Folge", number, discovered[number])

    candidates = sorted(set(discovered) - existing)

    print("Moegliche neue Folgen:", len(candidates))

    for number in candidates:
        print("PRUEFEN: Folge", number)
        print("LINK:", discovered[number])

    if not candidates:
        print("Keine unbekannten Folgennummern gefunden.")

    print("Hinweis: Staffel und Datum nicht bestaetigt.")
    print("Die feed.json wurde nicht veraendert.")


if __name__ == "__main__":
    main()
