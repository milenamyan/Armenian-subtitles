import pytest


@pytest.fixture(autouse=True)
def isolate_local_library(monkeypatch):
    # Test runs must never write media into the user's configured real library.
    monkeypatch.delenv('HAYSUB_LOCAL_FLAT_LIBRARY',raising=False)
    monkeypatch.delenv('HAYSUB_LIBRARY_ROOT',raising=False)
    # Developer cloud selection must not redirect test playback to real buckets.
    monkeypatch.delenv('HAYSUB_CLOUD_VIDEO_IDS',raising=False)
    monkeypatch.delenv('HAYSUB_HIDDEN_VIDEO_IDS',raising=False)
    monkeypatch.delenv('HAYSUB_MEDIA_STORAGE',raising=False)
