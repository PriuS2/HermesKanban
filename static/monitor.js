import { api } from './api.js?v=20260505-2';
import { t } from './i18n.js?v=20260505-2';
import { escapeHtml, renderMarkdown } from './markdown.js?v=20260505-2';

function fmtAge(seconds) {
  if (seconds == null) return '—';
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export async function renderMonitor(board, taskId, mount) {
  const data = await api.monitor(board, taskId);
  const run = data.current_run;
  mount.innerHTML = `
    <section class="monitor-card">
      <div class="section-title"><span>${t('monitor')}</span><strong>${escapeHtml(data.task.status)}</strong></div>
      <div class="monitor-grid">
        <div><small>run</small><strong>${run ? run.id : '—'}</strong></div>
        <div><small>pid</small><strong>${data.worker.pid ?? '—'}</strong></div>
        <div><small>elapsed</small><strong>${fmtAge(data.worker.elapsed_seconds)}</strong></div>
        <div><small>heartbeat</small><strong class="${data.heartbeat.overdue ? 'danger' : ''}">${fmtAge(data.heartbeat.age_seconds)}</strong></div>
        <div><small>claim</small><strong>${data.claim.expires_in_seconds == null ? '—' : fmtAge(data.claim.expires_in_seconds)}</strong></div>
        <div><small>workspace</small><strong title="${escapeHtml(data.workspace.path || '')}">${escapeHtml(data.workspace.kind || 'scratch')}</strong></div>
      </div>
      <details open>
        <summary>${t('log')} · ${data.log.exists ? `${data.log.size_bytes} bytes` : 'empty'}</summary>
        <pre class="log-tail">${escapeHtml(data.log.content || '')}</pre>
      </details>
      <details>
        <summary>${t('events')}</summary>
        <ol class="timeline">${data.events.map(ev => `<li><code>${ev.id}</code> ${escapeHtml(ev.kind)} <small>${escapeHtml(JSON.stringify(ev.payload || {}))}</small></li>`).join('')}</ol>
      </details>
      <details>
        <summary>${t('context')}</summary>
        <div class="markdown">${renderMarkdown(data.context_preview || '')}</div>
      </details>
    </section>
  `;
  return data;
}
