import hashlib
import json
import struct
import time
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient

from app import main, storage, public, media_api, media_db as db, media_store as stores, media_worker as worker
from app.media_formats import prepared_cues, webvtt, mp4_layout, validate_probe, MediaError

# Original synthetic container fixture, NOT a playable video. ffprobe integration
# is mocked here; codec/container checks have separate focused tests below.
def box(kind,raw):return struct.pack('>I4s',len(raw)+8,kind)+raw
RAW=box(b'ftyp',b'isom\0\0\0\0isommp42')+box(b'moov',b'')+box(b'mdat',b'HaySub original test fixture')
SUB='1\n00:00:01,250 --> 00:00:04,500\nԲարև\nաշխարհ\n\n2\n00:00:02,000 --> 00:00:05,000\nՑտեսություն\n'
INFO={'duration':6,'video':'h264','audio':'aac-lc','width':640,'height':360,'faststart':True}


@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'metadata.sqlite3')
    monkeypatch.setenv('HAYSUB_PUBLIC','0')
    monkeypatch.delenv('HAYSUB_DB',raising=False)
    monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','local')
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_SECRET','original-test-secret-with-at-least-32-characters')
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_DIR',str(tmp_path/'media'))
    monkeypatch.setenv('HAYSUB_LOCAL_VIDEO_FOLDER',str(tmp_path/'inbox'))
    monkeypatch.setattr(worker,'inspect_media',lambda *args:dict(INFO))
    public.attempts.clear()


def new(client,size=None):
    response=client.post('/api/owner/media',json={'title':'Իմ ֆիլմը','size':size or len(RAW),'fingerprint':hashlib.sha256(RAW).hexdigest()})
    assert response.status_code==200,response.text
    return response.json()


def put(client,item,raw=RAW,ack=True):
    signed=client.post(f"/api/owner/media/{item['id']}/part-url",json={'number':1})
    assert signed.status_code==200
    uploaded=client.put(signed.json()['url'],content=raw)
    assert uploaded.status_code==200,uploaded.text
    if ack:assert client.post(f"/api/owner/media/{item['id']}/ack",json={'number':1,'etag':uploaded.headers['etag']}).status_code==200
    return uploaded


def attach(client,identity,offset=0):
    response=client.post('/api/owner/media/'+identity+'/subtitles',files={'subtitles':('mine.srt',SUB.encode())},data={'offset':str(offset)})
    assert response.status_code==200,response.text
    return response


def ready(client):
    item=new(client);put(client,item);attach(client,item['id'])
    assert client.post('/api/owner/media/'+item['id']+'/complete').status_code==200
    assert worker.run_once()
    assert db.get(item['id'])['state']=='ready'
    return item['id']


def expire_bin(identity):
    with db.connect() as connection:
        connection.execute('UPDATE hosted_videos SET purge_after=? WHERE id=?',(time.time()-1,identity))


def test_local_resumable_upload_completion_range_preview_publish_and_delete():
    with TestClient(main.app) as client:
        item=new(client);identity=item['id'];uploaded=put(client,item)
        resumed=client.get('/api/owner/media/'+identity+'/resume').json()
        assert resumed['parts']==[{'number':1,'etag':uploaded.headers['etag']}]
        assert resumed['uploaded_bytes']==len(RAW)
        assert client.post('/api/owner/media/'+identity+'/complete').json()['state']=='finalizing'
        # The object is finalized outside the request handler, by the worker.
        assert stores.store().head(db.get(identity)['object_key']) is None
        assert worker.run_once();assert db.get(identity)['state']=='ready'
        assert client.patch('/api/owner/media/'+identity,json={'published':True}).status_code==409
        attach(client,identity)
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        access=client.get('/api/owner/media/'+identity+'/playback').json()
        assert client.get(access['video_url'],headers={'Range':'bytes=4-11'}).status_code==206
        assert client.get(access['video_url'],headers={'Range':'bytes=4-11'}).content==RAW[4:12]
        track=client.get(access['subtitle_url'])
        assert track.status_code==200 and track.headers['content-type'].startswith('text/vtt')
        assert track.content.startswith(b'WEBVTT') and 'Բարև\nաշխարհ' in track.text
        assert client.patch('/api/owner/media/'+identity,json={'published':True}).status_code==200
        assert client.get('/api/public/hosted/'+identity+'/playback').json()['visibility']=='unlisted'
        assert client.patch('/api/owner/media/'+identity,json={'published':False}).status_code==200
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        # Previously issued storage access remains valid until expiry or deletion.
        assert client.get(access['video_url']).status_code==200
        assert client.delete('/api/owner/media/'+identity).status_code==200
        assert db.get(identity)['state']=='bin'
        assert worker.run_once() is False
        assert client.get(access['video_url']).status_code==200
        expire_bin(identity)
        assert worker.run_once();assert db.get(identity) is None
        assert client.get(access['video_url']).status_code==404
        assert not list(stores.store().root.rglob('*.vtt'))


