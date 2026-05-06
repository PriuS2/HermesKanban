import { api } from './api.js?v=20260506-03';
import { t, applyI18n } from './i18n.js?v=20260506-03';
import { renderMarkdown, escapeHtml } from './markdown.js?v=20260506-03';
import { renderMonitor } from './monitor.js?v=20260506-03';
import { state, toast } from './state.js?v=20260506-03';

export function closeDrawer() {
  const drawer = document.getElementById('drawer');
  const overlay = document.getElementById('overlay');
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  overlay.hidden = true;
  state.selectedTaskId = null;
  document.dispatchEvent(new CustomEvent('kanban:dependency-selected', { detail: { taskId: null } }));
}

async function actionStatus(status, extra = {}) {
  if (!state.selectedTaskId) return;
  await api.updateTask(state.board, state.selectedTaskId, { status, ...extra });
  toast(`status → ${status}`);
  document.dispatchEvent(new CustomEvent('kanban:refresh'));
  await openTaskDrawer(state.selectedTaskId);
}

function formatTime(value) {
  if (!value) return '—';
  const date = new Date(Number(value) * 1000);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString();
}

function eventPayload(payload) {
  if (!payload || Object.keys(payload).length === 0) return '';
  return `<code>${escapeHtml(JSON.stringify(payload))}</code>`;
}

function runSummary(run) {
  const pieces = [run.status || run.outcome, run.summary, run.started_at ? formatTime(run.started_at) : null].filter(Boolean);
  return pieces.map(escapeHtml).join(' · ');
}

function taskLabel(task) {
  return `${task.id} — ${task.title}`;
}

function availableTasks(boardData, currentId, existingIds) {
  const existing = new Set(existingIds || []);
  return (boardData.tasks || []).filter(task => task.id !== currentId && !existing.has(task.id));
}

function taskOptions(tasks, selected = '') {
  return [`<option value="">— ${t('chooseTask')} —</option>`]
    .concat(tasks.map(task => `<option value="${escapeHtml(task.id)}" ${task.id === selected ? 'selected' : ''}>${escapeHtml(taskLabel(task))}</option>`))
    .join('');
}

function taskLookup(boardData) {
  const map = new Map();
  for (const task of boardData?.tasks || []) map.set(task.id, task);
  return map;
}

function dependencyMiniNode(id, role, tasks, isCurrent = false) {
  const task = isCurrent ? tasks.get(id) || { id, title: id, status: 'todo' } : tasks.get(id);
  const title = task?.title || id;
  const status = task?.status || 'unknown';
  const label = isCurrent ? t('currentTask') : t(role);
  return `<button type="button" class="dependency-mini-node ${role} ${isCurrent ? 'current' : ''} ${escapeHtml(status)}" data-mini-task-id="${escapeHtml(id)}">
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(title)}</strong>
    <code>${escapeHtml(id)}</code>
  </button>`;
}

function dependencyMiniMap(detail, boardData, task) {
  const parents = detail.links.parents || [];
  const children = detail.links.children || [];
  const tasks = taskLookup(boardData);
  tasks.set(task.id, task);
  if (!parents.length && !children.length) {
    return `<div class="dependency-mini-map empty-map"><p class="muted">${t('noDependencies')}</p>${dependencyMiniNode(task.id, 'current', tasks, true)}</div>`;
  }
  const parentNodes = parents.length ? parents.map(id => dependencyMiniNode(id, 'parent', tasks)).join('') : `<p class="muted">${t('none')}</p>`;
  const childNodes = children.length ? children.map(id => dependencyMiniNode(id, 'child', tasks)).join('') : `<p class="muted">${t('none')}</p>`;
  return `<div class="dependency-mini-map">
    <div class="dependency-mini-lane parents"><strong>${t('parents')}</strong>${parentNodes}</div>
    <div class="dependency-mini-current"><span></span>${dependencyMiniNode(task.id, 'current', tasks, true)}<span></span></div>
    <div class="dependency-mini-lane children"><strong>${t('children')}</strong>${childNodes}</div>
  </div>`;
}

