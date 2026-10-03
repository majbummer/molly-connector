// ConnectorDB — Molly Connector — client-side app logic

let allSpecs = [];

// ── Boot ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  loadSpecs();
  document.getElementById('searchInput')
    .addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

  // Load connector from URL on page load (?pn= param)
  const urlPn = new URLSearchParams(window.location.search).get('pn');
  if (urlPn) {
    document.getElementById('searchInput').value = urlPn;
    loadDetail(urlPn);
  }

  // Handle browser back/forward navigation
  window.addEventListener('popstate', e => {
    const pn = e.state?.pn;
    if (pn) {
      document.getElementById('searchInput').value = pn;
      loadDetail(pn, false); // false = don't push state again
    } else {
      // Back to no connector selected
      document.getElementById('detailPanel').innerHTML = `<div class="empty-state">
        <div class="empty-icon">⚡</div>
        <h2>Select a connector</h2>
        <p>Search for a part number on the left.</p>
      </div>`;
      document.querySelectorAll('.result-item').forEach(el => el.classList.remove('active'));
    }
  });
});

// ── Spec filter dropdowns ─────────────────────────────────────────────────────
async function loadSpecs() {
  allSpecs = await fetchJson('/api/specs') ?? [];
  const specSet = [...new Set(allSpecs.map(s => s.spec))];
  const specSel = document.getElementById('filterSpec');
  specSet.forEach(s => {
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    specSel.appendChild(o);
  });
  specSel.addEventListener('change', updateSeriesFilter);
}

function updateSeriesFilter() {
  const spec = document.getElementById('filterSpec').value;
  const sel  = document.getElementById('filterSeries');
  sel.innerHTML = '<option value="">All Series</option>';
  [...new Set((spec ? allSpecs.filter(s => s.spec === spec) : allSpecs)
    .map(s => s.series))].forEach(sr => {
      if (!sr) return;
      const o = document.createElement('option');
      o.value = sr; o.textContent = sr;
      sel.appendChild(o);
    });
}

// ── Search ────────────────────────────────────────────────────────────────────
async function doSearch() {
  const q      = document.getElementById('searchInput').value.trim();
  const spec   = document.getElementById('filterSpec').value;
  const series = document.getElementById('filterSeries').value;
  const type   = document.getElementById('filterType').value;

  if (!q && !spec && !series && !type) {
    document.getElementById('resultsCount').textContent = 'Enter a search above';
    document.getElementById('resultsList').innerHTML =
      `<div class="no-results"><span class="icon">🔌</span>Enter a part number or select a filter above.</div>`;
    return;
  }

  document.getElementById('resultsCount').innerHTML = '<span class="pulse">Searching…</span>';
  document.getElementById('resultsList').innerHTML =
    '<div class="loading"><div class="spinner"></div>Querying database…</div>';

  const params = new URLSearchParams();
  if (q)      params.set('q', q);
  if (spec)   params.set('spec', spec);
  if (series) params.set('series', series);
  if (type)   params.set('type', type);
  params.set('limit', '100');

  const data = await fetchJson('/api/search?' + params) ?? [];
  renderResults(data, q);
}

