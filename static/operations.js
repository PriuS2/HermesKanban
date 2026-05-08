import { api } from './api.js?v=20260508-02';
import { t } from './i18n.js?v=20260508-02';
import { escapeHtml } from './markdown.js?v=20260508-02';
import { openTaskDrawer } from './drawer.js?v=20260508-02';
import { state, toast } from './state.js?v=20260508-02';

function panel() { return document.getElementById('opsPanel'); }
function toggleButton() { return document.getElementById('opsToggleBtn'); }

function setPanelOpen(open) {
  state.opsOpen = Boolean(open);
  localStorage.setItem('kanbanOpsPanelOpen', state.opsOpen ? '1' : '0');
  const el = panel();
  if (el) el.hidden = !state.opsOpen;
  const btn = toggleButton();
  if (btn) btn.setAttribute('aria-expanded', state.opsOpen ? 'true' : 'false');
}

export function setupOperationsPanel() {
  const btn = toggleButton();
  const el = panel();
  if (!btn || !el) return;
  setPanelOpen(state.opsOpen);
  btn.addEventListener('click', async () => {
    setPanelOpen(!state.opsOpen);
    if (state.opsOpen) await refreshOperationsPanel();
  });
  el.addEventListener('click', ev => {
    const target = ev.target.closest('[data-ops-task-id]');
    if (!target) return;
    const taskId = target.dataset.opsTaskId;
    if (taskId) openTaskDrawer(taskId);
  });
}

export async function refreshOperationsPanel() {
  const el = panel();
  if (!el) return;
  if (!state.opsOpen) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.innerHTML = `<div class="ops-header"><strong>${t('operations')}</strong><span class="muted">${t('loading')}</span></div>`;
  try {
    state.opsData = await api.opsSummary(state.board);
    renderOperationsPanel(state.opsData);
  } catch (err) {
    const message = err.message || String(err);
    el.innerHTML = `<div class="ops-error">${escapeHtml(message)}</div>`;
    toast(message, 'error');
  }
}

export function renderOperationsPanel(data) {
  const el = panel();
  if (!el) return;
  const summary = data?.summary || {};
  el.innerHTML = `
    <div class="ops-header">
      <div>
        <p class="eyebrow">${t('operations')}</p>
        <h2>${t('opsOverview')}</h2>
        <p class="muted">${escapeHtml(t('opsEstimatedBackoffAdvisory'))}</p>
      </div>
      <span class="ops-chip">${formatTimestamp(data?.now)}</span>
    </div>
    ${renderSummaryCards(summary)}
    <div class="ops-sections">
      ${renderRunningTable(data?.running || [])}
      ${renderRetryTable(data?.retry_queue || [])}
      ${renderBlockedAfterRetries(data?.blocked_after_retries || [])}
      ${renderRecentFailures(data?.recent_failures || [])}
    </div>`;
}

function renderSummaryCards(summary) {
  const cards = [
    [t('opsRunning'), summary.running || 0, ''],
    [t('opsHeartbeatOverdue'), summary.heartbeat_overdue || 0, 'warning'],
    [t('opsRetryQueue'), summary.retry_candidates || 0, 'warning'],
    [t('opsBlockedAfterRetries'), summary.blocked_after_retries || 0, 'danger'],
    [t('unassigned'), summary.ready_unassigned || 0, ''],
  ];
  return `<div class="ops-grid">${cards.map(([label, value, tone]) => `
    <div class="ops-card">
      <small>${escapeHtml(label)}</small>
      <strong>${escapeHtml(String(value))}</strong>
      ${tone && Number(value) > 0 ? `<span class="ops-chip ${tone}">${escapeHtml(tone)}</span>` : ''}
    </div>`).join('')}</div>`;
}

function renderRunningTable(items) {
  const rows = items.map(item => {
    const task = item.task || {};
    return `<tr data-ops-task-id="${escapeHtml(task.id || '')}">
      <td>${taskLink(task)}</td>
      <td>${escapeHtml(task.assignee || t('unassigned'))}</td>
      <td>${formatDuration(item.worker?.elapsed_seconds)}</td>
      <td>${formatDuration(item.heartbeat?.age_seconds)} ${item.heartbeat?.overdue ? `<span class="ops-chip warning">${t('opsHeartbeatOverdue')}</span>` : ''}</td>
      <td>${formatDuration(item.claim?.expires_in_seconds)}</td>
      <td><code>${escapeHtml(String(item.worker?.pid || '—'))}</code></td>
      <td>${escapeHtml(item.last_event?.kind || '—')}</td>
    </tr>`;
  }).join('');
  return section(t('opsRunning'), items.length ? table(['Task', t('assignee'), 'Elapsed', 'Heartbeat', 'Claim', 'PID', t('events')], rows) : empty(t('opsNoRunning')));
}

