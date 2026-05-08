export const state = {
  board: localStorage.getItem('kanbanBoard') || 'default',
  includeArchived: false,
  query: '',
  assignee: '',
  latestEventId: 0,
  data: null,
  config: null,
  selectedTaskId: null,
  dependencyView: localStorage.getItem('dependencyView') || 'focus',
  workflowDraft: null,
  opsOpen: localStorage.getItem('kanbanOpsPanelOpen') === '1',
  opsData: null,
  refreshTimer: null
};

export function setBoard(slug) {
  state.board = slug || 'default';
  localStorage.setItem('kanbanBoard', state.board);
}

export function toast(message, tone = 'info') {
  const el = document.getElementById('toast');
  if (!el) return;
  el.textContent = message;
  el.dataset.tone = tone;
  el.classList.add('visible');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('visible'), 2600);
}