function assigneeOptions(assignees, current) {
  const names = new Set((assignees || []).map(item => item.name));
  if (current && !names.has(current)) assignees = [...assignees, { name: current, on_disk: false }];
  return [`<option value="">${t('unassigned')}</option>`]
    .concat((assignees || []).map(item => {
      const suffix = item.on_disk ? t('agentProfile') : t('manualAssignee');
      return `<option value="${escapeHtml(item.name)}" ${item.name === current ? 'selected' : ''}>${escapeHtml(item.name)} · ${escapeHtml(suffix)}</option>`;
    }))
    .join('');
}

function dependencyList(ids, role, taskId) {
  if (!ids?.length) return `<p class="muted">${t('none')}</p>`;
  return `<ul class="dependency-list">${ids.map(id => {
    const parentId = role === 'parent' ? id : taskId;
    const childId = role === 'parent' ? taskId : id;
    return `<li><code>${escapeHtml(id)}</code><button class="button ghost danger-btn" data-link-action="remove" data-parent-id="${escapeHtml(parentId)}" data-child-id="${escapeHtml(childId)}">${t('remove')}</button></li>`;
  }).join('')}</ul>`;
}

function homeChannelButtons(homeChannels) {
  if (!homeChannels?.length) return `<p class="muted">${t('noHomeChannels')}</p>`;
  return `<div class="home-channels">${homeChannels.map(home => {
    const label = home.subscribed ? `${home.platform} ✓` : home.platform;
    const title = `${home.name || 'Home'} ${home.thread_id ? `#${home.thread_id}` : ''}`.trim();
    return `<button class="button ${home.subscribed ? 'primary' : 'ghost'}" data-home-platform="${escapeHtml(home.platform)}" data-subscribed="${home.subscribed ? 'true' : 'false'}" title="${escapeHtml(title)}">${escapeHtml(label)}</button>`;
  }).join('')}</div>`;
}

function workflowInstanceId(task) {
  const key = task.idempotency_key || '';
  if (!key.startsWith('workflow:')) return '';
  return key.split(':')[1] || '';
}

function workflowDetailSection(task) {
  if (!task.workflow_template_id && !task.current_step_key && !task.idempotency_key) return '';
  const instance = workflowInstanceId(task);
  return `<section class="drawer-section workflow-detail">
    <div class="section-title"><h3>${t('workflow')}</h3></div>
    <div class="detail-grid workflow-meta">
      <span><strong>${t('workflowTemplate')}</strong>${escapeHtml(task.workflow_template_id || '—')}</span>
      <span><strong>${t('workflowStep')}</strong>${escapeHtml(task.current_step_key || '—')}</span>
      ${instance ? `<span><strong>${t('workflowInstance')}</strong>${escapeHtml(instance)}</span>` : ''}
      ${task.idempotency_key ? `<span><strong>Idempotency</strong><code>${escapeHtml(task.idempotency_key)}</code></span>` : ''}
    </div>
  </section>`;
}

async function renderWorkerLog(taskId, root) {
  const pre = root.querySelector('#workerLogContent');
  if (!pre) return;
  pre.textContent = 'Loading…';
  try {
    const log = await api.taskLog(state.board, taskId);
    pre.textContent = log.content || `— ${t('noWorkerLog')} —`;
  } catch (err) {
    pre.textContent = err.message || String(err);
  }
}

