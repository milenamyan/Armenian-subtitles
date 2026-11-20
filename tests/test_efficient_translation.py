import asyncio
import json
from types import SimpleNamespace

import pytest

from app import main, storage, translation


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'test.sqlite3')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setattr('app.rate_limits.limits', lambda model: (1000, 1000, 10000000))


def cues(count):
    return [dict(id=i+1, start=i*2, end=i*2+2, source='Hello') for i in range(count)]


def fake_client(monkeypatch, calls, bad_calls=0):
    class Client:
        aio = property(lambda self: self)
        models = property(lambda self: self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def generate_content(self, **kwargs):
            target = json.loads(kwargs['contents'])['target']
            calls.append([c['id'] for c in target])
            if len(calls) <= bad_calls:
                return SimpleNamespace(text='{"cues":[]}')
            return SimpleNamespace(text=json.dumps({'cues': [dict(id=c['id'], text='Բարև') for c in target]}))

    monkeypatch.setattr(translation.genai, 'Client', lambda **kwargs: Client())


def test_48_cues_use_two_requests_and_reload_uses_none(monkeypatch):
    calls = []
    fake_client(monkeypatch, calls)
    source = cues(48)
    job = main.new_job(None, source)
    asyncio.run(main.worker(job))
    assert not job['error'] and len(job['translated']) == 48
    assert calls == [list(range(1, 25)), list(range(25, 49))]
    restored = main.new_job(None, source)
    asyncio.run(main.worker(restored))
    assert restored['translated'] == job['translated']
    assert len(calls) == 2


def test_old_cache_and_saved_progress_are_not_retranslated(monkeypatch):
    source = cues(48)
    old_chunk = source[:12]
    old_context = source[12:15]
    storage.save_cache(translation.cache_key(old_chunk, old_context, 'test-model'),
                       {str(c['id']): 'Բարև' for c in old_chunk})
    job = main.new_job(None, source)
    # Saved file progress can end inside a new 24-cue batch.
    job['translated'] = {str(c['id']): 'Բարև' for c in source[12:18]}
    calls = []
    fake_client(monkeypatch, calls)
    asyncio.run(main.worker(job))
    assert not job['error'] and len(job['translated']) == 48
    assert calls == [list(range(19, 25)), list(range(25, 49))]


def test_partial_new_batch_is_preserved_when_worker_resumes(monkeypatch):
    source = cues(24)
    key = translation.cache_key(source, [], 'test-model')
    storage.save_cache(key + ':partial', {'1': 'Բարև'})
    calls = []
    fake_client(monkeypatch, calls)
    job = main.new_job(None, source)
    asyncio.run(main.worker(job))
    assert not job['error'] and len(job['translated']) == 24
    assert calls == [list(range(2, 25))]


@pytest.mark.parametrize('bad_calls', [1, 99])
def test_malformed_batches_shrink_without_fanout_to_24_single_requests(monkeypatch, bad_calls):
    calls = []
    fake_client(monkeypatch, calls, bad_calls=bad_calls)

    async def sleep(delay):
        pass

    monkeypatch.setattr(translation.asyncio, 'sleep', sleep)
    job = main.new_job(None, cues(24))
    asyncio.run(main.worker(job))
    if bad_calls == 1:
        assert not job['error'] and len(job['translated']) == 24
        assert [len(c) for c in calls] == [24, 12, 12]
    else:
        assert 'after three attempts' in job['error']
        assert [len(c) for c in calls] == [24, 12, 6]
