"""Pull Xavier's meet schedules from Athletic.net's public iCal feeds into data/schedule.json.

Runs in GitHub Actions on a timer. Only rewrites the file when a schedule actually changes.

Hand-maintained additions live in data/extras.json (meets missing from Athletic.net, plus
labels such as "Overnight" attached to meets by name). They are merged in here, so never
edit data/schedule.json by hand; it is regenerated on every sync.
"""
import datetime
import json
import pathlib
import re
import sys
import urllib.request

SCHOOL_ID = 9479  # Xavier (NY) on Athletic.net
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "schedule.json"
EXTRAS = ROOT / "data" / "extras.json"

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


def warn(message):
    print(f"WARNING: {message}", file=sys.stderr)


def load_extras():
    """Read data/extras.json. A missing or malformed file (or entry) is skipped with a warning; it must never break the sync."""
    empty = {"meets": [], "labels": []}
    if not EXTRAS.exists():
        return empty
    try:
        raw = json.loads(EXTRAS.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("top level must be a JSON object")
    except (OSError, ValueError) as err:
        warn(f"ignoring {EXTRAS.name}: {err}")
        return empty

    def entries(field):
        value = raw.get(field, [])
        if not isinstance(value, list):
            warn(f"{EXTRAS.name}: '{field}' must be a list; ignoring it")
            return []
        return value

    def text(entry, field):
        value = entry.get(field, "")
        return value.strip() if isinstance(value, str) else ""

    meets = []
    for entry in entries("meets"):
        if not isinstance(entry, dict):
            warn(f"{EXTRAS.name}: skipping non-object meet {entry!r}")
            continue
        sport, date, name = text(entry, "sport"), text(entry, "date"), text(entry, "name")
        season = entry.get("season")
        if (sport not in SPORTS or not name or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
                or isinstance(season, bool) or not isinstance(season, int)):
            warn(f"{EXTRAS.name}: skipping meet needing a valid sport, season, date (YYYY-MM-DD) and name: {entry!r}")
            continue
        meets.append({"sport": sport, "season": season, "date": date, "name": name,
                      "location": text(entry, "location"), "url": text(entry, "url")})

    labels = []
    for entry in entries("labels"):
        match, label = (text(entry, "match"), text(entry, "label")) if isinstance(entry, dict) else ("", "")
        if not match or not label:
            warn(f"{EXTRAS.name}: skipping label needing 'match' and 'label': {entry!r}")
            continue
        labels.append({"match": match, "label": label})
    return {"meets": meets, "labels": labels}


def apply_extras(key, season, meets, extras):
    """Merge hand-maintained meets for this sport/season into the feed meets, then attach labels."""
    meets = [dict(m) for m in meets]
    for extra in extras["meets"]:
        if extra["sport"] != key or extra["season"] != season:
            continue
        needle = extra["name"].lower()
        # Once Athletic.net lists the meet itself, drop the manual copy so it never shows twice.
        if any(m["date"] == extra["date"] and needle in m["name"].lower() for m in meets):
            continue
        meets.append({"date": extra["date"], "name": extra["name"], "location": extra["location"],
                      "url": extra["url"], "manual": True})
    # Stable sort by date: feed meets keep their (date, name) order and extras follow them on the same day.
    meets.sort(key=lambda m: m["date"])
    for meet in meets:
        labels = []
        for rule in extras["labels"]:
            if rule["match"].lower() in meet["name"].lower() and rule["label"] not in labels:
                labels.append(rule["label"])
        if labels:
            meet["labels"] = labels
    return meets


def main():
    extras = load_extras()
    data = {}
    for key, sport in SPORTS.items():
        season, meets = pick_season(sport)
        meets = apply_extras(key, season, meets, extras)
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
