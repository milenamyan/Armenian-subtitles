"""Package allowlisted application files, and an HTTPS read-only public extension.

Run without --server-url to prepare the hosting source ZIP first.
Run again with the actual deployed HTTPS origin to build the store ZIP.
"""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import struct
from urllib.parse import urlsplit
from zipfile import ZipFile, ZIP_DEFLATED
import zlib

ROOT = Path(__file__).resolve().parent.parent
EXTENSION_FILES = (
    'manifest.json', 'config.js', 'core.js', 'background.js', 'library-background.js',
    'site-background.js', 'site-controller.js', 'page-access.js', 'content.js',
    'translation-client.js', 'popup.html', 'popup.css', 'popup.js',
)


def validate_origin(value):
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Use the real HTTPS server origin, for example https://your-service.onrender.com (no path).')
    if parsed.hostname in ('localhost', 'example.com') or parsed.hostname.endswith(('.local','.test','.invalid')):
        raise ValueError('A public release needs the actual deployed server, not a placeholder or local address.')
    try:
        if not ipaddress.ip_address(parsed.hostname).is_global:
            raise ValueError('The server must be public.')
    except ValueError as exc:
        if str(exc) == 'The server must be public.':
            raise
    return value.rstrip('/')


def icon(size):
    """Original lavender H glyph on charcoal; PNG built with standard library."""
    def chunk(kind, raw):
        return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            nx,ny=x/size,y/size
            glyph = .23 <= ny <= .77 and (.22 <= nx <= .35 or .65 <= nx <= .78 or .43 <= ny <= .56 and .22 <= nx <= .78)
            inside=.125<=nx<.875 and .125<=ny<.875
            row.extend((184,169,232,255) if glyph else (27,27,34,255) if inside else (0,0,0,0))
        rows.append(row)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')


def prepare_icons():
    folder=ROOT/'extension'/'icons'
    folder.mkdir(exist_ok=True)
    for size in (16,32,48,128):
        (folder/f'icon{size}.png').write_bytes(icon(size))


def server_archive(output):
    files = [p for directory in ('app','static','scripts','docs') for p in (ROOT/directory).rglob('*')
             if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.js','.css','.html','.md','.json')]
    files += [ROOT/name for name in ('Dockerfile','.dockerignore','render.yaml','requirements.txt','requirements.lock.txt','.env.example','.gitignore','README.md','start.py','Start HaySub.bat')]
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path,path.relative_to(ROOT).as_posix())


def extension_archive(base, output):
    base=validate_origin(base)
    prepare_icons()
    manifest=json.loads((ROOT/'extension'/'manifest.json').read_text(encoding='utf-8'))
    manifest['name']='HaySub — Armenian subtitles'
    manifest['description']='Choose prepared Armenian subtitles and display them over supported video players. Local subtitle files are also supported.'
    manifest['host_permissions']=[base+'/*']
    manifest['content_security_policy']['extension_pages']="script-src 'self'; object-src 'none'; connect-src "+base
    config='globalThis.HaySubRelease=Object.freeze('+json.dumps({'apiBase':base,'publicMode':True})+');\n'
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        for name in EXTENSION_FILES:
            raw=(ROOT/'extension'/name).read_bytes()
            if name=='manifest.json':
                raw=json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8')
            elif name=='config.js':
                raw=config.encode('utf-8')
            elif name=='popup.html':
                html=raw.decode('utf-8')
                # Public users get prepared/local files; the owner-only translation UI is removed.
                start=html.index('<section id="translation-controls"')
                end=html.index('</section>',start)+len('</section>')
                # Keep only inert hidden controls used by the shared controller.
                hidden='<section id="translation-controls" hidden><input id="translate-enabled" type="checkbox"><progress id="translation-progress" hidden></progress><button id="translate-youtube" hidden></button><button id="translation-retry" hidden></button><button id="translation-stop" hidden></button></section>'
                html=html[:start]+hidden+html[end:]
                html=html.replace('Ենթագրեր՝ հենց YouTube-ի վրա','Հայերեն ենթագրեր՝ տեսանյութի վրա')
                html=html.replace('Միայն YouTube-ում կարելի է ավտոմատ ստանալ ենթագրերը՝ առանց ֆայլի։','Պատրաստ հայերեն ենթագրերի համար բացիր գրադարանը։')
                # Details describe this read-only release, not the developer backend.
                details=html.index('<details>')
                details_end=html.index('</details>',details)+len('</details>')
                html=html[:details]+'<details><summary>Ինչպես օգտագործել</summary><p class="hint">Ընտրիր գրադարանից ֆիլմի ճիշտ հայերեն թարգմանությունը կամ վերբեռնիր տեղային SRT/VTT։ Առանձին նվագարկիչի համար թույլատրի՛ր ընտրված frame-ի domain-ը։ Կարգավորիր շեղումը, եթե ֆիլմի տարբերակը տարբերվում է։</p></details>'+html[details_end:]
                raw=html.encode('utf-8')
            archive.writestr(name,raw)
        for path in (ROOT/'extension'/'icons').glob('*.png'):
            archive.write(path,'icons/'+path.name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-url',help='Actual deployed HTTPS server origin')
    args=parser.parse_args()
    if args.server_url:
        try: validate_origin(args.server_url)
        except ValueError as exc: parser.error(str(exc))
    folder=ROOT/'dist';folder.mkdir(exist_ok=True)
    prepare_icons()
    source=folder/'haysub-server-source.zip'
    server_archive(source)
    outputs=[source]
    if args.server_url:
        target=folder/'haysub-chrome-store.zip'
        extension_archive(args.server_url,target);outputs.append(target)
    for path in outputs:
        print(path)
        print('SHA256 '+hashlib.sha256(path.read_bytes()).hexdigest())
    if not args.server_url:
        print('Hosting source prepared. No public extension ZIP yet: rerun with --server-url after deployment.')


if __name__=='__main__':
    main()
