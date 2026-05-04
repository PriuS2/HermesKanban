from __future__ import annotations


def test_cli_parity_registry_and_route_table(client):
    registry = client.get('/api/ui/registry').json()['cli_parity']
    cli_names = {row['cli'] for row in registry}
    for expected in ['init', 'boards create', 'create', 'list', 'show', 'assign', 'claim', 'heartbeat', 'comment', 'complete', 'block', 'unblock', 'archive', 'tail/watch', 'runs', 'assignees', 'dispatch', 'stats', 'log', 'context', 'gc', 'daemon']:
        assert expected in cli_names

    route_apis = {row['api'] for row in registry}
    assert 'GET /api/tasks/{task_id}/monitor' not in route_apis  # monitor is UI-specific, not a CLI verb
    cfg = client.get('/api/config').json()
    assert len(cfg['cli_parity']) == len(registry)
