"""One local movie file and one original/Armenian subtitle pair per film."""
import os
from pathlib import Path
import re


def enabled(backend=None):
    root=os.getenv('HAYSUB_LIBRARY_ROOT')
    media=backend.root if backend is not None else Path(os.getenv('HAYSUB_LOCAL_MEDIA_DIR','data/local-media')).resolve()
    return bool(root and os.getenv('HAYSUB_LOCAL_FLAT_LIBRARY')=='1' and os.getenv('HAYSUB_MEDIA_STORAGE')=='local'
                and os.getenv('HAYSUB_PUBLIC')!='1' and Path(root).resolve()==media)


def root():
    return Path(os.environ['HAYSUB_LIBRARY_ROOT']).resolve()


def name(title):
    value=re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', title).strip(' .')[:150] or 'HaySub'
    if value.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        value='_'+value
    return value


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.is_file() and path.read_bytes()==data:return
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_bytes(data);temporary.replace(path)


def subtitle_folder(item):
    from app import storage
    if item.get('artifact_folder'):
        folder=(root()/item['artifact_folder']).resolve()
    else:
        title=name(item['title'])
        if any(other['id']!=item['id'] and name(other['title']).casefold()==title.casefold() for other in storage.list_library()):
            title+=' ('+item['id'][:8]+')'
        folder=root()/'subtitles'/title
    if not folder.is_relative_to(root()/'subtitles'):raise ValueError('Invalid subtitle folder.')
    return folder


def archive(item,job,text):
    import base64
    from app import storage
    from app.subtitles import render_srt
    folder=subtitle_folder(item)
    atomic_write(folder/'armenian.srt',('\ufeff'+text).encode('utf-8'))
    extension=Path(job.get('filename','')).suffix.lower()
    if extension not in ('.srt','.vtt'):extension='.srt'
    if job.get('original_base64'):
        original=base64.b64decode(job['original_base64'])
    else:
        extension='.srt'
        original=('\ufeff'+render_srt(job['cues'])).encode('utf-8')
    target=folder/('original'+extension)
    # A recovered source must never replace an exact uploaded original.
    existing=list(folder.glob('original.*'))
    if job.get('original_base64') or not existing:
        atomic_write(target,original)
        for path in existing:
            if path!=target and path.suffix in ('.srt','.vtt'):path.unlink()
    with storage.connect() as connection:
        connection.execute('UPDATE subtitle_library SET artifact_folder=? WHERE id=?',(folder.relative_to(root()).as_posix(),item['id']))
    return folder/'armenian.srt'


def place_video(item,backend):
    from app import media_db as db
    if not enabled(backend):return item
    source=backend.path(item['object_key'])
    destination=root()/'videos'/(name(item['title'])+source.suffix.lower())
    if source.resolve().parent==(root()/'videos').resolve():return item
    if destination.exists():destination=destination.with_stem(destination.stem+' ('+item['id'][:8]+')')
    destination.parent.mkdir(parents=True,exist_ok=True)
    source.rename(destination)
    db.update(item['id'],object_key=destination.relative_to(backend.root).as_posix(),upload_id=None)
    # Remove only empty staging directories, never another movie's files.
    parent=source.parent
    while parent!=backend.root and parent.is_relative_to(backend.root):
        try:parent.rmdir()
        except OSError:break
        parent=parent.parent
    return db.get(item['id'])


def bin_video(identity,backend):
    """Move one local video into bin while retaining its ID and subtitles."""
    import time
    from app import media_db as db, media_store as stores
    connection=db.connect()
    moved=None
    try:
        connection.execute('BEGIN IMMEDIATE')
        item=connection.execute('SELECT * FROM hosted_videos WHERE id=?',(identity,)).fetchone()
        if not item or item['state']=='deleting':raise stores.StorageError('Permanent cleanup has already started.')
        if item['state']=='bin' and item['bin_object_key']:return
        source=backend.path(item['object_key'])
        if source.parent!=root()/'videos':raise stores.StorageError('This video is not in the local videos folder.')
        if source.is_symlink():raise stores.StorageError('The video must be a regular local file.')
        target=backend.path('bin/'+source.name)
        if target.parent!=root()/'bin':raise stores.StorageError('Invalid local bin folder.')
        if target.exists():target=target.with_stem(target.stem+' ('+identity[:8]+')')
        if target.exists():raise stores.StorageError('A file with this bin name already exists.')
        target.parent.mkdir(parents=True,exist_ok=True)
        if source.exists():
            source.rename(target);moved=(source,target)
        previous=item['bin_previous_state'] if item['state']=='bin' else item['state']
        connection.execute("UPDATE hosted_videos SET state='bin',bin_previous_state=?,bin_object_key=?,published=0,binned_at=?,purge_after=NULL,error='',updated=? WHERE id=?",
                           (previous,target.relative_to(backend.root).as_posix(),time.time(),time.time(),identity))
        connection.commit()
    except Exception:
        connection.rollback()
        if moved and moved[1].exists() and not moved[0].exists():moved[1].rename(moved[0])
        raise
    finally:connection.close()


def restore_binned_video(identity,backend,*,move_file=False):
    """Recognize an unchanged bin filename moved back into videos by the owner."""
    import time
    from app import media_db as db
    connection=db.connect();moved=None
    try:
        connection.execute('BEGIN IMMEDIATE')
        item=connection.execute('SELECT * FROM hosted_videos WHERE id=?',(identity,)).fetchone()
        if not item or item['state']!='bin' or not item['bin_object_key']:return False
        if item['worker_token'] and item['lease_until']>time.time():return False
        source=backend.path(item['bin_object_key'])
        if source.parent!=root()/'bin' or source.is_symlink():return False
        target=backend.path('videos/'+source.name)
        if target.parent!=root()/'videos':return False
        if move_file:
            if not source.is_file() or target.exists():return False
            source.rename(target);moved=(source,target)
        elif source.exists():return False  # Copying is not a restore; the bin file must have moved.
        if not target.is_file() or target.is_symlink():return False
        stat=target.stat()
        if stat.st_size!=item['size'] or time.time()-stat.st_mtime<3:return False
        key=target.relative_to(backend.root).as_posix()
        conflict=connection.execute("SELECT id FROM hosted_videos WHERE id!=? AND object_key=?",(identity,key)).fetchone()
        if conflict:return False
        previous=item['bin_previous_state']
        state=previous if previous in ('ready','importing','error') else 'processing'
        connection.execute("UPDATE hosted_videos SET state=?,object_key=?,inbox_path=?,published=0,binned_at=NULL,purge_after=NULL,bin_previous_state=NULL,bin_object_key=NULL,error='',updated=?,worker_token=NULL,lease_until=0 WHERE id=?",
                           (state,key,str(target) if state=='importing' else None,time.time(),identity))
        connection.commit();moved=None
        return True
    finally:
        connection.rollback();connection.close()
        if moved and moved[1].exists() and not moved[0].exists():moved[1].rename(moved[0])


def sync_bin(backend):
    from app import media_db as db
    restored=0
    for item in db.all_videos():
        if item['backend']!=backend.identity or item['state']!='bin':continue
        if not item['object_key'].startswith('videos/'):continue
        if not item['bin_object_key']:bin_video(item['id'],backend)
        elif restore_binned_video(item['id'],backend):restored+=1
    return restored
