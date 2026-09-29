// Mobile menu
const menuBtn = document.querySelector('.menu-btn');
const links = document.querySelector('.links');
menuBtn.addEventListener('click', () => {
  const open = links.classList.toggle('open');
  menuBtn.setAttribute('aria-expanded', open);
});
links.querySelectorAll('a').forEach(a => a.addEventListener('click', () => links.classList.remove('open')));

// Schedule filter
const chips = document.querySelectorAll('.chip');
const rows = document.querySelectorAll('.sched tbody tr');
chips.forEach(chip => chip.addEventListener('click', () => {
  chips.forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  const f = chip.dataset.filter;
  rows.forEach(row => {
    const level = row.lastElementChild.textContent;
    const show = f === 'all' || level === 'All' || level.includes(f);
    row.style.display = show ? '' : 'none';
  });
}));
