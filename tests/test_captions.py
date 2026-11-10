import asyncio
import io
import sqlite3
import threading

import pytest
from fastapi.testclient import TestClient

from app import captions, main, storage, translation

VIDEO = 'dQw4w9WgXcQ'
URL = 'https://www.youtube.com/api/timedtext?lang=en&fmt=vtt'
VTT = b'WEBVTT\nKind: captions\nLanguage: en\n\n00:00:01.000 --> 00:00:03.000\nHello world\n\n00:00:02.000 --> 00:00:04.000\nHello world again\n\n00:00:03.000 --> 00:00:05.000\nworld again today\n'


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'test.sqlite3')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GEMINI_MODEL', raising=False)
    main.jobs.clear()


def fake_ydl(monkeypatch, info, payload=VTT, fail=None):
    calls = []

    class FakeYDL:
        def __init__(self, options):
            calls.append(('options', options))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download):
            calls.append(('extract', url, download))
            if isinstance(info, Exception):
                raise info
            return info

        def urlopen(self, url):
            calls.append(('caption', url))
            if fail:
                raise fail
            return io.BytesIO(payload)

    monkeypatch.setattr(captions, 'YoutubeDL', FakeYDL)
    return calls


def track(url=URL):
    return {'ext': 'vtt', 'url': url}


def test_creator_precedes_auto_and_does_not_normalize(monkeypatch):
    calls = fake_ydl(monkeypatch, {'subtitles': {'en-US': [track()]}, 'automatic_captions': {'en': [track(URL+'&auto=1')]}})
    result = captions.retrieve_captions(VIDEO)
    assert result['source'] == 'creator'
    assert result['cues'][1]['source'] == 'Hello world again'
    options = calls[0][1]
    assert options['skip_download'] is True
    assert options['writesubtitles'] is False and options['writeautomaticsub'] is False
    assert calls[1] == ('extract', 'https://www.youtube.com/watch?v='+VIDEO, False)
    assert [c for c in calls if c[0] == 'caption'] == [('caption', URL)]


def test_automatic_english_and_rolling_normalization(monkeypatch):
    fake_ydl(monkeypatch, {'automatic_captions': {'fr': [track()], 'en-orig': [track()]}})
    result = captions.retrieve_captions(VIDEO)
    assert result['source'] == 'automatic'
    assert [(c['start'], c['end'], c['source']) for c in result['cues']] == [(1,2,'Hello world'), (2,3,'again'), (3,5,'today')]
    assert [c['id'] for c in result['cues']] == [1,2,3]


def test_full_repeats_gaps_and_equal_start():
    def cue(start, end, text):
        return dict(id=99, start=start, end=end, source=text)
    cues = [cue(0,2,'Hello'), cue(0,3,'Hello world'), cue(1,4,'Hello world'), cue(8,10,'Hello world')]
    result = captions.normalize_rolling(cues)
    assert [(c['source'], c['start'], c['end']) for c in result] == [('Hello world',0,4), ('Hello world',8,10)]
    assert all(c['end'] > c['start'] for c in result)
    assert cues[0]['end'] == 2  # Never mutate the parser output.


def test_youtube_empty_window_events_are_skipped(monkeypatch):
    payload = b'WEBVTT\n\n00:00:00.000 --> 00:00:00.000\n\n00:00:01.000 --> 00:00:03.000\nHello\n\n00:00:03.000 --> 00:00:03.010\n \n\n00:00:04.000 --> 00:00:06.000\nHello again\n'
    fake_ydl(monkeypatch, {'automatic_captions': {'en': [track()]}}, payload=payload)
    result = captions.retrieve_captions(VIDEO)
    assert [(c['id'], c['start'], c['end'], c['source']) for c in result['cues']] == [(1,1,3,'Hello'), (2,4,6,'Hello again')]
    # The lenient setting must never leak into the user-upload parser.
    with pytest.raises(ValueError):
        captions.parse_subtitles(payload)


def test_empty_only_or_invalid_youtube_cues_are_not_success():
    for payload in [b'WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n', b'WEBVTT\n\n00:00:02.000 --> 00:00:01.000\n']:
        with pytest.raises(ValueError):
            captions.parse_subtitles(payload, allow_empty_cues=True)


