"""Prepare a buildless public catalog. Export only explicitly published Cloud media.

Default: preserve catalog-site/catalog.json, validate it, refresh shared assets, zip.
--export-local: replace its film list from the local SQLite library (read-only).
Secrets, SQLite databases, private films, and video files never enter the package.
"""
import argparse
import json
import math
import re
import shutil
import sqlite3
from pathlib import Path
from urllib.parse import quote, urlsplit, parse_qsl
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / 'catalog-site'
ASSETS = ('style.css', 'viewer.css', 'site-planet.png', 'poster-fallback.svg',
          'playback-progress.js', 'media-sources.js')


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


def export_library(database, config, destination):
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
        rows = db.execute("SELECT * FROM hosted_videos WHERE published=1 AND state='ready' ORDER BY COALESCE(published_at,created) DESC").fetchall()
        for raw in rows:
            row = dict(raw)
            if row['id'] in hidden and not row.get('list_restored'):
                continue
            if not re.fullmatch(r'[a-f0-9]{32}', row['id']):
                raise ValueError('Invalid saved film id.')
            external = row.get('external_video_url')
            if not external and '*' not in selected and row['id'] not in selected:
                skipped += 1
                continue
            film = {'id': row['id'], 'title': row['title'],
                    'video_url': external or cloud(row['object_key']),
                    'subtitle_url': row.get('external_subtitle_url') or cloud(row.get('subtitle_key')),
                    'subtitle_offset': row.get('subtitle_offset') or 0}
            if row.get('duration'):
                film['duration'] = row['duration']
            if row.get('poster'):
                extension = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}.get(row.get('poster_type'))
                if extension:
                    relative = 'assets/posters/' + row['id'] + '.' + extension
                    film['poster_url'] = relative
                    posters.append((relative, row['poster']))
            films.append(film)
    finally:
        db.close()
    data = validate({'version': 1, 'films': films})
    for relative, content in posters:
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return data, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export-local', action='store_true', help='Replace catalog.json with published local Cloud entries.')
    parser.add_argument('--database', type=Path, default=ROOT / 'data' / 'haysub.sqlite3')
    args = parser.parse_args()
    manifest = SITE / 'catalog.json'
    if args.export_local:
        from dotenv import dotenv_values
        config = {key: value or '' for key, value in dotenv_values(ROOT / '.env').items()}
        data, skipped = export_library(args.database, config, SITE)
        # Preserve an existing manifest before an explicit re-export.
        if manifest.exists():
            backup = ROOT / 'dist' / 'catalog-before-export.json'
            backup.parent.mkdir(exist_ok=True)
            shutil.copyfile(manifest, backup)
        manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Exported {len(data["films"])} published films; skipped {skipped} local-only films. Database unchanged.')
    data = validate(json.loads(manifest.read_text(encoding='utf-8')))
    assets = SITE / 'assets'
    assets.mkdir(exist_ok=True)
    for name in ASSETS:
        shutil.copyfile(ROOT / 'static' / name, assets / name)
    for film in data['films']:
        poster = film.get('poster_url', '')
        if poster.startswith('assets/') and not (SITE / poster).is_file():
            raise ValueError('A catalog poster file is missing.')
    output = ROOT / 'dist' / 'haysub-static-catalog.zip'
    output.parent.mkdir(exist_ok=True)
    # Explicit allowlist: do not accidentally package a local secret or database.
    files = [SITE / name for name in ('index.html', 'watch.html', 'catalog.css', 'catalog-model.js',
             'catalog.js', 'player.js', 'catalog.json')]
    files += [assets / name for name in ASSETS]
    files += [SITE / film['poster_url'] for film in data['films'] if film.get('poster_url', '').startswith('assets/')]
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, 'catalog-site/' + path.relative_to(SITE).as_posix())
        archive.write(ROOT / 'docs' / 'STATIC_CATALOG.md', 'STATIC_CATALOG.md')
    print(f'Static catalog ready: {len(data["films"])} films.\n{output}')


if __name__ == '__main__':
    main()
