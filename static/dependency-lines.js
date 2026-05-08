import { api } from './api.js?v=20260508-02';
import { t } from './i18n.js?v=20260508-02';
import { state, toast } from './state.js?v=20260508-02';

const VIEW_MODES = new Set(['focus', 'all', 'blocked', 'off']);
let currentData = null;
let hoverTaskId = null;
let linkDraft = null;
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
  const from = cardPoint(board, parentCard, 'left', ports.sourceOffset);
  const to = cardPoint(board, childCard, 'right', ports.targetOffset);
  const dx = Math.max(54, Math.abs(to.x - from.x) * 0.42);
  const direction = to.x >= from.x ? 1 : -1;
  return `M ${from.x.toFixed(1)} ${from.y.toFixed(1)} C ${(from.x + direction * dx).toFixed(1)} ${from.y.toFixed(1)}, ${(to.x - direction * dx).toFixed(1)} ${to.y.toFixed(1)}, ${to.x.toFixed(1)} ${to.y.toFixed(1)}`;
}

function portFromElement(el) {
  const port = el?.closest?.('.dependency-port[data-link-role][data-link-task-id]');
  if (!port) return null;
  const role = port.dataset.linkRole;
  if (!['parent', 'child'].includes(role)) return null;
  return { el: port, role, taskId: port.dataset.linkTaskId };
}

function portFromPoint(clientX, clientY) {
  const el = document.elementFromPoint(clientX, clientY);
  return portFromElement(el);
}

function compatiblePorts(source, target) {
  return Boolean(source && target && source.el !== target.el && source.taskId !== target.taskId && source.role !== target.role);
}

function relationFromPorts(source, target) {
  if (!compatiblePorts(source, target)) return null;
  return {
    parent_id: source.role === 'parent' ? source.taskId : target.taskId,
    child_id: source.role === 'child' ? source.taskId : target.taskId,
  };
}

function pointForPort(board, port) {
  if (!port) return null;
  const card = port.el.closest('.task-card[data-task-id]') || visibleCards(board).get(port.taskId);
  if (!card) return null;
  return cardPoint(board, card, port.role === 'parent' ? 'left' : 'right');
}

function clientPoint(board, clientX, clientY) {
  const boardRect = board.getBoundingClientRect();
  return {
    x: clientX - boardRect.left + board.scrollLeft,
    y: clientY - boardRect.top + board.scrollTop,
  };
}

function previewPathFor(board, start, end) {
  const dx = Math.max(54, Math.abs(end.x - start.x) * 0.42);
  const direction = end.x >= start.x ? 1 : -1;
  return `M ${start.x.toFixed(1)} ${start.y.toFixed(1)} C ${(start.x + direction * dx).toFixed(1)} ${start.y.toFixed(1)}, ${(end.x - direction * dx).toFixed(1)} ${end.y.toFixed(1)}, ${end.x.toFixed(1)} ${end.y.toFixed(1)}`;
}

function dependencyPreviewPath(board) {
  if (!linkDraft) return '';
  const start = pointForPort(board, linkDraft.source);
  const targetPoint = linkDraft.target ? pointForPort(board, linkDraft.target) : null;
  const end = targetPoint || clientPoint(board, linkDraft.x, linkDraft.y);
  if (!start || !end) return '';
  const classes = ['dependency-preview-edge'];
  if (linkDraft.target) classes.push(compatiblePorts(linkDraft.source, linkDraft.target) ? 'is-valid' : 'is-invalid');
  return `<path class="${classes.join(' ')}" d="${previewPathFor(board, start, end)}" />`;
}

function clearPortClasses(board) {
  if (!board) return;
  board.classList.remove('is-linking');
  board.querySelectorAll('.dependency-port').forEach(port => {
    port.classList.remove('is-link-source', 'is-link-target', 'is-link-compatible');
  });
}

function updatePortTargets(board, source, target) {
  board.querySelectorAll('.dependency-port').forEach(port => {
    const item = portFromElement(port);
    port.classList.toggle('is-link-source', item?.el === source?.el);
    port.classList.toggle('is-link-target', item?.el === target?.el);
    port.classList.toggle('is-link-compatible', compatiblePorts(source, item));
  });
}