function renderResults(rows, q = '') {
  const count = rows.length;
  document.getElementById('resultsCount').innerHTML =
    `Showing <b>${count}</b> result${count !== 1 ? 's' : ''}${count === 100 ? ' (limit)' : ''}`;

  if (!count) {
    document.getElementById('resultsList').innerHTML =
      `<div class="no-results"><span class="icon">🔍</span>No connectors matched.</div>`;
    return;
  }

  document.getElementById('resultsList').innerHTML = rows.map(r => {
    const typeTag = r.connectorType === 'Plug'
      ? `<span class="tag tag-plug">PLUG</span>`
      : r.connectorType === 'Receptacle'
        ? `<span class="tag tag-recep">RECEP</span>`
        : `<span class="tag tag-contacts">${r.connectorType || '?'}</span>`;

    const pnHl = q
      ? r.partNumber.replace(new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'),
          m => `<mark style="background:var(--amber-dim);color:var(--amber);border-radius:2px">${m}</mark>`)
      : r.partNumber;

    return `<div class="result-item" onclick="loadDetail('${esc(r.partNumber)}')" data-pn="${esc(r.partNumber)}">
      <div class="result-pn">${pnHl}</div>
      <div class="result-meta">
        <span class="tag tag-spec">${r.spec || ''}</span>
        ${typeTag}
        <span class="tag tag-contacts">${r.contactCount || '?'} contacts</span>
        ${r.insertArrangement
          ? `<span style="color:var(--text-faint);font-size:10px;font-family:var(--mono)">INS ${r.insertArrangement}</span>`
          : ''}
      </div>
    </div>`;
  }).join('');
}

