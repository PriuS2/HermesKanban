export const labels = {
  ko: {
    subtitle: '읽기 쉬운 작업 운영 보드', newBoard: '보드 추가', refresh: '새로고침', themeDark: '다크로 전환', themeLight: '라이트로 전환', quickTitle: '작업 제목을 입력하고 Enter',
    taskCreate: 'Task 추가', taskCreateHint: '필요할 때만 제목, 설명, 담당 프로필, 상태를 입력해 새 task를 생성합니다.', taskTitlePlaceholder: '작업 제목', taskBodyPlaceholder: '작업 설명/지시사항(선택)',
    assignee: '담당 프로필', create: '추가', created: '생성일', createdToast: '생성됨', search: '작업 제목/내용/ID 검색', allAssignees: '전체 담당자', unassigned: '미지정', agentProfile: '프로필', manualAssignee: '수동', showArchived: '보관함 표시',
    bulkCreate: '일괄 추가', boardName: '보드 이름', description: '설명', cancel: '취소', bulkHint: '한 줄에 작업 하나씩 입력하세요.', loading: '불러오는 중…',
    workflow: 'Workflow', workflowCreate: 'AI Workflow 생성', workflowPrompt: 'Workflow 프롬프트', workflowPromptPlaceholder: '목표, 산출물, 제약, 원하는 단계 수를 설명하세요', workflowPlannerProfile: 'Planner 프로필', workflowAttachments: '첨부파일', workflowPlan: '설계', workflowPlanning: 'AI가 workflow 초안을 설계하는 중…', workflowRevise: '수정', workflowRevisionPlaceholder: '변경할 단계/담당 프로필/의존성을 설명하세요', workflowApply: '적용', workflowDraftStatus: 'Draft 상태', workflowDraftEmpty: '프롬프트를 입력하고 설계를 누르면 초안이 표시됩니다.', workflowNotApplyable: '아직 적용할 수 없는 초안입니다. 질문을 해결한 뒤 수정 요청을 보내세요.', workflowInstance: 'Instance ID', workflowStep: '현재 단계', workflowSteps: '단계',
    updateAvailable: '새 업데이트 사용 가능', updateTitle: 'KanbanWebUI 업데이트', updateApply: '업데이트 후 재시작', updateLater: '나중에', updateChecking: '업데이트 상태 확인 중…', updateRestarting: '업데이트 적용 중… 서버가 재시작되면 자동으로 새로고침합니다.', updateBlocked: '자동 업데이트 불가', updateNoCommits: '커밋 목록 없음',
    triage: '분류', todo: '대기', ready: '준비', running: '실행중', blocked: '막힘', done: '완료', archived: '보관',
    title: '제목', body: '본문', noDescription: '설명 없음', priority: '우선순위', status: '상태', workspace: '워크스페이스', createdBy: '생성자',
    comments: '댓글', events: '이벤트', runs: '런', monitor: 'Live Run Monitor', context: '컨텍스트', log: '로그', workerLog: 'Worker 로그',
    dependencies: '의존성', parents: '부모', children: '자식', parent: '부모', child: '자식', chooseTask: '작업 선택', none: '없음', remove: '삭제',
    parentPortHint: '오른쪽 부모 포트: 다른 task의 왼쪽 자식 포트로 드래그해 부모로 연결', childPortHint: '왼쪽 자식 포트: 다른 task의 오른쪽 부모 포트로 드래그해 자식으로 연결', linkCreatedToast: '부모/자식 연결됨', linkInvalidToast: '오른쪽 부모 포트와 왼쪽 자식 포트만 연결할 수 있습니다.', linkSameTaskToast: '같은 task끼리는 연결할 수 없습니다.',
    dependencyViewFocus: '관계선: 선택 중심', dependencyViewAll: '관계선: 전체', dependencyViewBlocked: '관계선: 막힘', dependencyViewOff: '관계선: 숨김',
    dependencyMap: '관계 지도', currentTask: '현재 작업', noDependencies: '연결된 부모/자식 없음',
    notifyHomeChannels: '홈 채널 알림', noHomeChannels: '설정된 홈 채널 없음', noWorkerLog: 'worker 로그 없음',
    complete: '완료', block: '막기', unblock: '해제', archive: '보관', save: '저장', close: '닫기', addComment: '댓글 추가', empty: '없음'
  },
  en: {
    subtitle: 'Readable operations board', newBoard: 'New board', refresh: 'Refresh', themeDark: 'Switch dark', themeLight: 'Switch light', quickTitle: 'Type a task title and press Enter',
    taskCreate: 'Create task', taskCreateHint: 'Open this dialog only when you need to set title, details, agent profile, and status for a new task.', taskTitlePlaceholder: 'Task title', taskBodyPlaceholder: 'Task details/instructions (optional)',
    assignee: 'Agent profile', create: 'Create', created: 'Created', createdToast: 'Created', search: 'Search title/body/ID', allAssignees: 'All assignees', unassigned: 'Unassigned', agentProfile: 'profile', manualAssignee: 'manual', showArchived: 'Show archived',
    bulkCreate: 'Bulk create', boardName: 'Board name', description: 'Description', cancel: 'Cancel', bulkHint: 'One task per line.', loading: 'Loading…',
    workflow: 'Workflow', workflowCreate: 'Create AI workflow', workflowPrompt: 'Workflow prompt', workflowPromptPlaceholder: 'Describe goals, outputs, constraints, and desired step count', workflowPlannerProfile: 'Planner profile', workflowAttachments: 'Attachments', workflowPlan: 'Plan', workflowPlanning: 'AI is designing a workflow draft…', workflowRevise: 'Revise', workflowRevisionPlaceholder: 'Describe step/profile/dependency changes', workflowApply: 'Apply', workflowDraftStatus: 'Draft status', workflowDraftEmpty: 'Enter a prompt and click Plan to preview a draft.', workflowNotApplyable: 'This draft is not applyable yet. Resolve questions and send a revision.', workflowInstance: 'Instance ID', workflowStep: 'Current step', workflowSteps: 'steps',
    updateAvailable: 'Update available', updateTitle: 'KanbanWebUI update', updateApply: 'Update and restart', updateLater: 'Later', updateChecking: 'Checking update status…', updateRestarting: 'Applying update… this page will reload after the server restarts.', updateBlocked: 'Automatic update blocked', updateNoCommits: 'No commit details',
    triage: 'Triage', todo: 'Todo', ready: 'Ready', running: 'Running', blocked: 'Blocked', done: 'Done', archived: 'Archived',
    title: 'Title', body: 'Body', noDescription: 'No description', priority: 'Priority', status: 'Status', workspace: 'Workspace', createdBy: 'Created by',
    comments: 'Comments', events: 'Events', runs: 'Runs', monitor: 'Live Run Monitor', context: 'Context', log: 'Log', workerLog: 'Worker log',
    dependencies: 'Dependencies', parents: 'Parents', children: 'Children', parent: 'Parent', child: 'Child', chooseTask: 'Choose task', none: 'None', remove: 'Remove',
    parentPortHint: 'Right parent port: drag to another task left child port to link as parent', childPortHint: 'Left child port: drag to another task right parent port to link as child', linkCreatedToast: 'Parent/child linked', linkInvalidToast: 'Connect one right parent port with one left child port.', linkSameTaskToast: 'A task cannot link to itself.',
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
