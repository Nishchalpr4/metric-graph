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
  if (!result || result.error) {
    showError((result && result.error) || 'No result returned.');
    return;
  }

  const qm = result.query_meta || {};
  const ch = result.change || {};
  const direction = ch.direction || 'changed';
  const isUp = direction === 'increased';
  const pillClass = isUp ? 'up' : 'down';
  const arrow = isUp ? '▲' : '▼';
  const sign = isUp ? '+' : '';

  // MAIN ANALYSIS - Graph FIRST, then analysis below
  let html = '';

  // ─────────────────────────────────────────────────────────
  // 1. GRAPH ON TOP (immediately loaded, no lazy-loading)
  // ─────────────────────────────────────────────────────────
  html += `<div id="graphContainer" style="margin-bottom:32px;"></div>`;

  // ─────────────────────────────────────────────────────────
  // 2. ANALYSIS BELOW
  // ─────────────────────────────────────────────────────────

  if (query_text) {
    html += `<div class="card" style="background:var(--surface2);border-color:var(--accent);margin-bottom:16px;">
      <div class="card-title">Your Question</div>
      <div style="font-size:14px;color:var(--text);">"${escHtml(query_text)}"</div>
    </div>`;
  }

  if (warnings && warnings.length) {
    html += `<div class="error-banner" style="background:rgba(245,158,11,.08);border-color:rgba(245,158,11,.3);color:var(--yellow);margin-bottom:12px;">
      ${warnings.map(w => `⚠ ${escHtml(w)}`).join('<br/>')}
    </div>`;
  }

  // Change summary card
  html += `
    <div class="card" style="margin-bottom:16px;">
      <div class="card-title">${escHtml(qm.display_name || qm.metric || 'Metric')}</div>
      <div class="change-row">
        <div class="metric-big">${fmtVal(ch.current_value, qm.unit)}</div>
        <div>
          <div class="change-pill ${pillClass}">
            ${arrow} ${sign}${fmtVal(ch.absolute, qm.unit)} &nbsp; (${sign}${(ch.pct || 0).toFixed(1)}%)
          </div>
          <div class="vs-label" style="margin-top:4px;">
            ${escHtml(qm.period)} vs ${escHtml(qm.compare_period)} · ${escHtml(segment || qm.segment || '')}
          </div>
        </div>
        <div style="margin-left:auto;text-align:right;">
          <div style="color:var(--muted);font-size:11px;">Previous</div>
          <div style="font-size:18px;font-weight:600;">${fmtVal(ch.prev_value, qm.unit)}</div>
        </div>
      </div>
    </div>
  `;

  // Executive Summary
  if (result.summary) {
    html += `<div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--accent2);">Executive Summary</div>
      <div class="summary-text" style="line-height:1.8;font-size:14px;">${escHtml(result.summary)}</div>
    </div>`;
  }

  // All Drivers with full details
  const allDrivers = result.drivers || [];
  if (allDrivers.length) {
    html += `<div class="card" style="margin-bottom:16px;">
      <div class="card-title" style="color:var(--green);">Root Cause Analysis (All Drivers)</div>
      <div style="font-size:12px;color:var(--muted);margin-bottom:12px;">
        Complete list of all formula dependencies and causal drivers affecting <strong>${escHtml(qm.display_name)}</strong>
      </div>
      <div class="driver-list">
        ${allDrivers.map((d, i) => renderDriverCard(d, i, ch.absolute, true)).join('')}
      </div>
    </div>`;
  }

  // Business Events section (no tab, always visible)
  if (result.period_events && result.period_events.length > 0) {
    html += `<div class="card" style="margin-bottom:16px;">
      <div class="card-title">📌 Business Events in ${escHtml(qm.period || '')}</div>
      <div class="events-list">${result.period_events.map(renderEvent).join('')}</div>
    </div>`;
  }

  showContent(html);

  // Load graph immediately after content is set
  await loadGraphExplorerEmbedded();
}

