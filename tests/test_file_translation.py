import asyncio
from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from app import main, storage, translation
from app.subtitles import parse_subtitles, translated_srt, format_srt_time

SRT = b'1\n00:00:01,250 --> 00:00:03,500\nHello\n\n2\n00:00:04,000 --> 00:00:05,999\nGoodbye\n'


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-not-sent')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    main.file_jobs.clear()


async def finish():
    await asyncio.gather(*list(main.tasks))


def test_remaining_estimate_uses_new_work_and_excludes_restored_cues(monkeypatch):
    monkeypatch.setattr(main.time, 'monotonic', lambda: 160)
    job = main.new_job(None, [dict(id=i) for i in range(100)])
    job.update(filename='test.srt', running=True, model='gemini-3.1-flash-lite',
               translated={str(i): 'text' for i in range(60)},
               translation_started=100, translation_start_completed=48)
    assert main.file_status('test', job)['estimated_remaining_seconds'] == 200
    job['translation_start_completed'] = 60
    assert main.file_status('test', job)['estimated_remaining_seconds'] is None
    job.update(running=False, phase='cancelled')
    assert main.file_status('test', job)['estimated_remaining_seconds'] is None


def test_cancel_preserves_completed_cues_across_reload_and_retry(monkeypatch):
    raw = '\n\n'.join(f'{i+1}\n00:00:{i:02},000 --> 00:00:{i+1:02},000\nHello' for i in range(13)).encode()
    calls = []

    async def stub(cues, context):
        calls.append(cues[0]['id'])
        if calls == [1, 13]:
            await asyncio.Event().wait()
        return {str(c['id']):'Բարև' for c in cues}

    async def wait_for_second_chunk():
        while len(calls) < 2:
            await asyncio.sleep(0.001)

    monkeypatch.setattr(main, 'translate', stub)
    with TestClient(main.app) as client:
        identity = client.post('/api/subtitle-files', files={'subtitles':('test.srt',raw)}).json()['id']
        client.portal.call(asyncio.wait_for, wait_for_second_chunk(), 5)
        assert client.post(f'/api/subtitle-files/{identity}/cancel').status_code == 200
        main.file_jobs.clear()
        state = client.get(f'/api/subtitle-files/{identity}').json()
        assert state['phase'] == 'cancelled' and not state['running']
        assert state['completed'] == 12 and not state['ready'] and not state['error']
        client.post(f'/api/subtitle-files/{identity}/retry')
        client.portal.call(finish)
        assert client.get(f'/api/subtitle-files/{identity}').json()['ready']
        assert calls == [1, 13, 13]


def test_standalone_file_download_uses_existing_cache_and_keeps_timestamps(monkeypatch):
    cues = parse_subtitles(SRT)
    result = {'1':'Բարև\nԲարի գալուստ', '2':'Ցտեսություն'}
    storage.save_cache(translation.cache_key(cues, [], 'test-model'), result)
    monkeypatch.setattr(translation.genai, 'Client', lambda **kwargs: pytest.fail('Cached chunks must not call Gemini'))
    monkeypatch.setattr(main, 'retrieve_captions', lambda *args: pytest.fail('File translation must not request YouTube captions'))
    with TestClient(main.app) as client:
        response = client.post('/api/subtitle-files', files={'subtitles':('Հայերեն.srt', SRT)})
        assert response.status_code == 200
        identity = response.json()['id']
        client.portal.call(finish)
        state = client.get('/api/subtitle-files/'+identity).json()
        assert state['total'] == state['completed'] == 2 and state['ready']
        assert 'cues' not in state and 'translated' not in state  # Poll small summaries.
        output = client.get(state['download_url'])
        assert output.status_code == 200 and output.content.startswith(b'\xef\xbb\xbf')
        exported = parse_subtitles(output.content)
        assert [(c['start'],c['end']) for c in exported] == [(c['start'],c['end']) for c in cues]
        assert exported[0]['source'] == 'Բարև\nԲարի գալուստ'
        assert 'Hello' not in output.content.decode('utf-8')
        assert 'Հայերեն_hy.srt' in unquote(output.headers['content-disposition'])
        assert output.headers['cache-control'] == 'no-store'
        assert client.get('/api/videos').json() == []


