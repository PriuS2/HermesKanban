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
    assert 'quickCreateForm' in index
    assert '/static/app.js' in index

    root = Path(__file__).resolve().parents[1]
    for rel in ['static/app.js', 'static/board.js', 'static/drawer.js', 'static/monitor.js', 'static/i18n.js', 'static/design-tokens.css', 'DESIGN.md']:
        assert (root / rel).is_file(), rel


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
    assert 'style.css?v=20260506-03' in index
    assert 'app.js?v=20260506-03' in index
    assert './theme.js?v=20260506-03' in app
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
    for key in ['workflowCreate', 'workflowPrompt', 'workflowPlannerProfile', 'workflowAttachments', 'workflowRevise', 'workflowApply', 'workflowDraftStatus', 'workflowNotApplyable', 'workflowSteps']:
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
