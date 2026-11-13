import pytest
from fastapi.testclient import TestClient
from app import main, storage, media_db as db, media_store as stores

VIDEO='https://cdn.example/Film%20one.mp4?token=abc&quality=hd'
SUBTITLES='https://cdn.example/armenian.srt?signature=example'
ORIGIN='https://haysub.example'
TOKEN='test-cloud-links-owner-token-at-least-32-characters'


@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'metadata.sqlite3')
    monkeypatch.delenv('HAYSUB_DB',raising=False)
    monkeypatch.setenv('HAYSUB_PUBLIC','0')
    monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','')
    monkeypatch.setattr(stores,'store',lambda:pytest.fail('Saving and playing cloud links must not touch managed storage'))
    main.file_jobs.clear()
    return tmp_path


def add(client,title='My film',subtitle=SUBTITLES,headers=None):
    response=client.post('/api/owner/media/cloud',json={'title':title,'video_url':VIDEO,'subtitle_url':subtitle},headers=headers or {})
    assert response.status_code==200,response.text
    return response.json()


def test_links_persist_and_public_title_opens_the_saved_video_without_copying_files(isolated):
    with TestClient(main.app) as client:
        item=add(client)
        assert item['source_type']=='cloud' and item['published'] and item['has_subtitles']
        assert item['state']=='ready'
        listed=client.get('/api/public/videos').json()
        assert listed==[{'id':item['id'],'title':'My film','watch_url':'/watch/'+item['id'],'has_subtitles':True,'duration':None,'poster_url':None,'published_at':listed[0]['published_at']}]
        access=client.get('/api/public/hosted/'+item['id']+'/playback').json()
        assert access['video_url']==VIDEO and access['subtitle_url']==SUBTITLES
        assert access['source_type']=='cloud'
        page=client.get(listed[0]['watch_url']).text
        assert 'data-media-source="cloud"' in page and 'quality=hd' in page
        assert not list(isolated.rglob('*.mp4')) and not list(isolated.rglob('*.srt'))
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media/'+item['id']).json()['title']=='My film'
        assert client.get('/api/public/hosted/'+item['id']+'/playback').json()['subtitle_url']==SUBTITLES


def test_cloud_selected_video_stays_listed_without_local_file(isolated,monkeypatch):
    import time
    identity='b'*32
    backend=type('Backend',(),{'identity':'local','path':lambda self,key:isolated/key})()
    monkeypatch.setattr(stores,'store',lambda:backend)
    monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','local')
    db.create(dict(id=identity,title='Cloud movie',size=1,fingerprint='fixture',backend='local',
                   object_key='videos/missing.mp4',part_size=1,state='ready',created=time.time(),updated=time.time()))
    db.update(identity,published=1)
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media').json()==[]
        monkeypatch.setenv('HAYSUB_CLOUD_VIDEO_IDS',identity)
        for endpoint in ('/api/owner/media','/api/public/videos'):
            assert [item['id'] for item in client.get(endpoint).json()]==[identity]
        monkeypatch.setenv('HAYSUB_HIDDEN_VIDEO_IDS',identity)
        assert client.get('/api/owner/media').json()==[]


def test_saving_the_same_video_updates_its_title_and_links_without_duplicate_entries():
    with TestClient(main.app) as client:
        before=add(client)
        after=add(client,title='Renamed movie',subtitle='https://cdn.example/new.vtt')
        assert before['id']==after['id'] and len(client.get('/api/owner/media').json())==1
        assert client.get('/api/public/videos').json()[0]['title']=='Renamed movie'
        assert client.get('/api/public/hosted/'+after['id']+'/playback').json()['subtitle_url']=='https://cdn.example/new.vtt'


def test_cloud_duration_is_saved_for_first_time_visitors_and_retained_on_rename():
    with TestClient(main.app) as client:
        response=client.post('/api/owner/media/cloud',json={'title':'Film','video_url':VIDEO,'duration':6278.375})
        assert response.status_code==200
        identity=response.json()['id']
        assert client.get('/api/public/videos').json()[0]['duration']==6278.375
        assert client.get('/api/public/hosted/'+identity+'/playback').json()['duration']==6278.375
        add(client,title='Renamed')
        assert db.get(identity)['duration']==6278.375
        for invalid in (0,-1,86401,'NaN','Infinity'):
            assert client.post('/api/owner/media/cloud',json={'title':'Film','video_url':VIDEO,'duration':invalid}).status_code==422


