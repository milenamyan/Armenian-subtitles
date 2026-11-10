import asyncio
import base64
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

from app import local_library, main, media_db as db, media_store as stores, media_worker as worker, storage
from app.media_formats import validate_probe, MediaError


@pytest.fixture(autouse=True)
def flat(tmp_path,monkeypatch,isolate_local_library):
    monkeypatch.setattr(storage,'DB',tmp_path/'data/metadata.sqlite3')
    monkeypatch.delenv('HAYSUB_DB',raising=False)
    monkeypatch.setenv('HAYSUB_PUBLIC','0')
    monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','local')
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_DIR',str(tmp_path))
    monkeypatch.setenv('HAYSUB_LIBRARY_ROOT',str(tmp_path))
    monkeypatch.setenv('HAYSUB_LOCAL_FLAT_LIBRARY','1')
    from app.media_sources import R2_BASE_URL
    monkeypatch.setenv('HAYSUB_CLOUD_BASE_URL',R2_BASE_URL)
    monkeypatch.setenv('HAYSUB_CLOUD_PATH_PREFIX','data')
    monkeypatch.setenv('HAYSUB_CLOUD_VIDEO_IDS','')
    monkeypatch.setenv('HAYSUB_LOCAL_VIDEO_FOLDER',str(tmp_path/'videos'))
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_SECRET','x'*32)
    monkeypatch.setenv('GEMINI_API_KEY','test-not-sent')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    monkeypatch.setattr(worker,'inspect_media',lambda *args:{'duration':10,'faststart':True})
    main.file_jobs.clear()
    (tmp_path/'videos').mkdir()
    return tmp_path


def movie(root,title='Film'):
    path=root/'videos'/(title+'.mp4');path.write_bytes(b'video')
    os.utime(path,(time.time()-10,time.time()-10))
    assert worker.run_once()
    return next(item for item in db.all_videos() if item['title']==title)


def test_all_cloud_selection_applies_to_playback_and_public_page(flat, monkeypatch):
    from app.media_sources import cloud_url
    item=movie(flat)
    raw='1\n00:00:01,000 --> 00:00:03,000\nԲարև'.encode('utf-8')
    with TestClient(main.app) as client:
        client.post('/api/owner/media/'+item['id']+'/subtitles',files={'subtitles':('Film.srt',raw)})
        db.update(item['id'],published=1)
        monkeypatch.setenv('HAYSUB_CLOUD_VIDEO_IDS','*')
        access=client.get('/api/public/hosted/'+item['id']+'/playback').json()
        assert access['source_type']=='cloud'
        assert access['video_url']==cloud_url(item['object_key'])
        assert access['subtitle_url']==access['cloud_subtitle_url']
        page=client.get('/watch/'+item['id']).text
        assert 'data-media-source="cloud"' in page
        assert '<source id="hosted-source" type="video/mp4" data-media-source="cloud"' in page
        saved=client.post('/api/owner/media/cloud',json={
            'title':item['title'],'video_url':access['video_url'],
            'subtitle_url':access['subtitle_url']}).json()
        assert saved['id']==item['id']
        assert len(client.get('/api/owner/media').json())==1
        assert len(client.get('/api/public/videos').json())==1


def test_hidden_video_is_removed_from_lists_without_deleting_file(flat, monkeypatch):
    item=movie(flat,'720')
    db.update(item['id'],published=1)
    monkeypatch.setenv('HAYSUB_HIDDEN_VIDEO_IDS',item['id'])
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media').json()==[]
        assert client.get('/api/public/videos').json()==[]
    assert (flat/item['object_key']).read_bytes()==b'video'
    assert db.get(item['id']) is not None


def test_import_keeps_one_file_in_place_and_never_registers_it_twice(flat):
    item=movie(flat)
    assert item['object_key']=='videos/Film.mp4' and item['state']=='ready'
    assert (flat/item['object_key']).read_bytes()==b'video'
    assert worker.run_once() is False
    assert len(db.all_videos())==1
    assert list((flat/'videos').iterdir())==[flat/'videos/Film.mp4']


def test_deleting_one_flat_movie_never_deletes_siblings_or_shared_subtitles(flat):
    item=movie(flat);other=movie(flat,'Other')
    subtitle=flat/'subtitles/Film/armenian.srt';subtitle.parent.mkdir(parents=True);subtitle.write_text('saved',encoding='utf-8')
    with TestClient(main.app) as client:
        assert client.delete('/api/owner/media/'+item['id']).status_code==200
        assert (flat/'bin/Film.mp4').exists()
        assert client.post('/api/owner/media/'+item['id']+'/purge').status_code==200
    assert worker.run_once()
    assert not (flat/item['object_key']).exists()
    assert (flat/other['object_key']).exists() and subtitle.exists()
    assert worker.run_once() is False