export async function openTaskDrawer(taskId) {
  state.selectedTaskId = taskId;
  document.dispatchEvent(new CustomEvent('kanban:dependency-selected', { detail: { taskId } }));
  const drawer = document.getElementById('drawer');
  const overlay = document.getElementById('overlay');
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  overlay.hidden = false;
  drawer.innerHTML = '<div class="drawer-loading">Loading…</div>';

  const [detail, boardData, homes] = await Promise.all([
    api.task(state.board, taskId),
    api.board({ board: state.board, include_archived: true }),
    api.homeChannels(state.board, taskId).catch(() => ({ home_channels: [] }))
  ]);
  const task = detail.task;
  const parentOptions = taskOptions(availableTasks(boardData, task.id, detail.links.parents));
  const childOptions = taskOptions(availableTasks(boardData, task.id, detail.links.children));

  drawer.innerHTML = `
    <div class="drawer-header">
      <div><code>${escapeHtml(task.id)}</code><h2>${escapeHtml(task.title)}</h2></div>
      <button class="icon-button" id="drawerClose" aria-label="close">×</button>
    </div>

    <form id="taskMetaForm" class="drawer-section inline-form">
      <label>${t('title')}<input id="editTitle" name="title" value="${escapeHtml(task.title)}" /></label>
      <label>${t('assignee')}<select name="assignee">${assigneeOptions(boardData.assignees || [], task.assignee)}</select></label>
      <label>${t('priority')}<input name="priority" type="number" value="${Number(task.priority || 0)}" /></label>
      <button class="button primary" data-assignee-save data-priority-save>${t('save')}</button>
    </form>

    <div class="drawer-meta detail-grid">
      <span><strong>${t('status')}</strong>${escapeHtml(task.status)}</span>
      <span><strong>${t('workspace')}</strong>${escapeHtml(task.workspace_kind || 'scratch')}</span>
      <span><strong>${t('createdBy')}</strong>${escapeHtml(task.created_by || '—')}</span>
      <span><strong>${t('created')}</strong>${formatTime(task.created_at)}</span>
      ${task.tenant ? `<span><strong>Tenant</strong>${escapeHtml(task.tenant)}</span>` : ''}
    </div>

    ${workflowDetailSection(task)}

    <div class="drawer-actions">
      <button data-action="triage" data-status="triage" class="button ghost">→ triage</button>
      <button data-action="ready" data-status="ready" class="button ghost">→ ready</button>
      <button data-action="block" data-status="blocked" class="button ghost">${t('block')}</button>
      <button data-action="unblock" data-status="ready" class="button ghost">${t('unblock')}</button>
      <button data-action="complete" data-status="done" class="button ghost">${t('complete')}</button>
      <button data-action="archive" data-status="archived" class="button ghost danger-btn">${t('archive')}</button>
    </div>

    <section id="monitorMount"></section>

    <section class="drawer-section">
      <div class="section-title"><h3>${t('body')}</h3></div>
      <div class="markdown">${task.body ? renderMarkdown(task.body) : `<p class="muted">— ${t('noDescription')} —</p>`}</div>
      <form id="bodyEditForm" class="comment-form"><textarea name="body" rows="7">${escapeHtml(task.body || '')}</textarea><button class="button">${t('save')}</button></form>
    </section>

    <section class="drawer-section">
      <div class="section-title"><h3>${t('dependencies')}</h3></div>
      <div class="section-title dependency-map-title"><h4>${t('dependencyMap')}</h4></div>
      ${dependencyMiniMap(detail, boardData, task)}
      <div class="dependency-grid">
        <div><strong>${t('parents')}</strong>${dependencyList(detail.links.parents, 'parent', task.id)}
          <form id="addParentForm" class="dependency-form"><select id="addParentSelect" name="parent_id">${parentOptions}</select><button class="button">+ ${t('parent')}</button></form>
        </div>
        <div><strong>${t('children')}</strong>${dependencyList(detail.links.children, 'child', task.id)}
          <form id="addChildForm" class="dependency-form"><select id="addChildSelect" name="child_id">${childOptions}</select><button class="button">+ ${t('child')}</button></form>
        </div>
      </div>
    </section>

    <section class="drawer-section">
      <div class="section-title"><h3>${t('notifyHomeChannels')}</h3></div>
      ${homeChannelButtons(homes.home_channels)}
    </section>

    <section class="drawer-section"><h3>${t('comments')} (${detail.comments.length})</h3>
      <ol class="comment-list">${detail.comments.length ? detail.comments.map(c => `<li><strong>${escapeHtml(c.author)}</strong><small>${formatTime(c.created_at)}</small><p>${escapeHtml(c.body)}</p></li>`).join('') : `<li>${t('empty')}</li>`}</ol>
      <form id="commentForm" class="comment-form"><textarea name="body" placeholder="${t('addComment')}"></textarea><button class="button">${t('addComment')}</button></form>
    </section>

    <section class="drawer-section"><h3>${t('runs')}</h3><ol class="timeline">${detail.runs.length ? detail.runs.map(r => `<li><code>${r.id}</code> ${runSummary(r)}</li>`).join('') : `<li>${t('empty')}</li>`}</ol></section>
    <section class="drawer-section"><h3>${t('events')}</h3><ol class="timeline">${detail.events.map(e => `<li><code>${e.id}</code> ${escapeHtml(e.kind)} ${eventPayload(e.payload)} <small>${formatTime(e.created_at)}</small></li>`).join('')}</ol></section>

    <section class="drawer-section">
      <div class="section-title worker-log-head"><h3>${t('workerLog')}</h3><button class="button ghost" data-log-refresh>${t('refresh')}</button></div>
      <pre id="workerLogContent" class="log-tail"></pre>
    </section>
  `;
  applyI18n(drawer);
  drawer.querySelector('#drawerClose').addEventListener('click', closeDrawer);
  drawer.querySelectorAll('[data-mini-task-id]').forEach(btn => btn.addEventListener('click', async () => {
    const nextTaskId = btn.dataset.miniTaskId;
    if (!nextTaskId || nextTaskId === task.id) return;
    await openTaskDrawer(nextTaskId);
  }));
  drawer.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.action;
      const status = btn.dataset.status;
      if (action === 'block') {
        const reason = prompt('block reason?') || '';
        await actionStatus(status, { block_reason: reason });
      } else if (action === 'complete') {
        const summary = prompt('completion summary?') || '';
        await actionStatus(status, { summary, result: summary });
      } else if (action === 'archive') {
        if (confirm('Archive this task?')) await actionStatus(status);
      } else {
        await actionStatus(status);
      }
    });
  });
  drawer.querySelector('#taskMetaForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const data = new FormData(ev.currentTarget);
    await api.updateTask(state.board, task.id, {
      title: String(data.get('title') || '').trim(),
      assignee: String(data.get('assignee') || ''),
      priority: Number(data.get('priority') || 0)
    });
    toast('saved');
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
    await openTaskDrawer(task.id);
  });
  drawer.querySelector('#bodyEditForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const body = new FormData(ev.currentTarget).get('body');
    await api.updateTask(state.board, task.id, { body: String(body || '') });
    toast('saved');
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
    await openTaskDrawer(task.id);
  });
  drawer.querySelector('#commentForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const body = new FormData(ev.currentTarget).get('body');
    if (!String(body || '').trim()) return;
    await api.comment(state.board, task.id, { body, author: 'kanban-webui' });
    toast('comment added');
    await openTaskDrawer(task.id);
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
  });
  drawer.querySelector('#addParentForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const parentId = new FormData(ev.currentTarget).get('parent_id');
    if (!parentId) return;
    await api.linkTask(state.board, { parent_id: parentId, child_id: task.id });
    toast('parent added');
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
    await openTaskDrawer(task.id);
  });
  drawer.querySelector('#addChildForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const childId = new FormData(ev.currentTarget).get('child_id');
    if (!childId) return;
    await api.linkTask(state.board, { parent_id: task.id, child_id: childId });
    toast('child added');
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
    await openTaskDrawer(task.id);
  });
  drawer.querySelectorAll('[data-link-action="remove"]').forEach(btn => btn.addEventListener('click', async () => {
    await api.unlinkTask(state.board, btn.dataset.parentId, btn.dataset.childId);
    toast('dependency removed');
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
    await openTaskDrawer(task.id);
  }));
  drawer.querySelectorAll('[data-home-platform]').forEach(btn => btn.addEventListener('click', async () => {
    const platform = btn.dataset.homePlatform;
    if (btn.dataset.subscribed === 'true') {
      await api.unsubscribeHome(state.board, task.id, platform);
      toast('notification off');
    } else {
      await api.subscribeHome(state.board, task.id, platform);
      toast('notification on');
    }
    await openTaskDrawer(task.id);
  }));
  drawer.querySelector('[data-log-refresh]').addEventListener('click', () => renderWorkerLog(task.id, drawer));
  await renderWorkerLog(task.id, drawer);
  if (task.status === 'running' || task.current_run_id) {
    await renderMonitor(state.board, task.id, drawer.querySelector('#monitorMount'));
  }
}
