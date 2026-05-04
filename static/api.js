function tokenHeaders() {
  const token = localStorage.getItem('kanbanToken');
  return token ? { 'X-Kanban-Token': token } : {};
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
  if (!res.ok) {
    const message = data.detail || data.error || res.statusText;
    throw new Error(Array.isArray(message) ? message.map(x => x.msg || JSON.stringify(x)).join(', ') : message);
  }
  return data;
}

export const api = {
  health: () => request('/health'),
  status: () => request('/api/service/status'),
  config: () => request('/api/config'),
  boards: () => request('/api/boards'),
  createBoard: payload => request('/api/boards', { method: 'POST', body: payload }),
  switchBoard: slug => request(`/api/boards/${encodeURIComponent(slug)}/switch`, { method: 'POST' }),
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
  comment: (board, id, payload) => request(`/api/tasks/${encodeURIComponent(id)}/comments?${new URLSearchParams({ board })}`, { method: 'POST', body: payload }),
  monitor: (board, id) => request(`/api/tasks/${encodeURIComponent(id)}/monitor?${new URLSearchParams({ board, tail: 65536 })}`),
  events: (board, since = 0) => request(`/api/events?${new URLSearchParams({ board, since })}`)
};
