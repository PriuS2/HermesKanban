import { api } from './api.js?v=20260507-02';
import { t } from './i18n.js?v=20260507-02';

const DISMISSED_UPDATE_KEY = 'kanbanDismissedUpdateCommit';
let latestStatus = null;
let checking = false;

function refs() {
  const dialog = document.getElementById('updateDialog');
  if (!dialog) return null;
  return {
    dialog,
    status: document.getElementById('updateStatusMessage'),
    commits: document.getElementById('updateCommitList'),
    current: dialog.querySelector('[data-update-current]'),
    remote: dialog.querySelector('[data-update-remote]'),
    later: dialog.querySelector('[data-update-later]'),
    apply: dialog.querySelector('[data-update-apply]'),
  };
}

function setStatusText(elements, message) {
  if (elements.status) elements.status.textContent = message;
}

function dismissedCommit() {
  return localStorage.getItem(DISMISSED_UPDATE_KEY) || '';
}

function renderCommitList(elements, commits) {
  elements.commits.replaceChildren();
  if (!commits?.length) {
    const item = document.createElement('li');
    item.textContent = t('updateNoCommits');
    elements.commits.appendChild(item);
    return;
  }
  for (const commit of commits) {
    const item = document.createElement('li');
    const code = document.createElement('code');
    const subject = document.createElement('span');
    code.textContent = commit.short || commit.sha?.slice(0, 7) || 'unknown';
    subject.textContent = commit.subject || '';
    item.append(code, subject);
    elements.commits.appendChild(item);
  }
}

function showUpdateDialog(elements, status) {
  latestStatus = status;
  if (elements.current) elements.current.textContent = `HEAD ${status.current_short || ''}`.trim();
  if (elements.remote) elements.remote.textContent = `origin/main ${status.remote_short || ''}`.trim();
  renderCommitList(elements, status.commits || []);
  elements.apply.disabled = !status.can_update;
  setStatusText(elements, status.can_update ? t('updateAvailable') : `${t('updateBlocked')}: ${status.blocked_reason || ''}`);
  if (!elements.dialog.open) elements.dialog.showModal();
}

async function checkForUpdates(force = false) {
  if (checking) return;
  const elements = refs();
  if (!elements) return;
  checking = true;
  try {
    const status = await api.appUpdateStatus();
    if (!status.ok || !status.update_available) return;
    if (!force && status.remote_commit && dismissedCommit() === status.remote_commit) return;
    showUpdateDialog(elements, status);
  } catch (err) {
    console.warn('update check failed', err);
  } finally {
    checking = false;
  }
}

async function pollHealthUntilReady({ attempts = 40, delayMs = 500 } = {}) {
  for (let i = 0; i < attempts; i += 1) {
    try {
      const result = await api.health();
      if (result.ok) return true;
    } catch {
      // Expected while the server is restarting.
    }
    await new Promise(resolve => setTimeout(resolve, delayMs));
  }
  return false;
}

async function applyUpdate(elements) {
  if (!latestStatus) return;
  elements.apply.disabled = true;
  elements.later.disabled = true;
  setStatusText(elements, t('updateRestarting'));
  try {
    await api.applyAppUpdate();
    await pollHealthUntilReady();
    location.reload();
  } catch (err) {
    elements.apply.disabled = !latestStatus.can_update;
    elements.later.disabled = false;
    setStatusText(elements, err.message || String(err));
  }
}

export function setupAppUpdatePrompt() {
  const elements = refs();
  if (!elements) return;
  elements.later.addEventListener('click', () => {
    if (latestStatus?.remote_commit) localStorage.setItem(DISMISSED_UPDATE_KEY, latestStatus.remote_commit);
    elements.dialog.close();
  });
  elements.apply.addEventListener('click', () => applyUpdate(elements));
  checkForUpdates();
  setInterval(checkForUpdates, 300000);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') checkForUpdates();
  });
}
