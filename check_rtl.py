"""Reality Radar: discover and safely append verified RTL+ episodes."""

import json
import os
import re
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

FEED_PATH = Path("feed.json")
SOURCES_PATH = Path("show-sources.json")


class PageParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.links = []
        self.json_ld = []
        self._json_ld_parts = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(urljoin(self.base_url, attrs["href"]))
        if tag == "script" and "ld+json" in attrs.get("type", "").lower():
            self._json_ld_parts = []

    def handle_data(self, data):
        if self._json_ld_parts is not None:
            self._json_ld_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._json_ld_parts is not None:
            try:
                self.json_ld.append(json.loads("".join(self._json_ld_parts)))
            except json.JSONDecodeError:
                pass
            self._json_ld_parts = None


def load_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def walk_json(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def types_of(node):
    value = node.get("@type", [])
    return {value} if isinstance(value, str) else set(value) if isinstance(value, list) else set()


def subscription_dates(episode_node):
    dates = set()
    for node in walk_json(episode_node.get("potentialAction", {})):
        if node.get("category") != "subscription":
            continue
        date_text = node.get("availabilityStarts")
        if isinstance(date_text, str):
            try:
                dates.add(datetime.fromisoformat(date_text.replace("Z", "+00:00")).date().isoformat())
            except ValueError:
                pass
    return dates


def verify_episode(html, expected_number, expected_season, accepted_names):
    parser = PageParser("https://plus.rtl.de/")
    parser.feed(html)
    matches = set()
    for document in parser.json_ld:
        for node in walk_json(document):
            if "TVEpisode" not in types_of(node):
                continue
            season = node.get("partOfSeason")
            if not isinstance(season, dict):
                continue
            try:
                season_number = int(season.get("seasonNumber"))
            except (ValueError, TypeError):
                continue
            if season_number != expected_season:
                continue
            try:
                episode_number = int(node.get("episodeNumber"))
            except (ValueError, TypeError):
                continue
            if episode_number != expected_number:
                continue
            series = node.get("partOfSeries")
            if not isinstance(series, dict) or series.get("name", "").strip().casefold() not in accepted_names:
                continue
            matches.update(subscription_dates(node))
    if len(matches) != 1:
        raise ValueError("Staffel, Serie, Folgennummer oder Abo-Datum nicht eindeutig bestaetigt")
    return next(iter(matches))



def diagnose_inactive_sources(sources):
    """Inspect candidate RTL+ pages without modifying feed.json."""
    print("RTL+ DIAGNOSE (nur lesen, keine Aktivierung)")
    for source in sources:
        if source.get("source") != "rtl_plus" or source.get("enabled"):
            continue
        name = source.get("name", "?")
        url = source.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "plus.rtl.de":
            print(f"DIAGNOSE {name}: ungueltige RTL+-Adresse")
            continue
        try:
            page = PageParser(url)
            page.feed(load_page(url))
            rtl_links = [link for link in page.links
                         if urlparse(link).scheme == "https"
                         and urlparse(link).hostname == "plus.rtl.de"]
            base_path = parsed.path.rstrip("/") + "/video/"
            show_videos = [link for link in rtl_links
                           if urlparse(link).path.startswith(base_path)]
            episode_links = [link for link in show_videos
                             if re.search(r"/folge-(\d+)-c_", urlparse(link).path, re.I)]
            ld_types = sorted({str(t) for doc in page.json_ld
                               for node in walk_json(doc)
                               for t in types_of(node)})
            print(f"DIAGNOSE {name}: RTL-Links={len(rtl_links)}, "
                  f"Sendungsvideos={len(show_videos)}, "
                  f"Folgenmuster={len(episode_links)}, JSON-LD-Typen={','.join(ld_types[:8]) or 'keine'}")
            for link in show_videos[:2]:
                print(f"BEISPIEL {name}: {urlparse(link).path[:180]}")
            # Compare URL numbers against metadata before any source is enabled.
            checked = 0
            matching = 0
            differing = 0
            no_date = 0
            wrong_season = 0
            wrong_series = 0
            for episode_url in sorted(set(episode_links))[:5]:
                try:
                    detail_page = PageParser(episode_url)
                    detail_page.feed(load_page(episode_url))
                    url_match = re.search(r"/folge-(\d+)-c_", urlparse(episode_url).path, re.I)
                    if url_match is None:
                        print(f"ABGLEICH {name}: Unbekanntes URL-Format uebersprungen")
                        continue
                    url_number = int(url_match.group(1))
                    nodes = [node for doc in detail_page.json_ld
                             for node in walk_json(doc)
                             if "TVEpisode" in types_of(node)]
                    checked += 1
                    if len(nodes) != 1:
                        print(f"ABGLEICH {name}: URL-Folge={url_number}, TVEpisode-Anzahl={len(nodes)}")
                        continue
                    node = nodes[0]
                    try:
                        meta_number = int(node.get("episodeNumber"))
                    except (ValueError, TypeError):
                        meta_number = None
                    dates = subscription_dates(node)
                    season_node = node.get("partOfSeason")
                    series_node = node.get("partOfSeries")
                    try:
                        actual_season = int(season_node.get("seasonNumber")) if isinstance(season_node, dict) else None
                    except (ValueError, TypeError):
                        actual_season = None
                    expected_season_match = re.fullmatch(r"Staffel\s+(\d+)", source.get("season", ""), re.I)
                    expected_season = source.get("rtl_season_number")
                    if expected_season is None and expected_season_match:
                        expected_season = int(expected_season_match.group(1))
                    if expected_season is None or actual_season != expected_season:
                        wrong_season += 1
                        print(f"STAFFELWARNUNG {name}: Erwartet={expected_season}, Gefunden={actual_season}")
                    actual_series = series_node.get("name", "") if isinstance(series_node, dict) else ""
                    accepted = [name] + source.get("rtl_names", [])
                    if actual_series.strip().casefold() not in {n.strip().casefold() for n in accepted}:
                        wrong_series += 1
                        print(f"SERIENWARNUNG {name}: RTL-Name={actual_series!r}")
                    if meta_number == url_number:
                        matching += 1
                    else:
                        differing += 1
                        print(f"ABWEICHUNG {name}: URL-Folge={url_number}, Metadaten-Folge={meta_number}")
                    if len(dates) != 1:
                        no_date += 1
                except Exception as error:
                    print(f"ABGLEICH {name}: Seitenpruefung fehlgeschlagen: {error}")
            print(f"ABGLEICH {name}: geprueft={checked}, Nummer-gleich={matching}, "
                  f"Nummer-abweichend={differing}, Abo-Datum-nicht-eindeutig={no_date}, "
                  f"Staffelwarnungen={wrong_season}, Serienwarnungen={wrong_series}")
            # Inspect at most one unique episode per inactive show. No feed writes.
            unique_episodes = sorted(set(episode_links))
            if unique_episodes:
                try:
                    detail = PageParser(unique_episodes[0])
                    detail.feed(load_page(unique_episodes[0]))
                    episodes = [node for document in detail.json_ld
                                for node in walk_json(document)
                                if "TVEpisode" in types_of(node)]
                    print(f"DETAIL {name}: TVEpisode-Eintraege={len(episodes)}")
                    for node in episodes[:2]:
                        season = node.get("partOfSeason")
                        series = node.get("partOfSeries")
                        season_num = season.get("seasonNumber") if isinstance(season, dict) else None
                        series_name = series.get("name") if isinstance(series, dict) else None
                        dates = sorted(subscription_dates(node))
                        print(f"METADATEN {name}: Staffel={season_num!r}, "
                              f"Serie={series_name!r}, Folge={node.get('episodeNumber')!r}, "
                              f"Abo-Termine={dates}")
                    if not episodes:
                        print(f"HINWEIS {name}: Folgenseite ohne TVEpisode-Metadaten")
                except Exception as error:
                    print(f"DETAIL {name}: Abruf fehlgeschlagen: {error}")
            else:
                print(f"HINWEIS {name}: Noch keine belastbare automatische Erkennung")
        except Exception as error:
            print(f"DIAGNOSE {name}: Seitenpruefung fehlgeschlagen: {error}")


def main():
    with SOURCES_PATH.open(encoding="utf-8") as file:
        sources = json.load(file)["shows"]
    with FEED_PATH.open(encoding="utf-8") as file:
        feed = json.load(file)
    shows = feed if isinstance(feed, list) else feed["shows"]
    if os.environ.get("RTL_DIAGNOSTICS") == "1":
        diagnose_inactive_sources(sources)
    total_new = 0

    for source in sources:
        if not source.get("enabled") or source.get("source") != "rtl_plus":
            continue
        name = source["name"]
        season_label = source["season"]
        season_match = re.fullmatch(r"Staffel\s+(\d+)", season_label)
        season_number = source.get("rtl_season_number")
        if season_number is None and season_match:
            season_number = int(season_match.group(1))
        if type(season_number) is not int or season_number < 1:
            print(f"UEBERSPRUNGEN: RTL-Staffelnummer fehlt fuer {name}")
            continue
        accepted_names = {name.strip().casefold()}
        accepted_names.update(alias.strip().casefold() for alias in source.get("rtl_names", []) if isinstance(alias, str) and alias.strip())
        url = source["url"]
        parsed_url = urlparse(url)
        if parsed_url.scheme != "https" or parsed_url.hostname != "plus.rtl.de":
            print(f"UEBERSPRUNGEN: Ungueltige RTL+-URL fuer {name}")
            continue
        show = next((item for item in shows if item.get("name") == name and item.get("season") == season_label), None)
        if show is None:
            print(f"UEBERSPRUNGEN: {name} {season_label} fehlt in feed.json")
            continue
        episodes = show["episodes"]
        existing_numbers = {episode["number"] for episode in episodes}
        existing_ids = {episode["id"] for episode in episodes}
        if len(existing_numbers) != len(episodes) or len(existing_ids) != len(episodes):
            raise ValueError(f"Doppelte vorhandene Folgen bei {name} {season_label}")
        print(f"PRUEFE: {name} {season_label}")
        overview = PageParser(url)
        overview.feed(load_page(url))
        discovered = {}
        base_path = parsed_url.path.rstrip("/") + "/video/"
        for link in overview.links:
            parsed = urlparse(link)
            if parsed.scheme != "https" or parsed.hostname != "plus.rtl.de" or not parsed.path.startswith(base_path):
                continue
            match = re.search(r"/folge-(\d+)-c_", parsed.path, flags=re.IGNORECASE)
            if match:
                number = int(match.group(1))
                discovered.setdefault(number, set()).add(link)
        candidates = sorted(number for number in discovered if number not in existing_numbers)
        print(f"Neue Folgennummern: {len(candidates)}")
        new_episodes = []
        for number in candidates:
            links = discovered[number]
            if len(links) != 1:
                print(f"UEBERSPRUNGEN: Folge {number} hat mehrere Links")
                continue
            try:
                date = verify_episode(load_page(next(iter(links))), number, season_number, accepted_names)
                # The ID prefix is a legacy format. Existing IDs are never changed.
                prefix = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                episode_id = f"{prefix}-s{season_number}-e{number}"
                if episode_id in existing_ids or any(ep["id"] == episode_id for ep in new_episodes):
                    raise ValueError("ID bereits vorhanden")
                new_episodes.append({"id": episode_id, "number": number, "availableOn": date})
                print(f"NEU: Folge {number}, {date}")
            except Exception as error:
                print(f"UEBERSPRUNGEN: Folge {number}: {error}")
        if new_episodes:
            episodes.extend(new_episodes)
            total_new += len(new_episodes)

    if total_new:
        # All changes are applied only after all sources were processed successfully.
        with FEED_PATH.open("w", encoding="utf-8") as file:
            json.dump(feed, file, ensure_ascii=False, indent=2)
            file.write("\n")
        print(f"FEED AKTUALISIERT: {total_new} neue Folgen")
    else:
        print("Keine neuen geprueften Folgen. feed.json unveraendert.")


if __name__ == "__main__":
    main()
