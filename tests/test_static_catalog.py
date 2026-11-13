import importlib.util
import json
import sqlite3
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('static_builder', ROOT / 'scripts' / 'build_static_catalog.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_export_preserves_database_and_excludes_private_bin_and_local_only(tmp_path):
    database = tmp_path / 'library.sqlite3'
    db = sqlite3.connect(database)
    db.execute('''CREATE TABLE hosted_videos (id TEXT,title TEXT,object_key TEXT,
        subtitle_key TEXT,published INTEGER,state TEXT,published_at REAL,created REAL,
        external_video_url TEXT,external_subtitle_url TEXT,subtitle_offset REAL,
        poster BLOB,poster_type TEXT,duration REAL)''')
    for n, published, state in ((1, 1, 'ready'), (2, 0, 'ready'), (3, 1, 'bin'), (4, 1, 'ready')):
        db.execute('INSERT INTO hosted_videos VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                   (str(n) * 32, '<Film & Հայերեն>', 'videos/Film name.mp4',
                    'subtitles/Film name/armenian.srt', published, state, n if published else None, n,
                    None, None, 2, b'poster-bytes', 'image/png', 3600))
    db.commit()
    db.close()
    before = database.read_bytes()
    destination = tmp_path / 'site'
    destination.mkdir()
    data, skipped = builder.export_library(database, {
        'HAYSUB_CLOUD_BASE_URL': 'https://public.example.org',
        'HAYSUB_CLOUD_VIDEO_IDS': '1' * 32,
        'GEMINI_API_KEY': 'private-key-never-export',
        'HAYSUB_ADMIN_TOKEN': 'private-password-never-export'}, destination)
    assert database.read_bytes() == before
    assert skipped == 1
    assert len(data['films']) == 1
    film = data['films'][0]
    assert film['id'] == '1' * 32
    assert film['video_url'] == 'https://public.example.org/data/videos/Film%20name.mp4'
    assert (destination / film['poster_url']).read_bytes() == b'poster-bytes'
    assert 'private-key' not in json.dumps(data)
    assert 'private-password' not in json.dumps(data)


@pytest.mark.parametrize('url', ['http://localhost/video.mp4',
    'https://user:password@media.example.org/movie.mp4',
    'https://account.r2.cloudflarestorage.com/bucket/video.mp4',
    'https://media.example.org/video.mp4?X-Amz-Signature=private'])
def test_manifest_rejects_credentials_and_nonpublic_delivery_urls(url):
    with pytest.raises(ValueError):
        builder.validate({'version': 1, 'films': [{'id': 'film', 'title': 'Film', 'video_url': url}]})


def test_manifest_rejects_duplicate_ids():
    film = {'id': 'film', 'title': 'Film', 'video_url': 'https://media.example.org/film.mp4'}
    with pytest.raises(ValueError):
        builder.validate({'version': 1, 'films': [film, film]})
