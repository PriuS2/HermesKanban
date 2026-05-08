from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest


def test_static_shell_contains_required_ui_contracts(client):
    index = client.get('/').text
    assert 'Hermes KanbanWebUI' in index
    assert 'langToggle' in index
    assert 'boardSelect' in index
    assert 'taskCreateBtn' in index
    assert '/static/app.js' in index

    root = Path(__file__).resolve().parents[1]
    for rel in ['static/app.js', 'static/board.js', 'static/drawer.js', 'static/monitor.js', 'static/i18n.js', 'static/update.js', 'static/design-tokens.css', 'DESIGN.md']:
        assert (root / rel).is_file(), rel


def test_app_update_static_contract():
    root = Path(__file__).resolve().parents[1]
    index = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    api = (root / 'static' / 'api.js').read_text(encoding='utf-8')
    update = (root / 'static' / 'update.js').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    for phrase in [
        'id="updateDialog"',
        'id="updateCommitList"',
        'id="updateStatusMessage"',
        'data-update-current',
        'data-update-remote',
        'data-update-later',
        'data-update-apply',
    ]:
        assert phrase in index

    assert './update.js?v=20260508-02' in app
    assert 'setupAppUpdatePrompt' in app
    for phrase in ['appUpdateStatus', '/api/app/update-status', 'applyAppUpdate', '/api/app/update']:
        assert phrase in api
    for phrase in [
        'setupAppUpdatePrompt',
        'kanbanDismissedUpdateCommit',
        'api.appUpdateStatus',
        'api.applyAppUpdate',
        'pollHealthUntilReady',
        'location.reload()',
        'updateCommitList',
        'updateDialog',
        '300000',
    ]:
        assert phrase in update
    for key in ['updateAvailable', 'updateApply', 'updateLater', 'updateChecking', 'updateRestarting', 'updateBlocked', 'updateNoCommits']:
        assert key in i18n
    for css_class in ['.update-modal', '.update-commit-list', '.update-status']:
        assert css_class in style


def test_static_javascript_parses():
    node = shutil.which('node')
    if not node:
        pytest.skip('node is required for static JavaScript syntax checks')
    root = Path(__file__).resolve().parents[1]
    for path in sorted((root / 'static').glob('*.js')):
        subprocess.run([node, '--check', str(path)], check=True, cwd=root)


def test_dark_mode_static_contract():
    root = Path(__file__).resolve().parents[1]
    index = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    theme = (root / 'static' / 'theme.js').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')
    tokens = (root / 'static' / 'design-tokens.css').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    assert 'id="themeToggle"' in index
    assert 'aria-pressed="false"' in index
    assert 'style.css?v=20260508-02' in index
    assert 'app.js?v=20260508-02' in index
    assert './theme.js?v=20260508-02' in app
    assert 'setupThemeToggle' in app
    assert 'updateThemeToggleLabel' in app
    assert 'kanbanTheme' in theme
    assert 'prefers-color-scheme: dark' in theme
    assert 'document.documentElement.dataset.theme' in theme
    assert 'localStorage.setItem(THEME_STORAGE_KEY' in theme
    assert 'themeDark' in i18n
    assert 'themeLight' in i18n
    assert ':root[data-theme="dark"]' in tokens
    assert 'color-scheme: dark' in tokens
    for token in ['--body-background', '--control-bg', '--card-bg', '--column-header-bg', '--edge-stroke']:
        assert token in tokens
        assert f'var({token})' in style


def test_dragdrop_pointer_contract_strings():
    root = Path(__file__).resolve().parents[1]
    dragdrop = (root / 'static' / 'dragdrop.js').read_text(encoding='utf-8')
    for phrase in ['pointerdown', 'setPointerCapture', 'drag threshold', 'drop placeholder', 'autoScrollBoard', 'moveTask']:
        assert phrase in dragdrop


