"""Owner-only direct-upload control plane and authorized direct playback URLs."""
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
from uuid import uuid4
from urllib.parse import urlsplit

from fastapi import APIRouter, Request, HTTPException, File, Form, UploadFile
from fastapi.routing import APIRoute
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app import media_db as db, media_store as stores, public, storage, local_library, media_sources
from app.media_formats import prepared_cues, webvtt, MediaError
from app.media_worker import expected_parts, validated_manifest

class BoundedControlRoute(APIRoute):
    def get_route_handler(self):
        handler=super().get_route_handler()
        async def bounded(request):
            if request.url.path.startswith('/api/owner/media') and request.method in ('POST','PATCH','DELETE'):
                limit=2*1024*1024+65536 if request.url.path.endswith(('/subtitles','/poster')) else 65536
                try:length=int(request.headers.get('content-length','0'))
                except ValueError:raise HTTPException(400,'Invalid request length.') from None
                if length>limit:raise HTTPException(413,'This is a small control/subtitle endpoint. Upload video parts directly to storage.')
                body=bytearray()
                async for chunk in request.stream():
                    if len(body)+len(chunk)>limit:raise HTTPException(413,'Request exceeds the control/subtitle size limit.')
                    body.extend(chunk)
                # Starlette replays its cached body to the JSON/multipart parser.
                # This cache is strictly bounded; video bodies never enter it.
                request._body=bytes(body)
            response = await handler(request)
            # Export after the successful owner operation has committed. Also
            # check on list refresh to pick up folder-worker changes and retry
            # a failed export. Public deployments never write static files.
            if request.url.path.startswith('/api/owner/media') and (
                request.method in ('POST','PATCH','DELETE') or
                request.method=='GET' and request.url.path=='/api/owner/media'
            ) and response.status_code < 400:
                import asyncio
                from app import catalog_sync
                state = await asyncio.to_thread(catalog_sync.sync)
                if state != 'disabled':
                    response.headers['X-HaySub-Catalog-Sync'] = state
            return response
        return bounded


router=APIRouter(route_class=BoundedControlRoute)
STATIC=Path(__file__).resolve().parent.parent/'static'


def item_or_404(identity):
    if not re.fullmatch('[a-f0-9]{32}',identity):raise HTTPException(404,'Video not found.')
    item=db.get(identity)
    if not item:raise HTTPException(404,'Video not found.')
    return item


def backend_for(item=None):
    try:
        backend=stores.store()
        if item and item['backend']!=backend.identity:raise stores.StorageError('Restore this video\'s original storage configuration before continuing.')
        return backend
    except stores.StorageError as exc:raise HTTPException(503,str(exc)) from None


def summary(item):
    manifest=db.parts(item['id']);expected=expected_parts(item)
    return {key:item[key] for key in ('id','title','size','state','published','subtitle_offset','duration','error','created','updated','subtitle_height')}|{
        'part_size':item['part_size'],'part_count':len(expected),'fingerprint':item['fingerprint'],
        'is_new':bool(item['is_new']),
        'uploaded_bytes':sum(expected.get(p['number'],0) for p in manifest),
        'parts':manifest,'has_subtitles':bool(item['subtitle_key'] or item['external_subtitle_url']),
        'source_type':'cloud' if item['external_video_url'] or media_sources.cloud_selected(item['id']) else 'local',
        'share_url':'/watch/'+item['id'] if item['published'] else None,
        'preview_url':'/preview/'+item['id'],
        'poster_url':'/api/owner/media/'+item['id']+'/poster' if item['poster'] else None,
        'can_preview':item['state']=='ready' or (item['state']=='bin' and item['bin_previous_state']=='ready' and bool(item['purge_after'] and item['purge_after']>time.time())),
        'binned_at':item['binned_at'],'purge_after':item['purge_after'],
        'media_info':json.loads(item['media_info']) if item['media_info'] else None}


