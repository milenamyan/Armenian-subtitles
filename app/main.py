import asyncio
import base64
import hashlib
import json
import math
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4
from urllib.parse import quote
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app import storage
from app.subtitles import parse_subtitles, video_id, translated_srt, is_music_only, without_music_lines, normalize_timings, render_srt
from app.translation import translate
from app import translation
from app.rate_limits import limits as translation_limits
from app import public
from app import media_api
from app.captions import CaptionError, retrieve_captions

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
jobs = {}
file_jobs = {}
tasks = set()
job_tasks = {}
CHUNK_TIMEOUT = 165


@asynccontextmanager
async def lifespan(app):
    public.validate_configuration()
    if os.getenv('HAYSUB_DB'):
        storage.DB = Path(os.environ['HAYSUB_DB'])
    index_completed_translations()
    from app import catalog_sync
    await asyncio.to_thread(catalog_sync.sync)
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title='HaySub', lifespan=lifespan)
app.middleware('http')(public.access_control)
app.include_router(public.router)
app.include_router(media_api.router)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.get('/')
def index():
    if public.public_mode():return public.viewer_catalog()
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/config')
def config():
    return dict(configured=bool(os.getenv('GEMINI_API_KEY') and os.getenv('GEMINI_MODEL')))


def get_job(identity):
    if identity not in jobs:
        saved = storage.load_video(identity)
        if not saved:
            raise HTTPException(404, 'Video not found.')
        jobs[identity] = new_job(saved[0], saved[1])
        jobs[identity]['caption_source'] = saved[2] or ('uploaded' if saved[1] else None)
    return jobs[identity]


def new_job(video, cues):
    return dict(video=video, cues=cues, translated={}, position=0, error='', running=False,
                phase='ready', caption_source='uploaded' if cues else None, error_code=None,
                active_chunk=None, chunk_started=None)


async def worker(job):
    job['running'] = True
    job['translation_started'] = time.monotonic()
    job['translation_start_completed'] = len(job['translated'])
    job['error'] = ''
    job['phase'] = 'translating'
    try:
        cues = job['cues']
        while True:
            chunks = [cues[i:i + 12] for i in range(0, len(cues), 12)]
            pending = [chunk for chunk in chunks if any(str(cue['id']) not in job['translated'] for cue in chunk)]
            if not pending:
                break
            # Prefer the chunk covering playback, then the closest future chunk.
            position = job['position']
            chunk = min(pending, key=lambda c: (0 if c[0]['start'] <= position < c[-1]['end'] else 1, abs(c[0]['start'] - position)))
            first = chunk[0]['id'] - 1
            context = cues[max(0, first - 3):first] + cues[first + len(chunk):first + len(chunk) + 3]
            job['active_chunk'] = dict(first=chunk[0]['id'], last=chunk[-1]['id'], start=chunk[0]['start'], end=chunk[-1]['end'])
            job['chunk_started'] = time.monotonic()
            try:
                result = await asyncio.wait_for(translate(chunk, context), timeout=CHUNK_TIMEOUT)
            except translation.TemporaryTranslationError:
                delay = 3
                job.update(phase='retrying', retry_at=time.monotonic() + delay)
                if job.get('file_identity'):
                    storage.save_file_job(job)
                await asyncio.sleep(delay)
                job.update(phase='translating', retry_at=None)
                continue
            job['translated'].update(result)
            if job.get('file_identity'):
                storage.save_file_job(job)
    except asyncio.TimeoutError:
        job['error'] = 'Translation took too long and was stopped. Click Retry translation. Completed subtitles are saved.'
        job['error_code'] = 'translation_timeout'
    except Exception as exc:
        job['error'] = str(exc)
    finally:
        job['running'] = False
        job['phase'] = 'cancelled' if job.get('cancelled') else ('error' if job['error'] else 'ready')
        job['active_chunk'] = None
        job['chunk_started'] = None
        job['retry_at'] = None
        if job.get('file_identity'):
            storage.save_file_job(job)
            archive_completed_translation(job)


