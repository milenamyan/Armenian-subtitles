import asyncio
import json
from types import SimpleNamespace
import pytest
from app import storage, translation


@pytest.fixture(autouse=True)
def generous_test_budget(monkeypatch):
    monkeypatch.setattr('app.rate_limits.limits', lambda model: (1000, 1000, 10000000))


@pytest.mark.parametrize('fail_first_run', [False, True])
def test_repairs_only_invalid_cues_and_preserves_valid_results_across_retry(tmp_path, monkeypatch, fail_first_run):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only')
    monkeypatch.setenv('GEMINI_MODEL','test-model')
    cues=[dict(id=29,start=1,end=2,source='Hello'),dict(id=30,start=2,end=3,source='eo'),dict(id=31,start=3,end=4,source='vita')]
    calls=[]
    identity=translation.cache_key(cues,[],'test-model')
    class Client:
        aio=property(lambda self:self)
        models=property(lambda self:self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def generate_content(self,**kwargs):
            content=json.loads(kwargs['contents']);calls.append(content)
            ids=[c['id'] for c in content['target']]
            if len(calls)==1:
                return SimpleNamespace(text=json.dumps({'cues':[{'id':29,'text':'Բարև'},{'id':30,'text':'eo'},{'id':31,'text':'Կյանք'}]}))
            assert ids==[30]
            assert [c['id'] for c in content['context']]==[29,31]
            assert storage.cached(identity+':partial')=={'29':'Բարև','31':'Կյանք'}
            return SimpleNamespace(text=json.dumps({'cues':[{'id':30,'text':'eo' if fail_first_run and len(calls)<=3 else 'Էո'}]}))
    async def sleep(delay):pass
    monkeypatch.setattr(translation.genai,'Client',lambda **kwargs:Client())
    monkeypatch.setattr(translation.asyncio,'sleep',sleep)
    if fail_first_run:
        with pytest.raises(ValueError,match='cue 30'):
            asyncio.run(translation.translate(cues,[]))
        assert storage.cached(identity) is None
    result=asyncio.run(translation.translate(cues,[]))
    assert result=={'29':'Բարև','30':'Էո','31':'Կյանք'}
    assert list(result)==['29','30','31']
    assert storage.cached(identity)==result
    assert storage.cached(identity+':partial') is None
    assert len(calls)==(4 if fail_first_run else 2)


def test_wrong_ids_never_get_salvaged_or_cached():
    with pytest.raises(ValueError,match='reordered'):
        translation.validate_result({'cues':[{'id':30,'text':'Էո'},{'id':29,'text':'Բարև'}]},[dict(id=29,source='Hello'),dict(id=30,source='eo')])
