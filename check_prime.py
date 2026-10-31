"""Read-only verification of The 50 season 3 Prime Video schedule."""
import json
import urllib.request
from datetime import date, timedelta
from pathlib import Path

SHOW = "The 50"
SOURCE = "https://www.primevideo.com/-/de/detail/0F8L0CWF7XIA8WVEYDBZGXUR5B"

def main():
    feed = json.loads(Path("feed.json").read_text(encoding="utf-8"))
    shows = feed if isinstance(feed, list) else feed["shows"]
    show = next((s for s in shows if s.get("name") == SHOW), None)
    if show is None:
        print("PRIME FEHLER: The 50 nicht im Feed")
        raise SystemExit(1)
    if show.get("season") != "Staffel 3":
        print(f"PRIME WARNUNG: Unerwartete Staffel: {show.get('season')}")
        return
    expected = {}
    for batch in range(5):
        release = (date(2026, 3, 9) + timedelta(days=batch * 7)).isoformat()
        for number in range(batch * 3 + 1, batch * 3 + 4):
            expected[number] = release
    actual = {int(ep["number"]): ep["availableOn"] for ep in show.get("episodes", [])}
    mismatches = [(n, expected[n], actual.get(n)) for n in expected
                  if actual.get(n) != expected[n]]
    extra = sorted(set(actual) - set(expected))
    print(f"PRIME STATUS: The 50: Staffel=3, Feed-Folgen={len(actual)}, "
          f"Erwartete-Folgen=15, Termin-Abweichungen={mismatches}, "
          f"Zusaetzliche-Folgen={extra}")
    try:
        request = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=20) as response:
            page = response.read().decode("utf-8", "replace")
        print(f"PRIME QUELLE: The 50: Prime-Video-Seite-erreichbar=ja, "
              f"Serienname-erkannt={'the 50' in page.lower()}")
    except Exception as exc:
        print(f"PRIME QUELLENFEHLER: The 50: {type(exc).__name__}: {exc}")
    print("PRIME: Nur Terminpruefung; keine Feed-Aenderung und keine Verfuegbarkeitsgarantie.")

if __name__ == "__main__":
    main()
