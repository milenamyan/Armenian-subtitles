"""Persistent, shared budgets for all translation jobs and repair attempts."""
import asyncio
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
        db.execute('CREATE TABLE IF NOT EXISTS gemini_requests (model TEXT, sent REAL, tokens INTEGER)')
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM gemini_requests WHERE sent <= ?', (now - 86400,))
        daily = db.execute('SELECT COUNT(*) FROM gemini_requests WHERE model=?', (model,)).fetchone()[0]
        if daily >= rpd:
            raise QuotaBudgetError('Safe daily Gemini budget reached. Translation paused; completed subtitles are saved. Try again later.')
        recent = db.execute('SELECT sent,tokens FROM gemini_requests WHERE model=? AND sent>? ORDER BY sent',
                            (model, now - 61)).fetchall()
        if len(recent) >= rpm or sum(row[1] for row in recent) + tokens > tpm:
            return max(0.1, recent[0][0] + 61 - now)
        db.execute('INSERT INTO gemini_requests VALUES (?,?,?)', (model, now, tokens))
    return 0


async def acquire(model, contents, instruction, schema):
    # UTF-8 bytes conservatively overestimate text tokens without another API call.
    tokens = len((contents + instruction + schema).encode('utf-8')) + 4096
    while True:
        delay = reserve(model, tokens)
        if not delay:
            return
        await asyncio.sleep(delay)
