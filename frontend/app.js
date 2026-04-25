/* ============================================================
   Causal Financial Knowledge Graph — Frontend Logic
   ============================================================ */

// CHANGE THIS to your deployed backend URL:
// Render example: https://metric-graph-xxxxx.onrender.com
const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
  ? window.location.origin.replace('pages.dev', 'onrender.com')  // Auto-detect if on Cloudflare
  : 'http://127.0.0.1:8000';  // Local dev

// ─────────────────────────────────────────────────────────────────────────────
// Bootstrap
// ─────────────────────────────────────────────────────────────────────────────

window.addEventListener('DOMContentLoaded', async () => {
  // Populate company dropdown on load
  loadQQCompanies();
});

// ─────────────────────────────────────────────────────────────────────────────
// Quick Query Builder — cascading dropdowns backed by /api/available-data
// ─────────────────────────────────────────────────────────────────────────────

async function loadQQCompanies() {
  try {
    // Use companies-with-data endpoint — only companies with >= 2 usable periods
    const data = await apiFetch('/api/companies-with-data');
    const sel = document.getElementById('qqCompany');
    if (!sel || !data.companies) return;
    data.companies.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.name;
      sel.appendChild(opt);
    });
  } catch (_) {}
}

async function onQQCompanyChange() {
  const companyId = document.getElementById('qqCompany').value;
  const companyName = document.getElementById('qqCompany').selectedOptions[0]?.textContent || '';
  const metricSel = document.getElementById('qqMetric');
  const periodSel = document.getElementById('qqPeriod');
  const compareSel = document.getElementById('qqComparePeriod');
  const analyseBtn = document.getElementById('qqAnalyseBtn');
  const status = document.getElementById('qqStatus');

  // Reset dependents
  [metricSel, periodSel, compareSel].forEach(s => {
    s.innerHTML = '<option value="">— loading… —</option>';
    s.disabled = true;
  });
  analyseBtn.disabled = true;

  if (!companyId) {
    metricSel.innerHTML = '<option value="">— select company first —</option>';
    periodSel.innerHTML = '<option value="">— period —</option>';
    compareSel.innerHTML = '<option value="">— compare —</option>';
    status.textContent = '';
    return;
  }

  status.textContent = 'Loading available data…';

  try {
    const data = await apiFetch(`/api/available-data?company_id=${companyId}`);

    // Populate metrics — sort to put Operating Profit and Profit Before Tax on top
    metricSel.innerHTML = '<option value="">— select metric —</option>';
    const priorityNames = ['Operating Profit', 'Profit Before Tax'];
    const metrics = data.metrics || [];
    const sorted = [
      ...metrics.filter(m => priorityNames.includes(m.display_name)),
      ...metrics.filter(m => !priorityNames.includes(m.display_name))
    ];
    sorted.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.name;         // column name e.g. "revenue_from_operations"
      opt.dataset.display = m.display_name;
      opt.textContent = m.display_name;
      metricSel.appendChild(opt);
    });
    metricSel.disabled = false;

    // Populate both period dropdowns
    const periods = data.periods || [];
    [periodSel, compareSel].forEach(s => {
      s.innerHTML = '<option value="">— select —</option>';
      periods.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p;
        s.appendChild(opt);
      });
      s.disabled = false;
    });

    // Auto-select latest as current, second-latest as compare
    if (periods.length >= 2) {
      periodSel.value = periods[periods.length - 1];
      compareSel.value = periods[periods.length - 2];
    } else if (periods.length === 1) {
      periodSel.value = periods[0];
    }

    const n = data.metrics ? data.metrics.length : 0;
    const p = periods.length;
    status.textContent = `${n} metric${n !== 1 ? 's' : ''}, ${p} period${p !== 1 ? 's' : ''} available`;

    // Wire up analyse button enablement
    [metricSel, periodSel, compareSel].forEach(s => s.addEventListener('change', _qqCheckReady));
    _qqCheckReady();
  } catch (e) {
    status.textContent = 'Error loading data: ' + e.message;
  }
}