def test_add_to_page_restores_a_hidden_managed_cloud_video_without_duplicates(monkeypatch):
    from app import media_sources
    import time
    identity='a'*32
    db.create(dict(id=identity,title='720',size=0,fingerprint='fixture',backend='local',
                   object_key='videos/720.mp4',part_size=1,state='ready',created=time.time(),updated=time.time()))
    monkeypatch.setenv('HAYSUB_CLOUD_VIDEO_IDS','*')
    monkeypatch.setenv('HAYSUB_HIDDEN_VIDEO_IDS',identity)
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media').json()==[]
        response=client.post('/api/owner/media/cloud',json={
            'title':'720','video_url':media_sources.cloud_url('videos/720.mp4'),'subtitle_url':SUBTITLES})
        assert response.status_code==200
        assert response.json()['id']==identity
        assert response.json()['has_subtitles'] is True
        assert db.get(identity)['external_subtitle_url']==SUBTITLES
        backend=type('Backend',(),{'identity':'local','get_url':lambda self,*args:'/managed-video'})()
        monkeypatch.setattr(stores,'store',lambda:backend)
        monkeypatch.setattr(stores,'playback_ttl',lambda:14400)
        monkeypatch.setattr('app.local_library.enabled',lambda backend:False)
        for endpoint in ('/api/owner/media/','/api/public/hosted/'):
            playback=client.get(endpoint+identity+'/playback')
            assert playback.status_code==200
            assert playback.json()['subtitle_url']==SUBTITLES
            assert playback.json()['cloud_subtitle_url']==SUBTITLES
        for _ in range(2):
            assert [item['id'] for item in client.get('/api/owner/media').json()]==[identity]
        assert len(db.all_videos())==1
    with TestClient(main.app) as client:
        assert [item['id'] for item in client.get('/api/owner/media').json()]==[identity]


@pytest.mark.parametrize('url',['javascript:alert(1)','file:///C:/movie.mp4','https://user:password@cdn.example/video.mp4','not a url'])
def test_invalid_cloud_urls_are_rejected(url):
    with TestClient(main.app) as client:
        assert client.post('/api/owner/media/cloud',json={'title':'Bad link','video_url':url}).status_code==400
        assert client.get('/api/public/videos').json()==[]


def test_cloud_video_without_subtitles_can_play_and_unpublish():
    with TestClient(main.app) as client:
        item=add(client,subtitle=None)
        assert not item['has_subtitles']
        assert client.get('/api/public/hosted/'+item['id']+'/playback').json()['subtitle_url'] is None
        assert client.patch('/api/owner/media/'+item['id'],json={'published':False}).status_code==200
        assert client.get('/api/public/videos').json()==[]
        assert client.get('/api/public/hosted/'+item['id']+'/playback').status_code==404
        assert VIDEO not in client.get('/watch/'+item['id']).text
        assert client.patch('/api/owner/media/'+item['id'],json={'published':True}).status_code==200


def test_deleting_a_cloud_entry_removes_only_its_metadata(isolated):
    untouched=isolated/'original.mp4';untouched.write_bytes(b'original movie')
    with TestClient(main.app) as client:
        item=add(client)
        assert client.delete('/api/owner/media/'+item['id']).status_code==200
        assert db.get(item['id']) is None and client.get('/api/public/videos').json()==[]
        assert untouched.read_bytes()==b'original movie'


def test_existing_library_subtitles_can_be_attached_to_a_saved_cloud_video():
    raw='1\n00:00:01,000 --> 00:00:03,000\n\u0532\u0561\u0580\u0587'.encode('utf-8')
    with TestClient(main.app) as client:
        item=add(client,subtitle=None)
        library=client.post('/api/library/import',files={'subtitles':('film.srt',raw)}).json()
        attached=client.post('/api/owner/media/'+item['id']+'/subtitles',data={'library_id':library['id']})
        assert attached.status_code==200 and attached.json()['has_subtitles']
        access=client.get('/api/public/hosted/'+item['id']+'/playback').json()
        captions=client.get(access['subtitle_url'])
        assert captions.status_code==200 and '\u0532\u0561\u0580\u0587' in captions.text and captions.content.startswith(b'WEBVTT')


def test_only_the_owner_can_add_links_but_visitors_can_click_published_titles(monkeypatch):
    monkeypatch.setenv('HAYSUB_PUBLIC','1');monkeypatch.setenv('HAYSUB_PUBLIC_URL',ORIGIN);monkeypatch.setenv('HAYSUB_ADMIN_TOKEN',TOKEN)
    with TestClient(main.app,base_url=ORIGIN) as client:
        assert client.post('/api/owner/media/cloud',json={'title':'No','video_url':VIDEO}).status_code==401
        assert client.get('/api/public/videos').status_code==200
        assert client.post('/api/admin/login',json={'token':TOKEN},headers={'Origin':ORIGIN}).status_code==200
        item=add(client,headers={'Origin':ORIGIN})
        client.cookies.clear()
        assert client.get('/api/public/videos').json()[0]['id']==item['id']
        assert client.get('/watch/'+item['id']).status_code==200
        assert client.get('/api/public/hosted/'+item['id']+'/playback').json()['video_url']==VIDEO
        assert client.get('/api/owner/media').status_code==401