def test_failed_chunk_retry_retains_completed_work_and_blocks_partial_download(monkeypatch):
    raw = '\n\n'.join(f'{i+1}\n00:00:{i:02},000 --> 00:00:{i+1:02},000\nHello' for i in range(25)).encode()
    calls = []
    async def stub(cues, context):
        calls.append(cues[0]['id'])
        if calls == [1,13]:
            raise ValueError('Temporary translation failure')
        return {str(c['id']):'Բարև' for c in cues}
    monkeypatch.setattr(main, 'translate', stub)
    with TestClient(main.app) as client:
        identity = client.post('/api/subtitle-files', files={'subtitles':('test.srt',raw)}).json()['id']
        client.portal.call(finish)
        state = client.get('/api/subtitle-files/'+identity).json()
        assert state['completed'] == 12 and state['error'] and not state['ready']
        assert client.get('/api/subtitle-files/'+identity+'/download').status_code == 409
        client.post('/api/subtitle-files/'+identity+'/retry')
        client.portal.call(finish)
        assert client.get('/api/subtitle-files/'+identity).json()['ready']
        assert calls == [1,13,13,25]
        assert client.get('/api/subtitle-files/'+identity+'/download').status_code == 200


def test_temporary_failures_keep_retrying_and_preserve_completed_chunks(monkeypatch):
    cues = parse_subtitles('\n\n'.join(
        f'{i+1}\n00:00:{i:02},000 --> 00:00:{i+1:02},000\nHello'
        for i in range(25)).encode())
    job = main.new_job(None, cues)
    calls, delays = [], []

    async def stub(chunk, context):
        first = chunk[0]['id']
        calls.append(first)
        if first == 13 and calls.count(13) <= 4 or first == 25 and calls.count(25) == 1:
            raise translation.TemporaryTranslationError('HTTP 503')
        return {str(c['id']): 'Բարև' for c in chunk}

    async def sleep(delay):
        delays.append(delay)
        state = main.file_status('test', dict(job, filename='test.srt'))
        assert state['running'] and state['phase'] == 'retrying'
        assert not state['error'] and not state['ready']
        assert state['completed'] == (12 if len(delays) <= 4 else 24)
        assert 0 < state['retry_after_seconds'] <= delay

    monkeypatch.setattr(main, 'translate', stub)
    monkeypatch.setattr(main.asyncio, 'sleep', sleep)
    asyncio.run(main.worker(job))
    assert delays == [60, 60, 60, 60, 60]
    assert calls == [1, 13, 13, 13, 13, 13, 25, 25]
    assert len(job['translated']) == 25 and job['phase'] == 'ready'
    assert not job['running'] and not job['error'] and job['retry_at'] is None


def test_cancel_during_automatic_retry_preserves_progress(monkeypatch):
    job = main.new_job(None, parse_subtitles(SRT))
    job['translated'] = {'1': 'Բարև'}
    waiting = asyncio.Event()

    async def stub(chunk, context):
        raise translation.TemporaryTranslationError('HTTP 503')

    async def sleep(delay):
        waiting.set()
        await asyncio.Event().wait()

    async def run():
        main.start(job)
        await asyncio.wait_for(waiting.wait(), 2)
        assert job['phase'] == 'retrying'
        await main.stop_translation_job(job)

    monkeypatch.setattr(main, 'translate', stub)
    monkeypatch.setattr(main.asyncio, 'sleep', sleep)
    asyncio.run(run())
    assert job['phase'] == 'cancelled' and not job['running']
    assert job['translated'] == {'1': 'Բարև'} and not job['error']
    assert job['retry_at'] is None


def test_vtt_input_is_exported_as_srt(monkeypatch):
    async def stub(cues, context):
        return {str(c['id']):'Հայերեն' for c in cues}
    monkeypatch.setattr(main, 'translate', stub)
    with TestClient(main.app) as client:
        identity = client.post('/api/subtitle-files',files={'subtitles':('source.vtt',b'WEBVTT\n\n00:01.000 --> 00:02.250\nHello')}).json()['id']
        client.portal.call(finish)
        response = client.get('/api/subtitle-files/'+identity+'/download')
        assert 'source_hy.srt' in response.headers['content-disposition']
        assert '00:00:01,000 --> 00:00:02,250' in response.content.decode('utf-8-sig')


@pytest.mark.parametrize(('name','raw'), [('bad.txt',SRT),('bad.srt',b'garbage'),('empty.srt',b''),('big.srt',b'x'*(2*1024*1024+1))])
def test_bad_file_is_rejected(name, raw):
    with TestClient(main.app) as client:
        assert client.post('/api/subtitle-files',files={'subtitles':(name,raw)}).status_code == 400
        assert not main.file_jobs


