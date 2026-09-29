"""Pull Xavier's meet schedules from Athletic.net's public iCal feeds into data/schedule.json.

Runs in GitHub Actions on a timer. Only rewrites the file when a schedule actually changes.
"""
import datetime
import json
import pathlib
import re
import urllib.request

SCHOOL_ID = 9479  # Xavier (NY) on Athletic.net
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "schedule.json"

SPORTS = {
    "xc": {
        "label": "Cross Country",
        "feed": "https://www.athletic.net/CrossCountry/Print/ical.ashx?SchoolID={id}&S={season}",
        "team": "https://www.athletic.net/team/{id}/cross-country/{season}",
    },
    "tf": {
        "label": "Outdoor Track & Field",
        "feed": "https://www.athletic.net/TrackAndField/Print/ical.ashx?SchoolID={id}&S={season}",
        "team": "https://www.athletic.net/team/{id}/track-and-field-outdoor/{season}",
    },
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "xavier-track-xc schedule sync"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def unescape(value):
    return re.sub(r"\\([,;\\nN])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), value).strip()


def parse_ics(text):
    # Unfold continuation lines (RFC 5545: a line starting with a space continues the previous one).
    text = re.sub(r"\r?\n[ \t]", "", text)
    events, current = [], None
    for line in text.splitlines():
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT" and current is not None:
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            key, value = line.split(":", 1)
            current[key.split(";")[0]] = unescape(value)
    meets = []
    for ev in events:
        raw = ev.get("DTSTART", "")[:8]
        if not raw.isdigit():
            continue
        desc = ev.get("DESCRIPTION", "")
        meets.append({
            "date": f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}",
            "name": ev.get("SUMMARY", "Meet"),
            "location": ev.get("LOCATION", ""),
            "url": desc if desc.startswith("http") else "",
        })
    return sorted(meets, key=lambda m: (m["date"], m["name"]))


def pick_season(sport):
    """Use the season with the soonest upcoming meet; otherwise the most recent season with meets."""
    today = datetime.date.today().isoformat()
    year = datetime.date.today().year
    seasons = {}
    for season in (year + 1, year, year - 1):
        meets = parse_ics(fetch(sport["feed"].format(id=SCHOOL_ID, season=season)))
        if meets:
            seasons[season] = meets
    if not seasons:
        return None, []
    upcoming = {s: min(m["date"] for m in ms if m["date"] >= today)
                for s, ms in seasons.items() if any(m["date"] >= today for m in ms)}
    season = min(upcoming, key=upcoming.get) if upcoming else max(seasons)
    return season, seasons[season]


def main():
    data = {}
    for key, sport in SPORTS.items():
        season, meets = pick_season(sport)
        data[key] = {
            "label": sport["label"],
            "season": season,
            "athleticNet": sport["team"].format(id=SCHOOL_ID, season=season) if season else "",
            "subscribe": sport["feed"].format(id=SCHOOL_ID, season=season).replace("https://", "webcal://") if season else "",
            "meets": meets,
        }

    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    old.pop("updated", None)
    if old == data:
        print("Schedule unchanged.")
        return
    data["updated"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print("Schedule updated:", {k: len(v["meets"]) for k, v in data.items() if isinstance(v, dict)})


if __name__ == "__main__":
    main()
