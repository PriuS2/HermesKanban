export const labels = {
  ko: {
    subtitle: '읽기 쉬운 작업 운영 보드', newBoard: '보드 추가', refresh: '새로고침', themeDark: '다크로 전환', themeLight: '라이트로 전환', quickTitle: '작업 제목을 입력하고 Enter',
    assignee: '담당 프로필', create: '추가', search: '작업 제목/내용/ID 검색', allAssignees: '전체 담당자', unassigned: '미지정', agentProfile: '프로필', manualAssignee: '수동', showArchived: '보관함 표시',
    bulkCreate: '일괄 추가', boardName: '보드 이름', description: '설명', cancel: '취소', bulkHint: '한 줄에 작업 하나씩 입력하세요.',
    triage: '분류', todo: '대기', ready: '준비', running: '실행중', blocked: '막힘', done: '완료', archived: '보관',
    title: '제목', body: '본문', noDescription: '설명 없음', priority: '우선순위', status: '상태', workspace: '워크스페이스', createdBy: '생성자', created: '생성일',
    comments: '댓글', events: '이벤트', runs: '런', monitor: 'Live Run Monitor', context: '컨텍스트', log: '로그', workerLog: 'Worker 로그',
    dependencies: '의존성', parents: '부모', children: '자식', parent: '부모', child: '자식', chooseTask: '작업 선택', none: '없음', remove: '삭제',
    dependencyViewFocus: '관계선: 선택 중심', dependencyViewAll: '관계선: 전체', dependencyViewBlocked: '관계선: 막힘', dependencyViewOff: '관계선: 숨김',
    dependencyMap: '관계 지도', currentTask: '현재 작업', noDependencies: '연결된 부모/자식 없음',
    notifyHomeChannels: '홈 채널 알림', noHomeChannels: '설정된 홈 채널 없음', noWorkerLog: 'worker 로그 없음',
    complete: '완료', block: '막기', unblock: '해제', archive: '보관', save: '저장', close: '닫기', addComment: '댓글 추가', empty: '없음'
  },
  en: {
    subtitle: 'Readable operations board', newBoard: 'New board', refresh: 'Refresh', themeDark: 'Switch dark', themeLight: 'Switch light', quickTitle: 'Type a task title and press Enter',
    assignee: 'Agent profile', create: 'Create', search: 'Search title/body/ID', allAssignees: 'All assignees', unassigned: 'Unassigned', agentProfile: 'profile', manualAssignee: 'manual', showArchived: 'Show archived',
    bulkCreate: 'Bulk create', boardName: 'Board name', description: 'Description', cancel: 'Cancel', bulkHint: 'One task per line.',
    triage: 'Triage', todo: 'Todo', ready: 'Ready', running: 'Running', blocked: 'Blocked', done: 'Done', archived: 'Archived',
    title: 'Title', body: 'Body', noDescription: 'No description', priority: 'Priority', status: 'Status', workspace: 'Workspace', createdBy: 'Created by', created: 'Created',
    comments: 'Comments', events: 'Events', runs: 'Runs', monitor: 'Live Run Monitor', context: 'Context', log: 'Log', workerLog: 'Worker log',
    dependencies: 'Dependencies', parents: 'Parents', children: 'Children', parent: 'Parent', child: 'Child', chooseTask: 'Choose task', none: 'None', remove: 'Remove',
    dependencyViewFocus: 'Lines: Focus', dependencyViewAll: 'Lines: All', dependencyViewBlocked: 'Lines: Blocked', dependencyViewOff: 'Lines: Hidden',
    dependencyMap: 'Dependency map', currentTask: 'Current task', noDependencies: 'No parent/child links',
    notifyHomeChannels: 'Notify home channels', noHomeChannels: 'No home channels configured', noWorkerLog: 'No worker log yet',
    complete: 'Complete', block: 'Block', unblock: 'Unblock', archive: 'Archive', save: 'Save', close: 'Close', addComment: 'Add comment', empty: 'None'
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