def test_uploaded_video_moves_out_of_staging_into_flat_folder(flat):
    backend=stores.store();identity='a'*32;key=stores.key_prefix(identity)+'source.mp4'
    backend.put(key,b'upload','video/mp4')
    db.create(dict(id=identity,title='Uploaded film',size=6,fingerprint='upload',backend=backend.identity,object_key=key,part_size=5,state='processing',created=time.time(),updated=time.time()))
    assert worker.run_once()
    saved=db.get(identity)
    assert saved['state']=='ready' and saved['object_key']=='videos/Uploaded film.mp4'
    assert (flat/saved['object_key']).read_bytes()==b'upload'
    assert not backend.path(key).exists()
    assert worker.run_once() is False


def test_subtitle_uploads_keep_only_armenian_and_exact_original_per_film(flat,monkeypatch):
    async def translate(cues,context):return {str(cue['id']):'\u0532\u0561\u0580\u0587' for cue in cues}
    monkeypatch.setattr(main,'translate',translate)
    raw=b'WEBVTT\n\n00:01.000 --> 00:03.000\nHello'
    with TestClient(main.app) as client:
        response=client.post('/api/subtitle-files',files={'subtitles':('Film.vtt',raw)})
        assert response.status_code==200
        async def finish():await asyncio.gather(*list(main.tasks))
        client.portal.call(finish)
        folder=flat/'subtitles/Film'
        assert sorted(path.name for path in folder.iterdir())==['armenian.srt','original.vtt']
        assert (folder/'original.vtt').read_bytes()==raw
        assert '\u0532\u0561\u0580\u0587' in (folder/'armenian.srt').read_text(encoding='utf-8-sig')
        assert not (flat/'data/translated-subtitles').exists()
        # Re-uploading and restoring does not add copies or change the folder.
        client.post('/api/subtitle-files',files={'subtitles':('Another name.vtt',raw)})
        assert len(list((flat/'subtitles').iterdir()))==1


def test_attached_subtitles_are_served_as_vtt_without_a_stored_vtt_duplicate(flat):
    item=movie(flat)
    raw='1\n00:00:01,000 --> 00:00:03,000\n\u0532\u0561\u0580\u0587'.encode('utf-8')
    with TestClient(main.app) as client:
        result=client.post('/api/owner/media/'+item['id']+'/subtitles',files={'subtitles':('Film.srt',raw)})
        assert result.status_code==200
        playback=client.get('/api/owner/media/'+item['id']+'/playback').json()
        track=client.get(playback['subtitle_url'])
        assert track.status_code==200 and track.content.startswith(b'WEBVTT')
        assert sorted(p.name for p in (flat/'subtitles/Film').iterdir())==['armenian.srt','original.srt']
        assert not list(flat.rglob('*.vtt'))


def test_original_movie_can_keep_all_compatible_audio_tracks_without_a_second_copy(flat):
    probe={'format':{'duration':'60'},'streams':[{'codec_type':'video','codec_name':'h264','profile':'Main','level':40,'pix_fmt':'yuv420p'},{'codec_type':'audio','codec_name':'aac','profile':'LC','channels':2},{'codec_type':'audio','codec_name':'aac','profile':'LC','channels':2}]}
    assert validate_probe(probe,{'faststart':True})['audio']=='aac-lc'
    probe['streams'][2]['codec_name']='ac3'
    with pytest.raises(MediaError,match='AAC-LC'):validate_probe(probe,{'faststart':True})


def test_removing_a_subtitle_entry_does_not_create_another_export_in_the_bin(flat):
    raw='1\n00:00:01,000 --> 00:00:03,000\n\u0532\u0561\u0580\u0587'.encode('utf-8')
    with TestClient(main.app) as client:
        result=client.post('/api/subtitle-files',files={'subtitles':('Film.srt',raw)})
        assert result.status_code==200 and result.json()['ready']
        identity=result.json()['id']
        assert client.delete('/api/library/'+identity).status_code==200
        assert client.get('/api/library').json()==[]
        assert sorted(path.name for path in (flat/'subtitles/Film').iterdir())==['armenian.srt','original.srt']
        assert not list((flat/'data').rglob('*.srt'))