def test_missing_or_incorrect_part_receipts_cannot_complete():
    with TestClient(main.app) as client:
        item=new(client);identity=item['id'];put(client,item,ack=False)
        assert client.post('/api/owner/media/'+identity+'/complete').status_code==409
        assert client.get('/api/owner/media/'+identity+'/resume').json()['parts']==[]
        client.post('/api/owner/media/'+identity+'/ack',json={'number':1,'etag':'"incorrect"'})
        assert client.post('/api/owner/media/'+identity+'/complete').status_code==409
        put(client,item)
        assert client.post('/api/owner/media/'+identity+'/complete').status_code==200
        assert client.post('/api/owner/media/'+identity+'/complete').status_code==200


def test_declared_size_and_part_bounds_are_enforced_without_whole_file_buffering():
    with TestClient(main.app) as client:
        item=new(client)
        assert client.post('/api/owner/media/'+item['id']+'/part-url',json={'number':2}).status_code==400
        url=client.post('/api/owner/media/'+item['id']+'/part-url',json={'number':1}).json()['url']
        assert client.put(url,content=RAW+b'extra').status_code==413
        assert client.put(url,content=RAW[:-1]).status_code==400
        assert client.post('/api/owner/media/'+item['id']+'/complete').status_code==409
        huge=new(client,10*1024**3)
        assert huge['part_count']==160 and huge['part_size']==64*1024**2
        assert 'data' not in client.post('/api/owner/media/'+huge['id']+'/part-url',json={'number':160}).json()
        too_big=client.post('/api/owner/media',json={'title':'Too large','size':13*1024**3,'fingerprint':'a'*64})
        assert too_big.status_code==413


def test_control_endpoints_reject_video_sized_request_bodies_before_form_parsing():
    with TestClient(main.app) as client:
        item=new(client)
        assert client.post('/api/owner/media',content=b'x',headers={'Content-Length':str(10*1024**3)}).status_code==413
        assert client.post('/api/owner/media',content=iter([b'x'*32768,b'y'*32769])).status_code==413
        path='/api/owner/media/'+item['id']+'/subtitles'
        assert client.post(path,content=b'x',headers={'Content-Length':str(10*1024**3)}).status_code==413
        assert client.post(path,content=b'x'*(2*1024*1024+65537)).status_code==413


def test_local_link_signature_expiry_and_private_path_traversal():
    with TestClient(main.app) as client:
        identity=ready(client);backend=stores.store();item=db.get(identity)
        expired=backend.get_url(item['object_key'],-1,'video/mp4')
        assert client.get(expired).status_code==403
        access=client.get('/api/owner/media/'+identity+'/playback').json()
        assert client.get(access['video_url'].replace('source.mp4','elsewhere.mp4')).status_code==403
        with pytest.raises(stores.StorageError):backend.path('../../outside')


