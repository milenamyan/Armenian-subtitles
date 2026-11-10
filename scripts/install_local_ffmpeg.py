"""Download project-local Windows FFmpeg tools; verify publisher SHA-256 first."""
import hashlib
from pathlib import Path
import re
import shutil
from urllib.request import urlopen
from urllib.request import Request
from concurrent.futures import ThreadPoolExecutor
import math
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parent.parent
BASE='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'


def main():
    folder=ROOT/'.tools'/'ffmpeg';folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'download.zip'
    with urlopen(BASE+'.sha256',timeout=60) as response:
        expected=re.search(r'\b[a-fA-F0-9]{64}\b',response.read(4096).decode()).group().lower()
    print('Downloading Windows FFmpeg tools...',flush=True)
    with urlopen(Request(BASE,method='HEAD'),timeout=60) as response:total=int(response.headers['Content-Length'])
    prefix=folder/'existing.part'
    if archive.exists():archive.replace(prefix)
    existing=prefix.stat().st_size if prefix.exists() else 0
    part_size=math.ceil((total-existing)/8) if total>existing else 1
    ranges=[(i,start,min(total-1,start+part_size-1)) for i,start in enumerate(range(existing,total,part_size))]
    def fetch(item):
        index,start,end=item;part=folder/f'download-{index}.part'
        have=part.stat().st_size if part.exists() else 0
        if have>end-start+1:raise RuntimeError('Unexpected download segment size.')
        while have<end-start+1:
            first=start+have;last=min(end,first+1024*1024-1)
            with urlopen(Request(BASE,headers={'Range':f'bytes={first}-{last}'}),timeout=90) as response,part.open('ab') as output:
                if response.status!=206 or not response.headers.get('Content-Range','').startswith(f'bytes {first}-{last}/'):
                    raise RuntimeError('Publisher did not honor the bounded download request.')
                data=response.read(last-first+1)
                if len(data)!=last-first+1:raise RuntimeError('A download range is incomplete; rerun to resume.')
                output.write(data);have+=len(data)
        if part.stat().st_size!=end-start+1:raise RuntimeError('An archive segment is incomplete.')
        print(f'Download segment {index+1}/{len(ranges)} complete.',flush=True)
        return part
    with ThreadPoolExecutor(max_workers=8) as pool:parts=list(pool.map(fetch,ranges))
    with archive.open('wb') as output:
        for path in ([prefix] if existing else [])+parts:
            with path.open('rb') as stream:shutil.copyfileobj(stream,output,1024*1024)
    with archive.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256')
    if digest.hexdigest()!=expected:raise RuntimeError('FFmpeg archive checksum does not match the publisher. No binaries extracted.')
    with ZipFile(archive) as source:
        for executable in ('ffmpeg.exe','ffprobe.exe'):
            name=next(n for n in source.namelist() if n.endswith('/bin/'+executable))
            with source.open(name) as stream,(folder/executable).open('wb') as output:shutil.copyfileobj(stream,output,1024*1024)
    archive.unlink()
    for path in folder.glob('*.part'):path.unlink(missing_ok=True)
    print('Verified FFmpeg tools installed in '+str(folder),flush=True)


if __name__=='__main__':main()
