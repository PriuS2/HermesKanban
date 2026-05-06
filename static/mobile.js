import { api } from './api.js?v=20260506-03';
import { state, toast } from './state.js?v=20260506-03';

export function setupMobileFallback() {
  document.addEventListener('contextmenu', async ev => {
    const card = ev.target.closest?.('.task-card');
    if (!card || !matchMedia('(max-width: 760px)').matches) return;
    ev.preventDefault();
    const next = prompt('Move to status: triage/todo/ready/blocked/done/archived');
    if (!next) return;
    await api.updateTask(state.board, card.dataset.taskId, { status: next });
    toast(`moved → ${next}`);
    document.dispatchEvent(new CustomEvent('kanban:refresh'));
  });
}
