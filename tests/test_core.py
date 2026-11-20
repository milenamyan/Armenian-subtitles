import asyncio
import pytest
from fastapi.testclient import TestClient
from app import storage, translation
from app.subtitles import parse_subtitles, video_id
from app.main import app

SRT = b'1\n00:00:01,000 --> 00:00:03,000\nHello <i>world</i>\n\n2\n00:00:03,000 --> 00:00:05,000\nGoodbye\n'


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'test.sqlite3')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_MODEL', raising=False)


@pytest.mark.parametrize('url', ['https://youtu.be/dQw4w9WgXcQ', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'https://youtube.com/shorts/dQw4w9WgXcQ'])
def test_urls(url):
    assert video_id(url) == 'dQw4w9WgXcQ'


@pytest.mark.parametrize('url', ['https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ', 'file:///etc/passwd', 'https://evil.com/', 'https://user@youtube.com/watch?v=dQw4w9WgXcQ'])
def test_bad_urls(url):
    with pytest.raises(ValueError):
        video_id(url)


def test_parser():
    cues = parse_subtitles(SRT)
    assert cues[0] == dict(id=1, start=1, end=3, source='Hello world')
    assert parse_subtitles(b'WEBVTT\n\nname\n00:01.000 --> 00:03.000 align:start\nHi')[0]['start'] == 1


@pytest.mark.parametrize('raw', [b'', b'garbage', b'1\n00:00:03,000 --> 00:00:01,000\nHi', b'1\n00:99:00,000 --> 00:99:01,000\nHi', b'x' * (2*1024*1024+1)])
def test_bad_subtitles(raw):
    with pytest.raises(ValueError):
        parse_subtitles(raw)


def test_translation_validation():
    cues = parse_subtitles(SRT)
    for result in [dict(cues=[dict(id=1,text='Hello'),dict(id=2,text='Bye')]),dict(cues=[dict(id=2,text='Բարև'),dict(id=1,text='Ցտեսություն')]),dict(cues=[dict(id=1,text='Բարև'),dict(id=1,text='Բարև')])]:
        with pytest.raises(ValueError):
            translation.validate_result(result, cues)


def test_cache_identity_and_hit(monkeypatch):
    cues = parse_subtitles(SRT)
    a = translation.cache_key(cues, [], 'one')
    assert a != translation.cache_key(cues, [], 'two')
    assert a != translation.cache_key(cues[:1], [], 'one')
    assert a != translation.cache_key(cues, cues[:1], 'one')
    monkeypatch.setenv('GEMINI_MODEL', 'one')
    storage.save_cache(a, {'1':'Բարև', '2':'Ցտեսություն'})
    assert asyncio.run(translation.translate(cues, []))['1'] == 'Բարև'
    monkeypatch.setattr(translation, 'PROMPT_VERSION', 'changed')
    assert a != translation.cache_key(cues, [], 'one')


def test_upload_history_and_missing_key():
    with TestClient(app) as client:
        assert client.get('/').status_code == 200
        response = client.post('/api/videos', data={'url':'https://youtu.be/dQw4w9WgXcQ'}, files={'subtitles':('test.srt',SRT)})
        assert response.status_code == 200
        job = response.json()
        assert len(job['cues']) == 2 and not job['translated']
        assert client.get('/api/videos').json()[0]['id'] == job['id']
        assert client.post('/api/videos/'+job['id']+'/position', json={'seconds':4}).status_code == 200
        assert client.get('/api/videos/'+job['id']).json()['position'] == 4
        assert client.post('/api/videos',data={'url':'https://evil.com'}).status_code == 400
        assert client.get('/api/config').json() == {'configured':False}


def test_worker_prioritizes_seek_and_keeps_times(monkeypatch):
    from app.main import new_job, worker
    cues = [dict(id=i+1, start=i*2, end=i*2+2, source='Hello') for i in range(30)]
    job = new_job('dQw4w9WgXcQ', cues)
    job['position'] = 50
    order = []

    async def local_translation(chunk, context):
        order.append(chunk[0]['id'])
        return {str(c['id']): 'Բարև' for c in chunk}

    monkeypatch.setattr('app.main.translate', local_translation)
    asyncio.run(worker(job))
    assert order[0] == 25
    assert len(job['translated']) == 30
    assert job['cues'] == cues and not job['running'] and not job['error']


