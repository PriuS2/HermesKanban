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


def test_dragdrop_pointer_contract_strings():
    root = Path(__file__).resolve().parents[1]
    dragdrop = (root / 'static' / 'dragdrop.js').read_text(encoding='utf-8')
    for phrase in ['pointerdown', 'setPointerCapture', 'drag threshold', 'drop placeholder', 'autoScrollBoard', 'moveTask']:
        assert phrase in dragdrop
