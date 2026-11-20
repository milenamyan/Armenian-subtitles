from concurrent.futures import ThreadPoolExecutor

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