def test_youtube_blank_lines_inside_cue_do_not_lose_dialogue(monkeypatch):
    payload = b'WEBVTT\nKind: captions\nLanguage: en\n\n00:00:01.000 --> 00:00:03.000 align:start position:0%\n\n[music]\n\n00:00:03.000 --> 00:00:03.010\n \n\n00:00:04.000 --> 00:00:06.000\nHello\n\n<c>friends</c>\n'
    fake_ydl(monkeypatch, {'automatic_captions': {'en': [track()]}}, payload=payload)
    cues = captions.retrieve_captions(VIDEO)['cues']
    assert [(c['start'], c['end'], c['source']) for c in cues] == [(1,3,'[music]'), (4,6,'Hello friends')]


def test_translated_and_non_english_tracks_are_not_selected(monkeypatch):
    fake_ydl(monkeypatch, {'automatic_captions': {'en': [track(URL+'&tlang=en')], 'de': [track()]}, 'subtitles': {'eng': [track()]}})
    with pytest.raises(captions.CaptionError) as error:
        captions.retrieve_captions(VIDEO)
    assert error.value.code == 'missing_captions'
    assert '.srt' in str(error.value)


@pytest.mark.parametrize(('failure', 'code'), [('HTTP Error 429 Too Many Requests', 'rate_limited'), ('HTTP Error 403 Forbidden', 'access_denied'), ('Sign in to confirm you are not a bot', 'access_denied'), ('connection timed out signed-url-secret', 'retrieval_failed')])
def test_safe_error_classification(monkeypatch, failure, code):
    fake_ydl(monkeypatch, RuntimeError(failure))
    with pytest.raises(captions.CaptionError) as error:
        captions.retrieve_captions(VIDEO)
    assert error.value.code == code
    assert 'signed-url-secret' not in str(error.value)


def test_rate_limit_stops_track_attempts(monkeypatch):
    calls = fake_ydl(monkeypatch, {'subtitles': {'en': [track()]}, 'automatic_captions': {'en': [track()]}}, fail=RuntimeError('HTTP 429'))
    with pytest.raises(captions.CaptionError, match='YouTube'):
        captions.retrieve_captions(VIDEO)
    assert len([c for c in calls if c[0] == 'caption']) == 1


def test_bad_creator_payload_falls_back_to_auto(monkeypatch):
    calls = fake_ydl(monkeypatch, {'subtitles': {'en': [track('https://evil.example/captions')]}, 'automatic_captions': {'en': [track()]}})
    assert captions.retrieve_captions(VIDEO)['source'] == 'automatic'
    assert [c for c in calls if c[0] == 'caption'] == [('caption', URL)]


@pytest.mark.parametrize('payload', [b'invalid', b'x'*(captions.MAX_CAPTION_BYTES+1)])
def test_invalid_caption_payload(monkeypatch, payload):
    fake_ydl(monkeypatch, {'subtitles': {'en':[track()]}}, payload=payload)
    with pytest.raises(captions.CaptionError) as error:
        captions.retrieve_captions(VIDEO)
    assert error.value.code == 'retrieval_failed'


def test_upload_has_priority_and_invalid_upload_does_not_fallback(monkeypatch):
    def forbidden(video):
        raise AssertionError('YouTube must not be queried for uploaded subtitles')
    monkeypatch.setattr(main, 'retrieve_captions', forbidden)
    with TestClient(main.app) as client:
        response = client.post('/api/videos', data={'url':'https://youtu.be/'+VIDEO}, files={'subtitles':('test.vtt', VTT)})
        assert response.status_code == 200
        assert response.json()['caption_source'] == 'uploaded'
        assert response.json()['phase'] == 'ready'
        assert client.post('/api/videos', data={'url':'https://youtu.be/'+VIDEO}, files={'subtitles':('bad.vtt', b'invalid')}).status_code == 400


