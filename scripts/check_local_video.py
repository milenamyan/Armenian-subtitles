"""Generate an original two-second clip and verify local import/inspection/playback.

Uses an isolated temporary database and media folder; never touches owner videos.
"""
import os
import gc
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def main():
    tools=ROOT/'.tools';tools.mkdir(exist_ok=True)
    from app import main,storage,media_worker,media_db
    from fastapi.testclient import TestClient
    ffmpeg=tools/'ffmpeg'/'ffmpeg.exe';probe=tools/'ffmpeg'/'ffprobe.exe'
    if not ffmpeg.is_file() or not probe.is_file():raise RuntimeError('Install local FFmpeg tools first: python scripts/install_local_ffmpeg.py')
    with tempfile.TemporaryDirectory(prefix='local-video-check-',dir=tools,ignore_cleanup_errors=True) as temp:
        folder=Path(temp).resolve();assert folder.is_relative_to(tools.resolve())
        inbox=folder/'videos';inbox.mkdir()
        sample=inbox/'Original HaySub test.mp4'
        subprocess.run([str(ffmpeg),'-v','error','-f','lavfi','-i','color=c=blue:s=320x240:r=25',
            '-f','lavfi','-i','sine=frequency=440:sample_rate=48000','-t','2','-c:v','libx264',
            '-profile:v','baseline','-level:v','3.0','-pix_fmt','yuv420p','-c:a','aac','-profile:a','aac_low',
            '-ac','1','-movflags','+faststart',str(sample)],check=True,timeout=60,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        os.utime(sample,(time.time()-10,time.time()-10))
        os.environ.update(HAYSUB_PUBLIC='0',HAYSUB_MEDIA_STORAGE='local',HAYSUB_LOCAL_VIDEO_FOLDER=str(inbox),
            HAYSUB_LOCAL_MEDIA_DIR=str(folder/'media'),HAYSUB_FFPROBE=str(probe))
        os.environ.pop('HAYSUB_DB',None);storage.DB=folder/'metadata.sqlite3'
        with TestClient(main.app) as client:
            assert media_worker.run_once()
            items=client.get('/api/owner/media').json();assert len(items)==1
            item=items[0];assert item['state']=='ready',item['error']
            identity=item['id']
            text='1\n00:00:00,100 --> 00:00:01,900\nԲարև աշխարհ\n'
            response=client.post('/api/owner/media/'+identity+'/subtitles',files={'subtitles':('test.srt',text.encode())})
            assert response.status_code==200,response.text
            access=client.get('/api/owner/media/'+identity+'/playback').json()
            assert client.get(access['video_url'],headers={'Range':'bytes=0-31'}).status_code==206
            assert 'Բարև աշխարհ' in client.get(access['subtitle_url']).text
            assert client.patch('/api/owner/media/'+identity,json={'published':True}).status_code==200
            assert client.get('/api/public/hosted/'+identity+'/playback').status_code==200
            client.delete('/api/owner/media/'+identity)
            assert media_worker.run_once() is False
            with media_db.connect() as db:db.execute('UPDATE hosted_videos SET purge_after=? WHERE id=?',(time.time()-1,identity))
            assert media_worker.run_once();assert media_db.get(identity) is None
        gc.collect()
    print('Passed: generated original MP4, folder import, real ffprobe inspection, Armenian WebVTT, range playback, publication and expired-bin cleanup.')


if __name__=='__main__':main()
