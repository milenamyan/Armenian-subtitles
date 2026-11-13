"""Prepare a buildless catalog, retaining formerly published films as hidden.

Default: preserve catalog-site/catalog.json, validate it, refresh shared assets, zip.
--export-local: replace its film list from the local SQLite library (read-only).
Secrets, SQLite databases, private films, and video files never enter the package.
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SITE = ROOT / 'catalog-site'
ASSETS = ('style.css', 'viewer.css', 'site-planet.png', 'poster-fallback.svg',
          'playback-progress.js', 'media-sources.js')


from app.catalog_export import public_url, validate, export_library, save_manifest


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
        save_manifest(SITE, data)
        visible = sum(item.get('published', True) for item in data['films'])
        print(f'Exported {visible} visible and {len(data["films"]) - visible} hidden films; skipped {skipped}. Database unchanged.')
    data = validate(json.loads(manifest.read_text(encoding='utf-8')))
    (SITE / 'deployment.json').write_text(json.dumps({'updated_at': datetime.now(timezone.utc).isoformat()}) + '\n', encoding='utf-8')
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
             'catalog.js', 'player.js', 'catalog.json', 'build.cjs', 'deployment-date.js', 'deployment.json')]
    files += [assets / name for name in ASSETS]
    files += [SITE / film['poster_url'] for film in data['films'] if film.get('poster_url', '').startswith('assets/')]
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, 'catalog-site/' + path.relative_to(SITE).as_posix())
        archive.write(ROOT / 'docs' / 'STATIC_CATALOG.md', 'STATIC_CATALOG.md')
    visible = sum(item.get('published', True) for item in data['films'])
    print(f'Static catalog ready: {visible} visible, {len(data["films"]) - visible} hidden films.\n{output}')


if __name__ == '__main__':
    main()
