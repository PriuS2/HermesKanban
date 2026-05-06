import { state } from './state.js?v=20260506-03';

const VIEW_MODES = new Set(['focus', 'all', 'blocked', 'off']);
let currentData = null;
let hoverTaskId = null;
let raf = 0;

function validMode(value) {
  return VIEW_MODES.has(value) ? value : 'focus';
}

function mode() {
  state.dependencyView = validMode(state.dependencyView);
  return state.dependencyView;
}

function boardEl() {
  return document.getElementById('board');
}

function overlayEl(board) {
  let svg = board.querySelector(':scope > svg.dependency-overlay');
  if (!svg) {
    svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('dependency-overlay');
    svg.setAttribute('aria-hidden', 'true');
    board.prepend(svg);
  }
  return svg;
}

function taskMaps(data) {
  const tasks = new Map();
  for (const task of data?.tasks || []) tasks.set(task.id, task);
  return tasks;
}

function visibleCards(board) {
  const cards = new Map();
  board.querySelectorAll('.task-card[data-task-id]').forEach(card => cards.set(card.dataset.taskId, card));
  return cards;
}

function edgeIsBlocked(edge, tasks) {
  const parent = tasks.get(edge.parent_id);
  const child = tasks.get(edge.child_id);
  return child?.status === 'blocked' || parent?.status === 'blocked';
}

function edgeIsDone(edge, tasks) {
  return tasks.get(edge.parent_id)?.status === 'done';
}

function focusId() {
  return hoverTaskId || state.selectedTaskId || null;
}

function activeEdge(edge, id) {
  return Boolean(id && (edge.parent_id === id || edge.child_id === id));
}

function filteredEdges(data, board, tasks, id) {
  const cards = visibleCards(board);
  const raw = (data?.links || []).filter(edge => cards.has(edge.parent_id) && cards.has(edge.child_id));
  const currentMode = mode();
  if (currentMode === 'off') return [];
  if (currentMode === 'focus') return id ? raw.filter(edge => activeEdge(edge, id)) : [];
  if (currentMode === 'blocked') return raw.filter(edge => edgeIsBlocked(edge, tasks));
  return raw;
}

function edgeKey(edge) {
  return `${edge.parent_id}\u2192${edge.child_id}`;
}

function cardCenterY(card) {
  const rect = card.getBoundingClientRect();
  return rect.top + rect.height / 2;
}

function groupedEdges(edges, keyFn) {
  const groups = new Map();
  for (const edge of edges) {
    const key = keyFn(edge);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(edge);
  }
  return groups;
}

function portOffset(index, total, card) {
  if (total <= 1 || !card) return 0;
  const rect = card.getBoundingClientRect();
  const maxOffset = Math.max(6, rect.height / 2 - 18);
  const laneGap = Math.min(14, (maxOffset * 2) / (total - 1));
  return (index - (total - 1) / 2) * laneGap;
}

function assignEdgePorts(edges, cards) {
  const ports = new Map();
  for (const edge of edges) ports.set(edgeKey(edge), { sourceOffset: 0, targetOffset: 0 });

  for (const [parentId, group] of groupedEdges(edges, edge => edge.parent_id)) {
    const parentCard = cards.get(parentId);
    const sorted = [...group].sort((a, b) => {
      const ay = cardCenterY(cards.get(a.child_id));
      const by = cardCenterY(cards.get(b.child_id));
      return ay - by || a.child_id.localeCompare(b.child_id);
    });
    sorted.forEach((edge, index) => {
      ports.get(edgeKey(edge)).sourceOffset = portOffset(index, sorted.length, parentCard);
    });
  }

  for (const [childId, group] of groupedEdges(edges, edge => edge.child_id)) {
    const childCard = cards.get(childId);
    const sorted = [...group].sort((a, b) => {
      const ay = cardCenterY(cards.get(a.parent_id));
      const by = cardCenterY(cards.get(b.parent_id));
      return ay - by || a.parent_id.localeCompare(b.parent_id);
    });
    sorted.forEach((edge, index) => {
      ports.get(edgeKey(edge)).targetOffset = portOffset(index, sorted.length, childCard);
    });
  }

  return ports;
}

function cardPoint(board, card, side, offset = 0) {
  const boardRect = board.getBoundingClientRect();
  const rect = card.getBoundingClientRect();
  const maxOffset = Math.max(0, rect.height / 2 - 14);
  const safeOffset = Math.max(-maxOffset, Math.min(maxOffset, offset));
  const x = (side === 'right' ? rect.right : rect.left) - boardRect.left + board.scrollLeft;
  const y = rect.top + rect.height / 2 + safeOffset - boardRect.top + board.scrollTop;
  return { x, y };
}

function pathFor(board, parentCard, childCard, ports = { sourceOffset: 0, targetOffset: 0 }) {
  const parentRect = parentCard.getBoundingClientRect();
  const childRect = childCard.getBoundingClientRect();
  const forward = parentRect.left <= childRect.left;
  const from = cardPoint(board, parentCard, forward ? 'right' : 'left', ports.sourceOffset);
  const to = cardPoint(board, childCard, forward ? 'left' : 'right', ports.targetOffset);
  const dx = Math.max(54, Math.abs(to.x - from.x) * 0.42);
  const curve = forward ? dx : -dx;
  return `M ${from.x.toFixed(1)} ${from.y.toFixed(1)} C ${(from.x + curve).toFixed(1)} ${from.y.toFixed(1)}, ${(to.x - curve).toFixed(1)} ${to.y.toFixed(1)}, ${to.x.toFixed(1)} ${to.y.toFixed(1)}`;
}

