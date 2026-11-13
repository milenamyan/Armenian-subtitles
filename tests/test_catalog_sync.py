import json
import time
import pytest
from fastapi.testclient import TestClient
from app import main, storage, media_db, catalog_sync

VIDEO = 'https://media.example.org/movie.mp4'
CAPTIONS = 'https://media.example.org/armenian.srt'


@pytest.fixture
def synced(tmp_path, monkeypatch, isolate_local_library):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'metadata.sqlite3')
    monkeypatch.delenv('HAYSUB_DB', raising=False)
    monkeypatch.setenv('HAYSUB_PUBLIC', '0')
    monkeypatch.setenv('HAYSUB_STATIC_CATALOG_SYNC', '1')
    monkeypatch.setenv('HAYSUB_STATIC_CATALOG_DIR', str(tmp_path / 'site'))
    monkeypatch.setenv('HAYSUB_CLOUD_BASE_URL', 'https://media.example.org')
    monkeypatch.setenv('HAYSUB_CLOUD_VIDEO_IDS', '*')
    monkeypatch.setattr(catalog_sync, '_fingerprint', None)
    monkeypatch.setattr(catalog_sync, '_status', {'state': 'disabled'})
    with TestClient(main.app) as client:
        yield client, tmp_path / 'site'


def films(site):
    return json.loads((site / 'catalog.json').read_text(encoding='utf-8'))['films']


def add(client, video=VIDEO):
    response = client.post('/api/owner/media/cloud', json={
        'title': 'Հայերեն ֆիլմ', 'video_url': video, 'subtitle_url': CAPTIONS})
    assert response.status_code == 200, response.text
    return response


def test_owner_actions_sync_listings_titles_and_versioned_covers(synced):
    client, site = synced
    response = add(client)
    assert response.headers['X-HaySub-Catalog-Sync'] == 'saved'
    identity = response.json()['id']
    path = '/api/owner/media/' + identity
    assert films(site)[0]['id'] == identity
    assert films(site)[0]['subtitle_url'] == CAPTIONS
    assert client.patch(path, json={'title': 'Renamed film'}).status_code == 200
    assert films(site)[0]['title'] == 'Renamed film'

    png = b'\x89PNG\r\n\x1a\nfixture-poster'
    assert client.post(path + '/poster', files={'poster': ('cover.png', png, 'image/png')}).status_code == 200
    first_cover = site / films(site)[0]['poster_url']
    assert first_cover.read_bytes() == png
    jpeg = b'\xff\xd8\xffnew-cover'
    assert client.post(path + '/poster', files={'poster': ('cover.jpg', jpeg, 'image/jpeg')}).status_code == 200
    second_cover = site / films(site)[0]['poster_url']
    assert second_cover != first_cover and not first_cover.exists()
    assert second_cover.read_bytes() == jpeg

    assert client.patch(path, json={'published': False}).status_code == 200
    assert len(films(site)) == 1 and films(site)[0]['published'] is False
    assert films(site)[0]['title'] == 'Renamed film'
    assert second_cover.read_bytes() == jpeg
    assert client.patch(path, json={'published': True}).status_code == 200
    assert films(site)[0]['id'] == identity and films(site)[0]['published'] is True and second_cover.read_bytes() == jpeg
    assert client.delete(path).status_code == 200
    assert films(site) == [] and not second_cover.exists()


def test_worker_bin_restore_and_hidden_changes_are_picked_up_by_list_refresh(synced, monkeypatch):
    client, site = synced
    identity = 'a' * 32
    media_db.create(dict(id=identity, title='Managed film', size=10, fingerprint='fixture',
                         backend='local', object_key='videos/movie.mp4', subtitle_key='subtitles/armenian.srt',
                         part_size=10, state='ready', published=1, created=time.time(), updated=time.time()))
    assert client.get('/api/owner/media').status_code == 200
    assert films(site)[0]['id'] == identity
    media_db.bin_video(identity)
    client.get('/api/owner/media')
    assert films(site) == []
    assert media_db.restore_video(identity)
    client.get('/api/owner/media')
    assert len(films(site)) == 1 and films(site)[0]['published'] is False
    assert client.patch('/api/owner/media/' + identity, json={'published': True}).status_code == 200
    assert films(site)[0]['id'] == identity
    monkeypatch.setenv('HAYSUB_HIDDEN_VIDEO_IDS', identity)
    client.get('/api/owner/media')
    assert len(films(site)) == 1 and films(site)[0]['published'] is False
    media_db.update(identity, list_restored=1)
    client.get('/api/owner/media')
    assert films(site)[0]['id'] == identity and films(site)[0]['published'] is True