// ─────────────────────────────────────────────────────────
// New: Load graph embedded in main view (not in a tab)
// ─────────────────────────────────────────────────────────
async function loadGraphExplorerEmbedded() {
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
  const container = document.getElementById('graphContainer');
  if (!container) return;
  container.innerHTML = '<div class="loading"><div class="spinner"></div><span>Loading graph…</span></div>';
  
  try {
    const data = await apiFetch('/api/graph');
    const nodes = data.nodes || [];
    const edges = data.edges || [];

    // Create hierarchical layout
    const nodePositions = {};
    const WIDTH = 1600, HEIGHT = 900;
    
    // Categorize nodes by metric type for hierarchy
    const baseMetrics = nodes.filter(n => n.is_base);
    const derivedMetrics = nodes.filter(n => !n.is_base);
    
    // Further sub-categorize derived metrics
    const operationalDerived = derivedMetrics.filter(n => n.category === 'Operational');
    const financialDerived = derivedMetrics.filter(n => n.category === 'Financial');
    const userDerived = derivedMetrics.filter(n => n.category === 'User');

    // Position base metrics on far left (x=150)
    const baseY = HEIGHT / 2;
    baseMetrics.forEach((n, i) => {
      const offset = (i - baseMetrics.length / 2) * 80;
      nodePositions[n.id] = { x: 120, y: baseY + offset };
    });

    // Position operational derived in left-center (x=450)
    const opY = HEIGHT / 2;
    operationalDerived.forEach((n, i) => {
      const offset = (i - operationalDerived.length / 2) * 100;
      nodePositions[n.id] = { x: 450, y: opY + offset };
    });

    // Position user derived in center (x=700)
    const userY = HEIGHT / 2;
    userDerived.forEach((n, i) => {
      const offset = (i - userDerived.length / 2) * 100;
      nodePositions[n.id] = { x: 700, y: userY + offset };
    });

    // Position financial derived on right (x=1100, 1350)
    const finLevel1 = financialDerived.filter(m => ['gmv', 'take_rate', 'arpu', 'cac', 'delivery_charges', 'commission_rate'].includes(m.id));
    const finLevel2 = financialDerived.filter(m => ['revenue'].includes(m.id));
    
    const fin1Y = HEIGHT / 2;
    finLevel1.forEach((n, i) => {
      const offset = (i - finLevel1.length / 2) * 100;
      nodePositions[n.id] = { x: 1100, y: fin1Y + offset };
    });

    finLevel2.forEach((n, i) => {
      const offset = (i - finLevel2.length / 2) * 100;
      nodePositions[n.id] = { x: 1350, y: fin1Y + 50 + offset };
    });

    // Draw SVG edges
    const edgeSvg = edges.map(e => {
      const s = nodePositions[e.source];
      const t = nodePositions[e.target];
      if (!s || !t) return '';
      const color = e.direction === 'positive' ? '#22c55e' : '#ef4444';
      const strokeWidth = e.relationship_type === 'formula_dependency' ? 2 : 1.5;
      return `<line x1="${s.x + 45}" y1="${s.y}" x2="${t.x - 45}" y2="${t.y}" stroke="${color}" stroke-width="${strokeWidth}" opacity="0.5"/>`;
    }).join('');

    // Draw SVG nodes with labels
    const svgContent = nodes.map(n => {
      const pos = nodePositions[n.id];
      const displayName = (n.display_name || n.id).length > 18 
        ? (n.display_name || n.id).split(' ').slice(0, 2).join(' ')
        : (n.display_name || n.id);
      return `
        <g onclick="showNodeDetail('${n.id}')" style="cursor:pointer;">
          <rect x="${pos.x - 45}" y="${pos.y - 20}" width="90" height="40" rx="6" fill="${n.is_base ? '#f59e0b' : '#5b6ef5'}" opacity="0.8" stroke="${n.is_base ? '#fcd34d' : '#818cf8'}" stroke-width="2"/>
          <text x="${pos.x}" y="${pos.y - 4}" text-anchor="middle" font-size="10" font-weight="600" fill="#fff" font-family="Inter, sans-serif">${escHtml(displayName)}</text>
          <text x="${pos.x}" y="${pos.y + 10}" text-anchor="middle" font-size="8" fill="rgba(255,255,255,0.7)" font-family="Inter, sans-serif">${escHtml(n.unit)}</text>
        </g>
      `;
    }).join('');

    const graphHtml = `
      <div class="card" style="margin-bottom:24px;">
        <div class="card-title">📊 Metric Relationship Graph</div>
        <div class="graph-legend">
        <div class="legend-item"><div class="legend-dot" style="background:var(--yellow)"></div>Base (input) metric</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--accent)"></div>Derived metric</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>Positive causal driver</div>
        <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>Negative relationship</div>
        <div style="margin-left:auto;font-size:11px;color:var(--muted);">← Base Metrics | Operational | User Metrics | Financial | Revenue →</div>
      </div>
      <div style="position:relative;width:100%;margin:16px 0;border:1px solid var(--border);border-radius:8px;overflow:auto;background:rgba(15,17,23,.8);">
        <svg width="${WIDTH}" height="${HEIGHT}" style="display:block;cursor:grab;">
          <defs>
            <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
              <polygon points="0 0, 10 3, 0 6" fill="#8892b0"/>
            </marker>
          </defs>
          <!-- Vertical separator lines for clarity -->
          <line x1="300" y1="0" x2="300" y2="${HEIGHT}" stroke="rgba(139,146,176,.15)" stroke-width="1" stroke-dasharray="5,5"/>
          <line x1="600" y1="0" x2="600" y2="${HEIGHT}" stroke="rgba(139,146,176,.15)" stroke-width="1" stroke-dasharray="5,5"/>
          <line x1="900" y1="0" x2="900" y2="${HEIGHT}" stroke="rgba(139,146,176,.15)" stroke-width="1" stroke-dasharray="5,5"/>
          <line x1="1200" y1="0" x2="1200" y2="${HEIGHT}" stroke="rgba(139,146,176,.15)" stroke-width="1" stroke-dasharray="5,5"/>
          
          ${edgeSvg}
          ${svgContent}
        </svg>
      </div>
      <div style="padding:12px;background:var(--surface2);border-radius:8px;border:1px solid var(--border);font-size:12px;color:var(--muted);">
        <strong>📊 Graph Hierarchy (Left → Right):</strong><br/>
        <strong style="color:var(--yellow)">Layer 1 (Yellow):</strong> Base operational inputs — Orders, AOV, Marketing Spend, etc. (directly measured)<br/>
        <strong style="color:var(--text)">Layer 2 (Blue):</strong> Operational derived metrics — Basket Size, Order Frequency, Restaurant Partners, etc.<br/>
        <strong style="color:var(--text)">Layer 3 (Blue):</strong> User metrics — Monthly Active Users, New Users<br/>
        <strong style="color:var(--accent)">Layer 4 (Blue):</strong> Intermediate financial — GMV, Commission Rate, Delivery Revenue, Take Rate, CAC, ARPU<br/>
        <strong style="color:var(--accent)">Layer 5 (Blue, rightmost):</strong> Final outcome — <strong>Revenue</strong> (the ultimate business metric)<br/>
        <strong style="color:var(--green)">Green lines:</strong> Positive relationships | <strong style="color:var(--red)">Red lines:</strong> Negative relationships | <strong>Thicker lines:</strong> Formula dependencies (mathematical)
      </div>
    </div>`;

    // Store for use in showNodeDetail
    window._graphData = { nodes, edges };
    container.innerHTML = graphHtml;
  } catch (e) {
    container.innerHTML = `<div class="error-banner">Failed to load graph: ${escHtml(e.message)}</div>`;
  }
}

