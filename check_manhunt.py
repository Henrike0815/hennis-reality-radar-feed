"""Read-only YouTube RSS diagnostics for Manhunt Saigon, Staffel 4."""
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CHANNEL_ID = "UCnXFGVa7VEoiM2Adftm_Hug"
ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"

def main():
    feed = json.loads(Path("feed.json").read_text(encoding="utf-8"))
    shows = feed if isinstance(feed, list) else feed["shows"]
    show = next((s for s in shows if s.get("name") == "Manhunt Saigon"
                 and s.get("season") == "Staffel 4"), None)
    if show is None:
        raise SystemExit("MANHUNT: Sendung nicht im Feed gefunden")
    existing = {int(ep["number"]) for ep in show["episodes"]}
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + CHANNEL_ID
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            root = ET.fromstring(response.read())
    except Exception as exc:
        print(f"MANHUNT: RSS nicht abrufbar: {exc}")
        return
    found = {}
    for entry in root.findall(ATOM + "entry"):
        title = (entry.findtext(ATOM + "title") or "").strip()
        # Only numbered main episodes explicitly tagged Saigon, never BTS/reactions.
        if not re.search(r"MANHUNT\s*Saigon", title, re.I):
            continue
        match = re.match(r"^Folge\s*0*(\d+)\b\s*\|\s*MANHUNT\s+Saigon\b", title, re.I)
        if not match:
            continue
        number = int(match.group(1))
        published = entry.findtext(ATOM + "published")
        video_id = entry.findtext(YT + "videoId")
        if not published or not video_id:
            continue
        try:
            date = datetime.fromisoformat(published.replace("Z", "+00:00")).astimezone(
                ZoneInfo("Europe/Berlin")).date().isoformat()
        except ValueError:
            continue
        found.setdefault(number, set()).add((date, video_id, title))
    print(f"MANHUNT DIAGNOSE: RSS-Hauptfolgen={len(found)}, bereits im Feed={sorted(existing)}")
    for number in sorted(found):
        matches = found[number]
        if len(matches) != 1:
            print(f"MANHUNT WARNUNG: Folge {number} hat mehrere Videos")
            for date, video_id, title in sorted(matches):
                print(f"MANHUNT VERGLEICH: Folge {number}, Datum={date}, Video={video_id}, Titel={title!r}")
            continue
        date, video_id, title = next(iter(matches))
        status = "VORHANDEN" if number in existing else "KANDIDAT"
        print(f"MANHUNT {status}: Folge {number}, YouTube-Datum={date}, Video={video_id}, Titel={title!r}")
    print("MANHUNT: Nur Diagnose; feed.json unveraendert.")

if __name__ == "__main__":
    main()