async def caption_worker(identity, job):
    """Keep blocking yt-dlp off the event loop so status requests stay responsive."""
    try:
        retrieval = asyncio.to_thread(retrieve_captions, job['video'], allow_any_language=True) if job.get('native_captions') else asyncio.to_thread(retrieve_captions, job['video'])
        result = await asyncio.wait_for(retrieval, timeout=90)
        job['cues'] = result['cues']
        job['caption_source'] = result['source']
        job['caption_language'] = result['language']
        storage.save_video(identity, job['video'], job['cues'], result['source'])
        if config()['configured']:
            await worker(job)
        else:
            job['phase'] = 'ready'
    except asyncio.TimeoutError:
        job['error_code'] = 'retrieval_timeout'
        job['error'] = 'Ենթագրերի ստացումը շատ երկար տևեց։ Փորձիր կրկին կամ վերբեռնիր .srt/.vtt ֆայլ։'
        job['phase'] = 'error'
    except CaptionError as exc:
        job['error'], job['error_code'], job['phase'] = str(exc), exc.code, 'error'
    except Exception:
        job['error'] = 'Չհաջողվեց մշակել ենթագրերը։ Փորձիր կրկին կամ վերբեռնիր .srt/.vtt ֆայլ։'
        job['error_code'], job['phase'] = 'retrieval_failed', 'error'
    finally:
        job['running'] = False
        if job.get('cancelled'):
            job['phase'] = 'cancelled'


def track_job_task(job, coroutine):
    task = asyncio.create_task(coroutine)
    tasks.add(task)
    job_tasks[id(job)] = task
    def done(completed):
        tasks.discard(completed)
        if job_tasks.get(id(job)) is completed:
            job_tasks.pop(id(job), None)
    task.add_done_callback(done)


def start_captions(identity, job):
    if not job['running']:
        job.update(running=True, phase='retrieving', error='', error_code=None, cancelled=False)
        track_job_task(job, caption_worker(identity, job))


def start(job):
    if not job['running']:
        job.update(running=True, phase='translating', error='', error_code=None, cancelled=False)
        track_job_task(job, worker(job))


@app.post('/api/videos')
async def create(url: str = Form(...), subtitles: UploadFile | None = File(None), native_captions: bool = Form(False), summary: bool = Form(False)):
    try:
        video = video_id(url)
        cues = []
        if subtitles and subtitles.filename:
            if Path(subtitles.filename).suffix.lower() not in ('.srt', '.vtt'):
                raise ValueError('Only .srt and .vtt files are supported.')
            cues = parse_subtitles(await subtitles.read(2 * 1024 * 1024 + 1), allow_empty_cues=True)
        identity = uuid4().hex
        job = new_job(video, cues)
        job['native_captions'] = native_captions
        jobs[identity] = job
        storage.save_video(identity, video, cues)
        if cues and config()['configured']:
            start(job)
        elif not cues:
            start_captions(identity, job)
        return dict(id=identity, video=video, phase=job['phase'], running=job['running']) if summary else dict(id=identity, **job)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@app.get('/api/videos')
def history():
    return storage.history()


@app.get('/api/videos/{identity}')
def status(identity: str):
    job = get_job(identity)
    elapsed = int(time.monotonic() - job['chunk_started']) if job.get('chunk_started') is not None else 0
    return dict(job, chunk_elapsed_seconds=max(0, elapsed))


class Position(BaseModel):
    seconds: float = Field(ge=0, le=604800)


@app.post('/api/videos/{identity}/position')
def position(identity: str, body: Position):
    get_job(identity)['position'] = body.seconds
    return {'ok': True}


@app.post('/api/videos/{identity}/retry')
async def retry(identity: str, native_captions: bool = Form(False)):
    job = get_job(identity)
    if native_captions:
        job['native_captions'] = True
    if job['cues']:
        start(job)
    else:
        start_captions(identity, job)
    return {'ok': True}


@app.get('/api/videos/{identity}/translated-subtitles')
def translated_video_subtitles(identity: str):
    return compact_subtitles(get_job(identity))


def compact_subtitles(job):
    completed = sum(str(c['id']) in job['translated'] for c in job['cues'])
    cues = [dict(id=c['id'], start=c['start'], end=c['end'], text=without_music_lines(job['translated'][str(c['id'])]))
            for c in job['cues'] if str(c['id']) in job['translated'] and not is_music_only(c['source'])
            and without_music_lines(job['translated'][str(c['id'])])]
    return dict(cues=cues, total=len(job['cues']), completed=completed, running=job['running'],
                error=job['error'], phase=job['phase'], source=job['caption_source'],
                needs_resume=not job['running'] and not job['error'] and not job.get('cancelled') and (not job['cues'] or completed<len(job['cues'])))


