
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser

URL = "https://plus.rtl.de/love-island-vip-p_3030"


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(data.strip())


def main():
    print("REALITY RADAR - RTL+ FOLGENFINDER")
    print("--------------------------------")

    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    try:
        with urllib.request.urlopen(
            request, timeout=20
        ) as response:
            html = response.read().decode(
                "utf-8", errors="replace"
            )
            print("HTTP-Status:", response.status)

    except Exception as error:
        print("RTL+-Abruf fehlgeschlagen:", error)
        return

    parser = TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)

    patterns = [
        r"Staffel\s*\d+",
        r"Folge\s*\d+",
        r"Episode\s*\d+",
        r"\d{1,2}\.\d{1,2}\.\d{4}",
    ]

    print("\nGefundene Hinweise:")

    for pattern in patterns:
        matches = re.findall(
            pattern, text, flags=re.IGNORECASE
        )
        unique = list(dict.fromkeys(matches))

        print(f"\nSuchmuster: {pattern}")
        print(f"Treffer: {len(matches)}")

        for match in unique[:15]:
            print(" -", match)

    print("\nRTL+-Analyse abgeschlossen.")
    print("Die feed.json wurde nicht verändert.")


if __name__ == "__main__":
    main()
