import pytest
from fastapi.testclient import TestClient
from app import analytics, main, storage


@pytest.fixture
def local(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'analytics.sqlite3')
    monkeypatch.delenv('HAYSUB_DB', raising=False)
    monkeypatch.setenv('HAYSUB_PUBLIC', '0')
    with TestClient(main.app) as client:
        yield client


def test_visit_timing_survives_navigation_retries_and_device_categories(local, monkeypatch):
    now = [1000000.0]
    monkeypatch.setattr(analytics.time, 'time', lambda: now[0])
    body = {'id': 'a' * 32, 'active_seconds': 0}
    headers = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0) AppleWebKit Safari/605.1', 'Origin': 'http://testserver'}
    assert local.post('/api/visits', json=body, headers=headers).status_code == 200
    now[0] += 20
    body['active_seconds'] = 18
    assert local.post('/api/visits', json=body, headers=headers).status_code == 200
    body['active_seconds'] = 10
    local.post('/api/visits', json=body, headers=headers)
    result = local.get('/api/owner/analytics').json()
    assert result['summary']['visits'] == 1
    assert result['summary']['active_seconds'] == 18
    assert result['visits'][0]['device'] == 'phone'
    assert result['visits'][0]['platform'] == 'iOS'
    assert result['visits'][0]['browser'] == 'Safari'
    with analytics.connect() as db:
        assert {row[1] for row in db.execute('PRAGMA table_info(site_visits)')} == {'id', 'started', 'last_seen', 'active_seconds', 'device', 'browser', 'platform'}
    assert local.get('/admin/analytics').status_code == 200


def test_visit_durations_are_bounded_and_old_visits_expire(local, monkeypatch):
    now = [1000000.0]
    monkeypatch.setattr(analytics.time, 'time', lambda: now[0])
    first = {'id': 'a' * 32, 'active_seconds': 100000}
    local.post('/api/visits', json=first)
    assert local.get('/api/owner/analytics').json()['summary']['active_seconds'] == 0
    now[0] += 10
    local.post('/api/visits', json=first)
    assert local.get('/api/owner/analytics').json()['summary']['active_seconds'] == 12
    now[0] += 91 * 86400
    local.post('/api/visits', json={'id': 'b' * 32, 'active_seconds': 0})
    with analytics.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM site_visits').fetchone()[0] == 1


def test_analytics_rejects_bad_events_and_cross_site_writes(local):
    for body in ({'id': 'x', 'active_seconds': 0}, {'id': 'a' * 32, 'active_seconds': -1}, {'id': 'a' * 32, 'active_seconds': 'NaN'}):
        assert local.post('/api/visits', json=body).status_code == 422
    assert local.post('/api/visits', json={'id': 'a' * 32, 'active_seconds': 0}, headers={'Origin': 'https://other.test'}).status_code == 403
    assert local.get('/api/owner/analytics?days=91').status_code == 422


def test_public_hosting_does_not_enable_local_analytics(local, monkeypatch):
    monkeypatch.setenv('HAYSUB_PUBLIC', '1')
    assert local.get('/api/owner/analytics').status_code == 401
    assert local.get('/admin/analytics').status_code == 404
    assert 'visit-tracker.js' not in local.get('/catalog').text


def test_only_local_viewer_pages_include_tracker(local):
    assert 'visit-tracker.js' in local.get('/catalog').text
    assert 'visit-tracker.js' in local.get('/watch/' + 'a' * 32).text
    assert 'visit-tracker.js' not in local.get('/preview/' + 'a' * 32).text
    assert 'visit-tracker.js' not in local.get('/admin').text


@pytest.mark.parametrize('ua,device,browser,platform', [
    ('Mozilla/5.0 (Windows NT 10.0) Chrome/130.0 Edg/130.0', 'desktop', 'Edge', 'Windows'),
    ('Mozilla/5.0 (Linux; Android 14) Chrome/130.0 Mobile', 'phone', 'Chrome', 'Android'),
    ('Mozilla/5.0 (iPad; CPU OS 18_0) Safari/605.1', 'tablet', 'Safari', 'iPadOS'),
])
def test_device_categories(ua, device, browser, platform):
    assert analytics.device_info(ua) == (device, browser, platform)
