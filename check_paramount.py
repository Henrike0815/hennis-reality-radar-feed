"""Read-only verification of Paramount+ announced episode schedules."""
import json
import re
import urllib.request
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

SOURCES = {
    "Eating with My Ex VIP": (
        "https://paramount-presse.de/wahre-liebe-alte-wunden-und-die-rechnung-bitte-paramount-serviert-die-neue-reality-show-eating-with-my-ex-vip/",
        date(2026, 11, 3), 3),
    "Germany Shore": (
        "https://paramount-presse.de/bereit-fuer-das-naechste-level-der-eskalation-germany-shore-staffel-6-startet-exklusiv-bei-paramount/",
        date(2026, 11, 24), 12),
}

class VisibleText(HTMLParser):
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
        if not self.skip:
            self.parts.append(data)

def main():
    feed = json.loads(Path("feed.json").read_text(encoding="utf-8"))
    shows = feed if isinstance(feed, list) else feed["shows"]
    for name, (url, start, count) in SOURCES.items():
        show = next((s for s in shows if s.get("name") == name), None)
        if not show:
            print(f"PARAMOUNT WARNUNG: {name}: Nicht im Feed")
            continue
        expected = {n: (start + timedelta(days=7*(n-1))).isoformat()
                    for n in range(1, count+1)}
        actual = {int(e["number"]): e["availableOn"] for e in show.get("episodes", [])}
        wrong = [(n, expected[n], actual.get(n)) for n in expected
                 if actual.get(n) != expected[n]]
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=20) as response:
                page = response.read().decode("utf-8", "replace")
            parser = VisibleText()
            parser.feed(page)
            text = " ".join(" ".join(parser.parts).split()).lower()
            show_marker = ("eating with my ex vip" if name.startswith("Eating")
                           else "germany shore")
            found = show_marker in text and "november" in text
            print(f"PARAMOUNT QUELLE: {name}: Pressemitteilung-erreichbar=ja, "
                  f"Sendung-und-November-erkannt={found}")
        except Exception as exc:
            print(f"PARAMOUNT QUELLENFEHLER: {name}: {type(exc).__name__}: {exc}")
        print(f"PARAMOUNT STATUS: {name}: Erwartete-Folgen={count}, "
              f"Feed-Folgen={len(actual)}, Termin-Abweichungen={wrong}, "
              f"Modus=Nur-Pruefung")
    print("PARAMOUNT: Keine Feed-Aenderung; woechentliche Termine nach Presseankuendigung.")

if __name__ == "__main__":
    main()
