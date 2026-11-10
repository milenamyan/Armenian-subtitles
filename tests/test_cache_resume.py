import asyncio
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import main,storage,translation
from app.subtitles import parse_subtitles

SRT=b'1\n00:00:01,000 --> 00:00:02,000\nHello\n\n2\n00:00:02,000 --> 00:00:03,000\nGoodbye\n'


@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only');monkeypatch.setenv('GEMINI_MODEL','test-model')
    main.file_jobs.clear()


def test_exact_legacy_source_model_context_is_restored_without_gemini(monkeypatch):
    cues=parse_subtitles(SRT)
    legacy=translation.cache_key(cues,[],'test-model','eastern-armenian-v1')
    storage.save_cache(legacy,{'1':'Բարև','2':'Ցտեսություն'})
    monkeypatch.setattr(translation.genai,'Client',lambda **kwargs:pytest.fail('Proven cached work must not call Gemini'))
    with TestClient(main.app) as client:
        result=client.post('/api/subtitle-files',files={'subtitles':('old.srt',SRT)}).json()
        assert result['ready'] and result['completed']==result['restored_cues']==2
        assert result['compatible_cache_cues']==2 and not result['running']
        assert client.get(result['download_url']).status_code==200
    assert storage.cached(legacy)=={'1':'Բարև','2':'Ցտեսություն'}
    with sqlite3.connect(storage.DB) as db:
        row=db.execute('SELECT source_key,source_version,model FROM cache_reuse').fetchone()
        assert row==(legacy,'eastern-armenian-v1','test-model')


@pytest.mark.parametrize('changed',['source','timestamps','context','model','version'])
def test_incompatible_entries_are_not_reused(changed):
    cues=parse_subtitles(SRT);stored=[dict(c) for c in cues];context=[];model='test-model';version='eastern-armenian-v1'
    if changed=='source':stored[0]['source']='Different source'
    if changed=='timestamps':stored[0]['start']=1.5
    if changed=='context':context=[dict(id=3,start=4,end=5,source='Context')]
    if changed=='model':model='other-model'
    if changed=='version':version='unknown-prompt'
    storage.save_cache(translation.cache_key(stored,context,model,version),{'1':'Բարև','2':'Ցտեսություն'})
    restored,_=translation.restore_cached(cues,[],'test-model')
    assert restored=={}


def test_legacy_english_text_is_not_reused():
    cues=parse_subtitles(SRT)
    storage.save_cache(translation.cache_key(cues,[],'test-model','eastern-armenian-v1'),{'1':'Hello','2':'Ցտեսություն'})
    restored,info=translation.restore_cached(cues,[],'test-model')
    assert restored=={'2':'Ցտեսություն'} and info['compatible_cache_cues']==1


def test_completed_job_survives_memory_loss_and_renamed_reupload_without_api(monkeypatch):
    calls=[]
    async def stub(cues,context):
        calls.append(cues);return {str(c['id']):'Բարև' for c in cues}
    monkeypatch.setattr(main,'translate',stub)
    async def finish():await asyncio.gather(*list(main.tasks))
    with TestClient(main.app) as client:
        identity=client.post('/api/subtitle-files',files={'subtitles':('first.srt',SRT)}).json()['id']
        client.portal.call(finish)
        assert client.get('/api/subtitle-files/'+identity).json()['ready']
        main.file_jobs.clear()  # Simulate a fresh process with the same SQLite database.
        recovered=client.get('/api/subtitle-files/'+identity).json()
        assert recovered['completed']==2 and recovered['restored_cues']==2 and recovered['ready']
        main.file_jobs.clear()
        reuploaded=client.post('/api/subtitle-files',files={'subtitles':('renamed.srt',SRT)}).json()
        assert reuploaded['id']==identity and reuploaded['ready'] and reuploaded['completed']==2
        assert len(calls)==1


def test_partial_cache_with_first_cue_present_does_not_skip_unfinished_chunk(monkeypatch):
    cues=parse_subtitles(SRT)
    storage.save_cache(translation.cache_key(cues,[],'test-model')+':partial',{'1':'Բարև'})
    calls=[]
    async def stub(chunk,context):
        calls.append(chunk);return {'1':'Բարև','2':'Ցտեսություն'}
    monkeypatch.setattr(main,'translate',stub)
    async def finish():await asyncio.gather(*list(main.tasks))
    with TestClient(main.app) as client:
        result=client.post('/api/subtitle-files',files={'subtitles':('file.srt',SRT)}).json()
        assert result['completed']==1 and result['restored_cues']==1
        client.portal.call(finish)
        assert client.get('/api/subtitle-files/'+result['id']).json()['ready'] and len(calls)==1


def test_incomplete_persistent_job_restores_progress_and_retry(monkeypatch):
    job=main.new_job(None,parse_subtitles(SRT))
    job.update(file_identity='saved',file_fingerprint='fp',model='test-model',prompt_version=translation.PROMPT_VERSION,
               filename='saved.srt',translated={'1':'Բարև'},error='Temporary failure')
    storage.save_file_job(job)
    async def stub(cues,context):return {'1':'Բարև','2':'Ցտեսություն'}
    monkeypatch.setattr(main,'translate',stub)
    async def finish():await asyncio.gather(*list(main.tasks))
    with TestClient(main.app) as client:
        result=client.get('/api/subtitle-files/saved').json()
        assert result['completed']==1 and result['error'] and not result['running']
        client.post('/api/subtitle-files/saved/retry');client.portal.call(finish)
        assert client.get('/api/subtitle-files/saved').json()['ready']