def test_bin_preview_without_subtitles_and_explicit_permanent_cleanup():
    with TestClient(main.app) as client:
        identity=ready(client)
        db.update(identity,subtitle_key=None)
        client.delete('/api/owner/media/'+identity)
        listed=client.get('/api/owner/media').json()
        assert next(item for item in listed if item['id']==identity)['can_preview']
        access=client.get('/api/owner/media/'+identity+'/playback')
        assert access.status_code==200
        assert access.json()['subtitle_url'] is None
        assert client.get(access.json()['video_url']).content==RAW
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        assert client.post('/api/owner/media/'+identity+'/purge').status_code==200
        assert client.post('/api/owner/media/'+identity+'/restore').status_code==409
        assert client.get('/api/owner/media/'+identity+'/playback').status_code==409
        assert worker.run_once()
        assert db.get(identity) is None
        assert client.get(access.json()['video_url']).status_code==404


def test_permanent_cleanup_requires_bin():
    with TestClient(main.app) as client:
        identity=ready(client)
        assert client.post('/api/owner/media/'+identity+'/purge').status_code==409
        assert db.get(identity)['state']=='ready'


def test_bin_retains_for_24_hours_and_restores_privately_without_extending_deadline():
    with TestClient(main.app) as client:
        identity=ready(client);client.patch('/api/owner/media/'+identity,json={'published':True})
        before=time.time();removed=client.delete('/api/owner/media/'+identity).json()
        assert before+86400<=removed['purge_after']<=time.time()+86400
        assert client.delete('/api/owner/media/'+identity).json()['purge_after']==removed['purge_after']
        assert db.get(identity)['published']==0
        assert worker.run_once() is False
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        assert client.post('/api/owner/media/'+identity+'/subtitles',data={'offset':'1'}).status_code==409
        restored=client.post('/api/owner/media/'+identity+'/restore')
        assert restored.status_code==200 and restored.json()['state']=='ready'
        assert restored.json()['published']==0 and restored.json()['purge_after'] is None
        assert client.get('/api/owner/media/'+identity+'/playback').status_code==200
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404


def test_bin_deadline_survives_restart_and_expired_video_cannot_be_restored():
    with TestClient(main.app) as client:
        identity=ready(client);deadline=client.delete('/api/owner/media/'+identity).json()['purge_after']
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media/'+identity).json()['purge_after']==deadline
        assert worker.run_once() is False
        expire_bin(identity)
        assert client.post('/api/owner/media/'+identity+'/restore').status_code==409
        assert worker.run_once()
        assert client.get('/api/owner/media/'+identity).status_code==404
        assert not list(stores.store().root.rglob('*.vtt'))


def test_binned_partial_upload_can_resume_after_restore():
    with TestClient(main.app) as client:
        item=new(client);put(client,item)
        client.delete('/api/owner/media/'+item['id'])
        assert worker.run_once() is False
        assert client.post('/api/owner/media/'+item['id']+'/part-url',json={'number':1}).status_code==409
        assert client.post('/api/owner/media/'+item['id']+'/restore').json()['state']=='uploading'
        assert len(client.get('/api/owner/media/'+item['id']+'/resume').json()['parts'])==1


def test_idle_multipart_uploads_are_aborted_and_deleted():
    with TestClient(main.app) as client:
        item=new(client);put(client,item)
        folder=stores.store().root/'_uploads'/db.get(item['id'])['upload_id']
        with db.connect() as connection:connection.execute('UPDATE hosted_videos SET updated=? WHERE id=?',(time.time()-49*3600,item['id']))
        assert worker.run_once();assert not folder.exists();assert db.get(item['id']) is None


def test_worker_errors_are_private_and_retryable(monkeypatch):
    def fail(*args):raise MediaError('Unsupported codec. Use H.264/AAC MP4.')
    monkeypatch.setattr(worker,'inspect_media',fail)
    with TestClient(main.app) as client:
        item=new(client);put(client,item);client.post('/api/owner/media/'+item['id']+'/complete')
        assert worker.run_once();assert db.get(item['id'])['state']=='error'
        assert client.patch('/api/owner/media/'+item['id'],json={'published':True}).status_code==409
        monkeypatch.setattr(worker,'inspect_media',lambda *args:dict(INFO))
        assert client.post('/api/owner/media/'+item['id']+'/retry').status_code==200
        assert worker.run_once();assert db.get(item['id'])['state']=='ready'


