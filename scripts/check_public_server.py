"""Check the deployed public surface without a password or Gemini request."""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import urlopen

from build_release import validate_origin


def check(base):
    base=validate_origin(base)
    def get(path):
        try:
            with urlopen(base+path,timeout=20) as response:
                return response.status,response.read(3*1024*1024)
        except HTTPError as exc:
            return exc.code,exc.read(10000)
    status,body=get('/healthz')
    assert status==200 and json.loads(body)['status']=='ok','Health check failed'
    status,body=get('/')
    assert status==200 and b'Published translations' in body,'Public homepage is missing'
    for path in ('/privacy','/admin'):
        assert get(path)[0]==200,f'{path} is unavailable'
    for path in ('/api/library','/api/videos','/api/config','/openapi.json'):
        assert get(path)[0]==401,f'Owner endpoint is not protected: {path}'
    status,body=get('/api/public/library')
    assert status==200 and isinstance(json.loads(body),list),'Public catalog failed'
    items=json.loads(body)
    if items:
        status,body=get('/api/public/library/'+items[0]['id']+'/download')
        assert status==200 and b'-->' in body,'Published subtitle download failed'
    print(f'Public checks passed; {len(items)} translations on the first catalog page.')
    if not items:
        print('No films are published yet. Import/publish at least one before sharing.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('server_url')
    args=parser.parse_args()
    try:check(args.server_url)
    except (AssertionError,ValueError) as exc:parser.exit(1,str(exc)+'\n')
