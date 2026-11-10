"""Public viewer integration checks; no real browser/media decoding is simulated."""
import base64
import time

import pytest
from fastapi.testclient import TestClient
from app import main, storage, media_db as db, public

ORIGIN='https://viewer.example'
TOKEN='viewer-test-owner-password-long-enough'
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'viewer.sqlite3')
    monkeypatch.delenv('HAYSUB_DB',raising=False)
    monkeypatch.setenv('HAYSUB_PUBLIC','1')
    monkeypatch.setenv('HAYSUB_PUBLIC_URL',ORIGIN)
    monkeypatch.setenv('HAYSUB_ADMIN_TOKEN',TOKEN)
    public.attempts.clear()


def owner(client):
    assert client.post('/api/admin/login',json={'token':TOKEN},headers={'Origin':ORIGIN}).status_code==200


def add(client,name):
    response=client.post('/api/owner/media/cloud',json={'title':name,'video_url':'https://cdn.example/'+name+'.mp4'},headers={'Origin':ORIGIN})
    assert response.status_code==200
    return response.json()['id']


def test_public_catalog_includes_local_and_cloud_ready_only_and_orders_by_publication():
    with TestClient(main.app,base_url=ORIGIN) as client:
        owner(client);first=add(client,'first');second=add(client,'second')
        db.update(first,published_at=time.time()+100,duration=900)
        # A local published film must appear too, with no storage access needed to list it.
        with db.connect() as connection:
            connection.execute('UPDATE hosted_videos SET external_video_url=NULL WHERE id=?',(first,))
        listed=client.get('/api/public/videos').json()
        assert [row['id'] for row in listed]==[first,second]
        assert listed[0]['duration']==900
        db.update(first,published=0);db.update(second,state='bin')
        assert client.get('/api/public/videos').json()==[]


def test_direct_watch_refresh_unpublished_deleted_and_owner_tools():
    with TestClient(main.app,base_url=ORIGIN) as client:
        owner(client);identity=add(client,'film')
        client.post('/api/admin/logout',headers={'Origin':ORIGIN})
        for path in ('/','/catalog','/watch/'+identity,'/watch/'+identity):
            page=client.get(path);assert page.status_code==200
            assert 'watch-url-form' not in page.text and 'watch-save-form' not in page.text
        assert 'id="catalog-back"' in client.get('/watch/'+identity).text
        page=client.get('/watch/'+identity).text
        for removed in ('watch-controls','watch-speed','watch-subtitles','watch-fullscreen','watch-retry','watch-restart'):
            assert 'id="'+removed+'"' not in page
        db.update(identity,published=0)
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        assert 'https://cdn.example/film.mp4' not in client.get('/watch/'+identity).text
        with db.connect() as connection:connection.execute('DELETE FROM hosted_videos WHERE id=?',(identity,))
        assert client.get('/watch/'+identity).status_code==200
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        assert client.post('/api/owner/media/cloud',json={}).status_code==401


def test_optional_poster_is_bounded_owner_only_and_hidden_after_unpublication():
    with TestClient(main.app,base_url=ORIGIN) as client:
        owner(client);identity=add(client,'poster')
        path='/api/owner/media/'+identity+'/poster'
        assert client.post(path,files={'poster':('p.svg',b'<svg/>','image/svg+xml')},headers={'Origin':ORIGIN}).status_code==400
        assert client.post(path,files={'poster':('p.png',PNG)},headers={'Origin':ORIGIN}).status_code==200
        assert client.post(path,files={'poster':('p.png',PNG+b'x'*(2*1024*1024))},headers={'Origin':ORIGIN}).status_code==413
        url=client.get('/api/public/videos').json()[0]['poster_url']
        client.post('/api/admin/logout',headers={'Origin':ORIGIN})
        response=client.get(url);assert response.content==PNG and response.headers['content-type']=='image/png'
        assert client.post(path,files={'poster':('p.png',PNG)}).status_code==401
        assert client.get(path).status_code==401
        db.update(identity,published=0);assert client.get(url).status_code==404
