import { api } from './api.js';
import { state, toast, setBoard } from './state.js';

export function setupForms(load) {
  document.getElementById('quickCreateForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const form = new FormData(ev.currentTarget);
    const title = String(form.get('title') || '').trim();
    if (!title) return;
    const payload = { title, assignee: form.get('assignee') || null, status: form.get('status') || 'ready' };
    localStorage.setItem('lastAssignee', payload.assignee || '');
    await api.createTask(state.board, payload);
    ev.currentTarget.reset();
    document.getElementById('quickAssignee').value = localStorage.getItem('lastAssignee') || '';
    toast('created');
    await load();
  });

  const boardDialog = document.getElementById('boardDialog');
  document.getElementById('newBoardBtn').addEventListener('click', () => boardDialog.showModal());
  document.getElementById('boardForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const form = Object.fromEntries(new FormData(ev.currentTarget));
    if (!form.slug) return;
    const data = await api.createBoard({ ...form, switch: true });
    setBoard(data.current);
    boardDialog.close();
    toast('board created');
    await load();
  });

  const bulkDialog = document.getElementById('bulkDialog');
  document.getElementById('bulkBtn').addEventListener('click', () => bulkDialog.showModal());
  document.getElementById('bulkForm').addEventListener('submit', async ev => {
    ev.preventDefault();
    const lines = new FormData(ev.currentTarget).get('lines');
    const data = await api.bulkCreate(state.board, { lines });
    bulkDialog.close();
    toast(`${data.created} created`);
    await load();
  });
}
