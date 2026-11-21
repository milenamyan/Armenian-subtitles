"""Persistent, shared budgets for all translation jobs and repair attempts."""
import asyncio
import hashlib
import math
import os
import sqlite3
import time

from app import storage


class QuotaBudgetError(RuntimeError):
    pass


def limits(model):
    # Leave headroom below the owner's observed quotas. Unknown models fail safe.
    defaults = (10, 400, 200000) if model == 'gemini-3.1-flash-lite' else (3, 10, 200000)
    return tuple(min(default, max(1, int(os.getenv(name, default)))) for name, default in zip(
        ('GEMINI_SAFE_RPM', 'GEMINI_SAFE_RPD', 'GEMINI_SAFE_TPM'), defaults))


def _budget_schema(db):
    db.execute('CREATE TABLE IF NOT EXISTS gemini_requests (model TEXT, sent REAL, tokens INTEGER)')
    if 'project' not in {row[1] for row in db.execute('PRAGMA table_info(gemini_requests)')}:
        # Existing usage remains in the legacy scope; never discard its budget.
        db.execute("ALTER TABLE gemini_requests ADD COLUMN project TEXT NOT NULL DEFAULT ''")
    db.execute('CREATE TABLE IF NOT EXISTS gemini_key_projects (key_hash TEXT PRIMARY KEY, project TEXT NOT NULL)')
    db.execute('CREATE INDEX IF NOT EXISTS gemini_requests_project_model_sent ON gemini_requests(project,model,sent)')


def register_project(api_key, project):
    """Associate a key with its owner-supplied project without storing the key.

    Keys for the same project share one budget. Unregistered keys retain the
    conservative legacy budget rather than obtaining a fresh budget per key.
    """
    if not api_key or not project or project != project.strip():
        raise ValueError('An API key and its Google Cloud project ID are required.')
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    storage.DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(storage.DB, timeout=10) as db:
        db.execute('BEGIN IMMEDIATE')
        _budget_schema(db)
        existing = db.execute('SELECT project FROM gemini_key_projects WHERE key_hash=?', (key_hash,)).fetchone()
        if existing and existing[0] != project:
            raise ValueError('This key is already registered to a different project.')
        db.execute('INSERT OR IGNORE INTO gemini_key_projects VALUES (?,?)', (key_hash, project))


def reserve(model, tokens, now=None):
    """Atomically reserve a call, or return seconds until minute capacity frees.

    A rolling 24-hour budget is intentionally stricter than a calendar reset.
    Reservations survive failures, cancellation, restarts and concurrent workers.
    """
    now = time.time() if now is None else now
    rpm, rpd, tpm = limits(model)
    if tokens > tpm:
        raise QuotaBudgetError('Subtitle request exceeds the safe token budget. Use a smaller subtitle chunk.')
    storage.DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(storage.DB, timeout=10) as db:
        db.execute('BEGIN IMMEDIATE')
        _budget_schema(db)
        key_hash = hashlib.sha256(os.getenv('GEMINI_API_KEY', '').encode()).hexdigest()
        registered = db.execute('SELECT project FROM gemini_key_projects WHERE key_hash=?', (key_hash,)).fetchone()
        project = registered[0] if registered else ''
        db.execute('DELETE FROM gemini_requests WHERE sent <= ?', (now - 86400,))
        daily = db.execute('SELECT COUNT(*) FROM gemini_requests WHERE model=? AND project=?', (model, project)).fetchone()[0]
        if daily >= rpd:
            # If the configured budget was lowered, multiple reservations must
            # expire before a new call fits. Report the first usable slot.
            sent = db.execute('SELECT sent FROM gemini_requests WHERE model=? AND project=? ORDER BY sent LIMIT 1 OFFSET ?',
                              (model, project, daily - rpd)).fetchone()[0]
            minutes = max(1, math.ceil((sent + 86400 - now) / 60))
            raise QuotaBudgetError(f'App daily Gemini request budget reached ({rpd} requests per rolling 24 hours). '
                                   f'This is the app safety limit, not a token balance. Completed subtitles are saved. '
                                   f'Click Retry translation in about {minutes} minutes; more capacity opens as older requests expire.')
        recent = db.execute('SELECT sent,tokens FROM gemini_requests WHERE model=? AND project=? AND sent>? ORDER BY sent',
                            (model, project, now - 61)).fetchall()
        if len(recent) >= rpm or sum(row[1] for row in recent) + tokens > tpm:
            return max(0.1, recent[0][0] + 61 - now)
        db.execute('INSERT INTO gemini_requests (model,sent,tokens,project) VALUES (?,?,?,?)', (model, now, tokens, project))
    return 0


async def acquire(model, contents, instruction, schema):
    # UTF-8 bytes conservatively overestimate text tokens without another API call.
    tokens = len((contents + instruction + schema).encode('utf-8')) + 4096
    while True:
        delay = reserve(model, tokens)
        if not delay:
            return
        await asyncio.sleep(delay)