function _qqCheckReady() {
  const metric  = document.getElementById('qqMetric').value;
  const period  = document.getElementById('qqPeriod').value;
  const compare = document.getElementById('qqComparePeriod').value;
  document.getElementById('qqAnalyseBtn').disabled = !(metric && period && compare);
}

async function runQuickQuery() {
  const companyName = document.getElementById('qqCompany').selectedOptions[0]?.textContent || '';
  const metricOpt   = document.getElementById('qqMetric').selectedOptions[0];
  const period      = document.getElementById('qqPeriod').value;
  const compare     = document.getElementById('qqComparePeriod').value;
  const displayName = metricOpt?.dataset.display || metricOpt?.textContent || '';
  const metricName  = metricOpt?.value || '';

  if (!companyName || !metricName || !period || !compare) return;

  // Build a natural-language style query and submit through the normal NL path
  const q = `Why did ${displayName} change for ${companyName} in ${period} vs ${compare}`;
  document.getElementById('nlQuery').value = q;

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

async function syncFromNeon() {
  showLoading('Syncing data from Neon…');
  try {
    const result = await apiFetch('/api/sync-from-neon', {
      method: 'POST',
      body: JSON.stringify({
        clear_existing: false
      }),
    });
    showContent(`
      <div class="card">
        <div class="card-title" style="color:var(--green);">✓ Neon Sync Successful</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0;font-size:13px;">
          <div><span style="color:var(--muted);">Rows Synced:</span> <strong>${result.total_rows_synced || 0}</strong></div>
          <div><span style="color:var(--muted);">Inserted:</span> <strong>${result.rows_inserted || 0}</strong></div>
          <div><span style="color:var(--muted);">Updated:</span> <strong>${result.rows_updated || 0}</strong></div>
          <div><span style="color:var(--muted);">Errors:</span> <strong style="color:${result.error_count > 0 ? 'var(--red)' : 'var(--green)'};">${result.error_count || 0}</strong></div>
        </div>
        ${result.errors && result.errors.length ? `
          <div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:4px;padding:8px;font-size:11px;color:var(--red);max-height:150px;overflow-y:auto;">
            <div style="font-weight:600;margin-bottom:6px;">Errors encountered:</div>
            ${result.errors.map(e => `<div>• ${escHtml(e)}</div>`).join('')}
          </div>
        ` : '<p style="color:var(--green);font-size:12px;">All rows synced without errors!</p>'}
        <p style="margin-top:12px;color:var(--muted);font-size:12px;">You can now ask questions about your metrics.</p>
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
      <div class="driver-list">${allDrivers.map((d, i) => renderDriverCard(d, i, ch.absolute, true)).join('')}</div>
    </div>` : '';

  const eventsHtml = (result.period_events || []).length ? `
    <div class="card" style="padding:10px 12px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--yellow);margin-bottom:8px;">Business Events · ${escHtml(qm.period || '')}</div>
      <div class="events-list">${result.period_events.map(renderEvent).join('')}</div>
    </div>` : '';

  // Set 2-panel mode — graph LEFT, analysis RIGHT
  const contentEl = document.getElementById('content');
  contentEl.classList.add('two-panel-mode');
  
  // Store metrics used for graph highlighting
  window._metricsUsedInAnalysis = result.metrics_used || [];
  
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

  // Store context for graph-node navigation
  window._analysisContext = {
    company: segment || qm.segment || '',
    period: qm.period || '',
    compare_period: qm.compare_period || '',
  };
  window._navStack = [{ metricId: qm.metric || '', displayName: qm.display_name || qm.metric || '' }];

  await loadGraphInPanel();
}

// ─────────────────────────────────────────────────────────────────────────────
// Graph: hierarchical layout + bezier edges
// ─────────────────────────────────────────────────────────────────────────────

const NODE_W = 100, NODE_H = 42, X_GAP = 20, Y_LAYER = 88, Y_SUBROW = 56, PAD_TOP = 48;

/** Longest-path rank assignment (source=0, sinks get highest rank), then invert */
function computeHierarchicalLayout(nodes, edges, W) {
  const allIds = new Set(nodes.map(n => n.id));
  const rank = {};
  nodes.forEach(n => rank[n.id] = 0);

  let changed = true, iters = 0;
  while (changed && iters++ < 400) {
    changed = false;
    edges.forEach(e => {
      if (!allIds.has(e.source) || !allIds.has(e.target)) return;
      const nr = (rank[e.source] || 0) + 1;
      if (nr > (rank[e.target] || 0)) { rank[e.target] = nr; changed = true; }
    });
  }

  const maxRank = Math.max(...Object.values(rank), 0);

  // Invert: sinks (high rank) go to top row (displayRank 0)
  const groups = {};
  nodes.forEach(n => {
    const dr = maxRank - (rank[n.id] || 0);
    if (!groups[dr]) groups[dr] = [];
    groups[dr].push(n);
  });

  // Within each layer, center-heavy sort (most connected first)
  const outCount = {};
  nodes.forEach(n => outCount[n.id] = 0);
  edges.forEach(e => { if (allIds.has(e.source)) outCount[e.source] = (outCount[e.source] || 0) + 1; });
  Object.values(groups).forEach(g => g.sort((a, b) => (outCount[b.id]||0) - (outCount[a.id]||0)));

  // Max nodes per visual row before wrapping
  const maxPerRow = Math.max(3, Math.floor((W - 60) / (NODE_W + X_GAP)));

  const pos = {};
  let currentY = PAD_TOP;
  const sortedRanks = Object.keys(groups).map(Number).sort((a, b) => a - b);

  sortedRanks.forEach(dr => {
    const layerNodes = groups[dr];
    // Split layer into wrapped sub-rows
    for (let start = 0; start < layerNodes.length; start += maxPerRow) {
      const row = layerNodes.slice(start, start + maxPerRow);
      const rowTotalW = row.length * NODE_W + (row.length - 1) * X_GAP;
      const startX = Math.round((W - rowTotalW) / 2) + Math.round(NODE_W / 2);
      row.forEach((n, i) => {
        pos[n.id] = { x: startX + i * (NODE_W + X_GAP), y: currentY };
      });
      const isLastSubrow = start + maxPerRow >= layerNodes.length;
      currentY += isLastSubrow ? Y_LAYER : Y_SUBROW;
    }
  });

  return { pos, totalH: currentY + NODE_H + 24 };
}

/** Bezier path connecting bottom-center of source to top-center of target */
function edgePathD(pos, srcId, tgtId) {
  const s = pos[srcId], t = pos[tgtId];
  if (!s || !t) return null;
  const NH = 21; // half node height (NODE_H/2 = 42/2)
  const fy = s.y + NH, ty = t.y - NH;
  const midY = (fy + ty) / 2;
  return `M${s.x},${fy} C${s.x},${midY} ${t.x},${midY} ${t.x},${ty}`;
}

async function loadGraphInPanel() {
  const wrap = document.getElementById('graphSvgWrap');
  if (!wrap) return;
  try {
    const data = await apiFetch('/api/graph');
    const allNodes = data.nodes || [];
    const allEdges = data.edges || [];
    const metricsUsed = window._metricsUsedInAnalysis || [];
    const hasFilter = metricsUsed.length > 0;

    // When analysis is active: show only the causal subgraph –
    // include only edges that flow INTO analyzed metrics (drivers), never
    // edges that flow OUT of them (upstream effects like Profit Before Tax).
    let nodes, edges;
    if (hasFilter) {
      const edgeSet = new Set();
      const nodeSet = new Set(metricsUsed);
      allEdges.forEach(e => {
        // Only include edges where the TARGET is an analyzed metric
        // This keeps driver→metric edges and drops metric→consumer edges
        if (metricsUsed.includes(e.target)) {
          nodeSet.add(e.source);
          nodeSet.add(e.target);
          edgeSet.add(`${e.source}→${e.target}`);
        }
      });
      nodes = allNodes.filter(n => nodeSet.has(n.id));
      edges = allEdges.filter(e => edgeSet.has(`${e.source}→${e.target}`));
    } else {
      nodes = allNodes;
      edges = allEdges;
    }

    const W = Math.max(wrap.clientWidth || 600, 500);
    const H = Math.max(wrap.clientHeight || 500, 500);

    const { pos, totalH } = computeHierarchicalLayout(nodes, edges, W);
    const svgH = Math.max(H, totalH);

    // SVG arrow markers (strokeWidth units so they scale properly)
    const defs = `<defs>
      <marker id="arr_pos" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
        <path d="M0,0 L0,6 L8,3 z" fill="#22c55e"/>
      </marker>
      <marker id="arr_neg" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
        <path d="M0,0 L0,6 L8,3 z" fill="#ef4444"/>
      </marker>
      <marker id="arr_pos_dim" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
        <path d="M0,0 L0,6 L8,3 z" fill="rgba(34,197,94,0.3)"/>
      </marker>
      <marker id="arr_neg_dim" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
        <path d="M0,0 L0,6 L8,3 z" fill="rgba(239,68,68,0.3)"/>
      </marker>
    </defs>`;

    // Edges as bezier paths
    const edgesSvg = edges.map(e => {
      const d = edgePathD(pos, e.source, e.target);
      if (!d) return '';
      const isActive = !hasFilter || (metricsUsed.includes(e.source) && metricsUsed.includes(e.target));
      const isPos    = e.direction === 'positive';
      const col  = isPos ? '#22c55e' : '#ef4444';
      const sw   = isActive ? (e.relationship_type === 'formula_dependency' ? 2.2 : 1.5) : 1;
      const op   = hasFilter ? (isActive ? 0.85 : 0.18) : 0.5;
      const dash = e.relationship_type === 'causal_driver' ? '5,3' : 'none';
      const arrowId = isActive ? (isPos ? 'arr_pos' : 'arr_neg') : (isPos ? 'arr_pos_dim' : 'arr_neg_dim');
      return `<path id="edge_${e.source}_${e.target}" d="${d}" fill="none"
        stroke="${col}" stroke-width="${sw}" opacity="${op}"
        stroke-linecap="round" stroke-dasharray="${dash}" marker-end="url(#${arrowId})"/>`;
    }).join('');

    // Nodes
    const nodesSvg = nodes.map(n => {
      const p = pos[n.id];
      if (!p) return '';
      const label = n.display_name || n.id;
      const words = label.split(' ');
      const half  = Math.ceil(words.length / 2);
      const line1 = words.slice(0, half).join(' ');
      const line2 = words.length > 1 ? words.slice(half).join(' ') : null;

      const isAnalyzed   = !hasFilter || metricsUsed.includes(n.id);
      const isNavigable  = metricsUsed.includes(n.id) && !!(window._analysisContext);
      const fill   = isAnalyzed ? (n.is_base ? '#f59e0b' : '#818cf8') : (n.is_base ? 'rgba(245,158,11,0.2)' : 'rgba(129,140,248,0.2)');
      const stroke = isAnalyzed ? (n.is_base ? '#fcd34d' : '#c4b5fd') : 'rgba(110,110,130,0.25)';
      const sw     = isAnalyzed ? 2 : 1;
      const tOp   = isAnalyzed ? 1 : 0.35;
      const cursor = isNavigable ? 'pointer' : 'default';
      const ring   = isNavigable ? `<rect x="-52" y="-25" width="104" height="50" rx="11" fill="none" stroke="${n.is_base ? '#fcd34d' : '#c4b5fd'}" stroke-width="1.5" stroke-dasharray="3,2" opacity="0.55"/>` : '';
      const title  = `<title>${isNavigable ? 'Click to drill into ' : ''}${escHtml(label)}${n.unit ? ' (' + escHtml(n.unit) + ')' : ''}</title>`;
      const textEl = line2
        ? `<text y="-5" text-anchor="middle" font-size="9" font-weight="700" fill="#fff" opacity="${tOp}" font-family="Inter,sans-serif" pointer-events="none">${escHtml(line1)}</text>
           <text y="9"  text-anchor="middle" font-size="9" font-weight="700" fill="#fff" opacity="${tOp}" font-family="Inter,sans-serif" pointer-events="none">${escHtml(line2)}</text>`
        : `<text y="3" text-anchor="middle" font-size="9.5" font-weight="700" fill="#fff" opacity="${tOp}" font-family="Inter,sans-serif" pointer-events="none">${escHtml(line1)}</text>`;

      return `<g id="node_${n.id}" class="draggable-node${isNavigable ? ' navigable-node' : ''}" data-nodeid="${n.id}" transform="translate(${p.x},${p.y})" style="cursor:${cursor};">
        ${title}${ring}
        <rect x="-48" y="-21" width="96" height="42" rx="9" fill="${fill}" opacity="0.93" stroke="${stroke}" stroke-width="${sw}"/>
        ${textEl}
      </g>`;
    }).join('');

    wrap.style.overflow = 'auto';
    wrap.innerHTML = `<svg id="metricSvg" width="${W}" height="${svgH}" style="display:block;min-width:${W}px;">
      ${defs}
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
  let dragNode = null, panning = false;
  let startX = 0, startY = 0, nodeStartX = 0, nodeStartY = 0;
  let viewTX = 0, viewTY = 0, viewScale = 1;
  let _wasDragged = false;
  const vp = svg.querySelector('#viewport');

  function applyView() {
    if (vp) vp.setAttribute('transform', `translate(${viewTX},${viewTY}) scale(${viewScale})`);
  }
  function svgXY(e) {
    const r = svg.getBoundingClientRect();
    return { x: (e.clientX - r.left - viewTX) / viewScale, y: (e.clientY - r.top - viewTY) / viewScale };
  }

  svg.addEventListener('mousedown', e => {
    _wasDragged = false;
    const g = e.target.closest('.draggable-node');
    if (g) {
      e.preventDefault();
      dragNode = g.dataset.nodeid;
      const p = svgXY(e);
      startX = p.x; startY = p.y;
      nodeStartX = pos[dragNode].x; nodeStartY = pos[dragNode].y;
    } else {
      e.preventDefault();
      panning = true;
      startX = e.clientX - viewTX;
      startY = e.clientY - viewTY;
    }
  });

  svg.addEventListener('mousemove', e => {
    if (dragNode) {
      _wasDragged = true;
      const p = svgXY(e);
      const x = nodeStartX + (p.x - startX);
      const y = nodeStartY + (p.y - startY);
      pos[dragNode] = { x, y };
      const gEl = svg.querySelector(`#node_${dragNode}`);
      if (gEl) gEl.setAttribute('transform', `translate(${x},${y})`);
      edges.forEach(ed => {
        if (ed.source !== dragNode && ed.target !== dragNode) return;
        const pe = svg.querySelector(`#edge_${ed.source}_${ed.target}`);
        if (!pe) return;
        const d = edgePathD(pos, ed.source, ed.target);
        if (d) pe.setAttribute('d', d);
      });
    } else if (panning) {
      _wasDragged = true;
      viewTX = e.clientX - startX;
      viewTY = e.clientY - startY;
      applyView();
    }
  });

  svg.addEventListener('mouseup',    () => { dragNode = null; panning = false; });
  svg.addEventListener('mouseleave', () => { dragNode = null; panning = false; });

  // Zoom centred on mouse
  svg.addEventListener('wheel', e => {
    e.preventDefault();
    const r  = svg.getBoundingClientRect();
    const mx = e.clientX - r.left, my = e.clientY - r.top;
    const factor   = e.deltaY > 0 ? 0.9 : 1.1;
    const newScale = Math.max(0.15, Math.min(4, viewScale * factor));
    viewTX = mx - (mx - viewTX) * (newScale / viewScale);
    viewTY = my - (my - viewTY) * (newScale / viewScale);
    viewScale = newScale;
    applyView();
  }, { passive: false });

  // Click → navigate (highlighted nodes) or tooltip (others)
  svg.addEventListener('click', e => {
    if (_wasDragged) { _wasDragged = false; return; }
    const g   = e.target.closest('.draggable-node');
    const tip = document.getElementById('nodeTooltip');
    if (!g) { if (tip) tip.style.display = 'none'; return; }
    const nid  = g.dataset.nodeid;

    // Navigate if this node is part of the analysis and we have context
    const metricsUsed = window._metricsUsedInAnalysis || [];
    const ctx = window._analysisContext;
    if (ctx && ctx.company && metricsUsed.includes(nid)) {
      if (tip) tip.style.display = 'none';
      navigateToMetric(nid);
      return;
    }

    // Regular tooltip for non-highlighted nodes
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

// ─────────────────────────────────────────────────────────────────────────────
// Graph Knowledge Navigation
// ─────────────────────────────────────────────────────────────────────────────

async function navigateToMetric(nodeId) {
  const ctx = window._analysisContext;
  if (!ctx || !ctx.company) return;

  const panel = document.querySelector('.analysis-panel');
  if (!panel) return;

  const graphData = window._graphData;
  const node = graphData && graphData.nodes.find(n => n.id === nodeId);
  const displayName = (node && node.display_name) || nodeId;

  panel.innerHTML = `<div style="padding:24px;display:flex;align-items:center;gap:10px;color:var(--muted);"><div class="spinner"></div> Analysing ${escHtml(displayName)}…</div>`;

  try {
    const data = await apiFetch('/api/analyse', {
      method: 'POST',
      body: JSON.stringify({
        metric: nodeId,
        company: ctx.company,
        period: ctx.period,
        compare_period: ctx.compare_period,
      }),
    });

    const result = data.result;

    // Update nav stack — if going back to existing item, truncate; else push
    const existingIdx = (window._navStack || []).findIndex(n => n.metricId === nodeId);
    if (existingIdx >= 0) {
      window._navStack = window._navStack.slice(0, existingIdx + 1);
    } else {
      window._navStack = window._navStack || [];
      window._navStack.push({ metricId: nodeId, displayName });
    }

    // Update graph highlighting
    window._metricsUsedInAnalysis = (result.metrics_used || [nodeId]);
    updateGraphHighlighting();

    // Render the right panel with new analysis
    renderAnalysisPanelOnly(result);

  } catch (e) {
    panel.innerHTML = `<div class="error-banner" style="margin:16px;">${escHtml(e.message)}</div>`;
  }
}

function updateGraphHighlighting() {
  const svg = document.getElementById('metricSvg');
  if (!svg || !window._graphData) return;

  const metricsUsed = window._metricsUsedInAnalysis || [];
  const hasContext = !!(window._analysisContext && window._analysisContext.company);
  const { nodes, edges } = window._graphData;

  nodes.forEach(n => {
    const el = svg.querySelector(`#node_${n.id}`);
    if (!el) return;
    const texts = el.querySelectorAll('text');
    const isAnalyzed = !hasFilter || metricsUsed.includes(n.id);
    const isNavigable = isAnalyzed && hasContext;

    const mainRect = el.querySelector('rect:not([fill="none"])');
    if (mainRect) {
      mainRect.setAttribute('fill', isAnalyzed
        ? (n.is_base ? '#f59e0b' : '#818cf8')
        : (n.is_base ? 'rgba(245,158,11,0.2)' : 'rgba(129,140,248,0.2)'));
      mainRect.setAttribute('stroke', isAnalyzed
        ? (n.is_base ? '#fcd34d' : '#c4b5fd')
        : 'rgba(110,110,130,0.25)');
      mainRect.setAttribute('stroke-width', isAnalyzed ? '2' : '1');
    }
    texts.forEach(t => t.setAttribute('opacity', isAnalyzed ? '1' : '0.5'));
    el.style.cursor = isNavigable ? 'pointer' : 'grab';
  });

  const hasFilter = metricsUsed.length > 0;
  edges.forEach(e => {
    const pe = svg.querySelector(`#edge_${e.source}_${e.target}`);
    if (!pe) return;
    const isActive = !hasFilter || (metricsUsed.includes(e.source) && metricsUsed.includes(e.target));
    pe.setAttribute('opacity', hasFilter ? (isActive ? '0.85' : '0.08') : '0.45');
    pe.setAttribute('stroke-width', isActive
      ? (e.relationship_type === 'formula_dependency' ? '2.5' : '1.8')
      : '1');
  });
}

function renderAnalysisPanelOnly(result) {
  const panel = document.querySelector('.analysis-panel');
  if (!panel) return;

  const qm  = result.query_meta || {};
  const ch  = result.change || {};
  const isUp = (ch.direction || '') === 'increased';
  const pill = isUp ? 'up' : 'down';
  const arrow = isUp ? '▲' : '▼';
  const sign  = isUp ? '+' : '';
  const allDrivers = result.drivers || [];

  // Breadcrumb trail
  const navStack = window._navStack || [];
  const breadcrumbHtml = navStack.length > 1
    ? `<div style="font-size:11px;padding:3px 0 10px;border-bottom:1px solid var(--border);margin-bottom:8px;display:flex;align-items:center;gap:4px;flex-wrap:wrap;">
        <span style="color:var(--muted);font-size:10px;margin-right:4px;">PATH:</span>
        ${navStack.map((item, i) => {
          const isLast = i === navStack.length - 1;
          return isLast
            ? `<span style="color:var(--text);font-weight:600;">${escHtml(item.displayName)}</span>`
            : `<span style="color:var(--accent);cursor:pointer;" onclick="navigateToMetric('${item.metricId}')" title="go back">${escHtml(item.displayName)}</span><span style="color:var(--muted);margin:0 3px;">›</span>`;
        }).join('')}
      </div>`
    : '';

  const driversHtml = allDrivers.length ? `
    <div class="card" style="padding:10px 12px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--green);margin-bottom:8px;">
        Root Cause Analysis
        <span style="text-transform:none;font-size:9px;color:var(--muted);letter-spacing:0;margin-left:6px;">· click a bright node in graph to drill deeper</span>
      </div>
      <div class="driver-list">${allDrivers.map((d, i) => renderDriverCard(d, i, ch.absolute, true)).join('')}</div>
    </div>` : '';

  panel.innerHTML = `
    ${breadcrumbHtml}
    <div class="card" style="padding:12px 14px;">
      <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:6px;">${escHtml(qm.display_name || qm.metric || '')}</div>
      <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">
        <div style="font-size:28px;font-weight:700;">${fmtVal(ch.current_value, qm.unit)}</div>
        <div>
          <div class="change-pill ${pill}">${arrow} ${sign}${fmtVal(ch.absolute, qm.unit)} (${sign}${(ch.pct||0).toFixed(1)}%)</div>
          <div style="font-size:11px;color:var(--muted);margin-top:3px;">${escHtml(qm.period)} vs ${escHtml(qm.compare_period)} · ${escHtml(qm.segment || '')}</div>
        </div>
        <div style="margin-left:auto;text-align:right;">
          <div style="font-size:10px;color:var(--muted);">Prev</div>
          <div style="font-size:18px;font-weight:600;">${fmtVal(ch.prev_value, qm.unit)}</div>
        </div>
      </div>
    </div>
    ${result.summary ? `<div style="font-size:12px;line-height:1.65;color:var(--text);border-left:3px solid var(--accent);padding:6px 10px;background:var(--surface);border-radius:0 6px 6px 0;">${escHtml(result.summary)}</div>` : ''}
    ${driversHtml}
  `;
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
  // Suppress meaningless unit strings (USD, amount, empty)
  if (!unit || unit === 'USD' || unit === 'amount') return n.toLocaleString(undefined, {maximumFractionDigits: 2});
  return `${n.toFixed(2)} ${unit}`;
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