def test_owner_authentication_csrf_and_anonymous_public_access(monkeypatch):
    # A fake private remote store avoids any network, credentials or public upload.
    backend=stores.store()
    monkeypatch.setattr(stores,'store',lambda:backend)
    monkeypatch.setenv('HAYSUB_PUBLIC','1');monkeypatch.setenv('HAYSUB_PUBLIC_URL','https://haysub.test')
    monkeypatch.setenv('HAYSUB_ADMIN_TOKEN','owner-password-with-at-least-thirty-two-characters')
    origin={'Origin':'https://haysub.test'}
    with TestClient(main.app,base_url='https://haysub.test') as client:
        for path in ('/api/owner/media','/api/owner/media/config','/api/owner/media/'+'a'*32+'/playback'):
            assert client.get(path).status_code==401
        assert client.post('/api/owner/media').status_code==401
        for suffix in ('part-url','ack','complete','subtitles','retry','restore'):
            assert client.post('/api/owner/media/'+'a'*32+'/'+suffix).status_code==401
        assert client.delete('/api/owner/media/'+'a'*32).status_code==401
        assert client.patch('/api/owner/media/'+'a'*32).status_code==401
        assert client.get('/api/public/hosted/'+'a'*32+'/playback').status_code==404
        client.post('/api/admin/login',json={'token':'owner-password-with-at-least-thirty-two-characters'},headers=origin)
        assert client.get('/api/owner/media').status_code==200
        assert client.post('/api/owner/media',json={'title':'Film','size':10,'fingerprint':'a'*64}).status_code==403
        created=client.post('/api/owner/media',json={'title':'Film','size':10,'fingerprint':'a'*64},headers=origin)
        assert created.status_code==200
        identity=created.json()['id']
        db.update(identity,state='ready',subtitle_key=stores.key_prefix(identity)+'subtitles/fixture.vtt',duration=6)
        assert client.patch('/api/owner/media/'+identity,json={'published':True},headers=origin).status_code==200
        client.cookies.clear()
        assert client.get('/api/owner/media/'+identity+'/playback').status_code==401
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==200
        db.update(identity,published=0)
        assert client.get('/api/public/hosted/'+identity+'/playback').status_code==404
        assert client.get('/dev-media').status_code==404


def test_subtitle_snapshot_and_offset_do_not_change_shared_library_or_other_videos():
    with TestClient(main.app) as client:
        imported=client.post('/api/library/import',files={'subtitles':('Armenian.srt',SUB.encode())}).json()['id']
        first=new(client)['id'];second=new(client,size=len(RAW)+1)['id']
        assert first != second  # Identical uploads intentionally reuse one record.
        for identity in (first,second):assert client.post('/api/owner/media/'+identity+'/subtitles',data={'library_id':imported}).status_code==200
        before=storage.library_item(imported)['srt'];second_track=db.get(second)['subtitle_key']
        assert client.post('/api/owner/media/'+first+'/subtitles',data={'offset':'2'}).status_code==200
        track=stores.store().path(db.get(first)['subtitle_key']).read_text(encoding='utf-8')
        # The existing library exporter has already normalized its source timing.
        # Video attachment preserves that stored snapshot and applies only +2s.
        assert '00:00:03.250 --> 00:00:04.000' in track
        assert db.get(second)['subtitle_key']==second_track
        assert storage.library_item(imported)['srt']==before
        assert client.post('/api/owner/media/'+first+'/subtitles',data={'offset':'-600'}).status_code==400
        assert client.post('/api/owner/media/'+first+'/subtitles',files={'subtitles':('wrong.srt',SUB.replace('Բարև','Hello').replace('աշխարհ','world').replace('Ցտեսություն','Bye').encode())}).status_code==400


def test_webvtt_preserves_multiline_overlaps_escapes_markup_and_clamps_negative_offset():
    cues=prepared_cues(SUB.encode());cues[0]['source']+=' <script>alert(1)</script> & text'
    text=webvtt(cues).decode()
    assert text.startswith('WEBVTT\n\n')
    assert '00:00:01.250 --> 00:00:04.500' in text and '00:00:02.000 --> 00:00:05.000' in text
    assert '<script>' not in text and '&lt;script&gt;' in text and '&amp; text' in text
    assert '00:00:00.000 --> 00:00:02.500' in webvtt(cues,-2).decode()


