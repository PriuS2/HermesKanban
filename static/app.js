import { api } from './api.js?v=20260506-03';
import { applyI18n, lang, setLang, t } from './i18n.js?v=20260506-03';
import { setupThemeToggle, updateThemeToggleLabel } from './theme.js?v=20260506-03';
import { renderBoard, renderKpis } from './board.js?v=20260506-03';
import { setupDependencyControls } from './dependency-lines.js?v=20260506-03';
import { setupForms } from './forms.js?v=20260506-03';
import { setupMobileFallback } from './mobile.js?v=20260506-03';
import { closeDrawer } from './drawer.js?v=20260506-03';
import { state, setBoard, toast } from './state.js?v=20260506-03';

async function loadBoards() {
  const data = await api.boards();
  const select = document.getElementById('boardSelect');
  select.replaceChildren();
  for (const b of data.boards) {
    const option = document.createElement('option');
    option.value = b.slug;
    option.textContent = `${b.icon || ''} ${b.name || b.slug} (${b.total || 0})`;
    select.appendChild(option);
  }
  if (!data.boards.find(b => b.slug === state.board)) setBoard(data.current || 'default');
  select.value = state.board;
}

async function loadStatus() {
  const status = await api.status();
  document.getElementById('healthDot').classList.toggle('ok', status.ok);
  document.getElementById('healthText').textContent = status.ok ? 'OK' : 'Error';
  document.getElementById('dbPath').textContent = status.db_path || '';
  const serverLabel = document.getElementById('serverLabel');
  if (serverLabel) serverLabel.textContent = `${status.service || 'kanban-webui'} · ${window.location.host}`;
}

function countAssigneeTasks(assignee) {
  return Object.values(assignee.counts || {}).reduce((sum, count) => sum + Number(count || 0), 0);
}

function assigneeOptionLabel(assignee) {
  const count = countAssigneeTasks(assignee);
  const kind = assignee.on_disk ? t('agentProfile') : t('manualAssignee');
  return `${assignee.name} · ${kind}${count ? ` (${count})` : ''}`;
}

function appendOption(select, value, label) {
  const option = document.createElement('option');
  option.value = value;
  option.textContent = label;
  select.appendChild(option);
}

function renderAssigneeControls(data) {
  const assignees = Array.isArray(data.assignees) ? data.assignees : [];
  const profileAssignees = assignees.filter(item => item && item.on_disk);

  const quick = document.getElementById('quickAssignee');
  const previousQuick = quick.value || localStorage.getItem('lastAssignee') || '';
  quick.replaceChildren();
  appendOption(quick, '', t('unassigned'));
  for (const assignee of profileAssignees) appendOption(quick, assignee.name, assigneeOptionLabel(assignee));
  quick.value = profileAssignees.some(item => item.name === previousQuick) ? previousQuick : '';

  const filter = document.getElementById('assigneeFilter');
  const previousFilter = state.assignee || filter.value || '';
  filter.replaceChildren();
  appendOption(filter, '', t('allAssignees'));
  for (const assignee of assignees) appendOption(filter, assignee.name, assigneeOptionLabel(assignee));
  if (assignees.some(item => item.name === previousFilter)) {
    filter.value = previousFilter;
  } else {
    filter.value = '';
    state.assignee = '';
  }
}

export async function load() {
  await api.config().then(cfg => { state.config = cfg; });
  await loadBoards();
  const params = {
    board: state.board,
    include_archived: state.includeArchived,
    q: state.query,
    assignee: state.assignee
  };
  const data = await api.board(params);
  state.data = data;
  state.latestEventId = data.latest_event_id;
  renderAssigneeControls(data);
  document.getElementById('boardTitle').textContent = data.board_meta.name || data.board;
  document.getElementById('boardDescription').textContent = data.board_meta.description || 'Hermes CLI와 같은 DB를 사용하는 전용 칸반 WebUI';
  renderKpis(data);
  renderBoard(data);
  await loadStatus();
}

function setupControls() {
  document.getElementById('refreshBtn').addEventListener('click', load);
  document.getElementById('langToggle').addEventListener('click', () => { setLang(lang() === 'ko' ? 'en' : 'ko'); updateThemeToggleLabel(); load(); });
  document.getElementById('boardSelect').addEventListener('change', async ev => {
    setBoard(ev.target.value);
    await api.switchBoard(state.board);
    await load();
  });
  document.getElementById('archivedToggle').addEventListener('change', ev => { state.includeArchived = ev.target.checked; load(); });
  document.getElementById('searchInput').addEventListener('input', ev => { state.query = ev.target.value; clearTimeout(ev.target._timer); ev.target._timer = setTimeout(load, 250); });
  document.getElementById('assigneeFilter').addEventListener('change', ev => { state.assignee = ev.target.value; load(); });
  document.getElementById('overlay').addEventListener('click', closeDrawer);
  document.addEventListener('kanban:refresh', load);
  document.addEventListener('keydown', ev => {
    if (ev.key === 'Escape') closeDrawer();
    if (ev.key === '/') { ev.preventDefault(); document.getElementById('searchInput').focus(); }
    if (ev.key.toLowerCase() === 'n') document.getElementById('quickTitle').focus();
  });
}

async function pollEvents() {
  try {
    const data = await api.events(state.board, state.latestEventId || 0);
    if (data.events.length) await load();
  } catch (err) {
    console.warn(err);
  } finally {
    state.refreshTimer = setTimeout(pollEvents, 2500);
  }
}

async function main() {
  applyI18n();
  setupThemeToggle();
  setupControls();
  setupDependencyControls();
  setupForms(load);
  setupMobileFallback();
  document.getElementById('quickAssignee').value = localStorage.getItem('lastAssignee') || '';
  try {
    await load();
    pollEvents();
  } catch (err) {
    console.error(err);
    toast(err.message || String(err), 'error');
  }
}

main();
