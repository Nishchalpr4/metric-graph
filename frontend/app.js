/* ============================================================
   Causal Financial Knowledge Graph — Frontend Logic
   ============================================================ */

// CHANGE THIS to your deployed backend URL:
// Render example: https://metric-graph-xxxxx.onrender.com
const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost' 
  ? window.location.origin.replace('pages.dev', 'onrender.com')  // Auto-detect if on Cloudflare
  : 'http://127.0.0.1:8001';  // Local dev

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', async () => {
  // Initialization if needed
});

// ─────────────────────────────────────────────────────────────────────────────
// Actions
// ─────────────────────────────────────────────────────────────────────────────

async function seedDatabase() {
  showLoading('Seeding database (drops + recreates tables)…');
  try {
    const result = await apiFetch('/api/seed', { method: 'POST' });
    showContent(`
      <div class="card">
        <div class="card-title">Database Seeded Successfully</div>
        <pre style="color:var(--green);font-size:12px;">${JSON.stringify(result, null, 2)}</pre>
        <p style="margin-top:12px;color:var(--muted);font-size:12px;">
          You can now ask questions about your metrics.
        </p>
      </div>
    `);
  } catch (e) {
    showError(e.message);
  }
}

async function runNLQuery() {
  const q = document.getElementById('nlQuery').value.trim();
  if (!q) return;
  showLoading(`Analysing: "${q}"…`);
  try {
    const result = await apiFetch('/api/query', {
      method: 'POST',
      body: JSON.stringify({ query: q }),
    });
    await renderQueryResult(result, q);
  } catch (e) {
    showError(e.message);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Rendering
// ─────────────────────────────────────────────────────────────────────────────

async function renderQueryResult(data, raw_query) {
  if (data.result && data.result.error) {
    showError(data.result.error);
    return;
  }

  const type = data.result && data.result.type;

  if (type === 'trend') {
    renderTrend(data.result, data.warnings || []);
    return;
  }
  if (type === 'segment_breakdown') {
    renderSegmentBreakdown(data.result, data.warnings || []);
    return;
  }
  // Default: explain_change result
  await renderDirectResult(data.result, data.parsed && data.parsed.segment, data.warnings || [], raw_query);
}

async function renderDirectResult(result, segment, warnings = [], query_text = '') {
  if (!result || result.error) { showError((result && result.error) || 'No result returned.'); return; }

  const qm  = result.query_meta || {};
  const ch  = result.change || {};
  const isUp = (ch.direction || '') === 'increased';
  const pill = isUp ? 'up' : 'down';
  const arrow = isUp ? '▲' : '▼';
  const sign  = isUp ? '+' : '';

  const warnHtml = (warnings && warnings.length)
    ? `<div class="error-banner" style="background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.3);color:var(--yellow);font-size:11px;padding:8px 10px;">
        ${warnings.map(w => `⚠ ${escHtml(w)}`).join('<br/>')}
      </div>` : '';

  const allDrivers = result.drivers || [];

  const driversHtml = allDrivers.length ? `
    <div class="card" style="padding:10px 12px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--green);margin-bottom:8px;">Root Cause Analysis</div>
      <div class="driver-list">${allDrivers.map((d, i) => renderDriverCard(d, i, ch.absolute, false)).join('')}</div>
    </div>` : '';

  const eventsHtml = (result.period_events || []).length ? `
    <div class="card" style="padding:10px 12px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--yellow);margin-bottom:8px;">Business Events · ${escHtml(qm.period || '')}</div>
      <div class="events-list">${result.period_events.map(renderEvent).join('')}</div>
    </div>` : '';

  // Set 2-panel mode — graph LEFT, analysis RIGHT
  const contentEl = document.getElementById('content');
  contentEl.classList.add('two-panel-mode');
  contentEl.innerHTML = `
    <div class="two-panel">
      <div class="graph-panel" id="graphPanel">
        <div class="graph-panel-bar">
          <span>📊 Metric Graph</span>
          <span class="graph-legend" style="margin:0;gap:10px;">
            <div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div>Base</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--accent)"></div>Derived</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>+causal</div>
            <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>−causal</div>
          </span>
          <span style="margin-left:auto;font-size:10px;color:var(--muted);">Drag nodes · scroll to zoom</span>
        </div>
        <div class="graph-svg-wrap" id="graphSvgWrap">
          <div class="loading"><div class="spinner"></div><span>Loading…</span></div>
        </div>
        <div id="nodeTooltip" class="node-tooltip"></div>
      </div>

      <div class="analysis-panel">
        ${warnHtml}
        ${query_text ? `<div style="font-size:12px;color:var(--muted);font-style:italic;padding:4px 0 6px;border-bottom:1px solid var(--border);">"${escHtml(query_text)}"</div>` : ''}

        <div class="card" style="padding:12px 14px;">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:6px;">${escHtml(qm.display_name || qm.metric || '')}</div>
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
            <div style="font-size:28px;font-weight:700;">${fmtVal(ch.current_value, qm.unit)}</div>
            <div>
              <div class="change-pill ${pill}">${arrow} ${sign}${fmtVal(ch.absolute, qm.unit)} (${sign}${(ch.pct||0).toFixed(1)}%)</div>
              <div style="font-size:11px;color:var(--muted);margin-top:3px;">${escHtml(qm.period)} vs ${escHtml(qm.compare_period)} · ${escHtml(segment || qm.segment || '')}</div>
            </div>
            <div style="margin-left:auto;text-align:right;">
              <div style="font-size:10px;color:var(--muted);">Prev</div>
              <div style="font-size:18px;font-weight:600;">${fmtVal(ch.prev_value, qm.unit)}</div>
            </div>
          </div>
        </div>

        ${result.summary ? `<div style="font-size:12px;line-height:1.65;color:var(--text);border-left:3px solid var(--accent);padding:6px 10px;background:var(--surface);border-radius:0 6px 6px 0;">${escHtml(result.summary)}</div>` : ''}

        ${driversHtml}
        ${eventsHtml}
      </div>
    </div>`;

  await loadGraphInPanel();
}

// ─────────────────────────────────────────────────────────────────────────────
// Graph: load into left panel with fully draggable nodes
// ─────────────────────────────────────────────────────────────────────────────
async function loadGraphInPanel() {
  const wrap = document.getElementById('graphSvgWrap');
  if (!wrap) return;
  try {
    const data = await apiFetch('/api/graph');
    const nodes = data.nodes || [];
    const edges = data.edges || [];

    const W = wrap.clientWidth  || 600;
    const H = wrap.clientHeight || 500;

    const base   = nodes.filter(n => n.is_base);
    const der    = nodes.filter(n => !n.is_base);
    const opDer  = der.filter(n => n.category === 'Operational');
    const usDer  = der.filter(n => n.category === 'User');
    const finDer = der.filter(n => n.category === 'Financial');
    const finMain = finDer.filter(n => n.id !== 'revenue');
    const finTop  = finDer.filter(n => n.id === 'revenue');

    const pos = {};
    const mid = H / 2;
    const sp  = 58; // vertical spacing between nodes

    const place = (list, xFrac) => list.forEach((n, i) => {
      pos[n.id] = {
        x: Math.round(W * xFrac),
        y: Math.round(mid + (i - (list.length - 1) / 2) * sp)
      };
    });
    place(base,    0.07);
    place(opDer,   0.27);
    place(usDer,   0.47);
    place(finMain, 0.68);
    place(finTop,  0.91);

    // Edges (behind nodes)
    const edgesSvg = edges.map(e => {
      const s = pos[e.source], t = pos[e.target];
      if (!s || !t) return '';
      const col = e.direction === 'positive' ? '#22c55e' : '#ef4444';
      const sw  = e.relationship_type === 'formula_dependency' ? 2.5 : 1.5;
      return `<line id="edge_${e.source}_${e.target}" x1="${s.x+36}" y1="${s.y}" x2="${t.x-36}" y2="${t.y}" stroke="${col}" stroke-width="${sw}" opacity="0.55" stroke-linecap="round"/>`;
    }).join('');

    // Nodes (in front)
    const nodesSvg = nodes.map(n => {
      const p = pos[n.id];
      if (!p) return '';
      const label  = (n.display_name || n.id).split(' ').slice(0, 2).join(' ');
      const fill   = n.is_base ? '#f59e0b' : '#818cf8';
      const stroke = n.is_base ? '#fcd34d' : '#c4b5fd';
      return `<g id="node_${n.id}" class="draggable-node" data-nodeid="${n.id}"
                 transform="translate(${p.x},${p.y})" style="cursor:grab;">
        <rect x="-36" y="-15" width="72" height="30" rx="6"
              fill="${fill}" opacity="0.9" stroke="${stroke}" stroke-width="2"/>
        <text y="-3" text-anchor="middle" font-size="8.5" font-weight="700" fill="#fff"
              font-family="Inter,sans-serif" pointer-events="none">${escHtml(label)}</text>
        <text y="8" text-anchor="middle" font-size="6.5" fill="rgba(255,255,255,0.8)"
              font-family="Inter,sans-serif" pointer-events="none">${escHtml(n.unit)}</text>
      </g>`;
    }).join('');

    wrap.innerHTML = `<svg id="metricSvg" width="${W}" height="${H}"
        style="display:block;width:100%;height:100%;">
      <g id="viewport">
        <g id="edgeLayer">${edgesSvg}</g>
        <g id="nodeLayer">${nodesSvg}</g>
      </g>
    </svg>`;

    window._graphData = { nodes, edges };
    window._nodePos   = pos;
    initDraggableGraph(document.getElementById('metricSvg'), pos, edges, nodes);
  } catch (e) {
    wrap.innerHTML = `<div class="error-banner" style="margin:16px;">Failed to load graph: ${escHtml(e.message)}</div>`;
  }
}

function initDraggableGraph(svg, pos, edges, nodes) {
  let drag = null, sx = 0, sy = 0, nx = 0, ny = 0, scale = 1;
  const vp = svg.querySelector('#viewport');

  svg.addEventListener('mousedown', e => {
    const g = e.target.closest('.draggable-node');
    if (!g) return;
    e.preventDefault();
    drag = g.dataset.nodeid;
    sx = e.clientX; sy = e.clientY;
    nx = pos[drag].x; ny = pos[drag].y;
  });

  svg.addEventListener('mousemove', e => {
    if (!drag) return;
    const x = nx + (e.clientX - sx) / scale;
    const y = ny + (e.clientY - sy) / scale;
    pos[drag] = { x, y };

    const gEl = svg.querySelector(`#node_${drag}`);
    if (gEl) gEl.setAttribute('transform', `translate(${x},${y})`);

    edges.forEach(ed => {
      const ln = svg.querySelector(`#edge_${ed.source}_${ed.target}`);
      if (!ln) return;
      if (ed.source === drag) { ln.setAttribute('x1', x + 36); ln.setAttribute('y1', y); }
      if (ed.target === drag) { ln.setAttribute('x2', x - 36); ln.setAttribute('y2', y); }
    });
  });

  svg.addEventListener('mouseup',   () => { drag = null; });
  svg.addEventListener('mouseleave',() => { drag = null; });

  // Scroll to zoom
  svg.addEventListener('wheel', e => {
    e.preventDefault();
    scale = Math.max(0.3, Math.min(3, scale * (e.deltaY > 0 ? 0.9 : 1.1)));
    if (vp) vp.setAttribute('transform', `scale(${scale})`);
  }, { passive: false });

  // Click → tooltip
  svg.addEventListener('click', e => {
    if (drag) return;
    const g   = e.target.closest('.draggable-node');
    const tip = document.getElementById('nodeTooltip');
    if (!g) { if (tip) tip.style.display = 'none'; return; }
    const nid  = g.dataset.nodeid;
    const node = nodes.find(n => n.id === nid);
    if (!node || !tip) return;
    const ins  = edges.filter(ed => ed.target === nid);
    const outs = edges.filter(ed => ed.source === nid);
    tip.style.display = 'block';
    tip.style.pointerEvents = 'all';
    tip.innerHTML = `
      <button onclick="document.getElementById('nodeTooltip').style.display='none'"
              style="float:right;background:none;border:none;color:var(--muted);cursor:pointer;font-size:15px;line-height:1;">×</button>
      <div style="font-weight:700;color:var(--text);margin-bottom:3px;font-size:13px;">${escHtml(node.display_name)}</div>
      <div style="font-size:10px;color:var(--muted);margin-bottom:6px;">${escHtml(node.unit)} · ${escHtml(node.category)}</div>
      ${ins.length ? `<div style="font-size:10px;color:var(--yellow);">← inputs: ${ins.map(ed => escHtml(ed.source)).join(', ')}</div>` : ''}
      ${outs.length ? `<div style="font-size:10px;color:var(--accent2);margin-top:2px;">→ drives: ${outs.map(ed => escHtml(ed.target)).join(', ')}</div>` : ''}
      ${node.description ? `<div style="font-size:10px;color:var(--muted);margin-top:4px;">${escHtml(node.description)}</div>` : ''}`;
    const rect = svg.getBoundingClientRect();
    const cx = e.clientX - rect.left, cy = e.clientY - rect.top;
    tip.style.left = `${Math.min(cx + 10, rect.width  - 250)}px`;
    tip.style.top  = `${Math.max(cy - 40, 8)}px`;
  });
}



function renderDriverCard(driver, idx, totalChange, showSubDrivers = false) {
  const isFormula = driver.relationship_type === 'formula_dependency';
  const hasContrib = driver.contribution !== null && driver.contribution !== undefined;
  const pct = hasContrib ? driver.contribution_pct : null;
  const pctAbs = pct !== null ? Math.abs(pct) : Math.abs(driver.change_pct || 0);
  const barPct = Math.min(pctAbs, 100);
  const isPos = driver.direction === 'positive'
    ? (driver.change >= 0)
    : (driver.change < 0);  // causal: positive direction + metric went up = good
  const isContribPos = hasContrib ? driver.contribution >= 0 : driver.change >= 0;
  const barClass = isContribPos ? 'pos' : 'neg';
  const pctDisplay = pct !== null
    ? `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`
    : `${driver.change >= 0 ? '+' : ''}${(driver.change_pct || 0).toFixed(1)}%`;
  const pctColorClass = isContribPos ? 'pos' : 'neg';

  const id = `driver-${idx}-${Math.random().toString(36).slice(2,6)}`;

  let subHtml = '';
  if (showSubDrivers && driver.sub_drivers && driver.sub_drivers.length) {
    subHtml = `<div class="sub-drivers">
      <div style="font-size:11px;color:var(--muted);margin-bottom:4px;">↳ Sub-drivers:</div>
      ${driver.sub_drivers.map(sd => renderSubDriver(sd)).join('')}
    </div>`;
  }

  return `
    <div class="driver-item">
      <div class="driver-header" onclick="toggleDriver('${id}')">
        <span class="driver-toggle" id="toggle-${id}">▶</span>
        <span class="driver-name">${escHtml(driver.display_name || driver.metric)}</span>
        <span class="driver-type-badge ${isFormula ? 'badge-formula' : 'badge-causal'}">
          ${isFormula ? 'formula' : 'causal'}
        </span>
        <div class="bar-wrap">
          <div class="bar-bg"><div class="bar-fill ${barClass}" style="width:${barPct}%"></div></div>
        </div>
        <span class="driver-pct ${pct !== null ? pctColorClass : 'qualitative'}">${pctDisplay}</span>
      </div>
      <div class="driver-body" id="${id}">
        <div class="driver-values">
          <span>${escHtml(driver.prev_value !== undefined ? fmtVal(driver.prev_value, driver.unit) : 'N/A')}</span>
          <span style="color:var(--muted)">→</span>
          <span>${escHtml(driver.current_value !== undefined ? fmtVal(driver.current_value, driver.unit) : 'N/A')}</span>
          <span style="color:var(--muted)">|</span>
          <span class="${isContribPos ? 'pos' : 'neg'}" style="color:${isContribPos ? 'var(--green)' : 'var(--red)'}">
            ${driver.change >= 0 ? '+' : ''}${fmtVal(driver.change, driver.unit)}
            (${driver.change_pct >= 0 ? '+' : ''}${(driver.change_pct || 0).toFixed(1)}%)
          </span>
          ${hasContrib ? `<span style="color:var(--muted)">·</span>
          <span style="font-size:11px;color:var(--muted)">
            Contribution: ${isContribPos ? '+' : ''}${fmtVal(driver.contribution, '')} (${pctDisplay})
          </span>` : ''}
        </div>
        ${driver.explanation ? `<div class="driver-explanation">${escHtml(driver.explanation)}</div>` : ''}
        ${subHtml}
      </div>
    </div>
  `;
}

function renderSubDriver(sd) {
  const isPos = sd.change >= 0;
  return `<div class="sub-driver">
    <span class="sub-driver-name">${escHtml(sd.display_name || sd.metric)}</span>
    <span class="sub-driver-change ${isPos ? 'pos' : 'neg'}" style="margin-left:8px;color:${isPos ? 'var(--green)' : 'var(--red)'}">
      ${isPos ? '▲' : '▼'} ${isPos ? '+' : ''}${(sd.change_pct || 0).toFixed(1)}%
    </span>
    <span class="driver-type-badge ${sd.relationship_type === 'formula_dependency' ? 'badge-formula' : 'badge-causal'}" style="margin-left:8px;">
      ${sd.relationship_type === 'formula_dependency' ? 'formula' : 'causal'}
    </span>
    ${sd.explanation ? `<div class="sub-driver-explanation">${escHtml(sd.explanation)}</div>` : ''}
    ${sd.sub_drivers && sd.sub_drivers.length
      ? `<div class="sub-drivers">${sd.sub_drivers.map(s2 => renderSubDriver(s2)).join('')}</div>`
      : ''}
  </div>`;
}

function renderEvent(ev) {
  const isPos = ev.direction === 'positive';
  const metrics = (ev.affected_metrics || []).map(m => `<span>${escHtml(m)}</span>`).join('');
  return `<div class="event-item ${isPos ? '' : 'neg'}">
    <div>
      <span class="event-name">${escHtml(ev.event_name)}</span>
      <span class="event-magnitude">${escHtml(ev.magnitude || '')}</span>
      <span style="font-size:12px;margin-left:8px;color:${isPos ? 'var(--green)' : 'var(--red)'}">
        ${isPos ? '▲ positive impact' : '▼ negative impact'}
      </span>
    </div>
    ${ev.affected_metrics && ev.affected_metrics.length
      ? `<div class="event-metrics" style="margin-top:6px;">${metrics}</div>` : ''}
    <div class="event-explanation">${escHtml(ev.explanation || '')}</div>
  </div>`;
}

function renderTrend(result, warnings) {
  const data = result.data || [];
  if (!data.length) { showError('No trend data available.'); return; }
  const maxVal = Math.max(...data.map(d => d.value), 0.001);

  let barHtml = data.map(d => {
    const h = Math.max(4, Math.round((d.value / maxVal) * 140));
    return `<div class="chart-bar-wrap">
      <div class="chart-bar" style="height:${h}px;">
        <div class="chart-tooltip">${escHtml(d.period)}: ${fmtVal(d.value, result.unit)}</div>
      </div>
      <div class="chart-bar-label">${escHtml(d.period)}</div>
    </div>`;
  }).join('');

  const warnHtml = warnings.length
    ? `<div class="error-banner" style="background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.3);color:var(--yellow);margin-bottom:12px;">
        ${warnings.map(w => `⚠ ${escHtml(w)}`).join('<br/>')}
      </div>` : '';

  showContent(`
    ${warnHtml}
    <div class="card">
      <div class="card-title">${escHtml(result.display_name)} — Trend · ${escHtml(result.segment)}</div>
      <div class="trend-chart">
        <div class="chart-bars">${barHtml}</div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Data Table</div>
      <table style="width:100%;border-collapse:collapse;font-size:12px;">
        <thead>
          <tr>
            <th style="text-align:left;padding:6px;color:var(--muted);border-bottom:1px solid var(--border)">Period</th>
            <th style="text-align:right;padding:6px;color:var(--muted);border-bottom:1px solid var(--border)">Value</th>
            <th style="text-align:right;padding:6px;color:var(--muted);border-bottom:1px solid var(--border)">QoQ Δ</th>
          </tr>
        </thead>
        <tbody>
          ${data.map((d, i) => {
            const prev = i > 0 ? data[i-1].value : null;
            const delta = prev !== null ? d.value - prev : null;
            const isPos = delta !== null && delta >= 0;
            return `<tr>
              <td style="padding:6px;border-bottom:1px solid var(--border)">${escHtml(d.period)}</td>
              <td style="text-align:right;padding:6px;border-bottom:1px solid var(--border)">${fmtVal(d.value, result.unit)}</td>
              <td style="text-align:right;padding:6px;border-bottom:1px solid var(--border);color:${delta === null ? 'var(--muted)' : isPos ? 'var(--green)' : 'var(--red)'}">
                ${delta === null ? '—' : `${isPos ? '+' : ''}${fmtVal(delta, result.unit)}`}
              </td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  `);
}

function renderSegmentBreakdown(result, warnings) {
  const data = result.data || [];
  const maxV = Math.max(...data.map(d => d.value), 0.001);
  const segColors = { 'Food Delivery': '', 'Grocery Delivery': 'grocery' };
  const warnHtml = warnings.length
    ? `<div class="error-banner" style="background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.3);color:var(--yellow);margin-bottom:12px;">
        ${warnings.map(w => `⚠ ${escHtml(w)}`).join('<br/>')}
      </div>` : '';

  showContent(`
    ${warnHtml}
    <div class="card">
      <div class="card-title">${escHtml(result.display_name)} — Segment Breakdown · ${escHtml(result.period)}</div>
      <div class="segment-bars">
        ${data.map(d => `
          <div class="seg-bar-row">
            <div class="seg-name">${escHtml(d.segment)}</div>
            <div class="seg-bar-bg">
              <div class="seg-bar-fill ${segColors[d.segment] || ''}" style="width:${(d.value/maxV*100).toFixed(1)}%"></div>
            </div>
            <div class="seg-val">${fmtVal(d.value, result.unit)} <span style="color:var(--muted)">(${d.share_pct}%)</span></div>
          </div>
        `).join('')}
      </div>
    </div>
  `);
}

}

async function loadGraphExplorerEmbedded() {
  await loadGraphInPanel();
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Utilities
// ─────────────────────────────────────────────────────────────────────────────

function toggleDriver(id) {
  const body = document.getElementById(id);
  const toggle = document.getElementById('toggle-' + id);
  if (!body) return;
  const open = body.classList.toggle('open');
  if (toggle) toggle.textContent = open ? '▼' : '▶';
}

function showLoading(msg = 'Analysing…') {
  const el = document.getElementById('content');
  el.classList.remove('two-panel-mode');
  el.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <span>${escHtml(msg)}</span>
    </div>`;
}

function showError(msg) {
  const el = document.getElementById('content');
  el.classList.remove('two-panel-mode');
  el.innerHTML = `<div class="error-banner" style="margin:24px;">Error: ${escHtml(msg)}</div>`;
}

function showContent(html) {
  const el = document.getElementById('content');
  el.classList.remove('two-panel-mode');
  el.innerHTML = html;
}


// ─────────────────────────────────────────────────────────────────────────────
// Formatting
// ─────────────────────────────────────────────────────────────────────────────

function fmtVal(val, unit) {
  if (val === null || val === undefined) return 'N/A';
  const n = Number(val);
  if (unit === '₹B') return `₹${n.toFixed(2)}B`;
  if (unit === '₹')  return `₹${Math.round(n).toLocaleString()}`;
  if (unit === '%')  return `${n.toFixed(2)}%`;
  if (unit === 'M')  return `${n.toFixed(1)}M`;
  if (unit === 'K')  return `${n.toFixed(0)}K`;
  if (unit === 'items') return `${n.toFixed(1)} items`;
  if (unit === 'orders/user') return `${n.toFixed(2)}x`;
  if (unit === 'index') return n.toFixed(1);
  return n.toFixed(2);
}

function escHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─────────────────────────────────────────────────────────────────────────────
// API helper
// ─────────────────────────────────────────────────────────────────────────────

async function apiFetch(path, opts = {}) {
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  const resp = await fetch(API + path, { ...opts, headers });
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try { const j = await resp.json(); msg = j.detail || JSON.stringify(j); } catch (_) {}
    throw new Error(msg);
  }
  return resp.json();
}
