import { api } from './api.js?v=20260506-03';
import { escapeHtml } from './markdown.js?v=20260506-03';
import { t } from './i18n.js?v=20260506-03';
import { state, toast, setBoard } from './state.js?v=20260506-03';

function stepKey(step) {
  return step.step_key || step.key || '';
}

function renderWorkflowSteps(root, steps) {
  const items = (steps || []).map(step => {
    const key = stepKey(step);
    const deps = step.depends_on || [];
    const assignee = step.assignee ? `@${step.assignee}` : t('unassigned');
    const criteria = (step.acceptance_criteria || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');
    return `<li class="workflow-step ${escapeHtml(step.status || 'todo')}">
      <div><strong>${escapeHtml(step.title || key)}</strong><code>${escapeHtml(key)}</code></div>
      <div class="workflow-meta"><span>${escapeHtml(assignee)}</span><span>${escapeHtml(step.status || 'todo')}</span>${deps.length ? `<span>← ${deps.map(escapeHtml).join(', ')}</span>` : ''}</div>
      ${step.body ? `<p>${escapeHtml(step.body)}</p>` : ''}
      ${criteria ? `<ul class="workflow-criteria">${criteria}</ul>` : ''}
    </li>`;
  }).join('');
  root.innerHTML = items ? `<ol class="workflow-step-list">${items}</ol>` : `<p class="muted">${t('empty')}</p>`;
}

function renderAttachmentList(attachments) {
  const items = (attachments || []).map(att => `<li><span>${escapeHtml(att.filename || att.name || 'attachment')}</span><small>${Number(att.size_bytes || att.size || 0).toLocaleString()} B</small></li>`).join('');
  return items ? `<ul class="workflow-attachment-list">${items}</ul>` : '';
}

function renderWorkflowDraft(root, draft) {
  if (!root) return;
  if (!draft) {
    root.innerHTML = `<p class="muted">${t('workflowDraftEmpty')}</p>`;
    return;
  }
  const proposal = draft.proposal || {};
  const warnings = [...(proposal.warnings || []), ...((draft.validation || {}).warnings || [])];
  const questions = proposal.questions || [];
  const notApplyable = proposal.applyable === false;
  root.innerHTML = `
    <div class="workflow-draft-summary">
      <div class="workflow-meta"><span>${t('workflowDraftStatus')}: ${escapeHtml(draft.status || 'draft')}</span><span>${t('workflowPlannerProfile')}: ${escapeHtml(draft.planner_profile || '')}</span><span>rev ${escapeHtml(String(draft.revision || 1))}</span></div>
      <h4>${escapeHtml(proposal.title || t('workflowCreate'))}</h4>
      <p>${escapeHtml(proposal.summary || '')}</p>
      ${proposal.strategy ? `<p><strong>Strategy</strong> ${escapeHtml(proposal.strategy)}</p>` : ''}
      ${renderAttachmentList(draft.attachments || [])}
      ${notApplyable ? `<div class="workflow-warnings"><strong>${escapeHtml(t('workflowNotApplyable'))}</strong></div>` : ''}
      ${warnings.length ? `<div class="workflow-warnings"><strong>Warnings</strong><ul>${warnings.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>` : ''}
      ${questions.length ? `<div class="workflow-questions"><strong>Questions</strong><ul>${questions.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>` : ''}
    </div>`;
  const steps = document.createElement('div');
  renderWorkflowSteps(steps, proposal.steps || []);
  root.appendChild(steps);
}

async function readWorkflowAttachments(input) {
  const files = Array.from(input?.files || []);
  const attachments = [];
  for (const file of files) {
    attachments.push({
      filename: file.name,
      content_type: file.type || 'text/plain',
      content: await file.text()
    });
  }
  return attachments;
}

function setWorkflowBusy(form, busy) {
  form.querySelectorAll('button, input, textarea').forEach(el => {
    if (el.dataset.workflowCancel !== undefined) return;
    el.disabled = Boolean(busy);
  });
}

function updateWorkflowActionState(form) {
  const hasDraft = Boolean(state.workflowDraft?.draft_id);
  const applied = state.workflowDraft?.status === 'applied';
  const notApplyable = state.workflowDraft?.proposal?.applyable === false;
  const revise = form.querySelector('[data-workflow-revise]');
  const apply = form.querySelector('[data-workflow-apply]');
  if (revise) revise.disabled = !hasDraft || applied;
  if (apply) apply.disabled = !hasDraft || applied || notApplyable;
}

function resetWorkflowDesigner(form) {
  state.workflowDraft = null;
  form.reset();
  renderWorkflowDraft(document.getElementById('workflowDraftPreview'), null);
  updateWorkflowActionState(form);
}

async function createWorkflowDraft(form) {
  const prompt = String(form.querySelector('#workflowPrompt')?.value || '').trim();
  if (!prompt) return;
  const previewRoot = document.getElementById('workflowDraftPreview');
  previewRoot.innerHTML = `<p class="muted">${escapeHtml(t('workflowPlanning'))}</p>`;
  const result = await api.createWorkflowDraft(state.board, {
    prompt,
    planner_profile: String(form.querySelector('#workflowPlannerProfile')?.value || '').trim() || null,
    attachments: await readWorkflowAttachments(form.querySelector('#workflowAttachments'))
  });
  state.workflowDraft = result.draft;
  renderWorkflowDraft(previewRoot, state.workflowDraft);
  updateWorkflowActionState(form);
}

async function reviseWorkflowDraft(form) {
  const revisionPrompt = String(form.querySelector('#workflowRevisionPrompt')?.value || '').trim();
  if (!state.workflowDraft?.draft_id || !revisionPrompt) return;
  const previewRoot = document.getElementById('workflowDraftPreview');
  previewRoot.innerHTML = `<p class="muted">${escapeHtml(t('workflowPlanning'))}</p>`;
  const result = await api.reviseWorkflowDraft(state.board, state.workflowDraft.draft_id, { revision_prompt: revisionPrompt });
  state.workflowDraft = result.draft;
  form.querySelector('#workflowRevisionPrompt').value = '';
  renderWorkflowDraft(previewRoot, state.workflowDraft);
  updateWorkflowActionState(form);
}

async function applyWorkflowDraft(form, load) {
  if (!state.workflowDraft?.draft_id) return;
  const payload = { instance_id: String(form.querySelector('[name="instance_id"]')?.value || '').trim() || null };
  const result = await api.instantiateWorkflowDraft(state.board, state.workflowDraft.draft_id, payload);
  state.workflowDraft.status = 'applied';
  state.workflowDraft.applied_instance_id = result.instance_id;
  renderWorkflowDraft(document.getElementById('workflowDraftPreview'), state.workflowDraft);
  updateWorkflowActionState(form);
  toast(`${result.created} ${t('createdToast')} · ${result.existing} existing`);
  await load();
}

export function setupWorkflowDialog(load) {
  const workflowDialog = document.getElementById('workflowDialog');
  const workflowForm = document.getElementById('workflowForm');
  const workflowBtn = document.getElementById('workflowBtn');
  if (!workflowDialog || !workflowForm || !workflowBtn) return;

  workflowBtn.addEventListener('click', () => {
    resetWorkflowDesigner(workflowForm);
    workflowDialog.showModal();
  });
  workflowForm.addEventListener('submit', ev => ev.preventDefault());
  workflowForm.querySelector('[data-workflow-cancel]').addEventListener('click', () => workflowDialog.close());
  workflowForm.querySelector('[data-workflow-plan]').addEventListener('click', async () => {
    try {
      setWorkflowBusy(workflowForm, true);
      await createWorkflowDraft(workflowForm);
    } catch (err) {
      toast(err.message || String(err), 'error');
    } finally {
      setWorkflowBusy(workflowForm, false);
      updateWorkflowActionState(workflowForm);
    }
  });
  workflowForm.querySelector('[data-workflow-revise]').addEventListener('click', async () => {
    try {
      setWorkflowBusy(workflowForm, true);
      await reviseWorkflowDraft(workflowForm);
    } catch (err) {
      toast(err.message || String(err), 'error');
    } finally {
      setWorkflowBusy(workflowForm, false);
      updateWorkflowActionState(workflowForm);
    }
  });
  workflowForm.querySelector('[data-workflow-apply]').addEventListener('click', async () => {
    try {
      setWorkflowBusy(workflowForm, true);
      await applyWorkflowDraft(workflowForm, load);
    } catch (err) {
      toast(err.message || String(err), 'error');
    } finally {
      setWorkflowBusy(workflowForm, false);
      updateWorkflowActionState(workflowForm);
    }
  });
}

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

  setupWorkflowDialog(load);
}
