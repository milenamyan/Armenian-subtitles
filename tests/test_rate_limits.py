from concurrent.futures import ThreadPoolExecutor
import sqlite3

import pytest

from app import rate_limits, storage


@pytest.fixture
def budget(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'DB', tmp_path / 'quota.sqlite3')
    monkeypatch.setattr(rate_limits, 'limits', lambda model: (2, 3, 100))


def test_minute_and_token_budgets(budget):
    assert rate_limits.reserve('model', 60, now=100) == 0
    assert rate_limits.reserve('model', 50, now=101) == 60
    assert rate_limits.reserve('model', 40, now=101) == 0
    assert rate_limits.reserve('model', 1, now=102) == 59
    assert rate_limits.reserve('model', 1, now=162) == 0


def test_daily_budget_survives_connections_and_expires(budget):
    for now in (100, 200, 300):
        assert rate_limits.reserve('model', 10, now=now) == 0
    with pytest.raises(rate_limits.QuotaBudgetError, match='daily'):
        rate_limits.reserve('model', 10, now=400)
    assert rate_limits.reserve('other-model', 10, now=400) == 0
    assert rate_limits.reserve('model', 10, now=86501) == 0


def test_concurrent_reservations_cannot_exceed_budget(budget):
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: rate_limits.reserve('model', 10, now=100), range(4)))
    assert results.count(0) == 2


def test_oversized_request_is_blocked(budget):
    with pytest.raises(rate_limits.QuotaBudgetError, match='token'):
        rate_limits.reserve('model', 101, now=100)


def test_daily_message_reports_app_limit_and_first_usable_slot(budget, monkeypatch):
    for now in (100, 200, 300):
        assert rate_limits.reserve('model', 1, now=now) == 0
    monkeypatch.setattr(rate_limits, 'limits', lambda model: (2, 2, 100))
    with pytest.raises(rate_limits.QuotaBudgetError, match=r'App daily.*2 requests.*1439 minutes'):
        rate_limits.reserve('model', 1, now=300)
    # Expiring only the first reservation still leaves the lowered budget full.
    with pytest.raises(rate_limits.QuotaBudgetError):
        rate_limits.reserve('model', 1, now=86501)
    assert rate_limits.reserve('model', 1, now=86601) == 0


def test_new_project_has_separate_budget_and_old_key_keeps_history(budget, monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'old-key')
    for now in (100, 200, 300):
        assert rate_limits.reserve('model', 1, now=now) == 0
    rate_limits.register_project('new-key', 'new-project')
    monkeypatch.setenv('GEMINI_API_KEY', 'new-key')
    assert rate_limits.reserve('model', 1, now=400) == 0
    monkeypatch.setenv('GEMINI_API_KEY', 'old-key')
    with pytest.raises(rate_limits.QuotaBudgetError):
        rate_limits.reserve('model', 1, now=401)
    with sqlite3.connect(storage.DB) as db:
        assert db.execute('SELECT project,COUNT(*) FROM gemini_requests GROUP BY project ORDER BY project').fetchall() == [('', 3), ('new-project', 1)]
        assert db.execute('SELECT key_hash FROM gemini_key_projects').fetchone()[0] != 'new-key'


def test_same_project_keys_share_minute_token_and_daily_budgets(budget, monkeypatch):
    for key in ('first-key', 'second-key'):
        rate_limits.register_project(key, 'same-project')
    monkeypatch.setenv('GEMINI_API_KEY', 'first-key')
    assert rate_limits.reserve('model', 60, now=100) == 0
    monkeypatch.setenv('GEMINI_API_KEY', 'second-key')
    assert rate_limits.reserve('model', 50, now=101) == 60
    assert rate_limits.reserve('model', 40, now=101) == 0
    assert rate_limits.reserve('model', 1, now=102) == 59
    assert rate_limits.reserve('model', 1, now=200) == 0
    monkeypatch.setenv('GEMINI_API_KEY', 'first-key')
    with pytest.raises(rate_limits.QuotaBudgetError):
        rate_limits.reserve('model', 1, now=300)


def test_legacy_database_migration_preserves_usage_and_unknown_keys_fail_safe(budget, monkeypatch):
    with sqlite3.connect(storage.DB) as db:
        db.execute('CREATE TABLE gemini_requests (model TEXT, sent REAL, tokens INTEGER)')
        db.executemany('INSERT INTO gemini_requests VALUES (?,?,?)', [('model', t, 1) for t in (100, 200, 300)])
    rate_limits.register_project('new-key', 'new-project')
    for key in ('old-key', 'unknown-key'):
        monkeypatch.setenv('GEMINI_API_KEY', key)
        with pytest.raises(rate_limits.QuotaBudgetError):
            rate_limits.reserve('model', 1, now=400)
    with pytest.raises(ValueError, match='different project'):
        rate_limits.register_project('new-key', 'wrong-project')
    # Registering the same mapping is safe to repeat and doesn't reset usage.
    rate_limits.register_project('new-key', 'new-project')
    monkeypatch.setenv('GEMINI_API_KEY', 'new-key')
    assert rate_limits.reserve('model', 1, now=400) == 0