def test_drawer_matches_dashboard_detail_controls():
    root = Path(__file__).resolve().parents[1]
    drawer = (root / 'static' / 'drawer.js').read_text(encoding='utf-8')
    api = (root / 'static' / 'api.js').read_text(encoding='utf-8')

    for phrase in [
        'data-action="triage"',
        'data-action="unblock"',
        'data-assignee-save',
        'data-priority-save',
        'bodyEditForm',
        'addParentSelect',
        'addChildSelect',
        'data-link-action',
        'data-home-platform',
        'workerLogContent',
    ]:
        assert phrase in drawer

    for phrase in ['homeChannels', 'subscribeHome', 'unsubscribeHome', 'linkTask', 'unlinkTask', 'taskLog']:
        assert phrase in api


def test_button_hover_keeps_ghost_text_readable():
    root = Path(__file__).resolve().parents[1]
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '.button.primary, .button:hover' not in style
    assert '.button.ghost { background: var(--ghost-bg); color: var(--ink); }' in style
    assert '.button.ghost:hover { background: var(--ghost-hover-bg); color: var(--ink); border-color: var(--border); }' in style
    assert '.button.ghost.danger-btn:hover' in style


def test_drawer_forms_do_not_overflow_grid_tracks():
    root = Path(__file__).resolve().parents[1]
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    assert 'grid-template-columns: minmax(0, 1fr) minmax(0, .8fr) minmax(96px, .4fr) auto' in style
    assert 'minmax(220px, 1fr)' not in style
    assert '.inline-form label, .dependency-form { display: grid; gap: 6px; color: var(--muted); font-weight: 700; min-width: 0; }' in style
    assert '.inline-form input, .inline-form select, .dependency-form select, .dependency-form button { width: 100%; min-width: 0; }' in style
    assert '.dependency-grid > div { min-width: 0; }' in style


