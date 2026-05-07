function tokenHeaders() {
  const token = localStorage.getItem('kanbanToken');
  return token ? { 'X-Kanban-Token': token } : {};
}

function errorMessage(data, fallback) {
  const message = data.detail || data.error || fallback;
  if (Array.isArray(message)) return message.map(x => x.msg || JSON.stringify(x)).join(', ');
  if (message && typeof message === 'object') return JSON.stringify(message);
  return message;
}

export async function request(path, options = {}) {
  const headers = { ...(options.headers || {}), ...tokenHeaders() };
  let body = options.body;
  if (body && typeof body !== 'string' && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }
  const res = await fetch(path, { ...options, headers, body });
  const text = await res.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = { raw: text }; }
  if (!res.ok) throw new Error(errorMessage(data, res.statusText));
  return data;
}

function boardQuery(board, extra = {}) {
  const clean = { ...extra };
  if (board) clean.board = board;
  return new URLSearchParams(clean).toString();
}

export const api = {
  health: () => request('/health'),
  status: () => request('/api/service/status'),
  appUpdateStatus: () => request('/api/app/update-status'),
  applyAppUpdate: () => request('/api/app/update', { method: 'POST' }),
  config: () => request('/api/config'),
  boards: () => request('/api/boards'),
  createBoard: payload => request('/api/boards', { method: 'POST', body: payload }),
  switchBoard: slug => request(`/api/boards/${encodeURIComponent(slug)}/switch`, { method: 'POST' }),
  createWorkflowDraft: (board, payload) => request(`/api/workflows/drafts?${boardQuery(board)}`, { method: 'POST', body: payload }),
  getWorkflowDraft: (board, draftId) => request(`/api/workflows/drafts/${encodeURIComponent(draftId)}?${boardQuery(board)}`),
  reviseWorkflowDraft: (board, draftId, payload) => request(`/api/workflows/drafts/${encodeURIComponent(draftId)}/revise?${boardQuery(board)}`, { method: 'POST', body: payload }),
  instantiateWorkflowDraft: (board, draftId, payload = {}) => request(`/api/workflows/drafts/${encodeURIComponent(draftId)}/instantiate?${boardQuery(board)}`, { method: 'POST', body: payload }),
  workflowInstance: (board, instanceId) => request(`/api/workflows/instances/${encodeURIComponent(instanceId)}?${boardQuery(board)}`),
  board: params => {
    const clean = {};
    for (const [key, value] of Object.entries(params || {})) {
      if (value !== undefined && value !== null && value !== '') clean[key] = value;
    }
    const query = new URLSearchParams(clean).toString();
    return request(query ? `/api/board?${query}` : '/api/board');
  },
  createTask: (board, payload) => request(`/api/tasks?${new URLSearchParams({ board })}`, { method: 'POST', body: payload }),
  bulkCreate: (board, payload) => request(`/api/tasks/bulk-create?${new URLSearchParams({ board })}`, { method: 'POST', body: payload }),
  task: (board, id) => request(`/api/tasks/${encodeURIComponent(id)}?${new URLSearchParams({ board })}`),
  updateTask: (board, id, payload) => request(`/api/tasks/${encodeURIComponent(id)}?${new URLSearchParams({ board })}`, { method: 'PATCH', body: payload }),
  comment: (board, id, payload) => request(`/api/tasks/${encodeURIComponent(id)}/comments?${new URLSearchParams({ board })}`, { method: 'POST' , body: payload }),
  linkTask: (board, payload) => request(`/api/links?${new URLSearchParams({ board })}`, { method: 'POST', body: payload }),
  unlinkTask: (board, parentId, childId) => request(`/api/links?${new URLSearchParams({ board, parent_id: parentId, child_id: childId })}`, { method: 'DELETE' }),
  taskLog: (board, id, tail = 100000) => request(`/api/tasks/${encodeURIComponent(id)}/log?${new URLSearchParams({ board, tail })}`),
  homeChannels: (board, id) => request(`/api/home-channels?${new URLSearchParams({ board, task_id: id })}`),
  subscribeHome: (board, id, platform) => request(`/api/tasks/${encodeURIComponent(id)}/home-subscribe/${encodeURIComponent(platform)}?${new URLSearchParams({ board })}`, { method: 'POST' }),
  unsubscribeHome: (board, id, platform) => request(`/api/tasks/${encodeURIComponent(id)}/home-subscribe/${encodeURIComponent(platform)}?${new URLSearchParams({ board })}`, { method: 'DELETE' }),
  monitor: (board, id) => request(`/api/tasks/${encodeURIComponent(id)}/monitor?${new URLSearchParams({ board, tail: 65536 })}`),
  events: (board, since = 0) => request(`/api/events?${new URLSearchParams({ board, since })}`)
};
