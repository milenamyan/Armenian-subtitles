import os
import time

import pytest
from fastapi.testclient import TestClient
from app import main,storage,media_db as db,media_store as stores,media_worker as worker
from app.local_videos import scan


@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'metadata.sqlite3')
    monkeypatch.delenv('HAYSUB_DB',raising=False)
    monkeypatch.setenv('HAYSUB_PUBLIC','0')
    monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','local')
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_DIR',str(tmp_path/'managed'))
    monkeypatch.setenv('HAYSUB_LOCAL_VIDEO_FOLDER',str(tmp_path/'videos'))
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_SECRET','local-folder-test-secret-at-least-32-characters')
    monkeypatch.setattr(worker,'inspect_media',lambda *args:{'duration':10,'faststart':True})
    (tmp_path/'videos').mkdir()
    return tmp_path


def dropped(root,name='My film.mp4',age=10):
    path=root/'videos'/name;path.write_bytes(b'original synthetic test data')
    os.utime(path,(time.time()-age,time.time()-age));return path


def test_folder_video_appears_and_is_moved_without_an_upload(isolated):
    source=dropped(isolated)
    with TestClient(main.app) as client:
        assert client.post('/api/owner/media/scan-local').json()['added']==1
        assert client.post('/api/owner/media/scan-local').json()['added']==0
        item=client.get('/api/owner/media').json()[0]
        assert item['title']=='My film' and item['state']=='importing'
        assert worker.run_once()
        stored=db.get(item['id'])
        assert stored['state']=='ready' and stored['published']==0
        assert not source.exists()
        assert stores.store().path(stored['object_key']).read_bytes()==b'original synthetic test data'
        assert worker.run_once() is False
        assert len(client.get('/api/owner/media').json())==1


def test_scanning_a_copy_of_an_existing_video_does_not_add_another_card(isolated):
    dropped(isolated,'Original.mp4')
    with TestClient(main.app) as client:
        assert client.post('/api/owner/media/scan-local').json()['added']==1
        assert worker.run_once()
        dropped(isolated,'Renamed copy.mp4')
        result=client.post('/api/owner/media/scan-local').json()
        assert result['added']==0
        assert len(client.get('/api/owner/media').json())==1


def test_reselecting_the_same_upload_reuses_its_video_record(isolated):
    payload={'title':'Original','size':1024,'fingerprint':'a'*64}
    with TestClient(main.app) as client:
        first=client.post('/api/owner/media',json=payload)
        assert first.status_code==200
        again=client.post('/api/owner/media',json={**payload,'title':'Another title'})
        assert again.status_code==200
        assert again.json()['id']==first.json()['id']
        assert len(client.get('/api/owner/media').json())==1


def test_worker_auto_discovers_files_without_scan_button(isolated):
    dropped(isolated)
    assert worker.run_once()
    assert db.all_videos()[0]['state']=='ready'


def test_partial_new_and_nonvideo_files_are_not_imported(isolated):
    dropped(isolated,'copy.mp4.part');dropped(isolated,'notes.txt');dropped(isolated,'new.mp4',age=0)
    result=scan();assert result['added']==0 and result['waiting']==1
    assert db.all_videos()==[]


def test_recovery_after_file_move_before_metadata_commit(isolated,monkeypatch):
    source=dropped(isolated);scan();item=db.all_videos()[0]
    target=stores.store().path(item['object_key']);target.parent.mkdir(parents=True);source.rename(target)
    assert worker.run_once()
    assert db.get(item['id'])['state']=='ready'


def test_binned_pending_import_does_not_reappear_and_purges_after_deadline(isolated):
    source=dropped(isolated);scan();identity=db.all_videos()[0]['id']
    db.bin_video(identity)
    assert worker.run_once() is False
    assert len(db.all_videos())==1
    with db.connect() as connection:connection.execute('UPDATE hosted_videos SET purge_after=? WHERE id=?',(time.time()-1,identity))
    assert worker.run_once();assert db.get(identity) is None and not source.exists()
    assert worker.run_once() is False


def test_folder_import_is_disabled_in_public_or_s3_mode(isolated,monkeypatch):
    monkeypatch.setenv('HAYSUB_PUBLIC','1')
    with pytest.raises(stores.StorageError,match='only in local'):scan()
    monkeypatch.setenv('HAYSUB_PUBLIC','0');monkeypatch.setenv('HAYSUB_MEDIA_STORAGE','s3')
    with pytest.raises(stores.StorageError,match='only in local'):scan()


def test_renamed_film_folder_keeps_playback_subtitles_and_cleanup_together(isolated):
    dropped(isolated)
    assert worker.run_once()
    item=db.all_videos()[0];backend=stores.store()
    old=backend.path(item['object_key'])
    destination=old.parent.with_name('Readable film')
    old.parent.rename(destination)
    new=destination/'Readable film.mp4';(destination/old.name).rename(new)
    key=new.relative_to(backend.root).as_posix()
    with db.connect() as connection:
        connection.execute('UPDATE hosted_videos SET object_key=? WHERE id=?',(key,item['id']))
    with TestClient(main.app) as client:
        assert client.get('/api/owner/media/'+item['id']+'/playback').status_code==200
        raw='1\n00:00:01,000 --> 00:00:02,000\n\u0532\u0561\u0580\u0587'.encode('utf-8')
        result=client.post('/api/owner/media/'+item['id']+'/subtitles',files={'subtitles':('track.srt',raw)})
        assert result.status_code==200
        track=backend.path(db.get(item['id'])['subtitle_key'])
        assert track.is_relative_to(destination) and track.exists()
    db.bin_video(item['id'])
    with db.connect() as connection:
        connection.execute('UPDATE hosted_videos SET purge_after=? WHERE id=?',(time.time()-1,item['id']))
    assert worker.run_once()
    assert db.get(item['id']) is None and not destination.exists()