function showNodeDetail(nodeId) {
  const g = window._graphData;
  if (!g) return;
  const node = g.nodes.find(n => n.id === nodeId);
  if (!node) return;

  const outgoing = g.edges.filter(e => e.source === nodeId);
  const incoming = g.edges.filter(e => e.target === nodeId);

  const edgeRow = e => {
    const isPos = e.direction === 'positive';
    const typeClass = e.relationship_type === 'formula_dependency' ? 'badge-formula' : 'badge-causal';
    const typeName = e.relationship_type === 'formula_dependency' ? 'formula' : 'causal';
    return `<div style="padding:6px 0;border-bottom:1px solid var(--border);font-size:12px;">
      <span class="driver-type-badge ${typeClass}">${typeName}</span>
      <span style="margin-left:8px;color:${isPos ? 'var(--green)' : 'var(--red)'}">
        ${isPos ? '▲' : '▼'} ${isPos ? 'positive' : 'negative'}
      </span>
      <span style="margin-left:8px;color:var(--muted)">${escHtml(e.source)} → ${escHtml(e.target)}</span>
      <div style="color:var(--muted);margin-top:2px;">${escHtml(e.explanation || '')}</div>
    </div>`;
  };

  document.getElementById('nodeDetail').innerHTML = `
    <div class="card" style="border-color:var(--accent)">
      <div class="card-title">${escHtml(node.display_name || nodeId)}</div>
      <div style="color:var(--muted);font-size:12px;margin-bottom:10px;">${escHtml(node.description || '')}</div>
      ${incoming.length ? `<div style="font-size:11px;color:var(--muted);margin-bottom:4px;">INPUTS (${incoming.length})</div>${incoming.map(edgeRow).join('')}` : ''}
      ${outgoing.length ? `<div style="font-size:11px;color:var(--muted);margin-top:10px;margin-bottom:4px;">DRIVES (${outgoing.length})</div>${outgoing.map(edgeRow).join('')}` : ''}
    </div>
  `;
}

// ─────────────────────────────────────────────────────────────────────────────
// UI Utilities
// ─────────────────────────────────────────────────────────────────────────────

function switchTab(btn, panelId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.add('active');
}

function toggleDriver(id) {
  const body = document.getElementById(id);
  const toggle = document.getElementById('toggle-' + id);
  if (!body) return;
  const open = body.classList.toggle('open');
  if (toggle) toggle.textContent = open ? '▼' : '▶';
}

function showLoading(msg = 'Analysing…') {
  document.getElementById('content').innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <span>${escHtml(msg)}</span>
    </div>`;
}

function showError(msg) {
  document.getElementById('content').innerHTML = `
    <div class="error-banner">Error: ${escHtml(msg)}</div>`;
}

function showContent(html) {
  document.getElementById('content').innerHTML = html;
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
