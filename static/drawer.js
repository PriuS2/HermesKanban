import { api } from './api.js?v=20260505-2';
import { t, applyI18n } from './i18n.js?v=20260505-2';
import { renderMarkdown, escapeHtml } from './markdown.js?v=20260505-2';
import { renderMonitor } from './monitor.js?v=20260505-2';
import { state, toast } from './state.js?v=20260505-2';

export function closeDrawer() {
  const drawer = document.getElementById('drawer');
  const overlay = document.getElementById('overlay');
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  overlay.hidden = true;
  state.selectedTaskId = null;
}

async function actionStatus(status, extra = {}) {
  if (!state.selectedTaskId) return;
  await api.updateTask(state.board, state.selectedTaskId, { status, ...extra });
  toast(`status → ${status}`);
  document.dispatchEvent(new CustomEvent('kanban:refresh'));
  await openTaskDrawer(state.selectedTaskId);
}

export async function openTaskDrawer(taskId) {
  state.selectedTaskId = taskId;
  const drawer = document.getElementById('drawer');
  const overlay = document.getElementById('overlay');
  drawer.classList.add('open');
  drawer.setAttribute('aria-hidden', 'false');
  overlay.hidden = false;
  drawer.innerHTML = '<div class="drawer-loading">Loading…</div>';
  const detail = await api.task(state.board, taskId);
  const task = detail.task;
  drawer.innerHTML = `
    <div class="drawer-header">
      <div><code>${escapeHtml(task.id)}</code><h2 contenteditable="true" id="editTitle">${escapeHtml(task.title)}</h2></div>
      <button class="icon-button" id="drawerClose" aria-label="close">×</button>
    </div>
    <div class="drawer-meta">
      <span class="status ${task.status}">${escapeHtml(task.status)}</span>
      <span>@${escapeHtml(task.assignee || 'unassigned')}</span>
      <span>${t('priority')} ${task.priority}</span>
      ${task.tenant ? `<span>${escapeHtml(task.tenant)}</span>` : ''}
    </div>
    <div class="drawer-actions">
      <button data-action="ready" class="button ghost">ready</button>
      <button data-action="blocked" class="button ghost">${t('block')}</button>
      <button data-action="done" class="button ghost">${t('complete')}</button>
      <button data-action="archived" class="button ghost danger-btn">${t('archive')}</button>
      <button id="saveTitle" class="button primary">${t('save')}</button>
    </div>
    <section id="monitorMount"></section>
    <section class="drawer-section"><h3>Body</h3><div class="markdown">${renderMarkdown(task.body || '')}</div></section>
    <section class="drawer-section"><h3>${t('comments')}</h3>
      <ol class="comment-list">${detail.comments.map(c => `<li><strong>${escapeHtml(c.author)}</strong><p>${escapeHtml(c.body)}</p></li>`).join('')}</ol>
      <form id="commentForm" class="comment-form"><textarea name="body" placeholder="${t('addComment')}"></textarea><button class="button">${t('addComment')}</button></form>
    </section>
    <section class="drawer-section"><h3>${t('runs')}</h3><ol class="timeline">${detail.runs.map(r => `<li><code>${r.id}</code> ${escapeHtml(r.status)} <small>${r.summary ? escapeHtml(r.summary) : ''}</small></li>`).join('')}</ol></section>
    <section class="drawer-section"><h3>${t('events')}</h3><ol class="timeline">${detail.events.map(e => `<li><code>${e.id}</code> ${escapeHtml(e.kind)}</li>`).join('')}</ol></section>
  `;
  applyI18n(drawer);
  drawer.querySelector('#drawerClose').addEventListener('click', closeDrawer);
  drawer.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const status = btn.dataset.action;
      if (status === 'blocked') {
        const reason = prompt('block reason?') || '';
        await actionStatus(status, { block_reason: reason });
      } else if (status === 'done') {
        const summary = prompt('completion summary?') || '';
        await actionStatus(status, { summary, result: summary });
      } else if (status === 'archived') {
        if (confirm('Archive this task?')) await actionStatus(status);
      } else {
        await actionStatus(status);
      }
    });
  });
  drawer.querySelector('#saveTitle').addEventListener('click', async () => {
    const title = drawer.querySelector('#editTitle').textContent.trim();
    await api.updateTask(state.board, task.id, { title });
    toast('saved');
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
  });
  drawer.querySelector('#commentForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const body = new FormData(ev.currentTarget).get('body');
    await api.comment(state.board, task.id, { body, author: 'kanban-webui' });
    toast('comment added');
    await openTaskDrawer(task.id);
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
  });
  if (task.status === 'running' || task.current_run_id) {
    await renderMonitor(state.board, task.id, drawer.querySelector('#monitorMount'));
  }
}
