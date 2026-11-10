import asyncio
import pytest
from fastapi.testclient import TestClient
from app import main, storage, captions


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-not-sent')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    main.jobs.clear()


async def finish():
    await asyncio.gather(*list(main.tasks))


def test_extension_native_caption_source_uses_same_translation_pipeline(monkeypatch):
    calls=[]
    def retrieve(video, allow_any_language=False):
        calls.append((video,allow_any_language))
        return dict(cues=[dict(id=1,start=1,end=3,source='Привет')],source='creator',language='ru')
    async def translate(cues,context):
        return {'1':'Բարև'}
    monkeypatch.setattr(main,'retrieve_captions',retrieve);monkeypatch.setattr(main,'translate',translate)
    with TestClient(main.app) as client:
        result=client.post('/api/videos',data={'url':'https://www.youtube.com/watch?v=abcdefghijk','native_captions':'true','summary':'true'}).json()
        assert 'cues' not in result
        client.portal.call(finish)
        state=client.get('/api/videos/'+result['id']+'/translated-subtitles').json()
        assert state['cues']==[dict(id=1,start=1,end=3,text='Բարև')]
        assert state['source']=='creator' and not state['running'] and calls==[('abcdefghijk',True)]


def test_cancel_stops_running_translation_and_keeps_completed_cues(monkeypatch):
    entered=asyncio.Event()
    async def hanging(cues,context):
        entered.set();await asyncio.Event().wait()
    monkeypatch.setattr(main,'translate',hanging)
    with TestClient(main.app) as client:
        result=client.post('/api/videos',data={'url':'https://www.youtube.com/watch?v=abcdefghijk'},files={'subtitles':('test.srt',b'1\n00:00:01,000 --> 00:00:03,000\nHello')}).json()
        client.portal.call(entered.wait)
        client.post('/api/videos/'+result['id']+'/cancel')
        state=client.get('/api/videos/'+result['id']+'/translated-subtitles').json()
        assert state['phase']=='cancelled' and not state['running'] and not state['cues']


def test_any_language_order_still_prefers_creator_and_excludes_machine_translations():
    track=lambda url:dict(ext='vtt',url='https://www.youtube.com/api/timedtext?'+url)
    info={'subtitles':{'ru':[track('lang=ru')],'en':[track('lang=en')]},'automatic_captions':{'en':[track('lang=en&kind=asr')],'fr':[track('lang=de&tlang=fr')]}}
    sources=list(captions.english_tracks(info,allow_any_language=True))
    assert [(source,language) for source,language,_ in sources]==[('creator','en'),('creator','ru'),('automatic','en')]
    assert all(language=='en' for _,language,_ in captions.english_tracks(info))


def test_compact_status_marks_reconstructed_incomplete_job_for_resume():
    storage.save_video('restored','abcdefghijk',[dict(id=1,start=1,end=3,source='Hello')],'uploaded')
    with TestClient(main.app) as client:
        state=client.get('/api/videos/restored/translated-subtitles').json()
        assert state['needs_resume'] and state['completed']==0 and not state['running']


def test_generic_site_file_bridge_has_incremental_cues_position_and_cancel(monkeypatch):
    monkeypatch.setattr(main,'retrieve_captions',lambda *args,**kwargs:pytest.fail('Generic site must not fetch any video'))
    async def stub(cues,context):return {str(c['id']):'Բարև' for c in cues}
    monkeypatch.setattr(main,'translate',stub)
    with TestClient(main.app) as client:
        created=client.post('/api/subtitle-files',files={'subtitles':('generic.srt',b'1\n00:00:01,000 --> 00:00:03,000\nHello')}).json()
        client.portal.call(finish)
        base='/api/subtitle-files/'+created['id']
        assert client.post(base+'/position',json={'seconds':2}).status_code==200
        state=client.get(base+'/translated-subtitles').json()
        assert state['cues']==[dict(id=1,start=1,end=3,text='Բարև')]
        assert client.post(base+'/cancel').status_code==200
        assert client.get(base+'/translated-subtitles').json()['phase']=='cancelled'
