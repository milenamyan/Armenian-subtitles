import asyncio
from types import SimpleNamespace
import pytest
from app import storage, translation


@pytest.fixture(autouse=True)
def generous_test_budget(monkeypatch):
    # These tests exercise response retries; quota behavior has dedicated tests.
    monkeypatch.setattr('app.rate_limits.limits', lambda model: (1000, 1000, 10000000))


class APIError(Exception):
    def __init__(self, code):
        self.code = code


@pytest.mark.parametrize('bad_response', [None, 'not json', '{}', '{"cues":[]}', '{"cues":[{"id":1,"text":"Hello"}]}'])
@pytest.mark.parametrize('recovers', [True, False])
def test_invalid_responses_retry_without_caching(tmp_path, monkeypatch, bad_response, recovers):
    monkeypatch.setattr(storage, 'DB', tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only')
    monkeypatch.setenv('GEMINI_MODEL', 'test-model')
    calls, delays = [], []
    cues = [dict(id=1, start=0, end=1, source='Hello')]

    class Client:
        aio = property(lambda self: self)
        models = property(lambda self: self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text='{"cues":[{"id":1,"text":"Բարև"}]}' if recovers and len(calls) == 3 else bad_response)

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(translation.genai, 'Client', lambda **kwargs: Client())
    monkeypatch.setattr(translation.asyncio, 'sleep', sleep)
    if recovers:
        assert asyncio.run(translation.translate(cues, [])) == {'1': 'Բարև'}
        assert asyncio.run(translation.translate(cues, [])) == {'1': 'Բարև'}
    else:
        with pytest.raises(ValueError, match='after three attempts.*completed subtitles are saved'):
            asyncio.run(translation.translate(cues, []))
        assert storage.cached(translation.cache_key(cues, [], 'test-model')) is None
    assert len(calls) == 3
    assert delays == [5, 15]
    assert 'previous attempt failed validation' in calls[1]['config'].system_instruction


@pytest.mark.parametrize('source', ['...', '♪', '♪ ♫', '123', '—', '?!'])
def test_symbolic_cues_can_be_preserved(source):
    cues = [dict(id=13, source=source)]
    assert translation.validate_result({'cues': [{'id': 13, 'text': source}]}, cues) == {'13': source}


@pytest.mark.parametrize(('source', 'text'), [
    ('Hello', 'Hello'), ('Hello', '...'), ('[Music]', '[Music]'),
    ('...', ''), ('123', '456'), ('♪', '...'), ('Hello', '՜'),
])
def test_invalid_cue_error_identifies_the_cue(source, text):
    with pytest.raises(ValueError, match='cue 13'):
        translation.validate_result({'cues': [{'id': 13, 'text': text}]}, [dict(id=13, source=source)])


@pytest.mark.parametrize('code,expected_calls,fragment', [(503,1,'temporarily unavailable'), (429,1,'սահմանաչափ'), (403,1,'մերժվել')])
def test_retry_is_bounded_and_errors_are_specific(tmp_path, monkeypatch, code, expected_calls, fragment):
    monkeypatch.setattr(storage, 'DB', tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    calls, delays = [], []

    class Client:
        aio = property(lambda self:self)
        models = property(lambda self:self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def generate_content(self, **kwargs):
            calls.append(kwargs)
            raise APIError(code)

    async def sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(translation.genai, 'Client', lambda **kwargs:Client())
    monkeypatch.setattr(translation.asyncio, 'sleep', sleep)
    error_type = translation.TemporaryTranslationError if code == 503 else ValueError
    with pytest.raises(error_type, match=fragment):
        asyncio.run(translation.translate([dict(id=1,start=0,end=1,source='Hello')], []))
    assert len(calls) == expected_calls
    assert delays == ([5,15] if expected_calls == 3 else [])


def test_transient_503_recovers_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    calls = []

    class Client:
        aio = property(lambda self:self)
        models = property(lambda self:self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def generate_content(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise APIError(503)
            return SimpleNamespace(text='{"cues":[{"id":1,"text":"Բարև"}]}')

    async def sleep(delay):
        pass

    monkeypatch.setattr(translation.genai, 'Client', lambda **kwargs:Client())
    monkeypatch.setattr(translation.asyncio, 'sleep', sleep)
    cues = [dict(id=1,start=0,end=1,source='Hello')]
    with pytest.raises(translation.TemporaryTranslationError, match='HTTP 503'):
        asyncio.run(translation.translate(cues, []))
    # The worker owns the one-minute delay before the next attempt.
    assert asyncio.run(translation.translate(cues, [])) == {'1':'Բարև'}
    assert asyncio.run(translation.translate(cues, [])) == {'1':'Բարև'}
    assert len(calls) == 2
