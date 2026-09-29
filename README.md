# Xavier Track & Cross Country

Website for Xavier High School (NYC) Cross Country and Track & Field: schedule, records, varsity letter standards, venues and coaches.

Static site: `index.html`, `styles.css`, `script.js`.

## Schedule sync

The meet schedule comes from Athletic.net's public team calendar feeds (Xavier (NY), school ID 9479).
`.github/workflows/update-schedule.yml` runs `scripts/update_schedule.py` every 3 hours, writes
`data/schedule.json`, commits it when something changed, and redeploys the site to GitHub Pages.
Run it by hand from the repo's **Actions** tab → *Sync schedule & deploy* → *Run workflow*.
