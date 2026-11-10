import json
import subprocess

import pytest
from app import media_formats as formats
from app.media_formats import MediaError

PROBE={'format':{'duration':'60'},'streams':[{'codec_type':'video','codec_name':'h264','profile':'High','level':41,'pix_fmt':'yuv420p','width':1280,'height':720},{'codec_type':'audio','codec_name':'aac','profile':'LC','channels':2}]}


class PrivateSource:
    def probe_source(self,*args):return 'https://storage.test/private.mp4?signature=never-log-this-token'


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.setattr(formats,'mp4_layout',lambda *args:{'faststart':True})
    monkeypatch.setattr(formats.shutil,'which',lambda name:'ffprobe-test-executable')


def test_inspection_uses_bounded_child_safe_protocols_and_metadata_output(probe,monkeypatch):
    def run(args,**options):
        if formats.os.name=='posix':assert 'probe_runner.py' in args[1]
        else:assert args[0]=='ffprobe-test-executable'
        assert args[args.index('-enable_drefs')+1]=='0'
        assert args[args.index('-protocol_whitelist')+1]=='file,http,https,tcp,tls,crypto'
        assert args[args.index('-format_whitelist')+1]=='mov'
        assert options['timeout']==120 and options['check'] is True
        assert options['stdout'] is not subprocess.PIPE and options['stderr'] is not subprocess.PIPE
        options['stdout'].write(json.dumps(PROBE).encode())
    monkeypatch.setattr(formats.subprocess,'run',run)
    result=formats.inspect_media(PrivateSource(),'generated-source.mp4',12345)
    assert result['duration']==60 and result['audio']=='aac-lc'
    assert 'signature' not in json.dumps(result)


@pytest.mark.parametrize('failure',['timeout','process'])
def test_probe_failures_do_not_expose_signed_media_urls(probe,monkeypatch,failure):
    def run(args,**options):
        if failure=='timeout':raise subprocess.TimeoutExpired(args,120,stderr=b'never-log-this-token')
        raise subprocess.CalledProcessError(1,args,stderr=b'never-log-this-token')
    monkeypatch.setattr(formats.subprocess,'run',run)
    with pytest.raises(MediaError) as error:formats.inspect_media(PrivateSource(),'source.mp4',100)
    assert 'never-log-this-token' not in str(error.value) and 'signature=' not in str(error.value)


def test_missing_ffprobe_is_an_actionable_worker_error(probe,monkeypatch):
    monkeypatch.setattr(formats.shutil,'which',lambda name:None)
    with pytest.raises(MediaError,match='ffprobe is missing'):formats.inspect_media(PrivateSource(),'source.mp4',100)
