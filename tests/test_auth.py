from __future__ import annotations

from fastapi.testclient import TestClient


def test_optional_token_auth(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_KANBAN_HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('HERMES_KANBAN_WEBUI_TOKEN', 'secret-token')
    monkeypatch.delenv('HERMES_KANBAN_DB', raising=False)
    monkeypatch.delenv('HERMES_KANBAN_BOARD', raising=False)
    from kanban_webui.hermes_imports import kanban_db
    from kanban_webui.app import create_app

    kanban_db._INITIALIZED_PATHS.clear()
    client = TestClient(create_app())
    assert client.get('/api/config').status_code == 401
    assert client.get('/service/status').status_code == 401
    assert client.get('/api/config', params={'token': 'secret-token'}).status_code == 401
    assert client.get('/api/config', headers={'X-Kanban-Token': 'secret-token'}).status_code == 200
    assert client.get('/service/status', headers={'X-Kanban-Token': 'secret-token'}).status_code == 200
    assert client.get('/health').status_code == 200


def test_cross_origin_mutation_blocked(client):
    blocked = client.post('/api/tasks', json={'title': 'Drive-by'}, headers={'Origin': 'http://evil.example'})
    assert blocked.status_code == 403
    allowed = client.post('/api/tasks', json={'title': 'Same origin'}, headers={'Origin': 'http://testserver'})
    assert allowed.status_code == 200, allowed.text


def test_untrusted_host_header_blocked(client):
    rebound = client.post(
        '/api/tasks',
        json={'title': 'DNS rebinding'},
        headers={'Host': 'evil.example:8790', 'Origin': 'http://evil.example:8790'},
    )
    assert rebound.status_code == 400