@app.post('/api/videos/{identity}/cancel')
async def cancel_video_job(identity: str):
    return await stop_translation_job(get_job(identity))


async def stop_translation_job(job):
    job['cancelled'] = True
    task = job_tasks.get(id(job))
    if task and not task.done():
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    job.update(running=False, phase='cancelled', active_chunk=None, chunk_started=None)
    if job.get('file_identity'):
        storage.save_file_job(job)
    return {'ok': True}


# Standalone file translation uses the same worker, context windows and SQLite
# translation cache as video playback, but requires no YouTube URL or player.
def get_file_job(identity):
    if identity not in file_jobs:
        saved = storage.load_file_job(identity=identity)
        if not saved:
            raise HTTPException(404, 'This older job did not save its source file. Please upload the same file once to restore matching cached translations.')
        prepared = saved['model'] == 'imported' and saved['prompt_version'] == 'prepared-armenian'
        if not prepared and (saved['model'] != os.getenv('GEMINI_MODEL','') or saved['prompt_version'] != translation.PROMPT_VERSION):
            raise HTTPException(409, 'The translation configuration changed. Upload the file again to check compatible cached work safely.')
        restored = restore_file_state(saved)
        if not prepared:
            restore_file_cache(restored)
        if len(restored['translated']) == len(restored['cues']):
            restored.update(error='',phase='ready')
        file_jobs[identity] = restored
        storage.save_file_job(restored)
        archive_completed_translation(restored)
    return file_jobs[identity]


def restore_file_state(saved):
    job = new_job(None,saved['cues'])
    job.update(saved)
    valid = {}
    for cue in job['cues']:
        key = str(cue['id'])
        if is_music_only(cue['source']):
            valid[key] = ''
        elif isinstance(saved.get('translated',{}).get(key),str):
            try:
                translation.validate_text(saved['translated'][key],cue)
                valid[key] = saved['translated'][key]
            except ValueError:
                pass
    job.update(translated=valid,running=False,active_chunk=None,chunk_started=None,restored_cues=len(valid))
    if len(valid) == len(job['cues']):
        job.update(error='',phase='ready')
    elif job.get('phase') == 'cancelled':
        job.update(error='', cancelled=True)
    else:
        job.update(error=job.get('error') or 'Saved progress restored. Click Retry translation to continue.',phase='error')
    return job


def restore_file_cache(job):
    cues=job['cues']
    info=dict(cache_cues=0,compatible_cache_cues=0,silent_cues=0)
    for first in range(0,len(cues),12):
        chunk=cues[first:first+12]
        context=cues[max(0,first-3):first]+cues[first+len(chunk):first+len(chunk)+3]
        restored,counts=translation.restore_cached(chunk,context,job['model'])
        for key,value in restored.items():
            job['translated'].setdefault(key,value)
        for name in info:
            info[name]+=counts[name]
    job.update(info,restored_cues=len(job['translated']))


def file_status(identity, job):
    completed = sum(str(cue['id']) in job['translated'] for cue in job['cues'])
    ready = completed == len(job['cues']) and not job['running'] and not job['error']
    eta = None
    if job['running'] and not job['error'] and completed < len(job['cues']):
        gained = completed - job.get('translation_start_completed', completed)
        if gained > 0 and job.get('translation_started') is not None:
            seconds_per_cue = (time.monotonic() - job['translation_started']) / gained
            # Account for pacing even before a full minute of requests has passed.
            rpm = translation_limits(job.get('model') or os.getenv('GEMINI_MODEL', ''))[0]
            seconds_per_cue = max(seconds_per_cue, 61 / rpm / 12)
            eta = max(1, math.ceil(seconds_per_cue * (len(job['cues']) - completed)))
    return dict(id=identity, filename=job['filename'], total=len(job['cues']),
                completed=completed, running=job['running'], ready=ready, phase=job['phase'],
                error=job['error'], active_chunk=job['active_chunk'],
                retry_after_seconds=max(0, math.ceil(job['retry_at'] - time.monotonic())) if job.get('retry_at') is not None else None,
                estimated_remaining_seconds=eta,
                restored_cues=job.get('restored_cues',0),cache_cues=job.get('cache_cues',0),
                compatible_cache_cues=job.get('compatible_cache_cues',0),silent_cues=job.get('silent_cues',0),
                elapsed=int(time.monotonic() - job['chunk_started']) if job['chunk_started'] is not None else 0,
                download_url=f'/api/subtitle-files/{identity}/download' if ready else None)


