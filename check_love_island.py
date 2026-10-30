
import json
from pathlib import Path


def load_json(filename):
    with Path(filename).open(encoding="utf-8") as file:
        return json.load(file)


def main():
    feed = load_json("feed.json")
    schedule = load_json("love-island-schedule.json")

    # Sendungen in der bestehenden Folgenliste finden
    if isinstance(feed, list):
        shows = feed
    elif isinstance(feed, dict):
        shows = feed.get("shows", [])
    else:
        raise ValueError("Unbekanntes Feed-Format")

    if not isinstance(shows, list):
        raise ValueError("'shows' muss eine Liste sein")

    show = next(
        (
            item for item in shows
            if item.get("name") == schedule["show"]
            and item.get("season") == schedule["season"]
        ),
        None,
    )

    if show is None:
        raise ValueError("Love Island VIP wurde nicht gefunden")

    existing_episodes = show.get("episodes", [])
    existing_ids = {
        episode["id"] for episode in existing_episodes
    }

    scheduled_episodes = schedule["episodes"]

    new_episodes = [
        episode for episode in scheduled_episodes
        if episode["id"] not in existing_ids
    ]

    print("LOVE ISLAND VIP - FOLGENPRÜFUNG")
    print("--------------------------------")
    print(f"Bereits eingetragen: {len(existing_episodes)}")
    print(f"Im Testkalender: {len(scheduled_episodes)}")
    print(f"Fehlende Folgen: {len(new_episodes)}")

    for episode in new_episodes:
        print(
            f"NEU: Folge {episode['number']} "
            f"am {episode['availableOn']}"
        )

    if not new_episodes:
        print("Alles aktuell. Keine neuen Folgen nötig.")

    print("Die feed.json wurde nicht verändert.")


if __name__ == "__main__":
    main()
