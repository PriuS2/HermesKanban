from __future__ import annotations


def test_board_crud_switch_and_metadata(client):
    r = client.post('/api/boards', json={
        'slug': 'project-alpha',
        'name': 'Project Alpha',
        'description': 'Readable project board',
        'icon': '🚀',
        'color': '#0d74ce',
        'switch': True,
    })
    assert r.status_code == 200, r.text
    assert r.json()['current'] == 'project-alpha'

    boards = client.get('/api/boards').json()
    slugs = [b['slug'] for b in boards['boards']]
    assert 'default' in slugs and 'project-alpha' in slugs

    detail = client.get('/api/boards/project-alpha').json()['board']
    assert detail['name'] == 'Project Alpha'
    assert detail['is_current'] is True

    patched = client.patch('/api/boards/project-alpha', json={'name': 'Alpha Ops'}).json()['board']
    assert patched['name'] == 'Alpha Ops'

    switched = client.post('/api/boards/default/switch').json()
    assert switched['current'] == 'default'

    deleted = client.delete('/api/boards/project-alpha').json()['result']
    assert deleted['action'] == 'archived'


def test_board_view_accepts_empty_frontend_filters(client):
    created = client.post('/api/tasks', json={'title': 'Visible task', 'assignee': 'dev'})
    assert created.status_code == 200, created.text

    response = client.get(
        '/api/board',
        params={
            'board': 'default',
            'include_archived': 'false',
            'q': '',
            'assignee': '',
        },
    )
    assert response.status_code == 200, response.text
    assert any(task['title'] == 'Visible task' for task in response.json()['tasks'])