def test_dependency_visual_options_and_focus_overlay_contract():
    root = Path(__file__).resolve().parents[1]
    index = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    lines = (root / 'static' / 'dependency-lines.js').read_text(encoding='utf-8')
    drawer = (root / 'static' / 'drawer.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    assert 'id="dependencyView"' in index
    for mode in ['focus', 'all', 'blocked', 'off']:
        assert f'value="{mode}"' in index
    assert 'setupDependencyControls' in app
    assert 'renderDependencyOverlay' in board
    assert 'data-parent-count' in board
    assert 'data-child-count' in board
    for phrase in ['dependency-overlay', 'dependency-edge', 'dependency-focus', 'dependency-dim', 'dependency-blocked']:
        assert phrase in lines
        assert phrase in style
    assert 'dependency-mini-map' in drawer
    assert 'dependencyMiniMap' in drawer


def test_task_create_options_live_in_modal_not_toolbar():
    root = Path(__file__).resolve().parents[1]
    index = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    forms = (root / 'static' / 'forms.js').read_text(encoding='utf-8')
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    for phrase in [
        'id="taskCreateBtn"',
        'id="taskDialog"',
        'id="taskCreateForm"',
        'id="taskTitle"',
        'id="taskBody"',
        'id="taskAssignee"',
        'id="taskStatus"',
    ]:
        assert phrase in index

    for removed in ['id="quickCreateForm"', 'id="quickTitle"', 'id="quickAssignee"', 'id="quickStatus"']:
        assert removed not in index

    assert 'setupTaskCreateDialog' in forms
    assert "document.getElementById('taskCreateBtn')" in forms
    assert "document.dispatchEvent(new CustomEvent('kanban:open-task-create'" in board
    assert "kanban:open-task-create" in forms
    assert "document.getElementById('taskCreateBtn').click()" in app
    for key in ['taskCreate', 'taskCreateHint', 'taskTitlePlaceholder', 'taskBodyPlaceholder']:
        assert key in i18n
    for css_class in ['.toolbar-actions', '.task-field-grid', '.task-modal']:
        assert css_class in style



def test_unassigned_tasks_are_visually_flagged():
    root = Path(__file__).resolve().parents[1]
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')
    tokens = (root / 'static' / 'design-tokens.css').read_text(encoding='utf-8')

    for phrase in [
        'const isUnassigned = !task.assignee;',
        'profileMissing',
        'profileMissingShort',
        'missing-assignee-chip',
        'profile-missing-badge',
        "data-assignee-state=\"${isUnassigned ? 'missing' : 'assigned'}\"",
        "task.status}${isUnassigned ? ' is-unassigned' : ''}",
    ]:
        assert phrase in board
    for key in ['profileMissing', 'profileMissingShort']:
        assert key in i18n
    for css_class in ['.task-card.is-unassigned', '.profile-missing-badge', '.chips .missing-assignee-chip']:
        assert css_class in style
    assert './board.js?v=20260508-02' in app
    assert './i18n.js?v=20260508-02' in board
    for token in ['--warning-soft', '--warning-ring']:
        assert token in tokens


def test_operations_dashboard_static_contract():
    root = Path(__file__).resolve().parents[1]
    index = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    api = (root / 'static' / 'api.js').read_text(encoding='utf-8')
    ops = (root / 'static' / 'operations.js').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    for phrase in ['id="opsToggleBtn"', 'id="opsPanel"']:
        assert phrase in index
    assert './operations.js?v=20260508-02' in app
    for phrase in ['opsSummary', '/api/ops/summary']:
        assert phrase in api
    for phrase in ['renderOperationsPanel', 'setupOperationsPanel', 'retry_queue', 'blocked_after_retries', 'openTaskDrawer']:
        assert phrase in ops
    for key in ['operations', 'opsOverview', 'opsRunning', 'opsRetryQueue', 'opsBlockedAfterRetries', 'opsEstimatedBackoffAdvisory']:
        assert key in i18n
    for css_class in ['.ops-panel', '.ops-grid', '.ops-table', '.ops-chip']:
        assert css_class in style


def test_workflow_static_contract():
    root = Path(__file__).resolve().parents[1]
    index = (root / 'static' / 'index.html').read_text(encoding='utf-8')
    api = (root / 'static' / 'api.js').read_text(encoding='utf-8')
    app = (root / 'static' / 'app.js').read_text(encoding='utf-8')
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    drawer = (root / 'static' / 'drawer.js').read_text(encoding='utf-8')
    forms = (root / 'static' / 'forms.js').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    for phrase in [
        'id="workflowBtn"',
        'id="workflowDialog"',
        'id="workflowForm"',
        'id="workflowPrompt"',
        'id="workflowPlannerProfile"',
        'id="workflowAttachments"',
        'id="workflowDraftPreview"',
        'id="workflowRevisionPrompt"',
        'data-workflow-plan',
        'data-workflow-revise',
        'data-workflow-apply',
    ]:
        assert phrase in index

    for removed in ['workflowTemplateSelect', 'Workflow 템플릿', 'workflowTemplates', 'workflowPreview', 'instantiateWorkflow']:
        assert removed not in index
        assert removed not in app

    for phrase in ['createWorkflowDraft', 'reviseWorkflowDraft', 'getWorkflowDraft', 'instantiateWorkflowDraft']:
        assert phrase in api

    for phrase in ['setupWorkflowDialog', 'workflowPrompt', 'api.createWorkflowDraft', 'api.reviseWorkflowDraft', 'api.instantiateWorkflowDraft', 'proposal?.applyable === false', 'workflowNotApplyable']:
        assert phrase in forms

    assert 'loadWorkflowTemplates' not in app
    assert 'populateWorkflowTemplateSelect' not in app
    assert 'workflow-chip' in board
    assert 'workflowDetailSection' in drawer
    for key in ['workflowCreate', 'workflowDesignerHint', 'workflowPrompt', 'workflowPlannerProfile', 'workflowAttachments', 'workflowRevise', 'workflowApply', 'workflowDraftStatus', 'workflowNotApplyable', 'workflowSteps']:
        assert key in i18n
    for css_class in ['.workflow-step-list', '.workflow-step', '.workflow-chip', '.workflow-meta', '.workflow-draft-actions', '.workflow-attachment-list']:
        assert css_class in style


def test_board_columns_fill_available_resolution_width():
    root = Path(__file__).resolve().parents[1]
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    tokens = (root / 'static' / 'design-tokens.css').read_text(encoding='utf-8')

    assert '--column-min-width:' in tokens
    assert '--kanban-column-count' in board
    assert "root.style.setProperty('--kanban-column-count'" in board
    assert '.board { position: relative; display: grid;' in style
    assert 'grid-template-columns: repeat(var(--kanban-column-count, 6), minmax(var(--column-min-width), 1fr));' in style
    assert 'width: var(--column-width)' not in style
    assert 'min-width: var(--column-width)' not in style
    assert '.board-column { position: relative; min-width: 0;' in style


def test_kpi_row_uses_dynamic_status_count_when_archived_is_visible():
    root = Path(__file__).resolve().parents[1]
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    render_kpis = board.split('export function renderKpis(data) {', 1)[1].split('export function renderBoard(data) {', 1)[0]

    assert '--kpi-column-count' in render_kpis
    assert "root.style.setProperty('--kpi-column-count'" in render_kpis
    assert 'grid-template-columns: repeat(var(--kpi-column-count, 6), minmax(120px, 1fr));' in style
    assert 'overflow-x: auto;' in style
    assert '.kpi-row { grid-template-columns: repeat(3, 1fr); }' not in style
    assert '.kpi-row { grid-template-columns: repeat(2, 1fr); }' not in style


def test_dependency_lines_render_above_column_backgrounds_below_cards():
    root = Path(__file__).resolve().parents[1]
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')

    assert '.board-column { position: relative; min-width: 0;' in style
    assert '.board-column { position: relative; z-index: 1;' not in style
    assert '.cards { position: relative; z-index: 2;' in style
    assert '.task-card { position: relative;' in style
    assert '.dependency-overlay { position: absolute; left: 0; top: 0; z-index: 1;' in style


def test_dependency_edges_fan_out_shared_endpoints():
    root = Path(__file__).resolve().parents[1]
    lines = (root / 'static' / 'dependency-lines.js').read_text(encoding='utf-8')

    for phrase in [
        'assignEdgePorts',
        'sourceOffset',
        'targetOffset',
        'portOffset',
        'data-source-offset',
        'data-target-offset',
    ]:
        assert phrase in lines


def test_blueprint_dependency_ports_create_links_from_board():
    root = Path(__file__).resolve().parents[1]
    board = (root / 'static' / 'board.js').read_text(encoding='utf-8')
    lines = (root / 'static' / 'dependency-lines.js').read_text(encoding='utf-8')
    dragdrop = (root / 'static' / 'dragdrop.js').read_text(encoding='utf-8')
    style = (root / 'static' / 'style.css').read_text(encoding='utf-8')
    i18n = (root / 'static' / 'i18n.js').read_text(encoding='utf-8')

    for phrase in [
        'class="dependency-port child-port"',
        'class="dependency-port parent-port"',
        'data-link-role="child"',
        'data-link-role="parent"',
        'data-link-task-id',
    ]:
        assert phrase in board

    for phrase in [
        "import { api }",
        'setupBlueprintLinking',
        'pointerdown',
        'pointermove',
        'pointerup',
        'document.elementFromPoint',
        'relationFromPorts',
        'api.linkTask(state.board',
        'dependency-preview-edge',
        "cardPoint(board, parentCard, 'left'",
        "cardPoint(board, childCard, 'right'",
        'const direction = to.x >= from.x ? 1 : -1;',
        'from.x + direction * dx',
    ]:
        assert phrase in lines

    assert "ev.target.closest('.dependency-port')" in dragdrop
    assert '.dependency-port.child-port { right:' in style
    assert '.dependency-port.parent-port { left:' in style
    assert '.board.is-linking' in style
    assert '.dependency-preview-edge' in style
    for key in ['parentPortHint', 'childPortHint', 'linkCreatedToast', 'linkInvalidToast']:
        assert key in i18n
