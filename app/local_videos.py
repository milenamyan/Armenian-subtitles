"""Import completed files from a local inbox into private managed media storage.

Files are moved on the same disk, not copied into RAM or served from the inbox.
The durable importing state recovers a crash before/after the atomic move.
"""
import hashlib
import os
from functools import lru_cache
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from app import media_db as db, media_store as stores

EXTENSIONS={'.mp4','.m4v','.mov','.mkv','.webm','.avi'}


@lru_cache(maxsize=256)
def _same_video(first,first_size,first_modified,second,second_size,second_modified):
    """Compare candidate copies before registering another movie card."""
    if first_size!=second_size:return False
    with first.open('rb') as left,second.open('rb') as right:
        while True:
            a=left.read(4*1024*1024)
            if a!=right.read(4*1024*1024):return False
            if not a:return True


def same_video(first,second):
    left=first.stat();right=second.stat()
    return _same_video(first,left.st_size,left.st_mtime_ns,second,right.st_size,right.st_mtime_ns)


def folder():
    return Path(os.getenv('HAYSUB_LOCAL_VIDEO_FOLDER') or Path(__file__).resolve().parent.parent/'videos').resolve()


def scan():
    if os.getenv('HAYSUB_MEDIA_STORAGE')!='local' or os.getenv('HAYSUB_PUBLIC')=='1':
        raise stores.StorageError('Folder import is available only in local storage mode.')
    backend=stores.store();inbox=folder()
    from app import local_library
    flat=local_library.enabled(backend)
    if not flat and (inbox==backend.root or inbox.is_relative_to(backend.root) or backend.root.is_relative_to(inbox)):
        raise stores.StorageError('Choose a separate video inbox outside the managed media storage directory.')
    restored=local_library.sync_bin(backend) if flat else 0
    inbox.mkdir(parents=True,exist_ok=True);added=[];waiting=0;skipped=[]
    known_items=[item for item in db.all_videos() if item['backend']==backend.identity
                 and item['state'] not in ('bin','deleting') and not item['external_video_url']]
    known={backend.path(item['object_key']).resolve() for item in known_items} if flat else set()
    for path in sorted(inbox.iterdir())[:200]:
        if path.resolve() in known:continue
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
        stat=path.stat()
        if not stat.st_size or time.time()-stat.st_mtime<3:waiting+=1;continue
        if stat.st_size>stores.upload_limit():skipped.append(path.name+' exceeds the configured video size limit.');continue
        if any(same_video(path,backend.path(item['object_key'])) for item in known_items
               if item['size']==stat.st_size and backend.path(item['object_key']).is_file()):
            skipped.append(path.name+' is already in the library.')
            continue
        identity=uuid4().hex;now=time.time()
        try:
            db.create(dict(id=identity,title=''.join(c for c in path.stem if ord(c)>=32)[:200] or 'HaySub',
                size=stat.st_size,fingerprint=hashlib.sha256(f'{path}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest(),
                backend=backend.identity,object_key=path.relative_to(backend.root).as_posix() if flat else stores.key_prefix(identity)+'source.mp4',part_size=stores.part_size(),
                state='importing',inbox_path=str(path),created=now,updated=now))
            added.append(identity)
        except sqlite3.IntegrityError:pass  # Another scan already registered this exact file.
    return {'added':len(added),'restored':restored,'waiting':waiting,'skipped':skipped,'folder':str(inbox)}


def finish(item,backend,*,move_only=False):
    source=Path(item['inbox_path']);inbox=folder();target=backend.path(item['object_key'])
    if source.is_symlink() or source.resolve().parent!=inbox:raise stores.StorageError('The inbox file is no longer a regular file inside the configured video folder.')
    if source.resolve()==target.resolve():
        if not source.is_file():raise stores.StorageError('The selected video was removed before inspection.')
        stat=source.stat()
        if time.time()-stat.st_mtime<3:return False
        if stat.st_size!=item['size']:raise stores.StorageError('The file changed after registration. Finish copying before scanning.')
    if target.is_file():
        if target.stat().st_size!=item['size']:raise stores.StorageError('Imported file size changed. Retry after the original copy finishes.')
    else:
        if not source.is_file():raise stores.StorageError('The selected inbox video was removed before import.')
        stat=source.stat()
        if time.time()-stat.st_mtime<3:return False
        if stat.st_size!=item['size']:
            if move_only:raise stores.StorageError('The inbox file changed after removal. Check it before retrying cleanup.')
            if stat.st_size>stores.upload_limit():raise stores.StorageError('The video exceeds the configured video size limit.')
            db.update(item['id'],states=['importing'],token=item['worker_token'],size=stat.st_size)
            item['size']=stat.st_size
        target.parent.mkdir(parents=True,exist_ok=True)
        try:source.rename(target)
        except PermissionError:return False  # Windows copy still holds the file open; retry later.
        except OSError:raise stores.StorageError('Could not move the inbox video into storage. Keep both folders on the same disk and check permissions.') from None
    if move_only:return True
    return db.update(item['id'],states=['importing'],token=item['worker_token'],state='processing',inbox_path=None,error='')
