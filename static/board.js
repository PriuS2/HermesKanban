import { t } from './i18n.js';
import { escapeHtml } from './markdown.js';
import { openTaskDrawer } from './drawer.js';
import { attachDragHandlers } from './dragdrop.js';

function card(task) {
  const chips = [task.assignee ? `@${task.assignee}` : 'unassigned', task.tenant, task.priority ? `P${task.priority}` : null].filter(Boolean);
  const progress = task.progress ? `<span>${task.progress.done}/${task.progress.total}</span>` : '';
  return `<article class="task-card ${task.status}" data-task-id="${escapeHtml(task.id)}" tabindex="0">
    <div class="card-top"><code>${escapeHtml(task.id)}</code><span class="status-dot ${task.status}"></span></div>
    <h3>${escapeHtml(task.title)}</h3>
    ${task.body_preview ? `<p>${escapeHtml(task.body_preview)}</p>` : ''}
    <div class="chips">${chips.map(x => `<span>${escapeHtml(x)}</span>`).join('')}${progress}</div>
    <div class="card-foot"><span>💬 ${task.comment_count || 0}</span><span>↔ ${(task.link_counts?.parents || 0) + (task.link_counts?.children || 0)}</span>${task.status === 'running' ? '<strong>LIVE</strong>' : ''}</div>
  </article>`;
}

export function renderKpis(data) {
  const root = document.getElementById('kpiRow');
  const stats = data.stats?.by_status || {};
  root.innerHTML = data.column_order.map(status => `<div class="kpi"><small>${t(status)}</small><strong>${stats[status] || 0}</strong></div>`).join('');
}

export function renderBoard(data) {
  const root = document.getElementById('board');
  root.innerHTML = data.column_order.map(status => {
    const tasks = data.columns[status] || [];
    return `<section class="board-column" data-status="${status}">
      <header><div><h2>${t(status)}</h2><small>${tasks.length}</small></div><button class="mini-add" data-status="${status}">＋</button></header>
      <div class="drop-placeholder"></div>
      <div class="cards">${tasks.length ? tasks.map(card).join('') : `<div class="empty">${t('empty')}</div>`}</div>
    </section>`;
  }).join('');
  root.querySelectorAll('.task-card').forEach(el => {
    el.addEventListener('click', () => openTaskDrawer(el.dataset.taskId));
    el.addEventListener('keydown', ev => { if (ev.key === 'Enter') openTaskDrawer(el.dataset.taskId); });
  });
  root.querySelectorAll('.mini-add').forEach(btn => btn.addEventListener('click', () => {
    document.getElementById('quickStatus').value = btn.dataset.status;
    document.getElementById('quickTitle').focus();
  }));
  attachDragHandlers(root);
}