def test_existing_translation_attaches_to_the_selected_video_without_extra_files(flat,monkeypatch):
    item=movie(flat)
    async def translate(cues,context):return {str(cue['id']):'\u0532\u0561\u0580\u0587' for cue in cues}
    monkeypatch.setattr(main,'translate',translate)
    raw=b'1\n00:00:01,000 --> 00:00:03,000\nHello'
    with TestClient(main.app) as client:
        uploaded=client.post('/api/subtitle-files',files={'subtitles':('Film.srt',raw)}).json()
        async def finish():await asyncio.gather(*list(main.tasks))
        client.portal.call(finish)
        assert not client.get('/api/owner/media/'+item['id']).json()['has_subtitles']
        before={str(p) for p in flat.rglob('*') if p.is_file() and p.suffix in ('.srt','.vtt')}
        attached=client.post('/api/owner/media/'+item['id']+'/subtitles',data={'library_id':uploaded['id'],'offset':'0'})
        assert attached.status_code==200
        assert attached.json()['has_subtitles'] and attached.json()['state']=='ready'
        playback=client.get('/api/owner/media/'+item['id']+'/playback').json()
        track=client.get(playback['subtitle_url'])
        assert track.status_code==200 and '\u0532\u0561\u0580\u0587' in track.text
        assert 'Hello' not in track.text
        assert {str(p) for p in flat.rglob('*') if p.is_file() and p.suffix in ('.srt','.vtt')}==before
        assert db.get(item['id'])['subtitle_key']=='subtitles/Film/armenian.srt'
        assert client.get('/api/owner/media/'+item['id']).json()['has_subtitles']


def test_web_delete_moves_to_bin_and_manual_move_restores_same_video_and_subtitles(flat):
    item=movie(flat)
    db.update(item['id'],subtitle_key='subtitles/Film/armenian.srt',subtitle_cues='[]',published=1)
    with TestClient(main.app) as client:
        result=client.delete('/api/owner/media/'+item['id'])
        assert result.status_code==200 and result.json()['purge_after'] is None
        stored=db.get(item['id'])
        assert stored['state']=='bin' and not stored['published']
        assert (flat/'bin/Film.mp4').read_bytes()==b'video'
        assert not (flat/'videos/Film.mp4').exists()
        assert client.get('/api/owner/media').status_code==200
        assert client.get('/api/owner/media/'+item['id']+'/playback').status_code==409
        # The bin is controlled by the owner; waiting does not purge the file.
        with db.connect() as connection:connection.execute('UPDATE hosted_videos SET binned_at=? WHERE id=?',(time.time()-3*86400,item['id']))
        assert worker.run_once() is False
        assert (flat/'bin/Film.mp4').exists()
        (flat/'bin/Film.mp4').rename(flat/'videos/Film.mp4')
        assert worker.run_once() is False
        restored=db.get(item['id'])
        assert restored['state']=='ready' and restored['subtitle_key']=='subtitles/Film/armenian.srt'
        assert restored['bin_object_key'] is None and not restored['published']
        assert len(db.all_videos())==1 and worker.run_once() is False
        assert client.get('/api/owner/media/'+item['id']).json()['has_subtitles']


def test_existing_deleted_video_is_moved_into_physical_bin(flat):
    item=movie(flat);db.bin_video(item['id'])
    assert worker.run_once() is False
    assert (flat/'bin/Film.mp4').exists() and not (flat/'videos/Film.mp4').exists()
    assert db.get(item['id'])['purge_after'] is None


def test_copying_back_is_not_a_move_and_does_not_duplicate_video_records(flat):
    item=movie(flat)
    with TestClient(main.app) as client:assert client.delete('/api/owner/media/'+item['id']).status_code==200
    (flat/'videos/Film.mp4').write_bytes((flat/'bin/Film.mp4').read_bytes())
    assert worker.run_once() is False
    assert db.get(item['id'])['state']=='bin' and len(db.all_videos())==1


def test_bin_filename_collision_preserves_both_files_and_restores_the_same_identity(flat):
    item=movie(flat);(flat/'bin').mkdir(exist_ok=True);(flat/'bin/Film.mp4').write_bytes(b'older movie')
    with TestClient(main.app) as client:assert client.delete('/api/owner/media/'+item['id']).status_code==200
    stored=db.get(item['id']);binned=stores.store().path(stored['bin_object_key'])
    assert binned.name!='Film.mp4' and (flat/'bin/Film.mp4').read_bytes()==b'older movie'
    binned.rename(flat/'videos'/binned.name)
    assert worker.run_once() is False
    assert db.get(item['id'])['state']=='ready' and len(db.all_videos())==1


