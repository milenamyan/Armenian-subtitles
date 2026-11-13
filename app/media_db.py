"""Durable metadata and multipart manifests. Media bytes never enter SQLite."""
import time
from uuid import uuid4
from app import storage


def connect():
    db=storage.connect()
    db.row_factory=__import__('sqlite3').Row
    db.execute('''CREATE TABLE IF NOT EXISTS hosted_videos (
        id TEXT PRIMARY KEY, title TEXT NOT NULL, size INTEGER NOT NULL,
        fingerprint TEXT NOT NULL, backend TEXT NOT NULL, object_key TEXT NOT NULL,
        upload_id TEXT, part_size INTEGER NOT NULL, state TEXT NOT NULL,
        published INTEGER NOT NULL DEFAULT 0, subtitle_key TEXT,
        subtitle_cues TEXT NOT NULL DEFAULT '[]', subtitle_offset REAL NOT NULL DEFAULT 0,
        duration REAL, media_info TEXT, error TEXT NOT NULL DEFAULT '',
        created REAL NOT NULL, updated REAL NOT NULL, lease_until REAL NOT NULL DEFAULT 0,
        worker_token TEXT, failures INTEGER NOT NULL DEFAULT 0)''')
    db.execute('BEGIN IMMEDIATE')
    columns={row[1] for row in db.execute('PRAGMA table_info(hosted_videos)')}
    for name,kind in (('binned_at','REAL'),('purge_after','REAL'),('bin_previous_state','TEXT'),('bin_object_key','TEXT'),('inbox_path','TEXT'),('external_video_url','TEXT'),('external_subtitle_url','TEXT'),('published_at','REAL'),('poster','BLOB'),('poster_type','TEXT')):
        if name not in columns:db.execute('ALTER TABLE hosted_videos ADD COLUMN '+name+' '+kind)
    if 'list_restored' not in columns:db.execute('ALTER TABLE hosted_videos ADD COLUMN list_restored INTEGER NOT NULL DEFAULT 0')
    if 'is_new' not in columns:db.execute('ALTER TABLE hosted_videos ADD COLUMN is_new INTEGER NOT NULL DEFAULT 0')
    if 'subtitle_height' not in columns:db.execute('ALTER TABLE hosted_videos ADD COLUMN subtitle_height INTEGER NOT NULL DEFAULT 10')
    db.execute('UPDATE hosted_videos SET published_at=created WHERE published=1 AND published_at IS NULL')
    db.execute('CREATE UNIQUE INDEX IF NOT EXISTS hosted_inbox_path ON hosted_videos(inbox_path) WHERE inbox_path IS NOT NULL')
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS hosted_external_url ON hosted_videos(external_video_url) WHERE external_video_url IS NOT NULL AND state='ready'")
    db.commit()
    db.execute('''CREATE TABLE IF NOT EXISTS hosted_parts (
        video_id TEXT NOT NULL, number INTEGER NOT NULL, etag TEXT NOT NULL,
        PRIMARY KEY(video_id,number))''')
    db.execute('CREATE TABLE IF NOT EXISTS media_worker_status (id INTEGER PRIMARY KEY, heartbeat REAL NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS hosted_track_writes (id TEXT PRIMARY KEY,video_id TEXT NOT NULL,object_key TEXT NOT NULL,expires REAL NOT NULL)')
    return db


def heartbeat():
    with connect() as db:
        db.execute('INSERT INTO media_worker_status VALUES (1,?) ON CONFLICT(id) DO UPDATE SET heartbeat=excluded.heartbeat',(time.time(),))


def worker_online():
    with connect() as db:
        row=db.execute('SELECT heartbeat FROM media_worker_status WHERE id=1').fetchone()
        return bool(row and time.time()-row[0]<35)


def reserve_track(identity,key):
    token=uuid4().hex
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT id FROM hosted_videos WHERE id=? AND state NOT IN ('bin','deleting')",(identity,)).fetchone()
        if not row:return None
        db.execute('INSERT INTO hosted_track_writes VALUES (?,?,?,?)',(token,identity,key,time.time()+600))
    return token


def release_track(token):
    with connect() as db:db.execute('DELETE FROM hosted_track_writes WHERE id=?',(token,))


def get(identity):
    with connect() as db:
        row=db.execute('SELECT * FROM hosted_videos WHERE id=?',(identity,)).fetchone()
        return dict(row) if row else None


def all_videos():
    with connect() as db:
        # Lists need only poster presence, never megabytes of image data per row.
        columns=[row[1] for row in db.execute('PRAGMA table_info(hosted_videos)') if row[1]!='poster']
        selection=','.join(columns)+',poster IS NOT NULL AS poster'
        return [dict(row) for row in db.execute('SELECT '+selection+' FROM hosted_videos ORDER BY created DESC')]


