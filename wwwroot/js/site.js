// site.js — runs on every page

// Stats header (shared across all pages)
async function loadStats() {
  try {
    const d = await fetch('/api/summary').then(r => r.json());
    const chips = document.getElementById('statsChips');
    if (!chips) return;
    chips.innerHTML =
      `<div class="stat-chip"><b>${d.totalConnectors.toLocaleString()}</b> connectors</div>
       <div class="stat-chip"><b>${d.specs}</b> specs</div>`;
  } catch {}
}

// Highlight active nav link
function setActiveNav() {
  const path = window.location.pathname.toLowerCase();
  document.querySelectorAll('.nav-link').forEach(a => {
    const href = a.getAttribute('href').toLowerCase();
    a.classList.toggle('active',
      href === '/' ? path === '/' : path.startsWith(href));
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  setActiveNav();
});
