
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

URL = "https://plus.rtl.de/love-island-vip-p_3030"


class LinkFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return

        attributes = dict(attrs)
        href = attributes.get("href")

        if href:
            self.links.append(urljoin(URL, href))


def main():
    print("REALITY RADAR - RTL+ LINK-FINDER")
    print("--------------------------------")

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

    finder = LinkFinder()
    finder.feed(html)

    links = sorted(set(finder.links))

    print("Gefundene Links insgesamt:", len(links))

    keywords = [
        "love-island",
        "folge",
        "episode",
        "staffel",
    ]

    matches = [
        link for link in links
        if urlparse(link).hostname in (
            "plus.rtl.de",
            "www.plus.rtl.de",
        )
        and any(
            word in link.lower()
            for word in keywords
        )
    ]

    print("Passende RTL+-Links:", len(matches))

    for link in matches[:40]:
        print("LINK:", link)

    print("\nAnalyse abgeschlossen.")
    print("Keine Dateien wurden veraendert.")


if __name__ == "__main__":
    main()
