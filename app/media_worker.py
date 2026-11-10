"""One durable media worker: finalize multipart, inspect compatible MP4, delete.

Run on the same machine and persistent metadata volume as FastAPI. No re-encoding.
"""
import argparse
import json
import logging
import os
from pathlib import Path
import time
import threading

from dotenv import load_dotenv
from app import media_db as db, media_store as stores, storage, local_library
from app.media_formats import inspect_media, MediaError

log=logging.getLogger('haysub.media')


def expected_parts(item):
    count=(item['size']+item['part_size']-1)//item['part_size']
    return {number:min(item['part_size'],item['size']-(number-1)*item['part_size']) for number in range(1,count+1)}


def validated_manifest(item,backend):
    manifest=db.parts(item['id']);remote=backend.list_parts(item['object_key'],item['upload_id']);expected=expected_parts(item)
    actual={p['number']:p for p in remote}
    if len(remote)!=len(expected) or {p['number'] for p in manifest}!=set(expected):
        raise MediaError('Upload is incomplete. Resume all missing parts before completing.')
    for part in manifest:
        found=actual.get(part['number'])
        if not found or found['size']!=expected[part['number']] or found['etag']!=part['etag']:
            raise MediaError('Stored upload parts do not match the acknowledged upload. Re-upload mismatched parts before completing.')
    return manifest


def run_once():
    backend=stores.store()
    if isinstance(backend,stores.LocalStore) and os.getenv('HAYSUB_LOCAL_VIDEO_FOLDER'):
        from app.local_videos import scan
        scan()
    db.expire_uploads(stores.integer('HAYSUB_UPLOAD_IDLE_HOURS',48,1,168)*3600)
    db.expire_bin()
    item=db.claim(stores.integer('HAYSUB_MEDIA_LEASE_SECONDS',900,600,3600))
    if not item:return False
    identity=item['id'];token=item['worker_token']
    try:
        if item['external_video_url'] and item['state']=='deleting':
            db.remove(identity,token);return True  # Remove metadata only, never remote files.
        if item['backend']!=backend.identity:raise stores.StorageError('Storage configuration changed. Restore the original bucket/prefix before processing or deleting this video.')
        if item['state']=='deleting':
            # Cleanup follows bin expiry or the owner's explicit permanent deletion.
            if item['inbox_path'] and isinstance(backend,stores.LocalStore):
                from app.local_videos import finish
                if not finish(item,backend,move_only=True):return False
            if item['upload_id']:backend.abort(item['object_key'],item['upload_id'])
            if local_library.enabled(backend) and item['object_key'].startswith('videos/'):
                # The directory is shared: delete only this movie, never videos/.
                path=backend.path(item['bin_object_key'] or item['object_key'])
                if path.parent not in (local_library.root()/'videos',local_library.root()/'bin'):raise stores.StorageError('Invalid flat movie path.')
                path.unlink(missing_ok=True)
            else:
                backend.delete_prefix(stores.video_prefix(item))
            db.remove(identity,token);return True
        if item['state']=='importing':
            from app.local_videos import finish
            if not finish(item,backend):return False
            item=db.get(identity)
        if item['state']=='finalizing':
            head=backend.head(item['object_key'])
            if not head:
                manifest=validated_manifest(item,backend)
                backend.complete(item['object_key'],item['upload_id'],manifest)
                head=backend.head(item['object_key'])
            if not head or head['size']!=item['size']:raise MediaError('Completed object size does not match the declared upload. Delete this video and upload again.')
            if not db.update(identity,states=['finalizing'],token=token,state='processing'):return True
        current=db.get(identity)
        if not current or current['state']!='processing':return True
        info=inspect_media(backend,item['object_key'],item['size'])
        item=local_library.place_video(db.get(identity),backend)
        db.update(identity,states=['processing'],token=token,state='ready',duration=info['duration'],media_info=json.dumps(info),error='',failures=0)
    except (stores.StorageError,MediaError) as exc:
        current=db.get(identity)
        if current and current['state']=='deleting':
            failures=current['failures']+1
            db.update(identity,token=token,error=str(exc),failures=failures,lease_until=time.time()+min(3600,30*2**min(failures,7)))
        else:
            db.update(identity,states=['importing','finalizing','processing'],token=token,state='error',published=0,error=str(exc))
    except Exception:
        # Never log exception representations containing SDK URLs or credentials.
        current=db.get(identity)
        if current and current['state']=='deleting':
            db.update(identity,token=token,error='Cleanup failed. Check worker/storage configuration and retry.',lease_until=time.time()+60)
        else:db.update(identity,states=['importing','finalizing','processing'],token=token,state='error',published=0,error='Media processing failed. Check worker dependencies and storage, then retry.')
        log.error('Media operation failed for video %s (details withheld to protect signed URLs).',identity)
    finally:
        current=db.get(identity)
        if current and current['worker_token']==token:
            # A deletion requested during inspection is claimed on the next loop.
            delay=current['lease_until'] if current['state']=='deleting' and current['error'] else 0
            db.update(identity,token=token,worker_token=None,lease_until=delay)
    return True


def main():
    load_dotenv(Path(__file__).resolve().parent.parent/'.env')
    if os.getenv('HAYSUB_DB'):storage.DB=Path(os.environ['HAYSUB_DB'])
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--once',action='store_true');args=parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    def heartbeat():
        while True:
            try:db.heartbeat()
            except Exception:log.error('Worker heartbeat unavailable; check the persistent metadata database.')
            time.sleep(10)
    threading.Thread(target=heartbeat,daemon=True).start()
    while True:
        try:worked=run_once()
        except stores.StorageError as exc:
            log.error('%s',exc);worked=False
        if args.once:break
        if not worked:time.sleep(3)


if __name__=='__main__':main()
