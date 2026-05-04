from __future__ import annotations


def test_running_monitor_includes_run_heartbeat_log_and_context(client):
    created = client.post('/api/tasks', json={'title': 'Monitor me', 'body': 'Long task body', 'max_runtime_seconds': 3600})
    assert created.status_code == 200, created.text
    task_id = created.json()['task']['id']

    claim = client.post(f'/api/tasks/{task_id}/claim', json={'claimer': 'test-worker', 'ttl_seconds': 120})
    assert claim.status_code == 200, claim.text
    heartbeat = client.post(f'/api/tasks/{task_id}/heartbeat', json={'note': 'still alive'})
    assert heartbeat.status_code == 200, heartbeat.text

    from kanban_webui.hermes_imports import kanban_db

    log_path = kanban_db.worker_log_path(task_id, board='default')
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('line 1\nline 2\n', encoding='utf-8')

    monitor = client.get(f'/api/tasks/{task_id}/monitor', params={'tail': 4096})
    assert monitor.status_code == 200, monitor.text
    data = monitor.json()
    assert data['task']['status'] == 'running'
    assert data['current_run']['status'] == 'running'
    assert data['heartbeat']['age_seconds'] >= 0
    assert data['claim']['lock'] == 'test-worker'
    assert data['log']['exists'] is True
    assert 'line 2' in data['log']['content']
    assert 'Monitor me' in data['context_preview']