function cleanupBlueprintLinking() {
  document.removeEventListener('pointermove', handleBlueprintPointerMove);
  document.removeEventListener('pointerup', handleBlueprintPointerUp);
  document.removeEventListener('keydown', handleBlueprintKeydown);
  clearPortClasses(boardEl());
  linkDraft = null;
  scheduleDraw();
}

function startBlueprintLink(ev, portEl) {
  const source = portFromElement(portEl);
  if (!source) return;
  ev.preventDefault();
  ev.stopPropagation();
  if (linkDraft) cleanupBlueprintLinking();
  linkDraft = { source, pointerId: ev.pointerId, x: ev.clientX, y: ev.clientY, target: null };
  const board = boardEl();
  if (board) {
    board.classList.add('is-linking');
    updatePortTargets(board, source, null);
  }
  hoverTaskId = source.taskId;
  document.addEventListener('pointermove', handleBlueprintPointerMove, { passive: false });
  document.addEventListener('pointerup', handleBlueprintPointerUp);
  document.addEventListener('keydown', handleBlueprintKeydown);
  scheduleDraw();
}

function handleBlueprintPointerMove(ev) {
  if (!linkDraft || (ev.pointerId !== undefined && linkDraft.pointerId !== undefined && ev.pointerId !== linkDraft.pointerId)) return;
  ev.preventDefault();
  linkDraft.x = ev.clientX;
  linkDraft.y = ev.clientY;
  linkDraft.target = portFromPoint(ev.clientX, ev.clientY);
  const board = boardEl();
  if (board) updatePortTargets(board, linkDraft.source, linkDraft.target);
  scheduleDraw();
}

async function handleBlueprintPointerUp(ev) {
  if (!linkDraft || (ev.pointerId !== undefined && linkDraft.pointerId !== undefined && ev.pointerId !== linkDraft.pointerId)) return;
  ev.preventDefault();
  ev.stopPropagation();
  const source = linkDraft.source;
  const target = portFromPoint(ev.clientX, ev.clientY) || linkDraft.target;
  const sameTask = Boolean(target && source.taskId === target.taskId);
  const relation = relationFromPorts(source, target);
  cleanupBlueprintLinking();
  if (!target) return;
  if (!relation) {
    toast(sameTask ? t('linkSameTaskToast') : t('linkInvalidToast'), 'error');
    return;
  }
  try {
    await api.linkTask(state.board, relation);
    toast(`${t('linkCreatedToast')} ${relation.parent_id} → ${relation.child_id}`);
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
  } catch (err) {
    toast(err.message || String(err), 'error');
  }
}

function handleBlueprintKeydown(ev) {
  if (ev.key !== 'Escape') return;
  ev.preventDefault();
  cleanupBlueprintLinking();
}

export function setupBlueprintLinking(board) {
  if (!board || board.dataset.blueprintLinking === 'true') return;
  board.dataset.blueprintLinking = 'true';
  board.addEventListener('pointerdown', ev => {
    const port = ev.target.closest?.('.dependency-port[data-link-role][data-link-task-id]');
    if (!port) return;
    startBlueprintLink(ev, port);
  }, true);
  board.addEventListener('click', ev => {
    if (!ev.target.closest?.('.dependency-port')) return;
    ev.preventDefault();
    ev.stopPropagation();
  }, true);
  board.addEventListener('dragstart', ev => {
    if (ev.target.closest?.('.dependency-port')) ev.preventDefault();
  }, true);
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

function markerDefs() {
  return '<defs><marker id="dependency-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" /></marker></defs>';
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

  const preview = dependencyPreviewPath(board);
  if ((currentMode === 'off' || !edges.length) && !preview) {
    svg.innerHTML = '';
    return;
  }
  if (currentMode === 'off' || !edges.length) {
    svg.innerHTML = `${markerDefs()}${preview}`;
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

  svg.innerHTML = `${markerDefs()}${paths}${preview}`;
}

function scheduleDraw() {
  if (raf) cancelAnimationFrame(raf);
  raf = requestAnimationFrame(draw);
}

function attachBoardListeners(board) {
  if (board.dataset.dependencyListeners === 'true') return;
  board.dataset.dependencyListeners = 'true';
  board.addEventListener('scroll', scheduleDraw, { passive: true });
  setupBlueprintLinking(board);
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