@router.get('/api/owner/media/config')
def config():
    try:
        backend=stores.store()
        from app.local_videos import folder
        return {'configured':True,'storage':'s3' if isinstance(backend,stores.S3Store) else 'local','max_bytes':stores.upload_limit(),'part_bytes':stores.part_size(),'worker_online':db.worker_online(),'setup_message':'','video_folder':str(folder()) if isinstance(backend,stores.LocalStore) else None,'folder_bin':local_library.enabled(backend)}
    except stores.StorageError as exc:
        return {'configured':False,'setup_message':str(exc)}


def listed_videos():
    items=[item for item in db.all_videos() if not media_sources.hidden_from_lists(item['id'])]
    if os.getenv('HAYSUB_MEDIA_STORAGE')!='local':return items
    backend=stores.store()
    return [item for item in items if not (
        item['backend']==backend.identity and item['state']=='ready'
        and not item['external_video_url']
        and not media_sources.cloud_selected(item['id'])
        and not backend.path(item['object_key']).is_file())]


@router.get('/api/owner/media')
def owner_list():return [summary(item) for item in listed_videos()]


@router.post('/api/owner/media/scan-local')
def scan_local():
    from app.local_videos import scan
    try:return scan()
    except stores.StorageError as exc:raise HTTPException(503,str(exc)) from None


