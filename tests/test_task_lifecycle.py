from __future__ import annotations


def _create(client, title, **extra):
    r = client.post('/api/tasks', json={'title': title, **extra})
    assert r.status_code == 200, r.text
    return r.json()['task']['id']


def test_task_lifecycle_comments_links_and_bulk(client):
    parent = _create(client, 'Parent task', priority=5, assignee='dev')
    child = _create(client, 'Child task', parents=[parent], tenant='ops')

    board = client.get('/api/board').json()
    assert any(t['id'] == parent for t in board['tasks'])
    assert board['columns']['todo'][0]['id'] == child

    assigned = client.post(f'/api/tasks/{child}/assign', json={'assignee': 'reviewer'})
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()['task']['assignee'] == 'reviewer'

    comment = client.post(f'/api/tasks/{child}/comments', json={'body': 'Looks good', 'author': 'tester'})
    assert comment.status_code == 200, comment.text
    assert comment.json()['comments'][0]['body'] == 'Looks good'

    link = client.post('/api/links', json={'parent_id': child, 'child_id': parent})
    assert link.status_code == 400  # cycle guard from kanban_db

    unlink = client.delete('/api/links', params={'parent_id': parent, 'child_id': child})
    assert unlink.status_code == 200
    assert unlink.json()['ok'] is True

    move = client.patch(f'/api/tasks/{child}', json={'status': 'ready', 'priority': 7, 'title': 'Child task updated'})
    assert move.status_code == 200, move.text
    assert move.json()['task']['priority'] == 7

    complete = client.post(f'/api/tasks/{child}/complete', json={'summary': 'done', 'metadata': {'tests': ['unit']}})
    assert complete.status_code == 200
    assert complete.json()['results'][0]['ok'] is True

    bulk = client.post('/api/tasks/bulk-create', json={'lines': 'A\nB\nC', 'defaults': {'assignee': 'dev'}})
    assert bulk.status_code == 200, bulk.text
    assert bulk.json()['created'] == 3


def test_invalid_create_status_does_not_persist_task(client):
    before = client.get('/api/board').json()['tasks']
    r = client.post('/api/tasks', json={'title': 'Should not persist', 'status': 'running'})
    assert r.status_code == 400
    after = client.get('/api/board').json()['tasks']
    assert len(after) == len(before)
    assert all(t['title'] != 'Should not persist' for t in after)


def test_invalid_patch_payload_does_not_partially_mutate(client):
    task_id = _create(client, 'Atomic update target')
    initial = client.get(f'/api/tasks/{task_id}').json()['task']

    bad_status = client.patch(f'/api/tasks/{task_id}', json={'assignee': 'mutated', 'status': 'bogus'})
    assert bad_status.status_code == 400
    task = client.get(f'/api/tasks/{task_id}').json()['task']
    assert task['assignee'] == initial['assignee']
    assert task['status'] == initial['status']

    bad_title = client.patch(f'/api/tasks/{task_id}', json={'status': 'ready', 'title': '   '})
    assert bad_title.status_code == 400
    task = client.get(f'/api/tasks/{task_id}').json()['task']
    assert task['title'] == 'Atomic update target'
    assert task['status'] == initial['status']

    parent_id = _create(client, 'Parent for refused transition')
    child_id = _create(client, 'Child for refused transition', parents=[parent_id])
    child_initial = client.get(f'/api/tasks/{child_id}').json()['task']
    refused = client.patch(f'/api/tasks/{child_id}', json={'assignee': 'mutated', 'status': 'blocked'})
    assert refused.status_code == 409
    child = client.get(f'/api/tasks/{child_id}').json()['task']
    assert child['assignee'] == child_initial['assignee']
    assert child['status'] == child_initial['status']

    whitespace_assignee = _create(client, 'Whitespace assignee with status', assignee='dev')
    whitespace = client.patch(f'/api/tasks/{whitespace_assignee}', json={'status': 'blocked', 'assignee': '   '})
    assert whitespace.status_code == 200, whitespace.text
    task = client.get(f'/api/tasks/{whitespace_assignee}').json()['task']
    assert task['status'] == 'blocked'
    assert task['assignee'] is None

    bulk_assignee = _create(client, 'Bulk whitespace assignee', assignee='dev')
    bulk = client.post('/api/tasks/bulk', json={'ids': [bulk_assignee], 'status': 'blocked', 'assignee': '   '})
    assert bulk.status_code == 200, bulk.text
    assert bulk.json()['results'][0]['ok'] is True
    task = client.get(f'/api/tasks/{bulk_assignee}').json()['task']
    assert task['status'] == 'blocked'
    assert task['assignee'] is None


def test_bulk_create_status_validation_and_application(client):
    before = client.get('/api/board').json()['tasks']
    invalid = client.post('/api/tasks/bulk-create', json={'tasks': [{'title': 'Bad bulk status', 'status': 'running'}]})
    assert invalid.status_code == 200
    assert invalid.json()['created'] == 0
    assert invalid.json()['results'][0]['ok'] is False
    after = client.get('/api/board').json()['tasks']
    assert len(after) == len(before)
    assert all(t['title'] != 'Bad bulk status' for t in after)

    valid = client.post('/api/tasks/bulk-create', json={'tasks': [{'title': 'Triaged bulk', 'status': 'triage'}]})
    assert valid.status_code == 200, valid.text
    assert valid.json()['created'] == 1
    rows = client.get('/api/board', params={'include_archived': True}).json()['tasks']
    assert next(t for t in rows if t['title'] == 'Triaged bulk')['status'] == 'triage'


def test_patch_rejects_comma_separated_skills(client):
    task_id = _create(client, 'Skill validation target', skills=['safe-skill'])
    bad = client.patch(f'/api/tasks/{task_id}', json={'skills': ['safe-skill', 'bad,skill']})
    assert bad.status_code == 400
    task = client.get(f'/api/tasks/{task_id}').json()['task']
    assert task['skills'] == ['safe-skill']