def test_failed_move_leaves_the_video_on_the_page_and_in_its_folder(flat,monkeypatch):
    item=movie(flat)
    def locked(*args):raise PermissionError('File is open')
    monkeypatch.setattr(type(flat),'rename',locked)
    with TestClient(main.app) as client:assert client.delete('/api/owner/media/'+item['id']).status_code==409
    assert db.get(item['id'])['state']=='ready' and (flat/'videos/Film.mp4').exists()


def test_player_html_pairs_local_tags_with_inactive_exact_cloud_paths(flat):
    from html.parser import HTMLParser
    from urllib.parse import unquote
    from app.media_sources import R2_BASE_URL
    class Tags(HTMLParser):
        def __init__(self):super().__init__();self.tags=[];self.comments=[]
        def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))
        def handle_comment(self,text):self.comments.append(text.strip())
    title='Film & Friends-- \u0540\u0561\u0575\u0565\u0580\u0565\u0576'
    item=movie(flat,title)
    raw='1\n00:00:01,000 --> 00:00:03,000\n\u0532\u0561\u0580\u0587'.encode('utf-8')
    with TestClient(main.app) as client:
        assert client.post('/api/owner/media/'+item['id']+'/subtitles',files={'subtitles':('Film.srt',raw)}).status_code==200
        access=client.get('/api/owner/media/'+item['id']+'/playback').json()
        assert unquote(access['cloud_video_url'])==R2_BASE_URL+'/data/videos/'+title+'.mp4'
        assert unquote(access['cloud_subtitle_url'])==R2_BASE_URL+'/data/subtitles/'+title+'/armenian.srt'
        body=client.get('/preview/'+item['id']).text
        parsed=Tags();parsed.feed(body)
        original=Tags();original.feed((main.ROOT/'static/watch.html').read_text(encoding='utf-8'))
        assert next(attrs for tag,attrs in parsed.tags if tag=='video')==next(attrs for tag,attrs in original.tags if tag=='video')
        for tag,id,local_key,cloud_key in [('source','hosted-source','video_url','cloud_video_url'),('track','armenian-track','subtitle_url','cloud_subtitle_url')]:
            active=[attrs for kind,attrs in parsed.tags if kind==tag]
            assert len(active)==1
            if tag=='source':
                assert client.get(active[0]['src']).content==b'video'
            else:
                assert active[0]['src']==access[local_key]
            original_attrs=next(attrs for kind,attrs in original.tags if kind==tag)
            for key,value in original_attrs.items():assert active[0][key]==value
            assert active[0]['data-media-source']=='local'
            comment=next(text for text in parsed.comments if text.startswith('<'+tag+' '))
            assert '--' not in comment
            alternative=Tags();alternative.feed(comment);cloud=alternative.tags[0][1]
            assert cloud['src']==access[cloud_key] and cloud['data-media-source']=='cloud'
            for key,value in active[0].items():
                if key not in ('src','data-media-source'):assert cloud[key]==value
            assert body.index('<!-- '+comment+' -->')>body.index('id="'+id+'"')
        # Private media paths are never embedded into the public watch page.
        assert R2_BASE_URL not in client.get('/watch/'+item['id']).text
        db.update(item['id'],published=1)
        assert R2_BASE_URL in client.get('/watch/'+item['id']).text


def test_home_url_player_has_both_inputs_and_existing_native_controls(flat):
    with TestClient(main.app) as client:
        assert client.get('/player').status_code==404
        page=client.get('/')
        assert page.status_code==200
        for field in ['watch-url-form','watch-video-url','watch-subtitle-url','watch-url-load','hosted-player','hosted-source','armenian-track']:
            assert 'id="'+field+'"' in page.text
        assert 'Load &amp; Play' in page.text
        assert 'controls playsinline preload="metadata" crossorigin="anonymous"' in page.text
        assert 'kind="subtitles" srclang="hy"' in page.text
        homepage=client.get('/').text
        assert 'id="cloud-url-player"' in homepage
        assert 'id="watch-video-url"' in homepage and 'id="watch-subtitle-url"' in homepage
        assert 'data-url-player="true"' in homepage
