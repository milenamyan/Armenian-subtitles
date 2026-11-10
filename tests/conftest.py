import pytest


@pytest.fixture(autouse=True)
def isolate_local_library(monkeypatch):
    # Test runs must never write media into the user's configured real library.
    monkeypatch.delenv('HAYSUB_LOCAL_FLAT_LIBRARY',raising=False)
    monkeypatch.delenv('HAYSUB_LIBRARY_ROOT',raising=False)
