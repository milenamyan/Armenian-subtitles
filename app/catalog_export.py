"""Public-only static catalog export helpers shared by the CLI and local app."""
import hashlib
import json
import math
import os
import re
import sqlite3
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit, parse_qsl


def public_url(value, optional=False):
    if optional and not value:
        return ''
    if not isinstance(value, str):
        raise ValueError('Media URLs must be strings.')
    url = urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.hostname.endswith('.r2.cloudflarestorage.com')
            or url.hostname in ('localhost', '127.0.0.1') or any(c in value for c in '<>\r\n')):
        raise ValueError('Use a permanent public HTTPS media URL, without credentials or placeholders.')
    if any(re.search(r'signature|token|credential|secret|api.?key', key, re.I) for key, _ in parse_qsl(url.query)):
        raise ValueError('Signed/secret URLs cannot be published in the static catalog.')
    return value


def validate(data):
    if data.get('version') != 1 or not isinstance(data.get('films'), list):
        raise ValueError('catalog.json must contain version: 1 and a films array.')
    ids = set()
    for item in data['films']:
        identity = item.get('id', '')
        if not isinstance(identity, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', identity) or identity in ids:
            raise ValueError('Each film needs a unique id containing letters, numbers, underscores or hyphens.')
        ids.add(identity)
        height = item.get('subtitle_height', 10)
        if isinstance(height, bool) or not isinstance(height, int) or not 0 <= height <= 40:
            raise ValueError('subtitle_height must be an integer between 0 and 40.')
        if 'published' in item and not isinstance(item['published'], bool):
            raise ValueError('published must be true or false.')
        if 'is_new' in item and not isinstance(item['is_new'], bool):
            raise ValueError('is_new must be true or false.')
        if not isinstance(item.get('title'), str) or not item['title'].strip():
            raise ValueError('Each film needs a title.')
        public_url(item.get('video_url'))
        public_url(item.get('subtitle_url'), optional=True)
        poster = item.get('poster_url')
        if poster and not re.fullmatch(r'assets/posters/[a-zA-Z0-9_-]+\.(png|jpg|webp)', poster):
            public_url(poster)
        offset = item.get('subtitle_offset', 0)
        if isinstance(offset, bool) or not isinstance(offset, (int, float)) or not math.isfinite(offset) or abs(offset) > 86400:
            raise ValueError('Invalid subtitle offset.')
    return data


def atomic_write(path, content):
    path = Path(path)
    if path.is_file() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.catalog-', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def export_library(database, config, destination, *, strict=True):
    base = config.get('HAYSUB_CLOUD_BASE_URL', '').rstrip('/')
    selected = {s.strip() for s in config.get('HAYSUB_CLOUD_VIDEO_IDS', '').split(',')}
    hidden = {s.strip() for s in config.get('HAYSUB_HIDDEN_VIDEO_IDS', '').split(',')}
    prefix = config.get('HAYSUB_CLOUD_PATH_PREFIX', 'data').strip('/')
    def cloud(key):
        if not key:
            return ''
        public_url(base)
        return base + '/' + quote('/'.join(part for part in (prefix, key.lstrip('/')) if part), safe='/')
    films, posters, skipped = [], [], 0
    db = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute("SELECT * FROM hosted_videos WHERE state='ready' AND (published=1 OR published_at IS NOT NULL) ORDER BY COALESCE(published_at,created) DESC").fetchall()
        for raw in rows:
            row = dict(raw)
            visible = bool(row['published']) and not (row['id'] in hidden and not row.get('list_restored'))
            if not re.fullmatch(r'[a-f0-9]{32}', row['id']):
                raise ValueError('Invalid saved film id.')
            external = row.get('external_video_url')
            if not external and '*' not in selected and row['id'] not in selected:
                skipped += 1
                continue
            try:
                film = {'id': row['id'], 'title': row['title'], 'published': visible,
                        'video_url': external or cloud(row['object_key']),
                        'subtitle_url': row.get('external_subtitle_url') or cloud(row.get('subtitle_key')),
                        'subtitle_offset': row.get('subtitle_offset') or 0,
                        'subtitle_height': row.get('subtitle_height', 10), 'is_new': bool(row.get('is_new', False))}
                validate({'version': 1, 'films': [film]})
            except ValueError:
                if strict:
                    raise
                # Never let an invalid new link keep an unpublished/deleted film
                # in an old manifest. Omit the invalid entry and report it.
                skipped += 1
                continue
            if row.get('duration'):
                film['duration'] = row['duration']
            if row.get('poster'):
                extension = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}.get(row.get('poster_type'))
                if extension:
                    digest = hashlib.sha256(row['poster']).hexdigest()[:12]
                    relative = 'assets/posters/' + row['id'] + '-' + digest + '.' + extension
                    film['poster_url'] = relative
                    posters.append((relative, row['poster']))
            films.append(film)
    finally:
        db.close()
    data = validate({'version': 1, 'films': films})
    for relative, content in posters:
        path = destination / relative
        atomic_write(path, content)
    return data, skipped


def save_manifest(destination, data):
    """Replace JSON last, then remove only our obsolete generated cover files."""
    destination = Path(destination)
    atomic_write(destination / 'catalog.json', (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    keep = {item.get('poster_url') for item in data['films']}
    folder = destination / 'assets' / 'posters'
    if folder.is_dir():
        for path in folder.iterdir():
            if re.fullmatch(r'[a-f0-9]{32}(?:-[a-f0-9]{12})?\.(png|jpg|webp)', path.name):
                if path.is_file() and path.relative_to(destination).as_posix() not in keep:
                    path.unlink()

