# Xavier Track & Cross Country

Website for Xavier High School (NYC) Cross Country and Track & Field: schedule, records, varsity letter standards, venues and coaches.

Static site: `index.html`, `styles.css`, `script.js`.

## Schedule sync

The meet schedule comes from Athletic.net's public team calendar feeds (Xavier (NY), school ID 9479).
`.github/workflows/update-schedule.yml` runs `scripts/update_schedule.py` every 3 hours, writes
`data/schedule.json`, commits it when something changed, and redeploys the site to GitHub Pages.
Run it by hand from the repo's **Actions** tab → *Sync schedule & deploy* → *Run workflow*.

## Manual additions

`data/schedule.json` is regenerated on every sync, so don't edit it by hand. To add anything that isn't on
Athletic.net, edit `data/extras.json`; `scripts/update_schedule.py` merges it in on the next sync (or push to `main`).

- **`meets`**: add a meet that's missing from the feed. Each entry needs `sport` (`xc` or `tf`), `season`
  (the year of the season shown on the site), `date` (`YYYY-MM-DD`) and `name`; `location` and `url` are optional.
  On the same date, extras are listed after the feed's meets. Once Athletic.net lists the meet itself (same date,
  and its name contains the extra's name, ignoring case) the manual copy is dropped automatically.
- **`labels`**: attach a badge to any meet, feed or manual, whose name contains `match` (case-insensitive), e.g.
  `{"match": "NXR", "label": "Overnight"}`. "Overnight" shows a crescent-moon badge; other labels show a plain badge.

A missing or malformed `extras.json` (or entry) is skipped with a warning and never breaks the sync.
Preview locally with `python3 scripts/update_schedule.py`.
