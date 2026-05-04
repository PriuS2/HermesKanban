export const labels = {
  ko: {
    subtitle: '읽기 쉬운 작업 운영 보드', newBoard: '보드 추가', refresh: '새로고침', quickTitle: '작업 제목을 입력하고 Enter',
    assignee: '담당자', create: '추가', search: '검색', allAssignees: '전체 담당자', showArchived: '보관함 표시',
    bulkCreate: '일괄 추가', boardName: '보드 이름', description: '설명', cancel: '취소', bulkHint: '한 줄에 작업 하나씩 입력하세요.',
    triage: '분류', todo: '대기', ready: '준비', running: '실행중', blocked: '막힘', done: '완료', archived: '보관',
    priority: '우선순위', comments: '댓글', events: '이벤트', runs: '런', monitor: 'Live Run Monitor', context: '컨텍스트', log: '로그',
    complete: '완료', block: '막힘', unblock: '해제', archive: '보관', save: '저장', close: '닫기', addComment: '댓글 추가', empty: '작업 없음'
  },
  en: {
    subtitle: 'Readable operations board', newBoard: 'New board', refresh: 'Refresh', quickTitle: 'Type a task title and press Enter',
    assignee: 'Assignee', create: 'Create', search: 'Search', allAssignees: 'All assignees', showArchived: 'Show archived',
    bulkCreate: 'Bulk create', boardName: 'Board name', description: 'Description', cancel: 'Cancel', bulkHint: 'One task per line.',
    triage: 'Triage', todo: 'Todo', ready: 'Ready', running: 'Running', blocked: 'Blocked', done: 'Done', archived: 'Archived',
    priority: 'Priority', comments: 'Comments', events: 'Events', runs: 'Runs', monitor: 'Live Run Monitor', context: 'Context', log: 'Log',
    complete: 'Complete', block: 'Block', unblock: 'Unblock', archive: 'Archive', save: 'Save', close: 'Close', addComment: 'Add comment', empty: 'No tasks'
  }
};

let currentLang = localStorage.getItem('kanbanLang') || 'ko';

export function lang() { return currentLang; }
export function setLang(next) { currentLang = next === 'en' ? 'en' : 'ko'; localStorage.setItem('kanbanLang', currentLang); applyI18n(); }
export function t(key) { return (labels[currentLang] && labels[currentLang][key]) || labels.ko[key] || key; }

export function applyI18n(root = document) {
  root.documentElement?.setAttribute('lang', currentLang);
  root.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll('[data-i18n-placeholder]').forEach(el => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  const toggle = root.getElementById?.('langToggle');
  if (toggle) toggle.textContent = currentLang === 'ko' ? 'EN' : 'KO';
}
