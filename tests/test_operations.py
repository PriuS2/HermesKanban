from __future__ import annotations

import json
import time
from typing import Any


def _create(client, title: str, **extra: Any) -> str:
    response = client.post('/api/tasks', json={'title': title, **extra})
    assert response.status_code == 200, response.text
    return response.json()['task']['id']


def _mutate_task(task_id: str, assignments: dict[str, Any]) -> None:
    from kanban_webui.hermes_imports import kanban_db

    conn = kanban_db.connect(board='default')
    try:
        columns = ', '.join(f'{key} = ?' for key in assignments)
        values = [*assignments.values(), task_id]
        with kanban_db.write_txn(conn):
            conn.execute(f'UPDATE tasks SET {columns} WHERE id = ?', values)
    finally:
        conn.close()


def _insert_event(task_id: str, kind: str, payload: dict[str, Any], created_at: int) -> None:
    from kanban_webui.hermes_imports import kanban_db

    conn = kanban_db.connect(board='default')
    try:
        with kanban_db.write_txn(conn):
            conn.execute(
                'INSERT INTO task_events(task_id, kind, payload, created_at) VALUES (?, ?, ?, ?)',
                (task_id, kind, json.dumps(payload, ensure_ascii=False), created_at),
            )
    finally:
        conn.close()


def _set_run_heartbeat(task_id: str, heartbeat_at: int, started_at: int) -> None:
    from kanban_webui.hermes_imports import kanban_db

    conn = kanban_db.connect(board='default')
    try:
        with kanban_db.write_txn(conn):
            conn.execute(
                'UPDATE task_runs SET last_heartbeat_at = ?, started_at = ? WHERE task_id = ? AND status = ?',
                (heartbeat_at, started_at, task_id, 'running'),
            )
    finally:
        conn.close()


def test_ops_summary_includes_running_claim_and_heartbeat(client):
    task_id = _create(client, 'Running task', body='Long operation body', assignee='dev', max_runtime_seconds=3600)

    claim = client.post(f'/api/tasks/{task_id}/claim', json={'claimer': 'test-worker', 'ttl_seconds': 900})
    assert claim.status_code == 200, claim.text
    heartbeat = client.post(f'/api/tasks/{task_id}/heartbeat', json={'note': 'halfway'})
    assert heartbeat.status_code == 200, heartbeat.text

    now = int(time.time())
    old_heartbeat = now - 360
    _mutate_task(task_id, {'last_heartbeat_at': old_heartbeat, 'worker_pid': 12345, 'started_at': now - 600})
    _set_run_heartbeat(task_id, old_heartbeat, now - 600)

    response = client.get('/api/ops/summary')
    assert response.status_code == 200, response.text
    data = response.json()

    assert data['board'] == 'default'
    assert data['summary']['running'] == 1
    assert data['summary']['claimed'] == 1
    assert data['summary']['heartbeat_overdue'] == 1
    running = data['running'][0]
    assert running['task']['id'] == task_id
    assert running['task']['title'] == 'Running task'
    assert running['task']['body'] is None
    assert running['task']['body_preview'] == 'Long operation body'
    assert running['run']['status'] == 'running'
    assert running['claim']['lock'] == 'test-worker'
    assert running['claim']['expires_in_seconds'] > 0
    assert running['heartbeat']['last_heartbeat_at'] == old_heartbeat
    assert running['heartbeat']['age_seconds'] >= 300
    assert running['heartbeat']['overdue'] is True
    assert running['worker']['pid'] == 12345
    assert running['worker']['elapsed_seconds'] >= 500
    assert running['worker']['max_runtime_seconds'] == 3600
    assert running['workspace'] == {'kind': 'scratch', 'path': None}
    assert running['last_event']['kind'] == 'heartbeat'


def test_ops_summary_includes_retry_candidates_from_failure_fields(client):
    task_id = _create(client, 'Retry me', body='needs another attempt', assignee='dev')
    now = int(time.time())
    _mutate_task(
        task_id,
        {
            'status': 'ready',
            'consecutive_failures': 2,
            'last_failure_error': 'boom',
            'max_retries': 3,
        },
    )
    _insert_event(task_id, 'timed_out', {'error': 'boom', 'elapsed_seconds': 60}, now - 30)

    response = client.get('/api/ops/summary')
    assert response.status_code == 200, response.text
    data = response.json()

    assert data['summary']['ready'] >= 1
    assert data['summary']['retry_candidates'] == 1
    retry = data['retry_queue'][0]
    assert retry['task']['id'] == task_id
    assert retry['task']['title'] == 'Retry me'
    assert retry['attempt'] == 2
    assert retry['max_retries'] == 3
    assert retry['last_error'] == 'boom'
    assert retry['last_failure_kind'] == 'timed_out'
    assert retry['last_failure_at'] == now - 30
    assert retry['estimated_backoff_seconds'] == 20
    assert retry['eligible_at'] == now - 10
    assert retry['eligible_in_seconds'] == 0
    assert retry['state'] == 'eligible'


def test_ops_summary_separates_blocked_after_retries(client):
    retry_id = _create(client, 'Retry queue task', assignee='dev')
    blocked_id = _create(client, 'Gave up task', assignee='dev')
    now = int(time.time())
    _mutate_task(retry_id, {'status': 'ready', 'consecutive_failures': 1, 'last_failure_error': 'retryable'})
    _insert_event(retry_id, 'spawn_failed', {'error': 'retryable'}, now - 20)
    _mutate_task(
        blocked_id,
        {
            'status': 'blocked',
            'consecutive_failures': 3,
            'last_failure_error': 'profile missing',
            'max_retries': 3,
        },
    )
    _insert_event(blocked_id, 'gave_up', {'error': 'profile missing'}, now - 10)

    response = client.get('/api/ops/summary')
    assert response.status_code == 200, response.text
    data = response.json()

    assert data['summary']['retry_candidates'] == 1
    assert data['summary']['blocked_after_retries'] == 1
    assert [item['task']['id'] for item in data['retry_queue']] == [retry_id]
    blocked = data['blocked_after_retries'][0]
    assert blocked['task']['id'] == blocked_id
    assert blocked['attempt'] == 3
    assert blocked['max_retries'] == 3
    assert blocked['last_error'] == 'profile missing'
    assert blocked['last_failure_kind'] == 'gave_up'
    assert blocked['last_failure_at'] == now - 10


def test_ops_summary_is_read_only(client):
    task_id = _create(client, 'Read only target')
    _insert_event(task_id, 'spawn_failed', {'error': 'boom'}, int(time.time()) - 5)
    before = client.get('/api/events').json()['latest_event_id']

    response = client.get('/api/ops/summary')
    assert response.status_code == 200, response.text
    assert response.json()['summary']['recent_failures'] == 1

    after = client.get('/api/events').json()['latest_event_id']
    assert after == before