def test_missing_key_is_explicit():
    with pytest.raises(ValueError, match='GEMINI_API_KEY'):
        asyncio.run(translation.translate(parse_subtitles(SRT), []))


def test_uploaded_file_translates_with_key_retry_and_history(monkeypatch):
    from app import main
    monkeypatch.setenv('GEMINI_API_KEY', 'configured-test-key')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')

    calls = []
    async def translate_uploaded(cues, context):
        calls.append(cues)
        return {str(c['id']): 'Բարև' for c in cues}

    monkeypatch.setattr(main, 'translate', translate_uploaded)
    monkeypatch.setattr(main, 'retrieve_captions', lambda *args: pytest.fail('Uploaded subtitles must take priority over YouTube captions'))
    with TestClient(app) as client:
        job = client.post('/api/videos', data={'url':'https://youtu.be/dQw4w9WgXcQ'}, files={'subtitles':('sub.srt',SRT)}).json()
        assert job['caption_source'] == 'uploaded'
        assert job['cues'][0]['source'] == 'Hello world'
        async def finish():
            await asyncio.gather(*list(main.tasks))
        client.portal.call(finish)
        assert client.get('/api/videos/'+job['id']).json()['translated'] == {'1':'Բարև','2':'Բարև'}
        client.post('/api/videos/'+job['id']+'/retry')
        client.portal.call(finish)
        assert len(calls) == 1  # Completed chunks are not submitted again.
        main.jobs.pop(job['id'])
        restored = client.get('/api/videos/'+job['id']).json()
        assert restored['caption_source'] == 'uploaded'
        client.post('/api/videos/'+job['id']+'/retry')
        client.portal.call(finish)
        assert not client.get('/api/videos/'+job['id']).json()['running']
        assert len(calls) == 2


def test_upload_reports_zero_length_dialogue_instead_of_dropping_it():
    raw = b'1\n00:00:01,000 --> 00:00:02,000\n\n2\n00:00:02,000 --> 00:00:02,000\nInvisible\n\n3\n00:00:03,000 --> 00:00:05,000\nHello\n'
    with TestClient(app) as client:
        response = client.post('/api/videos',data={'url':'https://youtu.be/dQw4w9WgXcQ'},files={'subtitles':('test.srt',raw)})
        assert response.status_code == 400
        assert 'Subtitle cue 2' in response.json()['detail']
        assert 'end time must be later' in response.json()['detail']


def test_bad_duration_identifies_original_cue():
    with pytest.raises(ValueError, match='Subtitle cue 42 .*end time'):
        parse_subtitles(b'42\n00:00:05,000 --> 00:00:03,000\nHello', allow_empty_cues=True)


def test_stalled_second_chunk_stops_and_preserves_completed_cues(monkeypatch):
    from app import main
    monkeypatch.setattr(main, 'CHUNK_SIZE', 12)
    cues = [dict(id=i+1, start=i*2, end=i*2+2, source='Hello') for i in range(24)]
    job = main.new_job('dQw4w9WgXcQ', cues)
    entered = asyncio.Event()
    cancelled = []

    async def translate(chunk, context):
        if chunk[0]['id'] == 1:
            return {str(c['id']): 'Բարև' for c in chunk}
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)

    monkeypatch.setattr(main, 'translate', translate)
    monkeypatch.setattr(main, 'CHUNK_TIMEOUT', 0.02)

    async def scenario():
        task = asyncio.create_task(main.worker(job))
        await entered.wait()
        assert job['active_chunk']['first'] == 13
        assert job['chunk_started'] is not None
        await task

    asyncio.run(scenario())
    assert len(job['translated']) == 12
    assert job['phase'] == 'error' and not job['running']
    assert job['error_code'] == 'translation_timeout'
    assert job['active_chunk'] is None and cancelled