def is_armenian_subtitle_file(cues):
    # Inspect dialogue, not filenames, timestamps, music labels or formatting.
    has_armenian = False
    for cue in cues:
        if is_music_only(cue['source']):
            continue
        letters = [char for char in cue['source'] if char.isalpha()]
        if not letters:
            continue
        armenian = sum('\u0531' <= char <= '\u0556' or '\u0561' <= char <= '\u0587' for char in letters)
        if armenian <= len(letters) / 2:
            return False
        has_armenian = True
    return has_armenian


@app.post('/api/subtitle-files')
async def create_file_translation(subtitles: UploadFile = File(...)):
    try:
        filename = Path((subtitles.filename or '').replace('\\', '/')).name
        if Path(filename).suffix.lower() not in ('.srt', '.vtt'):
            raise ValueError('Upload an .srt or .vtt subtitle file.')
        original_bytes = await subtitles.read(2 * 1024 * 1024 + 1)
        cues = parse_subtitles(original_bytes, allow_empty_cues=True)
        prepared = is_armenian_subtitle_file(cues)
        model = 'imported' if prepared else os.getenv('GEMINI_MODEL','')
        prompt_version = 'prepared-armenian' if prepared else translation.PROMPT_VERSION
        fingerprint = hashlib.sha256(json.dumps([model,prompt_version,cues],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        saved = storage.load_file_job(fingerprint=fingerprint)
        identity = saved['file_identity'] if saved else uuid4().hex
        if identity in file_jobs and file_jobs[identity]['running']:
            return file_status(identity,file_jobs[identity])
        job = restore_file_state(saved) if saved else new_job(None, cues)
        job.update(model=model,prompt_version=prompt_version,file_identity=identity,file_fingerprint=fingerprint)
        job['filename'] = ''.join(char for char in filename if ord(char) >= 32)[:200]
        job['original_base64'] = base64.b64encode(original_bytes).decode('ascii')
        if prepared:
            job['translated'] = {str(cue['id']): '' if is_music_only(cue['source']) else cue['source'] for cue in cues}
        else:
            restore_file_cache(job)
        complete = len(job['translated']) == len(cues)
        if not complete and not config()['configured']:
            raise ValueError('Set GEMINI_API_KEY and GEMINI_MODEL in .env, then restart the server to translate files.')
        if complete:
            job.update(error='',phase='ready',running=False)
        file_jobs[identity] = job
        storage.save_file_job(job)
        archive_completed_translation(job)
        if not complete:
            start(job)
        return file_status(identity, job)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@app.get('/api/subtitle-files/{identity}')
def file_translation_status(identity: str):
    return file_status(identity, get_file_job(identity))


@app.get('/api/subtitle-files/{identity}/translated-subtitles')
def file_translation_cues(identity: str):
    return compact_subtitles(get_file_job(identity))


@app.post('/api/subtitle-files/{identity}/position')
def file_translation_position(identity: str, body: Position):
    get_file_job(identity)['position'] = body.seconds
    return {'ok': True}


@app.post('/api/subtitle-files/{identity}/cancel')
async def cancel_file_translation(identity: str):
    return await stop_translation_job(get_file_job(identity))


@app.post('/api/subtitle-files/{identity}/retry')
async def retry_file_translation(identity: str):
    job = get_file_job(identity)
    start(job)
    return file_status(identity, job)


@app.delete('/api/subtitle-files/{identity}')
async def remove_file_translation_process(identity: str):
    job = get_file_job(identity)
    await stop_translation_job(job)
    storage.bin_file_job(identity)
    file_jobs.pop(identity, None)
    return {'removed': True}


@app.get('/api/subtitle-files/{identity}/download')
def download_file_translation(identity: str):
    saved=storage.library_item(identity)
    if saved:
        return srt_response(saved['srt'],library_download_name(saved['title']))
    job = get_file_job(identity)
    if not file_status(identity, job)['ready']:
        raise HTTPException(409, 'The Armenian translation is not complete yet. Wait or retry the failed chunk.')
    filename = Path(job['filename']).stem + '_hy.srt'
    text = translated_srt(job['cues'], job['translated'])
    return srt_response(text,filename)


def srt_response(text,filename):
    # Normalize at the download boundary too, covering older/imported library SRTs.
    try:
        if text.strip():
            text = render_srt(normalize_timings(parse_subtitles(text.encode('utf-8'), preserve_text=True)))
    except ValueError as exc:
        raise HTTPException(422, f'Cannot export subtitle timings: {exc}') from None
    return Response(('\ufeff' + text).encode('utf-8'), media_type='application/x-subrip; charset=utf-8',
                    headers={'Content-Disposition': f"attachment; filename=\"haysub_hy.srt\"; filename*=UTF-8''{quote(filename, safe='')}",
                             'Cache-Control': 'no-store'})


def library_download_name(title):
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]','_',title).strip(' .')[:160] or 'haysub'
    name=re.sub(r'\.(srt|vtt)$','',name,flags=re.I)
    return name+'_hy.srt'


def archive_completed_translation(job):
    if not job.get('file_identity') or not job.get('cues') or job.get('error'):
        return False
    if any(str(c['id']) not in job['translated'] for c in job['cues']):
        return False
    try:
        for cue in job['cues']:
            if not is_music_only(cue['source']):
                translation.validate_text(job['translated'][str(cue['id'])],cue)
        text=translated_srt(job['cues'],job['translated'])
    except (ValueError,KeyError,TypeError):
        return False
    storage.save_library_translation(job,text)
    # Keep a normal subtitle file on disk as well as the recoverable database copy.
    item = storage.library_item(job['file_identity'])
    from app import local_library
    if local_library.enabled():
        local_library.archive(item,job,text)
        return True
    folder_name = Path(library_download_name(item['title'])).stem
    if any(other['id'] != item['id'] and
           Path(library_download_name(other['title'])).stem.casefold() == folder_name.casefold()
           for other in storage.list_library()):
        folder_name += '_' + job['file_identity']
    folder = storage.DB.parent / 'translated-subtitles' / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / library_download_name(item['title'])
    temporary = target.with_suffix('.srt.tmp')
    temporary.write_bytes(('\ufeff' + text).encode('utf-8'))
    temporary.replace(target)
    if job.get('original_base64'):
        original_name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', job['filename']).strip(' .')[:200]
        original = folder / ('original_' + (original_name or 'subtitles.srt'))
        original.write_bytes(base64.b64decode(job['original_base64']))
    else:
        # Older jobs kept source cues, but not the exact uploaded bytes.
        original = folder / 'original_recovered.srt'
        original.write_bytes(('\ufeff' + render_srt(job['cues'])).encode('utf-8'))
    return True


def index_completed_translations():
    # Recover older completed persisted jobs; never invent files from hash-only caches.
    for saved in storage.unindexed_file_jobs():
        archive_completed_translation(saved)


@app.get('/api/library')
def translation_library():
    return [dict(item,download_url=f"/api/library/{item['id']}/download") for item in storage.list_library()]


class LibraryRename(BaseModel):
    title: str = Field(min_length=1,max_length=200)


@app.patch('/api/library/{identity}')
def rename_translation(identity: str,body: LibraryRename):
    title=body.title.strip()
    if not title or any(ord(char)<32 or ord(char)==127 for char in title):
        raise HTTPException(400,'Enter a name without blank-only text or control characters.')
    if not storage.rename_library_item(identity,title):
        raise HTTPException(404,'Saved translation not found.')
    item=storage.library_item(identity)
    item.pop('srt')
    return dict(item,download_url=f'/api/library/{identity}/download')


@app.get('/api/library/{identity}/download')
def download_saved_translation(identity: str):
    item=storage.library_item(identity)
    if not item:
        raise HTTPException(404,'Saved translation not found.')
    return srt_response(item['srt'],library_download_name(item['title']))


@app.delete('/api/library/{identity}')
async def delete_saved_translation(identity: str):
    if file_jobs.get(identity, {}).get('running'):
        raise HTTPException(409, 'Wait for the translation to finish before deleting it.')
    if not storage.delete_library_item(identity):
        raise HTTPException(404, 'Saved translation not found.')
    file_jobs.pop(identity, None)
    return {'deleted': True}
