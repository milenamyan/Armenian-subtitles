from app.media_store import LocalStore


def test_local_worker_purge_removes_video_and_upload_parts_after_retention(tmp_path, monkeypatch):
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_DIR', str(tmp_path))
    monkeypatch.setenv('HAYSUB_LOCAL_MEDIA_SECRET', 'x' * 32)
    store = LocalStore()
    key = 'haysub-media/' + 'a' * 32 + '/source.mp4'
    store.put(key, b'video bytes', 'video/mp4')
    upload = store.create(key)
    (store.upload_folder(key, upload) / '1.part').write_bytes(b'partial bytes')
    store.abort(key, upload)
    store.delete_prefix('haysub-media/' + 'a' * 32 + '/')
    assert not store.path(key).exists()
    # User-facing removal is retained in SQLite's bin state for 24 hours.
    # These adapter methods are only called by permanent worker cleanup (or
    # to discard duplicate completed multipart parts), not by manual removal.
    assert not list(tmp_path.rglob('source.mp4'))
    assert not list(tmp_path.rglob('1.part'))
    store.delete_prefix('haysub-media/' + 'a' * 32 + '/')
