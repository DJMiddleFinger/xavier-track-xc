// Mobile menu
const menuBtn = document.querySelector('.menu-btn');
const links = document.querySelector('.links');
menuBtn.addEventListener('click', () => {
  const open = links.classList.toggle('open');
  menuBtn.setAttribute('aria-expanded', open);
});
links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));

// Schedule — data/schedule.json is refreshed from Athletic.net by a GitHub Action
const chips = document.querySelectorAll('.chip[data-sport]');
const body = document.getElementById('sched-body');
const note = document.getElementById('sched-note');
const anetLink = document.getElementById('sched-anet');
const subLink = document.getElementById('sched-sub');
let schedule = null;

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const toDate = iso => { const [y, m, d] = iso.split('-').map(Number); return new Date(y, m - 1, d); };
const fmt = d => d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
// Labels come from data/extras.json via the sync script (e.g. "Overnight"); "Overnight" gets a crescent-moon icon.
const MOON_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
const labelBadge = label => {
  const overnight = String(label).toLowerCase() === 'overnight';
  const title = overnight ? 'Overnight meet' : label;
  return ` <span class="label-badge${overnight ? ' overnight' : ''}" title="${esc(title)}">${overnight ? MOON_ICON : ''}${esc(label)}</span>`;
};

function render(sport) {
  const s = schedule && schedule[sport];
  if (!s || !s.meets.length) {
    body.innerHTML = '<tr><td colspan="3" class="empty">No meets posted on Athletic.net yet.</td></tr>';
    return;
  }
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const nextDate = (s.meets.find(m => toDate(m.date) >= today) || {}).date;
  body.innerHTML = s.meets.map(m => {
    const past = toDate(m.date) < today;
    const cls = past ? 'past' : m.date === nextDate ? 'next' : '';
    const name = m.url ? `<a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.name)}</a>` : esc(m.name);
    const badge = m.date === nextDate ? ' <span class="next-badge">Next</span>' : '';
    const labels = (m.labels || []).map(labelBadge).join('');
    return `<tr class="${cls}"><td>${fmt(toDate(m.date))}</td><td>${name}${badge}${labels}</td><td>${esc(m.location)}</td></tr>`;
  }).join('');
  anetLink.href = s.athleticNet;
  subLink.href = s.subscribe;
  const updated = schedule.updated ? ` · Last change ${new Date(schedule.updated).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : '';
  note.textContent = `${s.season} ${s.label} season · Synced automatically from Athletic.net${updated}`;
}

chips.forEach(chip => chip.addEventListener('click', () => {
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  render(chip.dataset.sport);
}));

fetch('data/schedule.json', { cache: 'no-cache' })
  .then(r => r.json())
  .then(data => { schedule = data; render('xc'); })
  .catch(() => {
    body.innerHTML = '<tr><td colspan="3" class="empty">Couldn\'t load the schedule. <a href="https://www.athletic.net/team/9479/cross-country" target="_blank" rel="noopener">See it on Athletic.net</a>.</td></tr>';
  });
