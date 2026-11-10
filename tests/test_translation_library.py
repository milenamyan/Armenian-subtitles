import asyncio
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from app import main, storage

SRT = b'1\n00:00:01,250 --> 00:00:03,500\nHello\n'


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-not-sent')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    main.file_jobs.clear()

    async def translate(cues, context):
        return {str(c['id']): 'Բարև' for c in cues}
    monkeypatch.setattr(main, 'translate', translate)


async def finish():
    await asyncio.gather(*list(main.tasks))


def upload(client, name='original.srt'):
    response = client.post('/api/subtitle-files', files={'subtitles': (name, SRT)})
    assert response.status_code == 200
    client.portal.call(finish)
    return response.json()['id']


def test_completed_upload_is_saved_and_rename_survives_reupload_and_restart(monkeypatch):
    with TestClient(main.app) as client:
        identity = upload(client)
        items = client.get('/api/library').json()
        assert len(items) == 1 and items[0]['title'] == 'original'
        assert 'srt' not in items[0] and 'cues' not in items[0]
        before = client.get(items[0]['download_url']).content
        local = storage.DB.parent / 'translated-subtitles' / 'original_hy' / 'original_hy.srt'
        assert local.read_bytes() == before
        assert (local.parent / 'original_original.srt').read_bytes() == SRT
        assert 'Բարև' in before.decode('utf-8-sig')
        assert '00:00:01,250 --> 00:00:03,500' in before.decode('utf-8-sig')
        renamed = client.patch('/api/library/'+identity, json={'title':'  Իմ ֆիլմը  '})
        assert renamed.status_code == 200 and renamed.json()['title'] == 'Իմ ֆիլմը'
        assert upload(client, 'another-name.srt') == identity
        assert client.get('/api/library').json()[0]['title'] == 'Իմ ֆիլմը'
    main.file_jobs.clear()
    monkeypatch.delenv('GEMINI_API_KEY')
    monkeypatch.setenv('GEMINI_MODEL', 'different-model')
    with TestClient(main.app) as client:
        item = client.get('/api/library').json()[0]
        assert item['source_filename'] == 'original.srt'
        download = client.get(item['download_url'])
        assert download.content == before
        assert 'Իմ ֆիլմը_hy.srt' in unquote(download.headers['content-disposition'])
        assert client.get('/api/subtitle-files/'+identity+'/download').content == before


def test_failed_or_partial_jobs_are_not_advertised_as_complete(monkeypatch):
    async def fail(cues, context):
        raise ValueError('Try again')
    monkeypatch.setattr(main, 'translate', fail)
    with TestClient(main.app) as client:
        identity = upload(client)
        assert client.get('/api/library').json() == []
        assert client.get('/api/library/'+identity+'/download').status_code == 404
        assert client.get('/api/subtitle-files/'+identity+'/download').status_code == 409


def test_previous_completed_jobs_are_indexed_at_startup():
    with TestClient(main.app) as client:
        identity = upload(client)
    with storage.connect() as db:
        db.execute('DELETE FROM subtitle_library')
    main.file_jobs.clear()
    with TestClient(main.app) as client:
        assert client.get('/api/library').json()[0]['id'] == identity


def test_deleted_translation_stays_deleted_after_restart():
    with TestClient(main.app) as client:
        identity = upload(client)
        client.patch('/api/library/'+identity+'/publication', json={'published': True})
        assert client.delete('/api/library/'+identity).status_code == 200
        archives=list((storage.DB.parent/'bin').glob('translation-*'))
        assert len(archives)==1
        assert (archives[0]/'translation.srt').read_text(encoding='utf-8-sig')
        import json
        archived=json.loads((archives[0]/'metadata.json').read_text(encoding='utf-8'))
        assert archived['translation']['id']==identity
        assert archived['job']['id']==identity
        assert identity not in main.file_jobs
        assert client.get('/api/library').json() == []
        assert client.get('/api/public/library').json() == []
        assert client.get('/api/library/'+identity+'/download').status_code == 404
        assert client.delete('/api/library/'+identity).status_code == 404
    with TestClient(main.app) as client:
        assert client.get('/api/library').json() == []


def test_cannot_delete_a_running_translation():
    with TestClient(main.app) as client:
        identity = upload(client)
        main.file_jobs[identity]['running'] = True
        assert client.delete('/api/library/'+identity).status_code == 409
        assert len(client.get('/api/library').json()) == 1
        main.file_jobs[identity]['running'] = False


@pytest.mark.parametrize('title', ['', '   ', 'bad\nname', 'bad\x00name', 'x'*201])
def test_invalid_names_are_rejected(title):
    with TestClient(main.app) as client:
        identity = upload(client)
        assert client.patch('/api/library/'+identity, json={'title':title}).status_code in (400,422)
        assert client.get('/api/library').json()[0]['title'] == 'original'


def test_names_are_metadata_and_download_filename_is_sanitized():
    with TestClient(main.app) as client:
        identity = upload(client)
        title = '../movie/<script>"; DROP TABLE subtitle_library;--'
        assert client.patch('/api/library/'+identity,json={'title':title}).json()['title'] == title
        assert len(client.get('/api/library').json()) == 1
        download = client.get('/api/library/'+identity+'/download')
        filename = unquote(download.headers['content-disposition'].split("filename*=UTF-8''")[1])
        assert '/' not in filename and '<' not in filename and '"' not in filename
        assert filename.endswith('_hy.srt')
        assert client.patch('/api/library/missing',json={'title':'Name'}).status_code == 404