def test_bad_new_link_does_not_prevent_removing_an_old_published_film(synced):
    client, site = synced
    original = add(client).json()['id']
    invalid = add(client, 'https://media.example.org/private.mp4?X-Amz-Signature=secret')
    assert invalid.headers['X-HaySub-Catalog-Sync'] == 'warning'
    assert [film['id'] for film in films(site)] == [original]
    response = client.patch('/api/owner/media/' + original, json={'published': False})
    assert response.status_code == 200
    assert len(films(site)) == 1 and films(site)[0]['published'] is False
    assert 'secret' not in (site / 'catalog.json').read_text()


def test_write_failure_reports_separate_error_and_refresh_retries(synced, monkeypatch):
    client, site = synced
    item = add(client).json()
    writer = catalog_sync.save_manifest
    def fail(*args):
        raise PermissionError('fixture')
    monkeypatch.setattr(catalog_sync, 'save_manifest', fail)
    response = client.patch('/api/owner/media/' + item['id'], json={'title': 'Saved in database'})
    assert response.status_code == 200
    assert response.headers['X-HaySub-Catalog-Sync'] == 'error'
    assert media_db.get(item['id'])['title'] == 'Saved in database'
    assert films(site)[0]['title'] != 'Saved in database'
    monkeypatch.setattr(catalog_sync, 'save_manifest', writer)
    response = client.get('/api/owner/media')
    assert response.headers['X-HaySub-Catalog-Sync'] == 'saved'
    assert films(site)[0]['title'] == 'Saved in database'


def test_unchanged_refresh_does_not_rewrite_public_files(synced):
    client, site = synced
    add(client)
    before = (site / 'catalog.json').stat().st_mtime_ns
    client.get('/api/owner/media')
    assert (site / 'catalog.json').stat().st_mtime_ns == before


def test_public_mode_cannot_export_local_catalog(synced, monkeypatch):
    client, site = synced
    add(client)
    before = (site / 'catalog.json').read_bytes()
    monkeypatch.setenv('HAYSUB_PUBLIC', '1')
    assert catalog_sync.sync() == 'disabled'
    assert (site / 'catalog.json').read_bytes() == before


def test_saved_height_is_per_film_persistent_and_exported_to_public_playback(synced):
    client, site = synced
    first = add(client).json()['id']
    second = add(client, 'https://media.example.org/other.mp4').json()['id']
    path = '/api/owner/media/' + first
    assert client.patch(path, json={'subtitle_height': 18}).json()['subtitle_height'] == 18
    assert media_db.get(first)['subtitle_height'] == 18
    assert media_db.get(second)['subtitle_height'] == 10
    exported = {film['id']: film for film in films(site)}
    assert exported[first]['subtitle_height'] == 18
    assert exported[second]['subtitle_height'] == 10
    assert client.patch('/api/owner/media/' + second, json={'subtitle_height': 0}).json()['subtitle_height'] == 0
    assert {film['id']: film for film in films(site)}[second]['subtitle_height'] == 0
    assert client.get('/api/public/hosted/' + first + '/playback').json()['subtitle_height'] == 18
    assert 'id="watch-height-save"' in client.get('/preview/' + first).text
    assert 'id="watch-height-save"' not in client.get('/watch/' + first).text
    for invalid in (-1, 41, 2.5, True):
        assert client.patch(path, json={'subtitle_height': invalid}).status_code == 422
    assert media_db.get(first)['subtitle_height'] == 18
    with TestClient(main.app) as reopened:
        assert reopened.get(path).json()['subtitle_height'] == 18


def test_new_badge_toggle_persists_and_exports_without_affecting_other_films(synced):
    client, site = synced
    first = add(client).json()['id']
    second = add(client, 'https://media.example.org/second.mp4').json()['id']
    path = '/api/owner/media/' + first
    assert client.get(path).json()['is_new'] is True
    assert client.patch('/api/owner/media/' + second, json={'is_new': False}).status_code == 200
    for enabled in (True, False):
        response = client.patch(path, json={'is_new': enabled})
        assert response.status_code == 200
        assert response.json()['is_new'] is enabled
        exported = {item['id']: item for item in films(site)}
        listed = {item['id']: item for item in client.get('/api/public/videos').json()}
        assert exported[first]['is_new'] is enabled
        assert listed[first]['is_new'] is enabled
        assert exported[second]['is_new'] is False
        assert bool(media_db.get(first)['is_new']) is enabled
    assert client.patch(path, json={'is_new': 'true'}).status_code == 422
