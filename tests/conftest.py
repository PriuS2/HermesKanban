from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    home = tmp_path / 'hermes-home'
    monkeypatch.setenv('HERMES_KANBAN_HOME', str(home))
    monkeypatch.delenv('HERMES_KANBAN_DB', raising=False)
    monkeypatch.delenv('HERMES_KANBAN_BOARD', raising=False)
    monkeypatch.delenv('HERMES_KANBAN_WEBUI_TOKEN', raising=False)
    from kanban_webui.hermes_imports import kanban_db

    kanban_db._INITIALIZED_PATHS.clear()
    from kanban_webui.app import create_app

    with TestClient(create_app()) as c:
        yield c