def bin_video(identity):
    now=time.time()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM hosted_videos WHERE id=?',(identity,)).fetchone()
        if not row:return None
        if row['state']=='bin':return row['purge_after']
        if row['state']=='deleting':return False
        db.execute("UPDATE hosted_videos SET bin_previous_state=state,state='bin',published=0,binned_at=?,purge_after=?,error='',updated=? WHERE id=?",(now,now+86400,now,identity))
        return now+86400


def restore_video(identity):
    now=time.time()
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM hosted_videos WHERE id=?',(identity,)).fetchone()
        if not row or row['state']!='bin' or not row['purge_after'] or now>=row['purge_after']:return False
        if row['worker_token'] and row['lease_until']>now:return False
        previous=row['bin_previous_state']
        state=previous if previous in ('ready','uploading','error','importing') else 'finalizing' if previous in ('processing','finalizing') else 'error'
        db.execute("UPDATE hosted_videos SET state=?,published=0,binned_at=NULL,purge_after=NULL,bin_previous_state=NULL,error='',updated=?,worker_token=NULL,lease_until=0 WHERE id=?",(state,now,identity))
    return True


def delete_from_bin(identity):
    return update(identity, states=['bin'], state='deleting', published=0, error='')


def expire_bin():
    with connect() as db:
        db.execute("UPDATE hosted_videos SET state='deleting',published=0 WHERE state='bin' AND purge_after<=?",(time.time(),))


def create(item):
    item={'subtitle_height':10,'is_new':1,**item}
    keys=tuple(item)
    with connect() as db:
        db.execute('INSERT INTO hosted_videos ('+','.join(keys)+') VALUES ('+','.join('?' for _ in keys)+')',tuple(item.values()))


def update(identity, *, states=None, token=None, **values):
    # The badge is an owner-controlled flag, independent of publication dates.
    allowed={'subtitle_height','list_restored','published_at','poster','poster_type','external_subtitle_url','object_key','title','upload_id','state','published','subtitle_key','subtitle_cues','subtitle_offset','duration','media_info','error','lease_until','worker_token','failures','inbox_path','size'}
    allowed.add('is_new')
    if not set(values)<=allowed:
        raise ValueError('Invalid media metadata update')
    if values.get('published'):
        previous=get(identity)
        if previous and not previous['published']:values['published_at']=time.time()
    values['updated']=time.time()
    condition='id=?';args=list(values.values())+[identity]
    if states:
        condition+=' AND state IN ('+','.join('?' for _ in states)+')';args+=list(states)
    if token:
        condition+=' AND worker_token=?';args.append(token)
    with connect() as db:
        return db.execute('UPDATE hosted_videos SET '+','.join(key+'=?' for key in values)+' WHERE '+condition,args).rowcount>0


def parts(identity):
    with connect() as db:
        return [dict(row) for row in db.execute('SELECT number,etag FROM hosted_parts WHERE video_id=? ORDER BY number',(identity,))]


def acknowledge(identity, number, etag):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        state=db.execute('SELECT state FROM hosted_videos WHERE id=?',(identity,)).fetchone()
        if not state or state[0]!='uploading':
            return False
        db.execute('INSERT INTO hosted_parts VALUES (?,?,?) ON CONFLICT(video_id,number) DO UPDATE SET etag=excluded.etag',(identity,number,etag))
        db.execute('UPDATE hosted_videos SET updated=? WHERE id=?',(time.time(),identity))
    return True


def claim(lease_seconds):
    now=time.time();token=uuid4().hex
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT * FROM hosted_videos WHERE state IN ('importing','finalizing','processing','deleting') AND lease_until<? AND NOT EXISTS (SELECT 1 FROM hosted_track_writes w WHERE w.video_id=hosted_videos.id AND w.expires>?) ORDER BY CASE state WHEN 'deleting' THEN 0 ELSE 1 END,updated LIMIT 1",(now,now)).fetchone()
        if not row:
            return None
        db.execute('UPDATE hosted_videos SET worker_token=?,lease_until=? WHERE id=?',(token,now+lease_seconds,row['id']))
        return dict(row,worker_token=token,lease_until=now+lease_seconds)


def remove(identity, token):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT * FROM hosted_videos WHERE id=? AND worker_token=? AND state='deleting'",(identity,token)).fetchone()
        if row:
            db.execute('DELETE FROM hosted_parts WHERE video_id=?',(identity,))
            db.execute('DELETE FROM hosted_track_writes WHERE video_id=?',(identity,))
            db.execute('DELETE FROM hosted_videos WHERE id=?',(identity,))


def expire_uploads(ttl):
    with connect() as db:
        db.execute("UPDATE hosted_videos SET state='deleting',published=0,error='' WHERE state IN ('allocating','uploading') AND updated<?",(time.time()-ttl,))
