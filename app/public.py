"""Public catalog and owner-only management. Local development stays unchanged."""
import hashlib
import hmac
import os
import re
import secrets
import time
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app import storage
from uuid import uuid4

router = APIRouter()
STATIC = Path(__file__).resolve().parent.parent / 'static'
COOKIE = 'haysub_owner'
attempts = OrderedDict()


def public_mode():
    return os.getenv('HAYSUB_PUBLIC', '0') == '1'


def validate_configuration():
    if public_mode():
        if len(os.getenv('HAYSUB_ADMIN_TOKEN', '')) < 32:
            raise RuntimeError('HAYSUB_PUBLIC=1 requires HAYSUB_ADMIN_TOKEN with at least 32 characters.')
        base = urlsplit(os.getenv('HAYSUB_PUBLIC_URL', ''))
        if base.scheme != 'https' or not base.netloc or base.path not in ('', '/') or base.query or base.fragment or base.username:
            raise RuntimeError('Set HAYSUB_PUBLIC_URL to the HTTPS origin of this service.')


def signature(value):
    return hmac.new(os.getenv('HAYSUB_ADMIN_TOKEN', '').encode(), value.encode(), hashlib.sha256).hexdigest()


def authenticated(request):
    if not public_mode():
        return True
    value = request.cookies.get(COOKIE, '')
    try:
        expiry, nonce, signed = value.split('.')
        return 0 < int(expiry) - time.time() <= 21600 and hmac.compare_digest(signed, signature(expiry+'.'+nonce))
    except (ValueError, TypeError):
        return False


async def access_control(request, call_next):
    response = await controlled_response(request, call_next)
    path = request.url.path
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    if path.startswith(('/api/', '/admin', '/preview/')):
        response.headers['Cache-Control'] = 'no-store'
    if public_mode():
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    return response


async def controlled_response(request, call_next):
    path = request.url.path
    if public_mode():
        # All existing APIs (including jobs, source files and caches) are owner-only.
        public_read = request.method in ('GET', 'HEAD') and (path == '/api/public/config' or path == '/api/public/library' or path.startswith('/api/public/library/'))
        public_read = public_read or (request.method in ('GET','HEAD') and (path=='/api/public/videos' or bool(re.fullmatch(r'/api/public/hosted/[a-f0-9]{32}/(?:playback|subtitles\.vtt|poster)',path))))
        login = path == '/api/admin/login' and request.method == 'POST'
        if path.startswith('/api/') and not public_read and not login and not authenticated(request):
            return JSONResponse({'detail':'Owner sign-in required.'}, status_code=401)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origin = request.headers.get('origin')
            expected = os.getenv('HAYSUB_PUBLIC_URL', '').rstrip('/')
            if origin != expected or request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail':'Use the owner page on this server to make changes.'}, status_code=403)
        if path in ('/docs','/redoc','/openapi.json') and not authenticated(request):
            return JSONResponse({'detail':'Owner sign-in required.'},status_code=401)
    return await call_next(request)


class OwnerLogin(BaseModel):
    token: str = Field(min_length=1, max_length=512)


@router.post('/api/admin/login')
def login(body: OwnerLogin, request: Request):
    if not public_mode():
        return {'ok':True}
    address = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    previous = [t for t in attempts.get(address, []) if now-t < 300]
    if len(previous) >= 10:
        raise HTTPException(429, 'Too many sign-in attempts. Wait five minutes.', headers={'Retry-After':'300'})
    attempts[address] = previous + [now]
    attempts.move_to_end(address)
    while len(attempts) > 1000:
        attempts.popitem(last=False)
    expected = os.getenv('HAYSUB_ADMIN_TOKEN','')
    if not expected or not secrets.compare_digest(body.token.encode(), expected.encode()):
        raise HTTPException(401, 'Incorrect owner password.')
    attempts.pop(address, None)
    value = str(int(time.time())+21600)+'.'+secrets.token_hex(16)
    response = JSONResponse({'ok':True})
    response.set_cookie(COOKIE, value+'.'+signature(value), max_age=21600, httponly=True, secure=True, samesite='strict', path='/')
    return response