function renderRetryTable(items) {
  const rows = items.map(item => {
    const task = item.task || {};
    const stateLabel = item.state === 'eligible' ? t('opsEligibleNow') : `${t('opsEstimatedWait')} ${formatDuration(item.eligible_in_seconds)}`;
    return `<tr data-ops-task-id="${escapeHtml(task.id || '')}">
      <td>${taskLink(task)}</td>
      <td>${escapeHtml(task.assignee || t('unassigned'))}</td>
      <td>${escapeHtml(String(item.attempt || 0))}/${escapeHtml(String(item.max_retries || 0))}</td>
      <td>${escapeHtml(item.last_failure_kind || '—')}</td>
      <td title="${escapeHtml(item.last_error || '')}">${escapeHtml(errorSummary(item))}</td>
      <td><span class="ops-chip warning">${formatDuration(item.estimated_backoff_seconds)}</span> ${escapeHtml(stateLabel)}</td>
    </tr>`;
  }).join('');
  return section(t('opsRetryQueue'), items.length ? table(['Task', t('assignee'), t('opsAttempt'), 'Kind', t('opsLastError'), 'Estimated backoff'], rows) : empty(t('opsNoRetry')));
}

function renderBlockedAfterRetries(items) {
  const rows = items.map(item => {
    const task = item.task || {};
    return `<tr data-ops-task-id="${escapeHtml(task.id || '')}">
      <td>${taskLink(task)}</td>
      <td>${escapeHtml(String(item.attempt || 0))}/${escapeHtml(String(item.max_retries || 0))}</td>
      <td>${escapeHtml(item.last_failure_kind || '—')}</td>
      <td title="${escapeHtml(item.last_error || '')}">${escapeHtml(errorSummary(item))}</td>
      <td><button class="button ghost" type="button" data-ops-task-id="${escapeHtml(task.id || '')}">${t('opsOpenTask')}</button></td>
    </tr>`;
  }).join('');
  return section(t('opsBlockedAfterRetries'), items.length ? table(['Task', t('opsAttempt'), 'Kind', t('opsLastError'), ''], rows) : empty(t('opsNoBlockedAfterRetries')));
}

function renderRecentFailures(items) {
  const rows = items.map(event => `<tr data-ops-task-id="${escapeHtml(event.task_id || '')}">
    <td><code>${escapeHtml(String(event.id))}</code></td>
    <td>${escapeHtml(event.kind || '')}</td>
    <td><code>${escapeHtml(event.task_id || '')}</code></td>
    <td>${formatTimestamp(event.created_at)}</td>
    <td>${escapeHtml(eventError(event))}</td>
  </tr>`).join('');
  return section(t('opsRecentFailures'), items.length ? table(['ID', 'Kind', 'Task', t('created'), t('opsLastError')], rows) : empty(t('opsNoFailures')));
}

function section(title, body) {
  return `<section class="ops-section"><div class="section-title"><span>${escapeHtml(title)}</span></div>${body}</section>`;
}

function table(headers, rows) {
  return `<div class="ops-table-wrap"><table class="ops-table"><thead><tr>${headers.map(header => `<th>${escapeHtml(header)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`;
}

function empty(message) {
  return `<p class="ops-empty">${escapeHtml(message)}</p>`;
}

function taskLink(task) {
  return `<button class="ops-task-link" type="button" data-ops-task-id="${escapeHtml(task.id || '')}"><code>${escapeHtml(task.id || '')}</code><span>${escapeHtml(task.title || '')}</span></button>`;
}

export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || Number.isNaN(Number(seconds))) return '—';
  const value = Math.max(0, Number(seconds));
  if (value < 60) return `${Math.round(value)}s`;
  if (value < 3600) return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
  return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`;
}

export function formatTimestamp(epoch) {
  if (!epoch) return '—';
  const date = new Date(Number(epoch) * 1000);
  if (Number.isNaN(date.getTime())) return String(epoch);
  return date.toLocaleString();
}

export function errorSummary(item) {
  const raw = item?.last_error || item?.payload?.error || item?.payload?.summary || '';
  const text = String(raw || '—');
  return text.length > 96 ? `${text.slice(0, 93)}…` : text;
}

function eventError(event) {
  const payload = event.payload || {};
  return errorSummary({ payload, last_error: payload.error || payload.summary || payload.reason || '' });
}
