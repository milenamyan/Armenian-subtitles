import json
import sqlite3
from pathlib import Path
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient

from app import main, public, storage
from scripts.build_release import extension_archive, server_archive, validate_origin

ORIGIN='https://haysub.onrender.com'
PASSWORD='test-owner-password-with-at-least-32-characters'
ARMENIAN='1\n00:00:01,000 --> 00:00:03,000\nԲարև աշխարհ\n'


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'haysub.sqlite3')
    monkeypatch.setenv('HAYSUB_PUBLIC','1')
    monkeypatch.setenv('HAYSUB_PUBLIC_URL',ORIGIN)
    monkeypatch.setenv('HAYSUB_ADMIN_TOKEN',PASSWORD)
    monkeypatch.delenv('HAYSUB_DB',raising=False)
    public.attempts.clear()
    main.file_jobs.clear()


def owner(client):
    response=client.post('/api/admin/login',json={'token':PASSWORD},headers={'Origin':ORIGIN})
    assert response.status_code==200
    assert 'HttpOnly' in response.headers['set-cookie'] and 'Secure' in response.headers['set-cookie']


def imported(client):
    response=client.post('/api/library/import',files={'subtitles':('My film.srt',ARMENIAN.encode())},headers={'Origin':ORIGIN})
    assert response.status_code==200
    return response.json()['id']


def test_public_home_and_all_owner_endpoints_are_protected():
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert '/static/public-catalog.js' in client.get('/').text
        assert '/static/admin-login.js' in client.get('/admin').text
        for path in ('/api/library','/api/videos','/api/config','/api/subtitle-files/unknown','/api/library/unknown/download','/docs','/openapi.json'):
            assert client.get(path).status_code==401
        for path in ('/api/videos','/api/subtitle-files','/api/library/import','/api/subtitle-files/unknown/retry'):
            assert client.post(path).status_code==401
        assert client.patch('/api/library/unknown',json={'title':'Bad'}).status_code==401
        assert client.get('/healthz').json()=={'status':'ok'}
        assert client.get('/privacy').status_code==200


def test_private_import_explicit_publication_download_and_unpublish(monkeypatch):
    monkeypatch.setattr(main,'translate',lambda *args:pytest.fail('Import/catalog must not translate'))
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    with TestClient(main.app,base_url=ORIGIN) as client:
        owner(client)
        identity=imported(client)
        assert client.get('/api/public/library').json()==[]
        assert client.get('/api/public/library/'+identity+'/download').status_code==404
        result=client.patch('/api/library/'+identity+'/publication',json={'published':True},headers={'Origin':ORIGIN})
        assert result.status_code==200
        client.patch('/api/library/'+identity,json={'title':'Իմ ֆիլմը'},headers={'Origin':ORIGIN})
        client.post('/api/admin/logout',headers={'Origin':ORIGIN})
        assert client.get('/api/library').status_code==401
        items=client.get('/api/public/library').json()
        assert items==[{'id':identity,'title':'Իմ ֆիլմը','cue_count':1,'updated':items[0]['updated']}]
        assert client.get('/api/public/library?q=Իմ').json()==items
        assert client.get('/api/public/library?q=իմ').json()==items
        assert client.get('/api/public/library?q=%').json()==[]
        response=client.get('/api/public/library/'+identity+'/download')
        assert 'Բարև աշխարհ' in response.content.decode('utf-8-sig')
        owner(client)
        client.patch('/api/library/'+identity+'/publication',json={'published':False},headers={'Origin':ORIGIN})
        assert client.get('/api/public/library').json()==[]
        assert client.get('/api/public/library/'+identity+'/download').status_code==404


def test_csrf_and_cross_site_login_are_blocked():
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert client.post('/api/admin/login',json={'token':PASSWORD}).status_code==403
        assert client.post('/api/admin/login',json={'token':PASSWORD},headers={'Origin':'https://evil.test'}).status_code==403
        owner(client)
        assert client.post('/api/library/import').status_code==403
        assert client.post('/api/admin/logout',headers={'Origin':ORIGIN,'Sec-Fetch-Site':'cross-site'}).status_code==403
        assert client.get('/api/library').status_code==200


def test_login_rate_limit_tampered_cookie_and_logout():
    with TestClient(main.app,base_url=ORIGIN) as client:
        for _ in range(10):
            assert client.post('/api/admin/login',json={'token':'wrong'},headers={'Origin':ORIGIN}).status_code==401
        assert client.post('/api/admin/login',json={'token':PASSWORD},headers={'Origin':ORIGIN}).status_code==429
        public.attempts.clear()
        owner(client)
        value=client.cookies.get(public.COOKIE)
        client.cookies.clear();client.cookies.set(public.COOKIE,value[:-1]+('a' if value[-1]!='a' else 'b'))
        assert client.get('/api/library').status_code==401
        client.cookies.clear();owner(client)
        assert client.post('/api/admin/logout',headers={'Origin':ORIGIN}).status_code==200
        assert client.get('/api/library').status_code==401


def test_import_rejects_english_and_empty_files():
    with TestClient(main.app,base_url=ORIGIN) as client:
        owner(client)
        for raw in (b'',b'garbage',ARMENIAN.replace('Բարև աշխարհ','Hello world').encode()):
            response=client.post('/api/library/import',files={'subtitles':('film.srt',raw)},headers={'Origin':ORIGIN})
            assert response.status_code==400
        assert client.get('/api/library').json()==[]