class CloudVideo(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    video_url:str=Field(min_length=1,max_length=8192)
    subtitle_url:str|None=Field(default=None,max_length=8192)
    duration:float|None=Field(default=None,gt=0,le=86400,allow_inf_nan=False)


def external_url(value):
    if not value:return None
    value=value.strip()
    try:
        parsed=urlsplit(value)
        valid=parsed.scheme in ('http','https') and parsed.hostname and not parsed.username and not parsed.password
        parsed.port  # Validate malformed ports without fetching the URL.
    except ValueError:valid=False
    if not valid or any(ord(char)<32 or ord(char)==127 for char in value):
        raise HTTPException(400,'Use a complete HTTP/HTTPS URL without a username or password.')
    return value


@router.post('/api/owner/media/cloud')
def save_cloud_video(body:CloudVideo):
    title=clean_title(body.title);video=external_url(body.video_url);subtitles=external_url(body.subtitle_url)
    if not video:raise HTTPException(400,'Enter a video URL.')
    # A managed film can already play from this exact cloud object. Reuse its
    # metadata, poster and viewing history instead of making a second card.
    for item in db.all_videos():
        if (item['state']=='ready' and not item['external_video_url']
                and media_sources.cloud_selected(item['id'])
                and media_sources.cloud_url(item['object_key'])==video):
            changes=dict(list_restored=1,title=title)
            if body.duration is not None:changes['duration']=body.duration
            if subtitles:changes.update(external_subtitle_url=subtitles,subtitle_offset=0)
            db.update(item['id'],**changes)
            if not item['published'] and (item['subtitle_key'] or item['external_subtitle_url'] or subtitles):
                db.update(item['id'],published=1,published_at=time.time())
            return summary(item_or_404(item['id']))
    now=time.time()
    with db.connect() as connection:
        connection.execute('BEGIN IMMEDIATE')
        existing=connection.execute("SELECT id FROM hosted_videos WHERE external_video_url=? AND state='ready'",(video,)).fetchone()
        if existing:
            identity=existing['id']
            connection.execute("UPDATE hosted_videos SET title=?,external_subtitle_url=?,subtitle_key=NULL,subtitle_cues='[]',subtitle_offset=0,published_at=CASE WHEN published=0 THEN ? ELSE published_at END,published=1,updated=? WHERE id=?",(title,subtitles,now,now,identity))
        else:
            identity=uuid4().hex
            connection.execute("INSERT INTO hosted_videos(id,title,size,fingerprint,backend,object_key,part_size,state,published,external_video_url,external_subtitle_url,created,updated,subtitle_height,is_new) VALUES (?,?,0,?,'external',?,1,'ready',1,?,?,?,?,10,1)",
                               (identity,title,hashlib.sha256(video.encode()).hexdigest(),'external/'+identity,video,subtitles,now,now))
    db.update(identity,list_restored=1)
    if body.duration is not None:db.update(identity,duration=body.duration)
    if not item_or_404(identity)['published_at']:db.update(identity,published_at=now)
    return summary(item_or_404(identity))


@router.get('/api/public/videos')
def public_videos():
    items=[item for item in listed_videos() if item['published'] and item['state']=='ready']
    items.sort(key=lambda item:item['published_at'] or item['created'],reverse=True)
    return [dict(id=item['id'],title=item['title'],watch_url='/watch/'+item['id'],
                 has_subtitles=bool(item['external_subtitle_url'] or item['subtitle_key']),duration=item['duration'],is_new=bool(item['is_new']),
                 published_at=item['published_at'],poster_url='/api/public/hosted/'+item['id']+'/poster' if item['poster'] else None)
            for item in items]


@router.post('/api/owner/media/{identity}/poster')
async def upload_poster(identity:str,poster:UploadFile=File(...)):
    item=item_or_404(identity)
    if item['state'] in ('bin','deleting'):raise HTTPException(409,'Restore this video first.')
    data=await poster.read(2*1024*1024+1)
    if len(data)>2*1024*1024:raise HTTPException(413,'Poster must be at most 2 MB.')
    kind='image/png' if data.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if data.startswith(b'\xff\xd8\xff') else 'image/webp' if data[:4]==b'RIFF' and data[8:12]==b'WEBP' else None
    if not kind:raise HTTPException(400,'Choose a PNG, JPEG or WebP poster.')
    if not db.update(identity,states=['ready','uploading','processing','error'],poster=data,poster_type=kind):raise HTTPException(409,'Video is unavailable.')
    return summary(item_or_404(identity))


@router.get('/api/owner/media/{identity}/poster')
def owner_poster(identity:str):
    return poster_response(item_or_404(identity))


def poster_response(item):
    if not item['poster']:raise HTTPException(404,'Poster not found.')
    return Response(bytes(item['poster']),media_type=item['poster_type'],headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


@router.get('/api/public/hosted/{identity}/poster')
def public_poster(identity:str):
    item=item_or_404(identity)
    if not item['published'] or item['state']!='ready':raise HTTPException(404,'Video is unavailable.')
    return poster_response(item)



class NewVideo(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    size:int=Field(gt=0)
    fingerprint:str=Field(pattern='^[a-f0-9]{64}$')


def clean_title(value):
    value=value.strip()
    if not value or any(ord(c)<32 or ord(c)==127 for c in value):raise HTTPException(400,'Enter a title without blank-only text or control characters.')
    return value


@router.post('/api/owner/media')
def create(body:NewVideo):
    backend=backend_for()
    try:limit=stores.upload_limit();part=stores.part_size()
    except stores.StorageError as exc:raise HTTPException(503,str(exc)) from None
    if body.size>limit:raise HTTPException(413,f'Video exceeds the configured {limit} byte limit.')
    if math.ceil(body.size/part)>10000:raise HTTPException(400,'Increase the configured multipart part size for this file.')
    # Reusing the same browser file should not create another video record.
    for existing in db.all_videos():
        if (existing['backend']==backend.identity and existing['size']==body.size
                and existing['fingerprint']==body.fingerprint
                and existing['state'] not in ('bin','deleting','error')):
            if (local_library.enabled(backend) and existing['state']=='ready'
                    and not backend.path(existing['object_key']).is_file()):
                continue
            return summary(existing)
    identity=uuid4().hex;key=stores.key_prefix(identity)+'source.mp4';now=time.time()
    item=dict(id=identity,title=clean_title(body.title),size=body.size,fingerprint=body.fingerprint,backend=backend.identity,object_key=key,part_size=part,state='allocating',created=now,updated=now)
    db.create(item)
    upload_id=None
    try:
        upload_id=backend.create(key)
        db.update(identity,states=['allocating'],upload_id=upload_id,state='uploading')
    except Exception:
        if upload_id:
            try:backend.abort(key,upload_id)
            except Exception:pass
        db.update(identity,state='deleting',error='Storage could not start this upload. Check configuration. Cleanup is queued.')
        raise HTTPException(503,'Could not start the storage upload. Check bucket credentials and permissions.') from None
    return summary(db.get(identity))


@router.get('/api/owner/media/{identity}')
def status(identity:str):return summary(item_or_404(identity))


@router.get('/api/owner/media/{identity}/resume')
def resume(identity:str):
    item=item_or_404(identity)
    if item['state']!='uploading':return summary(item)
    backend=backend_for(item)
    try:remote={p['number']:p for p in backend.list_parts(item['object_key'],item['upload_id'])}
    except stores.StorageError as exc:raise HTTPException(409,str(exc)) from None
    result=summary(item);expected=expected_parts(item)
    result['parts']=[p for p in result['parts'] if p['number'] in remote and remote[p['number']]['etag']==p['etag'] and remote[p['number']]['size']==expected[p['number']]]
    result['uploaded_bytes']=sum(expected[p['number']] for p in result['parts'])
    return result


class PartNumber(BaseModel):
    number:int=Field(ge=1,le=10000)


@router.post('/api/owner/media/{identity}/part-url')
def part_url(identity:str,body:PartNumber):
    item=item_or_404(identity)
    if item['state']!='uploading':raise HTTPException(409,'This upload is not accepting parts.')
    if body.number not in expected_parts(item):raise HTTPException(400,'Part number is outside the declared video size.')
    backend=backend_for(item)
    try:url=backend.part_url(item['object_key'],item['upload_id'],body.number,stores.upload_ttl())
    except Exception:raise HTTPException(503,'Could not authorize this upload part. Check object storage.') from None
    db.update(identity,states=['uploading'],error='')
    return {'url':url,'expires_in':stores.upload_ttl(),'size':expected_parts(item)[body.number]}


class PartAck(PartNumber):
    etag:str=Field(min_length=1,max_length=200)


@router.post('/api/owner/media/{identity}/ack')
def ack(identity:str,body:PartAck):
    item=item_or_404(identity)
    if body.number not in expected_parts(item) or any(ord(c)<32 or ord(c)>126 for c in body.etag):raise HTTPException(400,'Invalid upload part receipt.')
    if not db.acknowledge(identity,body.number,body.etag):raise HTTPException(409,'This upload is not accepting parts.')
    return {'ok':True}


@router.post('/api/owner/media/{identity}/complete')
def complete(identity:str):
    item=item_or_404(identity)
    if item['state'] in ('finalizing','processing','ready'):return summary(item)
    if item['state']!='uploading':raise HTTPException(409,'Resume or retry this upload before completing.')
    backend=backend_for(item)
    try:validated_manifest(item,backend)
    except (stores.StorageError,MediaError) as exc:raise HTTPException(409,str(exc)) from None
    if not db.update(identity,states=['uploading'],state='finalizing',error=''):raise HTTPException(409,'Video state changed. Refresh its status.')
    return summary(db.get(identity))


class Changes(BaseModel):
    title:str|None=Field(None,min_length=1,max_length=200)
    published:bool|None=None
    is_new:bool|None=Field(None,strict=True)
    subtitle_height:int|None=Field(None,ge=0,le=40,strict=True)


@router.patch('/api/owner/media/{identity}')
def change(identity:str,body:Changes):
    item=item_or_404(identity);values={}
    if body.title is not None:values['title']=clean_title(body.title)
    if body.subtitle_height is not None:values['subtitle_height']=body.subtitle_height
    if body.is_new is not None:values['is_new']=int(body.is_new)
    if body.published is not None:
        if body.published and (item['state']!='ready' or (not item['subtitle_key'] and not item['external_subtitle_url'] and not item['external_video_url'])):raise HTTPException(409,'Wait for successful media inspection and attach Armenian subtitles before publishing.')
        values['published']=int(body.published)
    if values and not db.update(identity,states=['allocating','importing','uploading','finalizing','processing','ready','error'],**values):raise HTTPException(409,'Video is being deleted.')
    return summary(item_or_404(identity))


@router.post('/api/owner/media/{identity}/subtitles')
async def attach(identity:str,library_id:str|None=Form(None),offset:float=Form(0,ge=-600,le=600),subtitles:UploadFile|None=File(None)):
    # Reads are bounded to 2 MB; no video bytes enter this handler.
    item=item_or_404(identity)
    if item['state'] in ('bin','deleting'):raise HTTPException(409,'Restore the video from the bin before changing subtitles.')
    if not math.isfinite(offset):raise HTTPException(400,'Invalid subtitle offset.')
    if library_id and subtitles:raise HTTPException(400,'Choose a library subtitle or a file, not both.')
    uploaded_raw=None
    try:
        if subtitles:
            if not (subtitles.filename or '').lower().endswith(('.srt','.vtt')):raise ValueError('Choose an Armenian SRT or VTT file.')
            uploaded_raw=await subtitles.read(2*1024*1024+1)
            cues=prepared_cues(uploaded_raw)
        elif library_id:
            source=storage.library_item(library_id)
            if not source:raise HTTPException(404,'Library subtitle not found.')
            cues=prepared_cues(source['srt'].encode('utf-8'))
        else:
            cues=json.loads(item['subtitle_cues'])
            if not cues:raise ValueError('Choose an Armenian subtitle from the library or upload a file.')
        data=webvtt(cues,offset)
    except ValueError as exc:raise HTTPException(400,str(exc)) from None
    if item['external_video_url']:
        if not db.update(identity,states=['ready'],external_subtitle_url=None,subtitle_key='attached-library',subtitle_cues=json.dumps(cues,ensure_ascii=False),subtitle_offset=offset):
            raise HTTPException(409,'Video is being removed.')
        return summary(item_or_404(identity))
    # S3 requests run off the event loop, including this small generated text object.
    import asyncio
    backend=backend_for(item);key=stores.video_prefix(item)+'subtitles/'+uuid4().hex+'.vtt'
    if local_library.enabled(backend):
        from app.subtitles import render_srt
        folder=local_library.subtitle_folder(source) if library_id else local_library.root()/'subtitles'/local_library.name(item['title'])
        key=(folder/'armenian.srt').relative_to(backend.root).as_posix()
        data=('\ufeff'+(source['srt'] if library_id else render_srt(cues))).encode('utf-8')
        if uploaded_raw and not list(folder.glob('original.*')):
            local_library.atomic_write(folder/('original'+Path(subtitles.filename).suffix.lower()),uploaded_raw)
    write=db.reserve_track(identity,key)
    if not write:raise HTTPException(409,'Video is being deleted.')
    operation=asyncio.create_task(asyncio.to_thread(backend.put,key,data,'text/vtt; charset=utf-8'))
    # A disconnected browser must not release the lease while the SDK thread
    # still writes an object. Deletion is safe only after that write has ended.
    def finished(task):
        try:task.exception()
        except BaseException:pass
        try:db.release_track(write)
        except Exception:pass  # The durable lease expires if the database is unavailable.
    operation.add_done_callback(finished)
    try:
        try:await asyncio.shield(operation)
        except Exception:raise HTTPException(503,'Could not save the subtitle track to storage. Check permissions and retry.') from None
        if not db.update(identity,states=['allocating','importing','uploading','finalizing','processing','ready','error'],subtitle_key=key,subtitle_cues=json.dumps(cues,ensure_ascii=False),subtitle_offset=offset):
            # Deletion waits for this reservation to finish, then cleans all versions.
            raise HTTPException(409,'Video is being deleted. Subtitle attachment was not applied.')
    finally:
        if operation.done():db.release_track(write)
    return summary(item_or_404(identity))


@router.post('/api/owner/media/{identity}/retry')
def retry(identity:str):
    item=item_or_404(identity);backend_for(item)
    if item['state']=='deleting':db.update(identity,states=['deleting'],error='',lease_until=0 if not item['worker_token'] else item['lease_until'])
    elif item['state']=='error':db.update(identity,states=['error'],state='importing' if item['inbox_path'] else 'finalizing',error='',lease_until=0)
    else:raise HTTPException(409,'Only failed media processing or cleanup can be retried.')
    return summary(item_or_404(identity))


@router.delete('/api/owner/media/{identity}')
def delete(identity:str):
    item=item_or_404(identity)
    if item['external_video_url']:
        with db.connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('DELETE FROM hosted_parts WHERE video_id=?',(identity,))
            connection.execute('DELETE FROM hosted_track_writes WHERE video_id=?',(identity,))
            connection.execute('DELETE FROM hosted_videos WHERE id=? AND external_video_url IS NOT NULL',(identity,))
        return {'ok':True,'state':'deleted','message':'Cloud link removed from the page. The original cloud files are unchanged.'}
    backend=backend_for(item)
    if local_library.enabled(backend) and item['object_key'].startswith('videos/'):
        try:local_library.bin_video(identity,backend)
        except (stores.StorageError,OSError):raise HTTPException(409,'Could not move this video to data/bin. Close any program using the file and try again.') from None
        return {'ok':True,'state':'bin','purge_after':None,'message':'Video moved to data/bin. Move it back to data/videos to restore it.'}
    deadline=db.bin_video(identity)
    if deadline is False:raise HTTPException(409,'Permanent cleanup has already started and cannot be undone.')
    return {'ok':True,'state':'bin','purge_after':deadline,'message':'Video moved to bin for 24 hours. New viewing access is disabled. Restore it before the deadline or the worker will permanently delete its media.'}


@router.post('/api/owner/media/{identity}/restore')
def restore(identity:str):
    item=item_or_404(identity);backend=backend_for(item)
    if local_library.enabled(backend) and item.get('bin_object_key'):
        if not local_library.restore_binned_video(identity,backend,move_file=True):
            raise HTTPException(409,'Move the video from data/bin back to data/videos, keeping its filename, to restore it.')
        return summary(item_or_404(identity))
    if not db.restore_video(identity):raise HTTPException(409,'The video cannot be restored: its 24-hour deadline passed, it is not in the bin, or an existing worker operation must finish first.')
    return summary(item_or_404(identity))


@router.post('/api/owner/media/{identity}/purge')
def purge(identity:str):
    item_or_404(identity)
    if not db.delete_from_bin(identity):raise HTTPException(409,'Only videos in the bin can be permanently deleted.')
    return {'ok':True,'state':'deleting'}


def playback(item,owner=False):
    if item['external_video_url']:
        if item['state']!='ready' or (not owner and not item['published']):raise HTTPException(404,'Video is unavailable.')
        subtitles=item['external_subtitle_url']
        if not subtitles and item['subtitle_key']:
            subtitles=('/api/owner/media/' if owner else '/api/public/hosted/')+item['id']+'/subtitles.vtt'
        return {'id':item['id'],'title':item['title'],'source_type':'cloud','video_url':item['external_video_url'],'subtitle_url':subtitles,
                'cloud_video_url':item['external_video_url'],'cloud_subtitle_url':subtitles,'subtitle_offset':0,'subtitle_height':item['subtitle_height'],'duration':item['duration'],
                'expires_in':14400,'expires_at':int(time.time())+14400,'visibility':'public' if item['published'] else 'owner-preview'}
    backend=backend_for(item)
    playable=item['state']=='ready' or (owner and item['state']=='bin' and item['bin_previous_state']=='ready' and bool(item['purge_after'] and item['purge_after']>time.time()))
    if not playable or (not owner and not (item['subtitle_key'] or item['external_subtitle_url'])):raise HTTPException(409,'Video and Armenian subtitles are not ready yet.')
    try:ttl=stores.playback_ttl()
    except stores.StorageError as exc:raise HTTPException(503,str(exc)) from None
    try:
        video_url=backend.get_url(item['object_key'],ttl,'video/mp4')
        subtitle_url=backend.get_url(item['subtitle_key'],ttl,'text/vtt; charset=utf-8') if item['subtitle_key'] else None
        if subtitle_url and local_library.enabled(backend):
            subtitle_url=('/api/owner/media/' if owner else '/api/public/hosted/')+item['id']+'/subtitles.vtt'
    except Exception:raise HTTPException(503,'Playback storage is unavailable. Please try again later.') from None
    if media_sources.cloud_selected(item['id']):
        video_url=media_sources.cloud_url(item['object_key'])
        subtitle_url=media_sources.cloud_url(item['subtitle_key'])
    if item['external_subtitle_url']:subtitle_url=item['external_subtitle_url']
    return {'id':item['id'],'title':item['title'],'video_url':video_url,'subtitle_url':subtitle_url,
            'source_type':'cloud' if media_sources.cloud_selected(item['id']) else 'local',
            'cloud_video_url':media_sources.cloud_url(item['object_key']),
            'cloud_subtitle_url':item['external_subtitle_url'] or media_sources.cloud_url(item['subtitle_key']),
            'subtitle_offset':item['subtitle_offset'],'subtitle_height':item['subtitle_height'],
            'duration':item['duration'],'expires_in':ttl,'expires_at':int(time.time())+ttl,'visibility':'unlisted' if item['published'] else 'owner-preview'}


@router.get('/api/owner/media/{identity}/playback')
def preview_access(identity:str):return playback(item_or_404(identity),owner=True)


@router.get('/api/owner/media/{identity}/subtitles.vtt')
def local_subtitle_track(identity:str):
    item=item_or_404(identity)
    if item['external_video_url'] and item['subtitle_key'] and item['state']=='ready':
        return Response(webvtt(json.loads(item['subtitle_cues']),item['subtitle_offset']),media_type='text/vtt; charset=utf-8')
    backend=backend_for(item)
    if not local_library.enabled(backend) or not item['subtitle_key'] or item['state']!='ready':
        raise HTTPException(404,'Subtitle track not available.')
    return Response(webvtt(json.loads(item['subtitle_cues']),item['subtitle_offset']),media_type='text/vtt; charset=utf-8',headers={'Cache-Control':'no-store'})


@router.get('/api/public/hosted/{identity}/subtitles.vtt')
def public_cloud_subtitles(identity:str):
    item=item_or_404(identity)
    if not item['published'] or item['state']!='ready' or not item['subtitle_key']:
        raise HTTPException(404,'Subtitle track not available.')
    return Response(webvtt(json.loads(item['subtitle_cues']),item['subtitle_offset']),media_type='text/vtt; charset=utf-8',headers={'Cache-Control':'no-store'})


@router.get('/api/public/hosted/{identity}/playback')
def public_access(identity:str):
    item=item_or_404(identity)
    if not item['published'] or item['state']!='ready':raise HTTPException(404,'This video is unavailable or has not been published.')
    return playback(item)


@router.get('/watch/{identity}')
def watch(identity:str):
    if not re.fullmatch('[a-f0-9]{32}',identity):raise HTTPException(404,'Video not found.')
    item=db.get(identity)
    return watch_page(item,owner=False)


def watch_page(item,owner=False):
    template=(STATIC/'watch.html').read_text(encoding='utf-8')
    if owner:
        template=template.replace('<video id="hosted-player"',(STATIC/'owner-watch-tools.html').read_text(encoding='utf-8')+'<video id="hosted-player"')
        template=template.replace('</video>','</video>'+(STATIC/'owner-subtitle-position.html').read_text(encoding='utf-8')+(STATIC/'owner-watch-controls.html').read_text(encoding='utf-8'))
    # Unavailable/unpublished pages keep their normal client-side error handling.
    if item and (owner or item['published']) and item['state']=='ready':
        try:access=playback(item,owner=owner)
        except HTTPException:return Response(template,media_type='text/html; charset=utf-8',headers={'Cache-Control':'no-store'})
        for tag_id,local_key,cloud_key in (('hosted-source','video_url','cloud_video_url'),('armenian-track','subtitle_url','cloud_subtitle_url')):
            pattern=r'<(?:source|track)\b[^>]*\bid="'+tag_id+r'"[^>]*>'
            use_cloud=media_sources.cloud_selected(item['id'])
            if item['external_video_url']:
                template=re.sub(pattern,lambda match:media_sources.source_tag(match.group(),access[cloud_key],'cloud'),template)
            else:
                template=re.sub(pattern,lambda match:media_sources.source_pair(match.group(),access[local_key],access[cloud_key],use_cloud=use_cloud),template)
    return Response(template,media_type='text/html; charset=utf-8',headers={'Referrer-Policy':'no-referrer','Cache-Control':'no-store'})


@router.get('/preview/{identity}')
def preview(identity:str,request:Request):
    if not public.authenticated(request):return FileResponse(STATIC/'admin-login.html')
    if not re.fullmatch('[a-f0-9]{32}',identity):raise HTTPException(404,'Video not found.')
    return watch_page(db.get(identity),owner=True)


@router.api_route('/dev-media',methods=['GET','HEAD','PUT'])
async def dev_media(request:Request):
    if os.getenv('HAYSUB_PUBLIC')=='1' or os.getenv('HAYSUB_MEDIA_STORAGE')!='local':raise HTTPException(404)
    backend=backend_for()
    try:values=backend.verify(request.query_params)
    except stores.StorageError as exc:raise HTTPException(403,str(exc)) from None
    key=values.get('key','')
    if values.get('operation')=='get' and request.method in ('GET','HEAD'):
        path=backend.path(key)
        if not path.is_file():raise HTTPException(404)
        return FileResponse(path,media_type=values.get('content_type','application/octet-stream'),headers={'Cache-Control':'no-store','Access-Control-Expose-Headers':'Accept-Ranges, Content-Range, ETag'})
    if values.get('operation')!='part' or request.method!='PUT':raise HTTPException(403)
    try:
        identity=key.split('/')[-2];item=item_or_404(identity);number=int(values['number'])
        if item['state']!='uploading' or item['object_key']!=key or item['upload_id']!=values.get('upload_id'):raise HTTPException(409,'Upload is no longer active.')
        expected=expected_parts(item).get(number)
        if expected is None:raise HTTPException(400,'Invalid upload part.')
        folder=backend.upload_folder(key,item['upload_id'])
    except (ValueError,KeyError,stores.StorageError):raise HTTPException(400,'Invalid upload part.') from None
    temporary=folder/(uuid4().hex+'.tmp');target=folder/(str(number)+'.part');digest=hashlib.md5();count=0
    try:
        with temporary.open('wb') as stream:
            async for chunk in request.stream():
                count+=len(chunk)
                if count>expected:raise HTTPException(413,'Upload part is larger than declared.')
                digest.update(chunk);stream.write(chunk)
        if count!=expected:raise HTTPException(400,'Upload part is incomplete.')
        os.replace(temporary,target);etag='"'+digest.hexdigest()+'"'
        target.with_suffix('.etag').write_text(etag,encoding='ascii')
    finally:temporary.unlink(missing_ok=True)
    return Response(status_code=200,headers={'ETag':etag,'Access-Control-Expose-Headers':'ETag'})