// ── Detail ────────────────────────────────────────────────────────────────────
async function loadDetail(partNumber, pushState = true) {
  document.querySelectorAll('.result-item').forEach(el =>
    el.classList.toggle('active', el.dataset.pn === partNumber));

  // Update URL so the link is shareable
  if (pushState) {
    const encoded = encodeURIComponent(partNumber);
    const newUrl = `${window.location.pathname}?pn=${encoded}`;
    window.history.pushState({ pn: partNumber }, '', newUrl);
  }

  const panel = document.getElementById('detailPanel');
  panel.innerHTML =
    `<div class="loading"><div class="spinner"></div>Loading ${partNumber}…</div>`;

  const d = await fetchJson('/api/connector/' + encodeURIComponent(partNumber));
  if (!d) {
    panel.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div>
      <h2>Not found</h2><p>${partNumber} is not in the database.</p></div>`;
    return;
  }
  // Update page title for shareability
  document.title = `${d.partNumber} — Molly Connector`;
  renderDetail(d);
}

async function renderDetail(d) {
  const panel = document.getElementById('detailPanel');

  const typeTag = d.connectorType === 'Plug'
    ? `<span class="tag-lg tag-plug">PLUG</span>`
    : d.connectorType === 'Receptacle'
      ? `<span class="tag-lg tag-recep">RECEPTACLE</span>`
      : `<span class="tag-lg tag-contacts">${d.connectorType || ''}</span>`;

  // Mating connectors
  let matesHtml = '';
  if (d.matingConnectorDetails?.length) {
    const cards = d.matingConnectorDetails.map(m => {
      const missing = m.notes === 'not_found';
      const tt = m.connectorType === 'Plug'
        ? `<span class="tag tag-plug">PLUG</span>`
        : m.connectorType === 'Receptacle'
          ? `<span class="tag tag-recep">RECEP</span>` : '';
      return `<div class="mate-card${missing ? ' mate-missing' : ''}"
                   onclick="loadDetail('${esc(m.partNumber)}')">
        <div style="flex:1">
          <div class="mate-pn">${m.partNumber}
            ${missing ? '<span style="font-size:10px;color:var(--text-faint);font-weight:300;margin-left:6px">not in DB</span>' : ''}
          </div>
          <div class="mate-meta">
            ${tt}
            ${m.spec ? `<span style="font-size:11px;color:var(--text-dim)">${m.spec} · ${m.shellStyle || ''} · ${m.contactCount || '?'} contacts</span>` : ''}
          </div>
        </div>
        <span class="mate-arrow">→</span>
      </div>`;
    }).join('');
    matesHtml = `<div class="section">
      <div class="section-header">
        <span class="section-title">Mating Connectors</span>
        <span class="section-badge">${d.matingConnectorDetails.length}</span>
      </div>
      <div class="mates-list">${cards}</div>
    </div>`;
  }

  // Fixtures
  let fixtureHtml = '';
  if (d.fixtures?.length) {
    const rows = d.fixtures.map(f => `<tr>
      <td>${f.fixtureId || ''}</td>
      <td>${f.assemblyConnector || ''}</td>
      <td>${f.matingConnector || ''}</td>
      <td>Box ${f.boxNumber}-${f.boxSection} Slot ${f.slotPosition}</td>
      <td>${f.fixtureStatus || ''}</td>
      <td>${f.lastVerifiedDate || '—'}</td>
    </tr>`).join('');
    fixtureHtml = `<div class="section">
      <div class="section-header">
        <span class="section-title">Fixture Inventory</span>
        <span class="section-badge">${d.fixtures.length}</span>
      </div>
      <table class="fixture-table">
        <thead><tr><th>ID</th><th>Assembly</th><th>Mating</th><th>Location</th><th>Status</th><th>Verified</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }

  // Tooling
  let toolHtml = '';
  if (d.contactTooling) {
    const t = d.contactTooling;
    toolHtml = `<div class="section">
      <div class="section-header">
        <span class="section-title">Contact Tooling</span>
        <span style="font-family:var(--mono);font-size:10px;color:var(--text-dim);margin-left:auto">${t.contactPartNumber || ''}</span>
      </div>
      <div class="tooling-grid">
        <div class="tool-item"><div class="tool-label">Crimper</div><div class="tool-value bold">${t.crimperTool || '—'}</div></div>
        <div class="tool-item"><div class="tool-label">Positioner</div><div class="tool-value bold">${t.positioner || '—'}</div></div>
        <div class="tool-item"><div class="tool-label">Locator / Die</div><div class="tool-value">${t.locator || '—'}</div></div>
        <div class="tool-item"><div class="tool-label">Tool Family</div><div class="tool-value">${t.toolFamily || '—'}</div></div>
        <div class="tool-item"><div class="tool-label">Inserter</div><div class="tool-value">${t.inserterTool || '—'}</div></div>
        <div class="tool-item"><div class="tool-label">Extractor</div><div class="tool-value">${t.extractorTool || '—'}</div></div>
        <div class="tool-item"><div class="tool-label">Wire Gauge</div><div class="tool-value">${t.wireGaugeRange || '—'} AWG</div></div>
        <div class="tool-item"><div class="tool-label">Strip Length</div><div class="tool-value">${t.stripLengthMin || '?'}"–${t.stripLengthMax || '?'}" (def ${t.defaultStripLength || '?'}")</div></div>
      </div>
      ${t.notes ? `<div class="notes-box">${t.notes}</div>` : ''}
      <div class="correction-bar">
        <span class="correction-hint">⚠ Contact or tooling data incorrect for this connector?</span>
        <button class="correction-btn" onclick="showCorrectionForm('${esc(d.partNumber)}', '${esc(t.contactPartNumber||'')}')">Suggest Correction</button>
      </div>
    </div>`;
  }

  // Decode panel
  const decodeHtml = await decodePartNumber(d.partNumber);

  const permalinkUrl = window.location.origin + '/connector/' + encodeURIComponent(d.partNumber).replace(/%2F/g, '/');
  panel.innerHTML = `<div>
    <div class="detail-permalink">
      <a href="${permalinkUrl}" target="_blank" class="permalink-btn">🔗 Permalink</a>
      <button class="permalink-copy-btn" onclick="copyPermalink('${esc(d.partNumber)}')">Copy link</button>
    </div>
    <div class="detail-pn">${d.partNumber}</div>
    <div class="detail-tags">
      ${typeTag}
      <span class="tag-lg tag-spec" style="font-family:var(--mono);font-size:11px;padding:3px 8px;border-radius:4px">${d.spec || ''}</span>
      <span class="tag-lg" style="font-family:var(--mono);font-size:11px;padding:3px 8px;border-radius:4px;background:var(--surface3);border:1px solid var(--border)">${d.series || ''}</span>
    </div>

    ${decodeHtml}

    <div class="section">
      <div class="section-header"><span class="section-title">Core Specifications</span></div>
      <div class="spec-grid">
        ${specCell('Shell Style',           d.shellStyle)}
        ${specCell('Mounting Type',         d.mountingType)}
        ${specCell('Insert Arrangement',    d.insertArrangement, true)}
        ${specCell('Contact Count',         d.contactCount,      true)}
        ${specCell('Contact Size',          d.contactSize)}
        ${specCell('Contact Type',          d.contactType === 'P' ? 'P — Pin (male)' : d.contactType === 'S' ? 'S — Socket (female)' : d.contactType)}
        ${specCell('Shell Size (Letter)',   d.shellSizeLetter)}
        ${specCell('Shell Size (Numeric)', d.shellSizeNumeric)}
        ${specCell('Keying',               d.keying)}
        ${specCell('Class',                d.class)}
        ${specCell('Prefix',               d.prefix)}
        ${specCell('Termination',          d.terminationType)}
      </div>
    </div>

    <div class="section">
      <div class="section-header"><span class="section-title">Physical &amp; Environmental</span></div>
      <div class="spec-grid">
        ${specCell('Shell Material',        d.shellMaterial)}
        ${specCell('Shell Plating',         d.shellPlating)}
        ${specCell('Environment',           d.environmentType)}
        ${specCell('Shielding',            d.shielding)}
        ${specCell('Compatible Sizes',     d.compatibleContactSizes)}
        ${specCell('Notes',                d.notes)}
      </div>
    </div>

    ${matesHtml}
    ${fixtureHtml}
    ${toolHtml}
  </div>`;
}