def test_background_retrieval_pipeline_and_cache(monkeypatch):
    calls = fake_ydl(monkeypatch, {'automatic_captions': {'en': [track()]}})
    cues = captions.normalize_rolling(captions.parse_subtitles(VTT))
    monkeypatch.setenv('GEMINI_API_KEY', 'test-key-never-used')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    expected = {str(c['id']):'Բարև' for c in cues}
    storage.save_cache(translation.cache_key(cues, [], 'test-model'), expected)
    monkeypatch.setattr(translation.genai, 'Client', lambda **kwargs: pytest.fail('Cached translation must not call Gemini'))

    async def scenario():
        job = main.new_job(VIDEO, [])
        storage.save_video('job', VIDEO, [])
        main.start_captions('job', job)
        assert job['phase'] == 'retrieving' and job['running']
        await asyncio.gather(*list(main.tasks))
        assert job['phase'] == 'ready' and not job['error']
        assert job['translated'] == expected
        assert storage.load_video('job') == (VIDEO, cues, 'automatic')
        # History reload uses the persisted source and cues without retrieval.
        assert main.get_job('job')['caption_source'] == 'automatic'
        assert len([c for c in calls if c[0] == 'extract']) == 1
    asyncio.run(scenario())


def test_retrieval_progress_api_and_retry(monkeypatch):
    gate, entered = threading.Event(), threading.Event()
    attempts = []

    def retrieve(video):
        attempts.append(video)
        entered.set()
        gate.wait(3)
        if len(attempts) == 1:
            raise captions.CaptionError('missing_captions', 'No English captions.')
        return dict(cues=captions.parse_subtitles(VTT), source='creator', language='en')

    monkeypatch.setattr(main, 'retrieve_captions', retrieve)
    with TestClient(main.app) as client:
        response = client.post('/api/videos', data={'url':'https://youtu.be/'+VIDEO})
        identity = response.json()['id']
        assert response.json()['phase'] == 'retrieving'
        assert entered.wait(2)
        assert client.get('/api/videos/'+identity).json()['phase'] == 'retrieving'
        # Repeated retries during an active retrieval must not start another one.
        client.post('/api/videos/'+identity+'/retry')
        assert len(attempts) == 1
        gate.set()

        async def finish():
            await asyncio.gather(*list(main.tasks))
        client.portal.call(finish)
        failed = client.get('/api/videos/'+identity).json()
        assert failed['error_code'] == 'missing_captions'
        assert not failed['running'] and not failed['cues']
        client.post('/api/videos/'+identity+'/retry')
        client.portal.call(finish)
        ready = client.get('/api/videos/'+identity).json()
        assert ready['phase'] == 'ready' and ready['cues']
        assert not ready['error'] and ready['error_code'] is None


def test_existing_database_migration_preserves_history():
    with sqlite3.connect(storage.DB) as db:
        db.execute('CREATE TABLE videos (id TEXT PRIMARY KEY, video TEXT, cues TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
        db.execute('INSERT INTO videos(id,video,cues) VALUES (?,?,?)', ('old', VIDEO, '[]'))
    assert storage.load_video('old') == (VIDEO, [], None)
    storage.save_video('old', VIDEO, [], 'creator')
    assert storage.load_video('old')[2] == 'creator'


def test_timeout_offers_upload_without_late_result(monkeypatch):
    async def timeout(awaitable, timeout):
        assert timeout == 90
        awaitable.close()  # Do not launch a network thread in a timeout unit test.
        raise asyncio.TimeoutError

    monkeypatch.setattr(main.asyncio, 'wait_for', timeout)
    job = main.new_job(VIDEO, [])
    asyncio.run(main.caption_worker('timeout', job))
    assert job['phase'] == 'error' and job['error_code'] == 'retrieval_timeout'
    assert not job['running'] and not job['cues'] and '.srt/.vtt' in job['error']


def test_restricted_caption_warning_is_not_reported_as_missing(monkeypatch):
    calls = fake_ydl(monkeypatch, {'id': VIDEO})
    # Capture how the installed integration passes yt-dlp warnings to our logger.
    original = captions.YoutubeDL.extract_info

    def restricted(self, *args, **kwargs):
        calls[0][1]['logger'].warning('Subtitles skipped because a PO token was not provided')
        return original(self, *args, **kwargs)

    monkeypatch.setattr(captions.YoutubeDL, 'extract_info', restricted)
    with pytest.raises(captions.CaptionError) as error:
        captions.retrieve_captions(VIDEO)
    assert error.value.code == 'access_denied'
