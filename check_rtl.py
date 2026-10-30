
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
    print("REALITY RADAR - RTL+ TEST")
    print("------------------------")

    request = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
        },
    )

    try:
        with urllib.request.urlopen(
            request, timeout=20
        ) as response:
            html = response.read().decode(
                "utf-8", errors="replace"
            )
            print("HTTP-Status:", response.status)

    except urllib.error.HTTPError as error:
        print("RTL+ antwortet mit HTTP:", error.code)
        return

    except Exception as error:
        print("Abruf fehlgeschlagen:", error)
        return

    parser = TextExtractor()
    parser.feed(html)

    text = " ".join(parser.parts)

    print("HTML-Zeichen:", len(html))
    print("Sichtbare Textzeichen:", len(text))
    print(
        "Love Island im Text:",
        "love island" in text.lower(),
    )

    print("RTL+-Abrufprüfung abgeschlossen.")
    print("Keine Dateien wurden verändert.")


if __name__ == "__main__":
    main()