// ── Part Number Decode ────────────────────────────────────────────────────────
async function decodePartNumber(partNumber) {
  const result = await fetchJson('/api/decode/' + encodeURIComponent(partNumber));
  if (!result?.fields?.length) return '';

  const colors = ['#f5a623','#4eb4f5','#2dd67a','#b87af5','#f5883a','#f55f5f','#56d6c8','#e0a0f5'];

  const fieldCards = result.fields.map((f, i) => `
    <div class="decode-field" style="animation-delay:${i * 40}ms">
      <div class="decode-chars" style="color:${colors[i % colors.length]}">${f.characters}</div>
      <div class="decode-arrow">↓</div>
      <div class="decode-label">${f.fieldName}</div>
      <div class="decode-desc">${f.description}</div>
    </div>`).join('');

  // Build color-highlighted PN string
  let pn = result.partNumber;
  let highlighted = '';
  let cursor = 0;
  result.fields.forEach((f, i) => {
    const chars = f.characters.toUpperCase();
    const idx   = pn.toUpperCase().indexOf(chars, cursor);
    if (idx >= 0) {
      if (idx > cursor)
        highlighted += `<span class="decode-pn-plain">${pn.slice(cursor, idx)}</span>`;
      highlighted += `<span class="decode-pn-seg"
        style="color:${colors[i % colors.length]};border-color:${colors[i % colors.length]}55"
        title="${f.fieldName}: ${f.description}">${pn.slice(idx, idx + chars.length)}</span>`;
      cursor = idx + chars.length;
    }
  });
  if (cursor < pn.length)
    highlighted += `<span class="decode-pn-plain">${pn.slice(cursor)}</span>`;

  const warningHtml = result.warning
    ? `<div class="decode-warning">⚠ ${result.warning}</div>` : '';

  return `<div class="section">
    <div class="section-header">
      <span class="section-title">Part Number Decode</span>
      <span style="font-family:var(--mono);font-size:10px;color:var(--text-dim);margin-left:auto">${result.specName}</span>
    </div>
    <div class="decode-panel">
      <div class="decode-pn-display">${highlighted}</div>
      <div class="decode-fields">${fieldCards}</div>
      ${warningHtml}
    </div>
  </div>`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function specCell(label, value, highlight = false) {
  const v = value !== null && value !== undefined && value !== ''
    ? `<div class="spec-value${highlight ? ' highlight' : ''}">${value}</div>`
    : `<div class="spec-value" style="color:var(--text-faint)">—</div>`;
  return `<div class="spec-cell"><div class="spec-label">${label}</div>${v}</div>`;
}

function esc(str) { return String(str).replace(/'/g, "\\'"); }

async function fetchJson(url) {
  try {
    const r = await fetch(url);
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}


// ── Corrections ───────────────────────────────────────────────────────────────
function showCorrectionForm(partNumber, currentContact) {
  const existing = document.getElementById('correctionForm');
  if (existing) { existing.remove(); return; }

  const form = document.createElement('div');
  form.id = 'correctionForm';
  form.className = 'correction-form';
  form.innerHTML = `
    <div class="correction-form-inner">
      <div class="correction-form-title">Suggest a Correction</div>
      <div class="correction-form-sub">For: <b>${partNumber}</b></div>
      <div class="cf-row">
        <label>Field</label>
        <select id="cfField">
          <option value="contact_part_number">Contact Part Number</option>
          <option value="crimper_tool">Crimper Tool</option>
          <option value="positioner">Positioner</option>
          <option value="locator">Locator / Die</option>
          <option value="wire_gauge_range">Wire Gauge Range</option>
          <option value="other">Other</option>
        </select>
      </div>
      <div class="cf-row">
        <label>Current Value</label>
        <input type="text" id="cfOld" value="${currentContact}" placeholder="Current value">
      </div>
      <div class="cf-row">
        <label>Correct Value</label>
        <input type="text" id="cfNew" placeholder="What it should be">
      </div>
      <div class="cf-row">
        <label>Notes</label>
        <input type="text" id="cfNotes" placeholder="Source, drawing number, etc. (optional)">
      </div>
      <div class="cf-actions">
        <span class="cf-saved" id="cfSaved"></span>
        <button class="cf-cancel" onclick="document.getElementById('correctionForm').remove()">Cancel</button>
        <button class="cf-submit" onclick="submitCorrection('${partNumber}')">Submit</button>
      </div>
    </div>`;

  // Insert after tooling section
  const toolSection = document.querySelector('.section:last-child');
  toolSection.after(form);
  document.getElementById('cfNew').focus();
}

async function submitCorrection(partNumber) {
  const field    = document.getElementById('cfField').value;
  const oldVal   = document.getElementById('cfOld').value;
  const newVal   = document.getElementById('cfNew').value.trim();
  const notes    = document.getElementById('cfNotes').value.trim();

  if (!newVal) { document.getElementById('cfNew').focus(); return; }

  const btn = document.querySelector('.cf-submit');
  btn.disabled = true;

  const res = await fetch('/api/correction', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      PartNumber: partNumber, FieldName: field,
      OldValue: oldVal, CorrectedValue: newVal,
      Notes: notes || null
    })
  });

  if (res.ok) {
    const saved = document.getElementById('cfSaved');
    saved.textContent = '✓ Submitted — thank you!';
    saved.style.color = 'var(--green)';
    setTimeout(() => document.getElementById('correctionForm')?.remove(), 2000);
  } else {
    btn.disabled = false;
  }
}

// ── Permalink copy ────────────────────────────────────────────────────────────
function copyPermalink(partNumber) {
  const url = window.location.origin + '/connector/' + encodeURIComponent(partNumber).replace(/%2F/g, '/');
  navigator.clipboard.writeText(url).then(() => {
    const btn = document.querySelector('.permalink-copy-btn');
    if (!btn) return;
    const orig = btn.textContent;
    btn.textContent = '✓ Copied!';
    btn.style.color = 'var(--green)';
    setTimeout(() => { btn.textContent = orig; btn.style.color = ''; }, 2000);
  });
}
