import json
import sqlite3
import os
from uuid import uuid4
from pathlib import Path

DB = Path(os.getenv('HAYSUB_DB') or Path(__file__).resolve().parent.parent / 'data' / 'haysub.sqlite3')


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    (DB.parent / 'bin').mkdir(exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS videos (id TEXT PRIMARY KEY, video TEXT, cues TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE IF NOT EXISTS translations (key TEXT PRIMARY KEY, result TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS cache_reuse (target_key TEXT, source_key TEXT, source_version TEXT, model TEXT, PRIMARY KEY(target_key,source_key))')
    db.execute('CREATE TABLE IF NOT EXISTS file_jobs (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, updated TEXT DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE IF NOT EXISTS subtitle_library (id TEXT PRIMARY KEY, title TEXT NOT NULL, source_filename TEXT NOT NULL, srt TEXT NOT NULL, cue_count INTEGER NOT NULL, model TEXT, prompt_version TEXT, created TEXT DEFAULT CURRENT_TIMESTAMP, updated TEXT DEFAULT CURRENT_TIMESTAMP)')
    if 'published' not in {row[1] for row in db.execute('PRAGMA table_info(subtitle_library)')}:
        db.execute('ALTER TABLE subtitle_library ADD COLUMN published INTEGER NOT NULL DEFAULT 0')
        db.commit()
    if 'artifact_folder' not in {row[1] for row in db.execute('PRAGMA table_info(subtitle_library)')}:
        db.execute('ALTER TABLE subtitle_library ADD COLUMN artifact_folder TEXT')
        db.commit()
    if 'source' not in {row[1] for row in db.execute('PRAGMA table_info(videos)')}:
        db.execute('ALTER TABLE videos ADD COLUMN source TEXT')
        db.commit()
    return db


def cached(key):
    with connect() as db:
        row = db.execute('SELECT result FROM translations WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else None


def save_cache(key, result):
    with connect() as db:
        db.execute('INSERT OR REPLACE INTO translations VALUES (?,?)', (key, json.dumps(result)))


def delete_cache(key):
    with connect() as db:
        db.execute('DELETE FROM translations WHERE key=?', (key,))


def record_cache_reuse(target_key, source_key, source_version, model):
    with connect() as db:
        db.execute('INSERT OR IGNORE INTO cache_reuse VALUES (?,?,?,?)', (target_key, source_key, source_version, model))


def save_file_job(job):
    fields = ('filename','original_base64','cues','translated','model','prompt_version','error','error_code','phase',
              'restored_cues','cache_cues','compatible_cache_cues','silent_cues')
    payload = {field:job.get(field) for field in fields}
    with connect() as db:
        db.execute('INSERT INTO file_jobs(id,fingerprint,payload) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload,updated=CURRENT_TIMESTAMP',
                   (job['file_identity'], job['file_fingerprint'], json.dumps(payload,ensure_ascii=False)))


def load_file_job(identity=None, fingerprint=None):
    with connect() as db:
        row = (db.execute('SELECT id,fingerprint,payload FROM file_jobs WHERE id=?',(identity,)).fetchone()
               if identity is not None else db.execute('SELECT id,fingerprint,payload FROM file_jobs WHERE fingerprint=?',(fingerprint,)).fetchone())
    if not row:
        return None
    return dict(json.loads(row[2]),file_identity=row[0],file_fingerprint=row[1])


def bin_file_job(identity):
    with connect() as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM file_jobs WHERE id=?', (identity,)).fetchone()
        if not row:
            return False
        folder = DB.parent / 'bin' / ('process-' + uuid4().hex)
        folder.mkdir(parents=True)
        (folder / 'job.json').write_text(json.dumps(dict(row), ensure_ascii=False, indent=2), encoding='utf-8')
        db.execute('DELETE FROM file_jobs WHERE id=?', (identity,))
        return True


def unindexed_file_jobs():
    with connect() as db:
        rows=db.execute('SELECT j.id,j.fingerprint,j.payload FROM file_jobs j LEFT JOIN subtitle_library l ON j.id=l.id WHERE l.id IS NULL').fetchall()
    return [dict(json.loads(row[2]),file_identity=row[0],file_fingerprint=row[1]) for row in rows]


def save_library_translation(job, text):
    # A user's chosen title must survive worker saves and identical reuploads.
    title=Path(job['filename']).stem.strip() or 'HaySub'
    with connect() as db:
        db.execute('''INSERT INTO subtitle_library(id,title,source_filename,srt,cue_count,model,prompt_version)
                      VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                      srt=excluded.srt,cue_count=excluded.cue_count,model=excluded.model,
                      prompt_version=excluded.prompt_version,updated=CURRENT_TIMESTAMP
                      WHERE subtitle_library.srt != excluded.srt''',
                   (job['file_identity'],title,job['filename'],text,len(job['cues']),job.get('model'),job.get('prompt_version')))


def list_library():
    with connect() as db:
        db.row_factory=sqlite3.Row
        return [dict(row) for row in db.execute('SELECT id,title,source_filename,cue_count,model,prompt_version,created,updated,published FROM subtitle_library ORDER BY created DESC,id')]


def publish_library_item(identity, published):
    with connect() as db:
        return db.execute('UPDATE subtitle_library SET published=?,updated=CURRENT_TIMESTAMP WHERE id=?', (int(published), identity)).rowcount > 0


def public_library(query='', offset=0):
    with connect() as db:
        db.row_factory = sqlite3.Row
        db.create_function('haysub_fold', 1, lambda value: (value or '').casefold(), deterministic=True)
        # instr is a literal search: %, _ and quotes do not change the query.
        return [dict(row) for row in db.execute('SELECT id,title,cue_count,updated FROM subtitle_library WHERE published=1 AND instr(haysub_fold(title),haysub_fold(?))>0 ORDER BY title,id LIMIT 50 OFFSET ?', (query, offset))]


def library_item(identity):
    with connect() as db:
        db.row_factory=sqlite3.Row
        row=db.execute('SELECT * FROM subtitle_library WHERE id=?',(identity,)).fetchone()
        return dict(row) if row else None


def rename_library_item(identity,title):
    with connect() as db:
        return db.execute('UPDATE subtitle_library SET title=?,updated=CURRENT_TIMESTAMP WHERE id=?',(title,identity)).rowcount>0


def delete_library_item(identity):
    with connect() as db:
        db.row_factory = sqlite3.Row
        db.execute('BEGIN IMMEDIATE')
        item = db.execute('SELECT * FROM subtitle_library WHERE id=?', (identity,)).fetchone()
        if not item:
            return False
        job = db.execute('SELECT * FROM file_jobs WHERE id=?', (identity,)).fetchone()
        folder = DB.parent / 'bin' / ('translation-' + uuid4().hex)
        folder.mkdir(parents=True)
        # Preserve the complete artifact and job before removing active records.
        from app import local_library
        if not local_library.enabled():
            (folder / 'translation.srt').write_text(item['srt'], encoding='utf-8-sig')
        (folder / 'metadata.json').write_text(json.dumps({'translation': dict(item), 'job': dict(job) if job else None}, ensure_ascii=False, indent=2), encoding='utf-8')
        deleted = db.execute('DELETE FROM subtitle_library WHERE id=?', (identity,)).rowcount > 0
        if deleted:
            # Otherwise startup recovery would recreate the deleted library entry.
            db.execute('DELETE FROM file_jobs WHERE id=?', (identity,))
        return deleted


def save_video(job, video, cues, source=None):
    with connect() as db:
        db.execute('INSERT INTO videos(id,video,cues,source) VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET cues=excluded.cues, source=excluded.source', (job, video, json.dumps(cues), source or ('uploaded' if cues else None)))


def history():
    with connect() as db:
        return [dict(id=r[0], video=r[1], created=r[2]) for r in db.execute('SELECT id,video,created FROM videos ORDER BY created DESC LIMIT 20')]


def load_video(job):
    with connect() as db:
        row = db.execute('SELECT video,cues,source FROM videos WHERE id=?', (job,)).fetchone()
        return (row[0], json.loads(row[1]), row[2]) if row else None
