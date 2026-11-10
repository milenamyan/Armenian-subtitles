import asyncio
import json
from types import SimpleNamespace
import pytest
from app import storage, translation


@pytest.mark.parametrize('problem',['missing','duplicate','reordered','malformed'])
def test_bad_batch_ids_fall_back_to_individual_cues_without_accepting_bad_batch(tmp_path,monkeypatch,problem):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only');monkeypatch.setenv('GEMINI_MODEL','test-model')
    cues=[dict(id=i,start=i,end=i+1,source='Hello') for i in range(1165,1168)]
    calls=[]
    key=translation.cache_key(cues,[],'test-model')
    class Client:
        aio=property(lambda self:self);models=property(lambda self:self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def generate_content(self,**kwargs):
            content=json.loads(kwargs['contents']);ids=[c['id'] for c in content['target']];calls.append(ids)
            schema=kwargs['config'].response_json_schema['properties']['cues']
            assert schema['minItems']==schema['maxItems']==len(ids)
            assert schema['items']['properties']['id']['enum']==ids
            assert content['expected_cue_ids']==ids
            if len(calls)==1:
                ids={'missing':[1165],'duplicate':[1165,1165,1167],'reordered':[1167,1166,1165]}.get(problem,[])
                return SimpleNamespace(text='not JSON' if problem=='malformed' else json.dumps({'cues':[{'id':i,'text':'Սխալ պատասխան'} for i in ids]}))
            assert len(ids)==1
            if len(calls)==2:assert storage.cached(key+':partial') is None
            return SimpleNamespace(text=json.dumps({'cues':[{'id':ids[0],'text':'Բարև'}]}))
    async def sleep(delay):pass
    monkeypatch.setattr(translation.genai,'Client',lambda **kwargs:Client());monkeypatch.setattr(translation.asyncio,'sleep',sleep)
    result=asyncio.run(translation.translate(cues,[]))
    assert calls==[[1165,1166,1167],[1165],[1166],[1167]]
    assert list(result)==['1165','1166','1167'] and set(result.values())=={'Բարև'}
    assert storage.cached(key)==result and storage.cached(key+':partial') is None


def test_single_cue_id_failure_is_bounded_and_keeps_completed_cache(tmp_path,monkeypatch):
    monkeypatch.setattr(storage,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setenv('GEMINI_API_KEY','test-only');monkeypatch.setenv('GEMINI_MODEL','test-model')
    cues=[dict(id=1,start=1,end=2,source='Hello'),dict(id=2,start=2,end=3,source='Bye')]
    calls=[]
    class Client:
        aio=property(lambda self:self);models=property(lambda self:self)
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def generate_content(self,**kwargs):
            ids=[c['id'] for c in json.loads(kwargs['contents'])['target']];calls.append(ids)
            if ids==[1]:return SimpleNamespace(text='{"cues":[{"id":1,"text":"Բարև"}]}')
            return SimpleNamespace(text='{"cues":[]}')
    async def sleep(delay):pass
    monkeypatch.setattr(translation.genai,'Client',lambda **kwargs:Client());monkeypatch.setattr(translation.asyncio,'sleep',sleep)
    with pytest.raises(ValueError,match='after three attempts'):
        asyncio.run(translation.translate(cues,[]))
    assert calls==[[1,2],[1],[2],[2]]
    key=translation.cache_key(cues,[],'test-model')
    assert storage.cached(key) is None
    assert storage.cached(key+':partial')=={'1':'Բարև'}