@router.post('/api/admin/logout')
def logout():
    response = JSONResponse({'ok':True})
    response.delete_cookie(COOKIE, path='/', secure=True, httponly=True, samesite='strict')
    return response


@router.get('/admin')
def admin(request: Request):
    return FileResponse(STATIC / ('index.html' if authenticated(request) else 'admin-login.html'))


@router.get('/healthz')
def health():
    with storage.connect() as db:
        db.execute('SELECT 1')
    return {'status':'ok'}


@router.get('/privacy')
def privacy():
    return FileResponse(STATIC / 'privacy.html')


class Publish(BaseModel):
    published: bool


@router.patch('/api/library/{identity}/publication')
def publication(identity: str, body: Publish):
    if body.published:
        item = storage.library_item(identity)
        if item and not item['srt'].strip():
            raise HTTPException(409, 'This file has no displayable subtitles to publish.')
    if not storage.publish_library_item(identity, body.published):
        raise HTTPException(404, 'Saved translation not found.')
    return {'id':identity, 'published':body.published}


@router.get('/api/public/library')
def catalog(q: str = Query('', max_length=200), offset: int = Query(0, ge=0, le=100000)):
    return storage.public_library(q.strip(), offset)


@router.get('/api/public/config')
def public_config():
    store = os.getenv('HAYSUB_STORE_URL', '')
    parsed = urlsplit(store)
    if parsed.scheme != 'https' or parsed.hostname != 'chromewebstore.google.com' or parsed.username:
        store = ''
    return {'store_url':store, 'contact_email':os.getenv('HAYSUB_CONTACT_EMAIL','')}


@router.post('/api/library/import')
async def import_translation(subtitles: UploadFile = File(...)):
    from app.subtitles import parse_subtitles, translated_srt, is_music_only
    from app.translation import validate_text
    name = Path((subtitles.filename or '').replace('\\','/')).name
    if not name.lower().endswith(('.srt','.vtt')):
        raise HTTPException(400, 'Choose an Armenian SRT or VTT file.')
    raw = await subtitles.read(2*1024*1024+1)
    if not raw or len(raw) > 2*1024*1024:
        raise HTTPException(400, 'Choose a non-empty file up to 2 MB.')
    try:
        cues = parse_subtitles(raw)
        translated = {}
        for cue in cues:
            text = '' if is_music_only(cue['source']) else cue['source']
            if text:
                validate_text(text, cue)
            translated[str(cue['id'])] = text
        identity = uuid4().hex
        job = dict(file_identity=identity, filename=name[:200], cues=cues, model='imported', prompt_version='prepared-armenian')
        text=translated_srt(cues,translated)
        storage.save_library_translation(job,text)
        from app import local_library
        if local_library.enabled():
            import base64
            local_library.archive(storage.library_item(identity),dict(job,original_base64=base64.b64encode(raw).decode('ascii')),text)
        return {'id':identity,'title':Path(name).stem,'published':False}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from None


@router.get('/api/public/library/{identity}/download')
def public_download(identity: str):
    from app.main import srt_response, library_download_name
    item = storage.library_item(identity)
    if not item or not item['published']:
        raise HTTPException(404, 'Published translation not found.')
    return srt_response(item['srt'], library_download_name(item['title']))


@router.get('/catalog')
def viewer_catalog():
    template=(STATIC/'public.html').read_text(encoding='utf-8')
    def versioned(match):
        name=match.group(1)
        digest=hashlib.sha256((STATIC/name).read_bytes()).hexdigest()[:12]
        return '/static/'+name+'?v='+digest
    template=re.sub(r'/static/([a-zA-Z0-9_.-]+\.(?:js|css))(?:\?[^"\s<>]*)?',versioned,template)
    return Response(template,media_type='text/html',headers={'Cache-Control':'no-store'})
