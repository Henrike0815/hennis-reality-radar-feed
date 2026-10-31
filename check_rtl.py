
import json
from datetime import datetime
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


def load_page(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
    )

    with urllib.request.urlopen(
        request, timeout=20
    ) as response:
        html = response.read().decode(
            "utf-8", errors="replace"
        )
        print("HTTP-Status:", response.status)

    return html
    

def create_episode(number, date):
    return {
        "id": f"love-island-vip-s3-e{number}",
        "number": number,
        "availableOn": date,
    }
def is_new_episode(number, existing_numbers):
    return number not in existing_numbers
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

    print("UEBERSICHTSSEITE")
    html = load_page(URL)
    print("HTML-Laenge:", len(html))

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

    print("Vorhandene Folgen:", len(existing))
    print("Gefundene RTL+-Folgenlinks:", len(discovered))

    for number in sorted(discovered):
        print(
            "RTL+ gefunden: Folge",
            number,
            discovered[number],
        )
    print("-----------------------------------")
    print("AUTOMATISCHE ABO-DATUMSPRUEFUNG")

    for number, link in sorted(discovered.items()):
        try:
            page_html = load_page(link)

            abo_dates = re.findall(
                r'"category"\s*:\s*"subscription"'
                r'.{0,500}?"availabilityStarts"\s*:\s*"([^"]+)"',
                page_html,
            )

            if len(set(abo_dates)) == 1:
                date = datetime.fromisoformat(abo_dates[0]).date()
                print(f"Folge {number}: ABO {date.isoformat()}")
            else:
                print(f"Folge {number}: Kein eindeutiger ABO-Start")

        except Exception as error:
            print(f"Folge {number}: Fehler bei der Pruefung: {error}")

        candidates = sorted(
        number
        for number in discovered
        if is_new_episode(number, existing)
    )

    print("Moegliche neue Folgen:", len(candidates))

    for number in candidates:
        print("PRUEFEN: Folge", number)

        try:
            candidate_html = load_page(discovered[number])
            season_match = re.search(
                r'"partOfSeason"\s*:\s*\{[^{}]*"seasonNumber"\s*:\s*(\d+)',
                candidate_html,
            )

            if not season_match or int(season_match.group(1)) != 3:
                print("UEBERSPRUNGEN: Staffel 3 nicht bestaetigt")
                continue

            abo_dates = re.findall(
                r'"category"\s*:\s*"subscription"'
                r'.{0,500}?"availabilityStarts"\s*:\s*"([^"]+)"',
                candidate_html,
            )

            if len(set(abo_dates)) != 1:
                print("UEBERSPRUNGEN: Kein eindeutiger Abo-Start")
                continue

            date = datetime.fromisoformat(abo_dates[0]).date()
            episode = create_episode(number, date.isoformat())

            print(
                "NEUER FOLGENEINTRAG:",
                json.dumps(episode, ensure_ascii=False),
            )

        except Exception as error:
            print("UEBERSPRUNGEN:", error)

    if not candidates:
        print("Keine unbekannten Folgennummern gefunden.")

    print("-----------------------------------")
    print("FOLGENSEITE - TEST")

    episode_url = (
        "https://plus.rtl.de/love-island-vip-p_3030/"
        "video/folge-14-2026-c_2174504"
    )

    episode_html = load_page(episode_url)

    print("HTML-Laenge:", len(episode_html))
    print("2026-10-28:", "2026-10-28" in episode_html)
    position = episode_html.find("2026-10-28")
    if position >= 0:
        print("DATUM-KONTEXT:")
        print(episode_html[max(0, position - 150):position + 150])
    print("releaseDate:", "releaseDate" in episode_html)
    print("datePublished:", "datePublished" in episode_html)
    dates = re.findall(
        r'"availabilityStarts"\s*:\s*"([^"]+)"',
        episode_html
    )
    print("RTL+ Verfügbarkeitsdaten:", sorted(set(dates)))
    abo_dates = re.findall(
        r'"category"\s*:\s*"subscription"'
        r'.{0,500}?"availabilityStarts"\s*:\s*"([^"]+)"',
        episode_html
    )

    if abo_dates:
        abo_date = datetime.fromisoformat(abo_dates[0]).date()
        print("ABO-START ERKANNT:", abo_date.isoformat())
    else:
        print("KEIN ABO-START ERKANNT")
    print(
        "ABO-ZUGANG VORHANDEN:",
        '"category":"subscription"' in episode_html
    )
    position = episode_html.find("2026-10-28T22:15:00")
    if position >= 0:
        print("VERFUEGBARKEIT-KONTEXT:")
        print(episode_html[max(0, position - 250):position + 250])
    print("-----------------------------------")
    print("Hinweis: Staffel und Datum nicht bestaetigt.")
    print("Die feed.json wurde nicht veraendert.")


if __name__ == "__main__":
    main()