def test_missing_storage_and_local_public_mode_fail_with_setup_message(monkeypatch):
    monkeypatch.delenv('HAYSUB_MEDIA_STORAGE')
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media/config').json()['configured'] is False
        assert client.post('/api/owner/media',json={'title':'Film','size':100,'fingerprint':'a'*64}).status_code==503
    monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','local');monkeypatch.setenv('HAYSUB_PUBLIC','1')
    with pytest.raises(stores.StorageError,match='development-only'):stores.store()


def test_mp4_container_and_supported_codec_validation():
    class Bytes:
        def read_range(self,key,start,count):return RAW[start:start+count]
    assert mp4_layout(Bytes(),'source.mp4',len(RAW))['faststart']
    info={'format':{'duration':'6'},'streams':[{'codec_type':'video','codec_name':'h264','profile':'High','level':40,'pix_fmt':'yuv420p'},{'codec_type':'audio','codec_name':'aac','profile':'LC','channels':2}]}
    assert validate_probe(info,{'faststart':True})['duration']==6
    info['streams'][0]['codec_name']='hevc'
    with pytest.raises(MediaError,match='H.264'):validate_probe(info,{})
    info['streams'][0]['codec_name']='h264';info['streams'][1]['codec_name']='dts'
    with pytest.raises(MediaError,match='AAC'):validate_probe(info,{})


def test_cleanup_failure_is_retried_without_losing_metadata(monkeypatch):
    with TestClient(main.app) as client:
        identity=ready(client);backend=stores.store();original=backend.delete_prefix
        monkeypatch.setattr(stores,'store',lambda:backend)
        monkeypatch.setattr(backend,'delete_prefix',lambda prefix:(_ for _ in ()).throw(stores.StorageError('Cleanup permissions missing.')))
        client.delete('/api/owner/media/'+identity);expire_bin(identity);assert worker.run_once()
        assert db.get(identity)['state']=='deleting' and db.get(identity)['error']
        monkeypatch.setattr(backend,'delete_prefix',original)
        client.post('/api/owner/media/'+identity+'/retry');assert worker.run_once();assert db.get(identity) is None


def test_worker_recovers_finalization_after_object_was_committed_before_restart():
    with TestClient(main.app) as client:
        item=new(client);put(client,item);client.post('/api/owner/media/'+item['id']+'/complete')
        saved=db.get(item['id']);backend=stores.store()
        backend.complete(saved['object_key'],saved['upload_id'],db.parts(item['id']))
        assert worker.run_once();assert db.get(item['id'])['state']=='ready'


def test_delete_waits_for_inflight_subtitle_write_then_removes_every_generated_file(monkeypatch):
    with TestClient(main.app) as client:
        identity=ready(client);backend=stores.store();original=backend.put
        monkeypatch.setattr(stores,'store',lambda:backend)
        def write_and_delete(key,data,mime):
            db.update(identity,state='deleting',published=0)
            assert worker.run_once() is False,'Cleanup must not run while a subtitle object is still being written'
            original(key,data,mime)
        monkeypatch.setattr(backend,'put',write_and_delete)
        response=client.post('/api/owner/media/'+identity+'/subtitles',files={'subtitles':('mine.srt',SUB.encode())})
        assert response.status_code==409
        assert worker.run_once();assert db.get(identity) is None
        assert not list(backend.root.rglob('*.vtt'))


def test_delete_during_inspection_cannot_republish_a_video(monkeypatch):
    with TestClient(main.app) as client:
        item=new(client);put(client,item);client.post('/api/owner/media/'+item['id']+'/complete')
        def inspect(*args):db.update(item['id'],state='deleting',published=0);return dict(INFO)
        monkeypatch.setattr(worker,'inspect_media',inspect)
        assert worker.run_once();assert db.get(item['id'])['state']=='deleting'
        assert worker.run_once();assert db.get(item['id']) is None
