"""Subtitle snapshots and bounded MP4 inspection; no transcoding."""
import html
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile

from app.subtitles import parse_subtitles, without_music_lines
from app.translation import validate_text


class MediaError(Exception):
    pass


def prepared_cues(raw):
    cues=parse_subtitles(raw,allow_empty_cues=True)
    result=[]
    for cue in cues:
        cue={**cue,'source':without_music_lines(cue['source'])}
        if not cue['source']:continue
        validate_text(cue['source'],cue)
        result.append(cue)
    if not result:raise ValueError('No displayable Armenian subtitle cues were found.')
    return result


def webvtt(cues,offset=0):
    """Keep overlaps and durations; an offset affects this video's copy only."""
    if not math.isfinite(offset) or abs(offset)>600:raise ValueError('Subtitle offset must be between -600 and +600 seconds.')
    def timestamp(seconds):
        total=max(0,round(seconds*1000));hours,total=divmod(total,3600000);minutes,total=divmod(total,60000);seconds,ms=divmod(total,1000)
        return f'{hours:02}:{minutes:02}:{seconds:02}.{ms:03}'
    blocks=['WEBVTT']
    for cue in cues:
        start=max(0,cue['start']+offset);end=cue['end']+offset
        if end<=start:continue
        # Entity escaping is required: WebVTT has its own markup, even without HTML overlays.
        text=html.escape(cue['source'],quote=False)
        blocks.append(f'{len(blocks)}\n{timestamp(start)} --> {timestamp(end)}\n{text}')
    if len(blocks)==1:raise ValueError('This offset puts every subtitle before the start of the video.')
    return ('\n\n'.join(blocks)+'\n').encode('utf-8')


def mp4_layout(backend,key,size):
    position=0;brand_ok=False;moov=None;mdat=None
    for _ in range(128):
        if position+8>size:break
        header=backend.read_range(key,position,min(64,size-position))
        if len(header)<8:break
        length,kind=struct.unpack('>I4s',header[:8]);header_size=8
        if length==1:
            if len(header)<16:raise MediaError('The MP4 header is incomplete.')
            length=struct.unpack('>Q',header[8:16])[0];header_size=16
        if length==0:length=size-position
        if length<header_size or position+length>size:raise MediaError('The MP4 container is incomplete or damaged.')
        if kind==b'ftyp':
            payload=backend.read_range(key,position+header_size,min(length-header_size,1024))
            brands=[payload[:4]]+[payload[i:i+4] for i in range(8,len(payload),4)]
            brand_ok=payload[:4]!=b'qt  ' and bool(set(brands)&{b'isom',b'iso2',b'iso5',b'iso6',b'mp41',b'mp42',b'avc1',b'M4V '})
        if kind==b'moov':moov=position
        if kind==b'mdat' and mdat is None:mdat=position
        position+=length
    if not brand_ok or moov is None or mdat is None:
        raise MediaError('Upload a valid MP4 container. Renaming MKV/MOV to .mp4 does not make it compatible.')
    return {'faststart':moov<mdat}


def inspect_media(backend,key,size):
    layout=mp4_layout(backend,key,size)
    timeout=int(os.getenv('HAYSUB_FFPROBE_TIMEOUT_SECONDS','120'))
    if not 10<=timeout<=300:raise MediaError('HAYSUB_FFPROBE_TIMEOUT_SECONDS must be between 10 and 300.')
    memory=int(os.getenv('HAYSUB_FFPROBE_MEMORY_MB','512'))
    if not 128<=memory<=2048:raise MediaError('HAYSUB_FFPROBE_MEMORY_MB must be between 128 and 2048.')
    executable=shutil.which(os.getenv('HAYSUB_FFPROBE','ffprobe'))
    if not executable:raise MediaError('ffprobe is missing on the media worker. Install FFmpeg/ffprobe, then retry inspection.')
    source=backend.probe_source(key,min(900,timeout+120))
    args=[executable,'-v','error','-max_alloc','67108864',
        '-protocol_whitelist','file,http,https,tcp,tls,crypto','-format_whitelist','mov',
        '-rw_timeout','15000000','-probesize','10485760','-analyzeduration','10000000',
        '-enable_drefs','0','-use_absolute_path','0','-threads','1',
        '-show_entries','format=format_name,duration:stream=codec_type,codec_name,profile,pix_fmt,width,height,level,channels,color_transfer',
        '-of','json',source]
    if os.name=='posix':args=[sys.executable,str(Path(__file__).with_name('probe_runner.py'))]+args
    try:
        with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
            subprocess.run(args,stdout=output,stderr=errors,timeout=timeout,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            output.seek(0);raw=output.read(1024*1024+1)
            if len(raw)>1024*1024:raise MediaError('Media inspection returned excessive metadata.')
            info=json.loads(raw)
    except FileNotFoundError:
        raise MediaError('ffprobe is missing on the media worker. Install FFmpeg/ffprobe, then retry inspection.') from None
    except subprocess.TimeoutExpired:
        raise MediaError('Media inspection timed out. Check storage access, file integrity and MP4 layout, then retry.') from None
    except (subprocess.CalledProcessError,ValueError):
        # ffprobe stderr/argv can contain signed storage URLs. Never return/log them.
        raise MediaError('The worker could not inspect this MP4. Check file integrity and storage access. Only H.264/AAC MP4 is supported.') from None
    return validate_probe(info,layout)


def validate_probe(info,layout):
    streams=info.get('streams',[]);videos=[s for s in streams if s.get('codec_type')=='video'];audio=[s for s in streams if s.get('codec_type')=='audio']
    from app import local_library
    if len(videos)!=1 or (len(audio)>1 and not local_library.enabled()):raise MediaError('Use an MP4 with one video stream and at most one audio stream.')
    video=videos[0]
    if video.get('codec_name')!='h264' or video.get('pix_fmt')!='yuv420p' or video.get('profile') not in ('Baseline','Constrained Baseline','Main','High') or video.get('level',999)>42:
        raise MediaError('For this release use H.264 8-bit yuv420p, Baseline/Main/High profile, level 4.2 or lower. HEVC, 10-bit and other codecs are not supported.')
    if video.get('color_transfer') in ('smpte2084','arib-std-b67'):raise MediaError('Use SDR H.264 video; HDR playback is not supported in this release.')
    if any(track.get('codec_name')!='aac' or track.get('profile')!='LC' or track.get('channels',99)>2 for track in audio):
        raise MediaError('Use AAC-LC mono/stereo audio. Other audio formats require conversion before upload.')
    try:duration=float(info['format']['duration'])
    except (KeyError,ValueError,TypeError):raise MediaError('The MP4 has no valid duration.') from None
    if not math.isfinite(duration) or not 0<duration<=86400:raise MediaError('The MP4 duration must be between zero and 24 hours.')
    return {'duration':duration,'video':'h264','audio':'aac-lc' if audio else 'none','width':video.get('width'),'height':video.get('height'),**layout}