def test_public_mode_requires_password_and_real_https_origin(monkeypatch):
    monkeypatch.setenv('HAYSUB_ADMIN_TOKEN','short')
    with pytest.raises(RuntimeError,match='32'):
        public.validate_configuration()
    monkeypatch.setenv('HAYSUB_ADMIN_TOKEN',PASSWORD)
    monkeypatch.setenv('HAYSUB_PUBLIC_URL','http://localhost:8000')
    with pytest.raises(RuntimeError,match='HTTPS'):
        public.validate_configuration()


def test_store_link_is_validated_and_secrets_are_never_returned(monkeypatch):
    monkeypatch.setenv('HAYSUB_STORE_URL','javascript:alert(1)')
    with TestClient(main.app,base_url=ORIGIN) as client:
        config=client.get('/api/public/config').json()
        assert config['store_url']==''
        assert PASSWORD not in json.dumps(config)


def test_publication_survives_restart_and_legacy_rows_remain_private():
    with TestClient(main.app,base_url=ORIGIN) as client:
        owner(client)
        identity=imported(client)
        client.patch('/api/library/'+identity+'/publication',json={'published':True},headers={'Origin':ORIGIN})
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert client.get('/api/public/library').json()[0]['id']==identity


def test_old_database_schema_is_migrated_without_publishing_existing_files():
    with sqlite3.connect(storage.DB) as db:
        db.execute('CREATE TABLE subtitle_library (id TEXT PRIMARY KEY,title TEXT NOT NULL,source_filename TEXT NOT NULL,srt TEXT NOT NULL,cue_count INTEGER NOT NULL,model TEXT,prompt_version TEXT,created TEXT DEFAULT CURRENT_TIMESTAMP,updated TEXT DEFAULT CURRENT_TIMESTAMP)')
        db.execute('INSERT INTO subtitle_library(id,title,source_filename,srt,cue_count) VALUES (?,?,?,?,?)',('a'*32,'Private old title','private.srt',ARMENIAN,1))
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert client.get('/api/public/library').json()==[]
        owner(client)
        item=client.get('/api/library').json()[0]
        assert item['title']=='Private old title' and item['published']==0


def test_expired_cookie_does_not_authorize_owner_access():
    with TestClient(main.app,base_url=ORIGIN) as client:
        value='1.nonce'
        client.cookies.set(public.COOKIE,value+'.'+public.signature(value))
        assert client.get('/api/library').status_code==401


def test_public_extension_package_has_exact_host_no_keys_and_public_config(tmp_path):
    output=tmp_path/'extension.zip'
    extension_archive(ORIGIN,output)
    with ZipFile(output) as archive:
        manifest=json.loads(archive.read('manifest.json'))
        assert manifest['host_permissions']==[ORIGIN+'/*']
        assert '127.0.0.1' not in json.dumps(manifest)
        assert 'connect-src '+ORIGIN in manifest['content_security_policy']['extension_pages']
        assert '"publicMode": true' in archive.read('config.js').decode()
        assert archive.read('icons/icon128.png').startswith(b'\x89PNG')
        assert 'tests/' not in '\n'.join(archive.namelist())
        assert not any(name.endswith(('.env','.sqlite3','.py')) for name in archive.namelist())
        assert 'library-background.js' in archive.namelist()
        for name in archive.namelist():
            assert PASSWORD.encode() not in archive.read(name)


def test_server_source_package_never_contains_local_secrets_or_database(tmp_path):
    output=tmp_path/'server.zip';server_archive(output)
    with ZipFile(output) as archive:
        names=archive.namelist()
        assert '.env' not in names and '.env.example' in names
        assert not any('data/' in name or '.venv/' in name or '__pycache__' in name for name in names)
        assert 'Dockerfile' in names and 'app/public.py' in names
        assert 'static/site-planet.png' in names


@pytest.mark.parametrize('url',['http://real.net','https://localhost','https://127.0.0.1','https://example.com','https://user:secret@host.net','https://host.net/path','https://host.net?q=1'])
def test_invalid_public_release_origins_are_rejected(url):
    with pytest.raises(ValueError):
        validate_origin(url)


def test_removed_url_player_route_is_not_available():
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert client.get('/player').status_code==404
        owner(client)
        assert client.get('/player').status_code==404


def test_security_headers_cover_public_pages_and_denied_requests():
    with TestClient(main.app,base_url=ORIGIN) as client:
        for path in ('/', '/privacy', '/admin', '/api/library'):
            response=client.get(path)
            assert response.headers['X-Content-Type-Options']=='nosniff'
            assert response.headers['Referrer-Policy']=='no-referrer'
            assert "frame-ancestors 'self'" in response.headers['Content-Security-Policy']
            assert response.headers['X-Frame-Options']=='SAMEORIGIN'
            assert response.headers['Strict-Transport-Security']=='max-age=31536000'
        assert client.get('/api/library').headers['Cache-Control']=='no-store'
        denied=client.post('/api/admin/login',json={'token':PASSWORD})
        assert denied.status_code==403
        assert denied.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('path',['/.env','/.git/config','/data/haysub.sqlite3','/static/../.env'])
def test_private_files_are_not_served(path):
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert client.get(path).status_code==404
