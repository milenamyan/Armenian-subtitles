import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app import main, storage, translation
from app.subtitles import is_music_only, without_music_lines, translated_srt

CASES=json.loads((Path(__file__).parent/'music-cases.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('case',CASES,ids=lambda case:case['text'])
def test_music_detection_is_conservative(case):
    assert is_music_only(case['text']) == case['silent']


def test_music_only_chunk_skips_gemini_and_keeps_internal_ids(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.delenv('GEMINI_MODEL',raising=False)
    monkeypatch.setattr(translation.genai,'Client',lambda **kwargs:pytest.fail('Music must not call Gemini'))
    cues=[dict(id=1,start=1,end=3,source='[Music]'),dict(id=2,start=3,end=5,source='[музыка]')]
    result=asyncio.run(translation.translate(cues,[]))
    assert result == {'1':'','2':''}
    assert translated_srt(cues,result) == ''


def test_cached_music_is_silent_without_invalidating_dialogue_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_MODEL','cached-model')
    cues=[dict(id=1,start=1,end=2,source='[music]'),dict(id=2,start=2,end=3,source='Hello')]
    storage.save_cache(translation.cache_key(cues,[],'cached-model'),{'1':'Երաժշտություն','2':'Բարև'})
    result=asyncio.run(translation.translate(cues,[]))
    assert result == {'1':'','2':'Բարև'}
    output=translated_srt(cues,result)
    assert 'Բարև' in output and 'Երաժշտություն' not in output
    assert '00:00:02,000 --> 00:00:03,000' in output


def test_mixed_chunk_sends_only_dialogue_targets_to_model(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only');monkeypatch.setenv('GEMINI_MODEL','test-model')
    class Client:
        aio=property(lambda self:self);models=property(lambda self:self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def generate_content(self,**kwargs):
            assert [c['id'] for c in json.loads(kwargs['contents'])['target']] == [2]
            return SimpleNamespace(text='{"cues":[{"id":2,"text":"Բարև"}]}')
    monkeypatch.setattr(translation.genai,'Client',lambda **kwargs:Client())
    cues=[dict(id=1,start=1,end=2,source='♪'),dict(id=2,start=2,end=3,source='Hello')]
    assert asyncio.run(translation.translate(cues,[])) == {'1':'','2':'Բարև'}


def test_compact_extension_response_counts_silent_cues_but_does_not_display_them():
    job=main.new_job('abcdefghijk',[dict(id=1,start=1,end=2,source='[music]'),dict(id=2,start=2,end=3,source='Hello')])
    job['translated']={'1':'Երաժշտություն','2':'Բարև'}
    main.jobs['music-test']=job
    try:
        with TestClient(main.app) as client:
            result=client.get('/api/videos/music-test/translated-subtitles').json()
            assert result['completed']==2 and len(result['cues'])==1
            assert result['cues'][0]['id']==2 and not result['needs_resume']
    finally:
        main.jobs.pop('music-test',None)


def test_mixed_music_line_and_lyrics_are_preserved_as_dialogue():
    assert without_music_lines('[music]\nHello')=='Hello'
    assert without_music_lines('♪ Sing with me ♪')=='♪ Sing with me ♪'
