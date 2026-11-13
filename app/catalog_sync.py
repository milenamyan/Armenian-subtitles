"""Keep the local static publish folder in step with owner library changes.

Never pushes Git commits, uploads media, or runs on a public server.
"""
import logging
import os
import threading
import time
from pathlib import Path
from app import storage
from app.catalog_export import export_library, save_manifest

ROOT = Path(__file__).resolve().parent.parent
_lock = threading.Lock()
_status = {'state': 'disabled'}
_fingerprint = None


def enabled():
    return os.getenv('HAYSUB_PUBLIC') != '1' and os.getenv('HAYSUB_STATIC_CATALOG_SYNC') == '1'


def destination():
    return Path(os.getenv('HAYSUB_STATIC_CATALOG_DIR') or ROOT / 'catalog-site').resolve()


def status():
    if not enabled():
        return {'state': 'disabled'}
    return dict(_status)


def sync():
    global _fingerprint, _status
    if not enabled():
        return 'disabled'
    with _lock:
        try:
            target = destination()
            # Use the running app's database and environment, including changes
            # made by workers. Do not accidentally export a different .env DB.
            from app import media_db
            with media_db.connect() as connection:
                stamp = tuple(tuple(row) for row in connection.execute('SELECT id,updated,published,state FROM hosted_videos ORDER BY id'))
            config = {key: os.getenv(key, '') for key in ('HAYSUB_CLOUD_BASE_URL', 'HAYSUB_CLOUD_VIDEO_IDS', 'HAYSUB_HIDDEN_VIDEO_IDS')}
            config['HAYSUB_CLOUD_PATH_PREFIX'] = os.getenv('HAYSUB_CLOUD_PATH_PREFIX', 'data')
            marker = (str(storage.DB.resolve()), str(target), stamp, tuple(config.items()))
            if marker == _fingerprint and (target / 'catalog.json').exists():
                return _status['state']
            data, skipped = export_library(storage.DB, config, target, strict=False)
            save_manifest(target, data)
            _fingerprint = marker
            _status = {'state': 'warning' if skipped else 'saved', 'films': sum(item['published'] for item in data['films']),
                       'hidden': sum(not item['published'] for item in data['films']),
                       'skipped': skipped, 'updated': time.time()}
        except Exception:
            # The library operation has already committed: report the separate
            # export failure without pretending it failed or hiding the issue.
            _fingerprint = None
            _status = {'state': 'error'}
            logging.getLogger(__name__).warning('Static catalog export failed; retry from the local library.')
        return _status['state']
