"""Anonymous, local-only visit timing. No IPs, raw user agents or URLs are saved."""
import math
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import public, storage

router = APIRouter()
RETENTION = 90 * 86400


def local_only():
    if public.public_mode():
        raise HTTPException(404, 'Local analytics only.')


def connect():
    db = storage.connect()
    db.row_factory = __import__('sqlite3').Row
    db.execute('''CREATE TABLE IF NOT EXISTS site_visits (
        id TEXT PRIMARY KEY, started REAL NOT NULL, last_seen REAL NOT NULL,
        active_seconds REAL NOT NULL DEFAULT 0, device TEXT NOT NULL,
        browser TEXT NOT NULL, platform TEXT NOT NULL)''')
    db.execute('CREATE INDEX IF NOT EXISTS visits_started ON site_visits(started DESC)')
    db.execute('CREATE INDEX IF NOT EXISTS visits_last_seen ON site_visits(last_seen)')
    return db


def device_info(agent):
    ua = agent.lower()
    device = 'tablet' if 'ipad' in ua or ('android' in ua and 'mobile' not in ua) else 'phone' if any(s in ua for s in ('iphone', 'android', 'mobile')) else 'desktop'
    browser = next((name for token, name in (
        ('edg', 'Edge'), ('opr/', 'Opera'), ('firefox', 'Firefox'), ('fxios', 'Firefox'),
        ('chrome', 'Chrome'), ('crios', 'Chrome'), ('safari', 'Safari')) if token in ua), 'Other')
    platform = next((name for token, name in (
        ('android', 'Android'), ('iphone', 'iOS'), ('ipad', 'iPadOS'), ('windows', 'Windows'),
        ('macintosh', 'macOS'), ('linux', 'Linux')) if token in ua), 'Other')
    return device, browser, platform


class Visit(BaseModel):
    id: str = Field(pattern=r'^[a-f0-9]{32}$')
    active_seconds: float = Field(ge=0, le=172800, allow_inf_nan=False)


@router.post('/api/visits')
def record_visit(body: Visit, request: Request):
    local_only()
    # Accept only same-origin visitor timing, without enabling cross-site writes.
    origin = request.headers.get('origin')
    if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin != str(request.base_url).rstrip('/')):
        raise HTTPException(403, 'Use this local website.')
    now = time.time()
    device, browser, platform = device_info(request.headers.get('user-agent', '')[:1024])
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        previous = db.execute('SELECT started,active_seconds FROM site_visits WHERE id=?', (body.id,)).fetchone()
        # The first event establishes server time; later reports cannot add more
        # active time than the elapsed visit. MAX makes retries/order harmless.
        seconds = min(body.active_seconds, max(0, now - previous['started']) + 2) if previous else 0
        if not math.isfinite(seconds):
            seconds = 0
        db.execute('''INSERT INTO site_visits VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,
            active_seconds=MAX(site_visits.active_seconds,excluded.active_seconds)''',
            (body.id, now, now, seconds, device, browser, platform))
        db.execute('DELETE FROM site_visits WHERE last_seen<?', (now - RETENTION,))
    return {'ok': True}


@router.get('/api/owner/analytics')
def report(request: Request, days: int = Query(7, ge=1, le=90)):
    local_only()
    if not public.authenticated(request):
        raise HTTPException(401, 'Owner sign-in required.')
    now = time.time()
    with connect() as db:
        cutoff = now - days * 86400
        summary = dict(db.execute('''SELECT COUNT(*) AS visits, COALESCE(SUM(active_seconds),0) AS active_seconds,
            COALESCE(AVG(active_seconds),0) AS average_seconds,
            COALESCE(SUM(last_seen>=?),0) AS recent_visits FROM site_visits WHERE started>=?''',
            (now - 45, cutoff)).fetchone())
        devices = [dict(row) for row in db.execute('SELECT device,COUNT(*) AS visits FROM site_visits WHERE started>=? GROUP BY device', (cutoff,))]
        visits = [dict(row) for row in db.execute('''SELECT started,last_seen,active_seconds,device,browser,platform
            FROM site_visits WHERE started>=? ORDER BY started DESC LIMIT 200''', (cutoff,))]
    return {'summary': summary, 'devices': devices, 'visits': visits, 'days': days}


@router.get('/admin/analytics')
def analytics_page():
    local_only()
    return FileResponse(Path(__file__).resolve().parent.parent / 'static' / 'analytics.html', headers={'Cache-Control': 'no-store'})