def test_missing_api_configuration_is_explained(monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    with TestClient(main.app) as client:
        response = client.post('/api/subtitle-files',files={'subtitles':('test.srt',SRT)})
        assert response.status_code == 400 and '.env' in response.json()['detail']
        assert not main.file_jobs


def test_export_rejects_missing_translation_and_rounds_timestamp_carries():
    assert format_srt_time(59.9996) == '00:01:00,000'
    assert format_srt_time(3599.9996) == '01:00:00,000'
    assert format_srt_time(1.25) == '00:00:01,250'
    with pytest.raises(ValueError,match='not complete'):
        translated_srt(parse_subtitles(SRT), {'1':'Բարև'})


def test_missing_job_gives_reupload_instruction():
    with TestClient(main.app) as client:
        response = client.get('/api/subtitle-files/missing')
        assert response.status_code == 404 and 'upload' in response.json()['detail']


def test_page_has_utf8_translator_section_and_script():
    with TestClient(main.app) as client:
        html = client.get('/').text
        assert 'Թարգմանիր SRT/VTT ենթագրերը հայերեն' in html
        assert 'id="file-translator"' in html
        assert '/static/file-translator.js' in html
        assert html.index('id="file-translator"') < html.index('id="translation-library"') < html.index('id="video-library"')

def test_remove_process_stops_worker_and_preserves_job_in_bin(monkeypatch):
    async def blocked(cues, context):
        await asyncio.Event().wait()
    monkeypatch.setattr(main, 'translate', blocked)
    with TestClient(main.app) as client:
        identity = client.post('/api/subtitle-files', files={'subtitles': ('process.srt', SRT)}).json()['id']
        assert client.delete('/api/subtitle-files/'+identity).status_code == 200
        assert identity not in main.file_jobs
        assert storage.load_file_job(identity=identity) is None
        assert list((storage.DB.parent/'bin').glob('process-*/job.json'))
        assert client.get('/api/subtitle-files/'+identity).status_code == 404
        assert not any(not task.done() for task in main.tasks)


@pytest.mark.parametrize('extension', ['srt', 'vtt'])
def test_armenian_upload_is_ready_immediately_without_translation_configuration(monkeypatch, extension):
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_MODEL', raising=False)
    monkeypatch.setattr(main, 'start', lambda job: pytest.fail('Armenian uploads must not start translation'))
    dialogue = '\u0532\u0561\u0580\u0587, \u056b\u0576\u0579\u057a\u0565\u055e\u057d \u0565\u057d'
    raw = ('1\n00:00:01,250 --> 00:00:03,500\n' + dialogue + '\n\n2\n00:00:04,000 --> 00:00:05,999\n123!\n').encode('utf-8')
    if extension == 'vtt':
        raw = b'WEBVTT\n\n' + raw.replace(b',', b'.')
    with TestClient(main.app) as client:
        response = client.post('/api/subtitle-files', files={'subtitles': ('film.'+extension, raw)})
        assert response.status_code == 200
        state = response.json()
        assert state['ready'] and not state['running'] and state['phase'] == 'ready'
        assert state['completed'] == state['total'] == 2
        items = client.get('/api/library').json()
        assert len(items) == 1 and items[0]['id'] == state['id']
        output = parse_subtitles(client.get(state['download_url']).content)
        expected = dialogue.replace(',', '.') if extension == 'vtt' else dialogue
        assert output[0]['source'] == expected
        assert output[0]['start'] == 1.25 and output[0]['end'] == 3.5
        assert output[1]['source'] == '123!'
        main.file_jobs.clear()
        assert client.get('/api/subtitle-files/'+state['id']).json()['ready']


def test_non_armenian_upload_starts_translation_automatically(monkeypatch):
    calls = []
    async def stub(cues, context):
        calls.append(cues)
        return {str(cue['id']): '\u0532\u0561\u0580\u0587' for cue in cues}
    monkeypatch.setattr(main, 'translate', stub)
    with TestClient(main.app) as client:
        response = client.post('/api/subtitle-files', files={'subtitles': ('armenian-name.srt', SRT)})
        assert response.status_code == 200
        client.portal.call(finish)
        assert calls
        state = client.get('/api/subtitle-files/'+response.json()['id']).json()
        assert state['ready']
        assert len(client.get('/api/library').json()) == 1


def test_mixed_language_dialogue_is_not_mistaken_for_a_ready_armenian_file():
    assert not main.is_armenian_subtitle_file([{'source':'Hello \u0532\u0561\u0580\u0587'}, {'source':'Goodbye'}])
    assert not main.is_armenian_subtitle_file([{'source':'123!'}])