function resetCardClasses(board) {
  board.querySelectorAll('.task-card').forEach(card => {
    card.classList.remove('dependency-focus', 'dependency-parent', 'dependency-child', 'dependency-dim', 'dependency-blocked');
  });
}

function markCards(board, edges, tasks, id) {
  resetCardClasses(board);
  const currentMode = mode();
  if (!edges.length || currentMode === 'off') return;
  const cards = visibleCards(board);
  const related = new Set();
  if (id && cards.has(id)) {
    cards.get(id).classList.add('dependency-focus');
    related.add(id);
  }
  for (const edge of edges) {
    const parent = cards.get(edge.parent_id);
    const child = cards.get(edge.child_id);
    if (!parent || !child) continue;
    if (id && edge.child_id === id) parent.classList.add('dependency-parent');
    if (id && edge.parent_id === id) child.classList.add('dependency-child');
    if (edgeIsBlocked(edge, tasks)) {
      parent.classList.add('dependency-blocked');
      child.classList.add('dependency-blocked');
    }
    if (id && activeEdge(edge, id)) {
      related.add(edge.parent_id);
      related.add(edge.child_id);
    }
  }
  if (currentMode === 'focus' && id) {
    board.querySelectorAll('.task-card').forEach(card => {
      if (!related.has(card.dataset.taskId)) card.classList.add('dependency-dim');
    });
  }
}

function draw() {
  raf = 0;
  const board = boardEl();
  if (!board || !currentData) return;
  const svg = overlayEl(board);
  const currentMode = mode();
  const tasks = taskMaps(currentData);
  const id = focusId();
  const edges = filteredEdges(currentData, board, tasks, id);
  markCards(board, edges, tasks, id);

  svg.style.width = `${board.scrollWidth}px`;
  svg.style.height = `${board.scrollHeight}px`;
  svg.setAttribute('width', String(board.scrollWidth));
  svg.setAttribute('height', String(board.scrollHeight));
  svg.setAttribute('viewBox', `0 0 ${board.scrollWidth} ${board.scrollHeight}`);
  if (currentMode === 'off' || !edges.length) {
    svg.innerHTML = '';
    return;
  }

  const cards = visibleCards(board);
  const ports = assignEdgePorts(edges, cards);
  const paths = edges.map(edge => {
    const parent = cards.get(edge.parent_id);
    const child = cards.get(edge.child_id);
    if (!parent || !child) return '';
    const classes = ['dependency-edge'];
    if (activeEdge(edge, id)) classes.push('is-active');
    if (edge.child_id === id) classes.push('is-incoming');
    if (edge.parent_id === id) classes.push('is-outgoing');
    if (edgeIsBlocked(edge, tasks)) classes.push('is-blocked');
    if (edgeIsDone(edge, tasks)) classes.push('is-done');
    if (id && currentMode === 'all' && !activeEdge(edge, id)) classes.push('is-muted');
    const edgePorts = ports.get(edgeKey(edge)) || { sourceOffset: 0, targetOffset: 0 };
    return `<path class="${classes.join(' ')}" d="${pathFor(board, parent, child, edgePorts)}" data-parent-id="${edge.parent_id}" data-child-id="${edge.child_id}" data-source-offset="${edgePorts.sourceOffset.toFixed(1)}" data-target-offset="${edgePorts.targetOffset.toFixed(1)}" />`;
  }).join('');

  svg.innerHTML = `<defs><marker id="dependency-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" /></marker></defs>${paths}`;
}

function scheduleDraw() {
  if (raf) cancelAnimationFrame(raf);
  raf = requestAnimationFrame(draw);
}

function attachBoardListeners(board) {
  if (board.dataset.dependencyListeners === 'true') return;
  board.dataset.dependencyListeners = 'true';
  board.addEventListener('scroll', scheduleDraw, { passive: true });
}

export function setupDependencyControls() {
  const saved = validMode(localStorage.getItem('dependencyView'));
  state.dependencyView = saved;
  const select = document.getElementById('dependencyView');
  if (select) {
    select.value = saved;
    select.addEventListener('change', ev => {
      state.dependencyView = validMode(ev.target.value);
      localStorage.setItem('dependencyView', state.dependencyView);
      scheduleDraw();
    });
  }
  window.addEventListener('resize', scheduleDraw);
  document.addEventListener('kanban:dependency-selected', ev => {
    state.selectedTaskId = ev.detail?.taskId || null;
    scheduleDraw();
  });
}

export function renderDependencyOverlay(data) {
  currentData = data;
  const board = boardEl();
  if (!board) return;
  attachBoardListeners(board);
  scheduleDraw();
}

export function focusDependencyTask(taskId) {
  hoverTaskId = taskId || null;
  scheduleDraw();
}

export function clearDependencyFocus(taskId) {
  if (!taskId || hoverTaskId === taskId) {
    hoverTaskId = null;
    scheduleDraw();
  }
}

export function selectDependencyTask(taskId) {
  state.selectedTaskId = taskId || null;
  document.dispatchEvent(new CustomEvent('kanban:dependency-selected', { detail: { taskId: state.selectedTaskId } }));
}
