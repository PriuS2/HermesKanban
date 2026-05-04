from __future__ import annotations


def test_health_and_config(client):
    assert client.get('/health').json()['ok'] is True
    init = client.post('/api/init')
    assert init.status_code == 200
    cfg = client.get('/api/config').json()
    assert cfg['default_language'] == 'ko'
    assert 'running' in cfg['columns']
    assert any(row['cli'] == 'boards create' for row in cfg['cli_parity'])
    status = client.get('/api/service/status').json()
    assert status['port'] == 8790
    assert status['current_board'] == 'default'
