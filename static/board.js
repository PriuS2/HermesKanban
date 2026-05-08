import { t } from './i18n.js?v=20260508-01';
import { escapeHtml } from './markdown.js?v=20260508-01';
import { openTaskDrawer } from './drawer.js?v=20260508-01';
import { attachDragHandlers } from './dragdrop.js?v=20260508-01';
import { clearDependencyFocus, focusDependencyTask, renderDependencyOverlay, selectDependencyTask } from './dependency-lines.js?v=20260508-01';

function card(task) {
  const isUnassigned = !task.assignee;
  const assigneeHint = escapeHtml(t('profileMissing'));
  const assigneeChip = task.assignee
    ? `<span>@${escapeHtml(task.assignee)}</span>`
    : `<span class="missing-assignee-chip" title="${assigneeHint}">⚠ ${assigneeHint}</span>`;
  const chips = [task.tenant, task.priority ? `P${task.priority}` : null].filter(Boolean);
  const parents = Number(task.link_counts?.parents || 0);
  const children = Number(task.link_counts?.children || 0);
  const progress = task.progress ? `<span>${task.progress.done}/${task.progress.total}</span>` : '';
  const workflow = task.workflow_template_id || task.current_step_key
    ? `<span class="workflow-chip" title="${escapeHtml(task.workflow_template_id || '')}">↔ ${escapeHtml(task.current_step_key || task.workflow_template_id || 'workflow')}</span>`
    : '';
  const taskId = escapeHtml(task.id);
  const childPortHint = escapeHtml(t('childPortHint'));
  const parentPortHint = escapeHtml(t('parentPortHint'));
  return `<article class="task-card ${task.status}${isUnassigned ? ' is-unassigned' : ''}" data-task-id="${taskId}" data-parent-count="${parents}" data-child-count="${children}" data-assignee-state="${isUnassigned ? 'missing' : 'assigned'}" tabindex="0">
    <button type="button" class="dependency-port child-port" data-link-role="child" data-link-task-id="${taskId}" title="${childPortHint}" aria-label="${childPortHint}"><span>${escapeHtml(t('child'))}</span></button>
    <button type="button" class="dependency-port parent-port" data-link-role="parent" data-link-task-id="${taskId}" title="${parentPortHint}" aria-label="${parentPortHint}"><span>${escapeHtml(t('parent'))}</span></button>
    <div class="card-top"><code>${taskId}</code>${isUnassigned ? `<span class="profile-missing-badge" title="${assigneeHint}" aria-label="${assigneeHint}">⚠ ${escapeHtml(t('profileMissingShort'))}</span>` : ''}<span class="status-dot ${task.status}"></span></div>
    <h3>${escapeHtml(task.title)}</h3>
    ${task.body_preview ? `<p>${escapeHtml(task.body_preview)}</p>` : ''}
    <div class="chips">${assigneeChip}${chips.map(x => `<span>${escapeHtml(x)}</span>`).join('')}${progress}${workflow}</div>
    <div class="card-foot"><span>💬 ${task.comment_count || 0}</span><span class="relation-badge" title="parents ${parents} · children ${children}">↑ ${parents} ↓ ${children}</span>${task.status === 'running' ? '<strong>LIVE</strong>' : ''}</div>
  </article>`;
}

export function renderKpis(data) {
  const root = document.getElementById('kpiRow');
  const stats = data.stats?.by_status || {};
  const statuses = data.column_order || [];
  root.style.setProperty('--kpi-column-count', String(Math.max(1, statuses.length)));
  root.innerHTML = statuses.map(status => `<div class="kpi"><small>${t(status)}</small><strong>${stats[status] || 0}</strong></div>`).join('');
}

export function renderBoard(data) {
  const root = document.getElementById('board');
  const statuses = data.column_order || [];
  root.style.setProperty('--kanban-column-count', String(Math.max(1, statuses.length)));
  root.innerHTML = statuses.map(status => {
    const tasks = data.columns[status] || [];
    return `<section class="board-column" data-status="${status}">
      <header><div><h2>${t(status)}</h2><small>${tasks.length}</small></div><button class="mini-add" data-status="${status}">＋</button></header>
      <div class="drop-placeholder"></div>
      <div class="cards">${tasks.length ? tasks.map(card).join('') : `<div class="empty">${t('empty')}</div>`}</div>
    </section>`;
  }).join('');
  root.querySelectorAll('.task-card').forEach(el => {
    const open = () => {
      selectDependencyTask(el.dataset.taskId);
      openTaskDrawer(el.dataset.taskId);
    };
    el.addEventListener('mouseenter', () => focusDependencyTask(el.dataset.taskId));
    el.addEventListener('mouseleave', () => clearDependencyFocus(el.dataset.taskId));
    el.addEventListener('focus', () => focusDependencyTask(el.dataset.taskId));
    el.addEventListener('blur', () => clearDependencyFocus(el.dataset.taskId));
    el.addEventListener('click', open);
    el.addEventListener('keydown', ev => { if (ev.key === 'Enter') open(); });
  });
  root.querySelectorAll('.mini-add').forEach(btn => btn.addEventListener('click', () => {
    document.dispatchEvent(new CustomEvent('kanban:open-task-create', { detail: { status: btn.dataset.status } }));
  }));
  attachDragHandlers(root);
  renderDependencyOverlay(data);
}
