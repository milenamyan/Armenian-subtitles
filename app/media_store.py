"""Private S3 multipart storage plus an explicitly development-only disk adapter."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urlencode, urlsplit
from uuid import uuid4


class StorageError(Exception):
    pass


def integer(name, default, low, high):
    try:value=int(os.getenv(name,str(default)))
    except ValueError:raise StorageError(name+' must be an integer.') from None
    if not low<=value<=high:raise StorageError(name+' is outside its supported range.')
    return value


def upload_limit():
    return integer('HAYSUB_MEDIA_MAX_BYTES',12*1024**3,1024**2,5*1024**4)


def part_size():
    return integer('HAYSUB_MEDIA_PART_BYTES',64*1024**2,5*1024**2,512*1024**2)


def upload_ttl():
    return integer('HAYSUB_UPLOAD_URL_SECONDS',900,60,3600)


def playback_ttl():
    return integer('HAYSUB_PLAYBACK_TTL_SECONDS',14400,60,21600)


def store():
    key_prefix('0'*32)  # Validate the namespace before any upload can be allocated.
    mode=os.getenv('HAYSUB_MEDIA_STORAGE','').lower()
    if mode=='s3':return S3Store()
    if mode=='local':
        if os.getenv('HAYSUB_PUBLIC')=='1':raise StorageError('Local media storage is development-only. Configure private S3 storage for public hosting.')
        return LocalStore()
    raise StorageError('Video storage is not configured. Set HAYSUB_MEDIA_STORAGE=s3 and the S3 endpoint, bucket, region and credentials. See docs/VIDEO_HOSTING.md.')


def key_prefix(identity):
    if not re.fullmatch('[a-f0-9]{32}',identity):raise StorageError('Invalid media identity.')
    prefix=os.getenv('HAYSUB_S3_PREFIX','haysub-media').strip('/')
    if not re.fullmatch('[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*',prefix):raise StorageError('Use a simple dedicated HAYSUB_S3_PREFIX without dots or spaces.')
    return prefix+'/'+identity+'/'


def video_prefix(item):
    # Follow the stored location so renamed film folders share one cleanup scope.
    return item['object_key'].rsplit('/', 1)[0] + '/'


class S3Store:
    def __init__(self):
        bucket=os.getenv('HAYSUB_S3_BUCKET','');region=os.getenv('HAYSUB_S3_REGION','')
        access=os.getenv('HAYSUB_S3_ACCESS_KEY_ID','');secret=os.getenv('HAYSUB_S3_SECRET_ACCESS_KEY','')
        endpoint=os.getenv('HAYSUB_S3_ENDPOINT','')
        if not all((bucket,region,access,secret)):
            raise StorageError('Complete HAYSUB_S3_BUCKET, HAYSUB_S3_REGION, HAYSUB_S3_ACCESS_KEY_ID and HAYSUB_S3_SECRET_ACCESS_KEY on the server.')
        if endpoint:
            parsed=urlsplit(endpoint)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.query or parsed.fragment:
                raise StorageError('HAYSUB_S3_ENDPOINT must be the provider HTTPS API endpoint, not a bucket object URL.')
        try:
            import boto3
            from botocore.config import Config
        except ImportError:
            raise StorageError('Install the project dependencies, including boto3, on both server and worker.') from None
        style=os.getenv('HAYSUB_S3_ADDRESSING_STYLE','path')
        if style not in ('path','virtual','auto'):raise StorageError('S3 addressing style must be path, virtual or auto.')
        if os.getenv('HAYSUB_S3_VERSIONED','0') not in ('0','1'):raise StorageError('HAYSUB_S3_VERSIONED must be 0 or 1, matching the bucket versioning setting.')
        self.bucket=bucket
        try:
            self.client=boto3.client('s3',endpoint_url=endpoint or None,region_name=region,
                aws_access_key_id=access,aws_secret_access_key=secret,
                aws_session_token=os.getenv('HAYSUB_S3_SESSION_TOKEN') or None,
                config=Config(signature_version='s3v4',connect_timeout=10,read_timeout=30,retries={'max_attempts':2},s3={'addressing_style':style},request_checksum_calculation='when_required',response_checksum_validation='when_required'))
        except Exception:raise StorageError('Invalid S3 client configuration. Check endpoint, region, credentials and installed SDK versions.') from None
        self.identity='s3:'+hashlib.sha256(json.dumps([endpoint,bucket,region,os.getenv('HAYSUB_S3_PREFIX','haysub-media')]).encode()).hexdigest()

    def call(self, method, **values):
        try:return getattr(self.client,method)(Bucket=self.bucket,**values)
        except Exception as exc:
            code=getattr(exc,'response',{}).get('Error',{}).get('Code','')
            if code in ('NoSuchKey','404','NotFound'):return None
            if code=='NoSuchUpload':raise StorageError('Multipart upload is no longer available. Start a new upload.') from None
            raise StorageError('Object storage request failed. Check server credentials, bucket permissions, endpoint and network.') from None

    def create(self,key):
        return self.call('create_multipart_upload',Key=key,ContentType='video/mp4')['UploadId']

    def part_url(self,key,upload_id,number,ttl):
        return self.client.generate_presigned_url('upload_part',Params={'Bucket':self.bucket,'Key':key,'UploadId':upload_id,'PartNumber':number},ExpiresIn=ttl,HttpMethod='PUT')

    def list_parts(self,key,upload_id):
        result=[];marker=0
        while True:
            page=self.call('list_parts',Key=key,UploadId=upload_id,PartNumberMarker=marker)
            result.extend({'number':p['PartNumber'],'etag':p['ETag'],'size':p['Size']} for p in page.get('Parts',[]))
            if not page.get('IsTruncated'):return result
            marker=page['NextPartNumberMarker']

    def complete(self,key,upload_id,parts):
        self.call('complete_multipart_upload',Key=key,UploadId=upload_id,MultipartUpload={'Parts':[{'PartNumber':p['number'],'ETag':p['etag']} for p in parts]})

    def head(self,key):
        result=self.call('head_object',Key=key)
        return {'size':result['ContentLength']} if result else None

    def abort(self,key,upload_id):
        try:self.call('abort_multipart_upload',Key=key,UploadId=upload_id)
        except StorageError as exc:
            if 'no longer available' not in str(exc):raise
            return
        # Parts already in flight can outlive the first abort on S3. Verify and
        # retry rather than dropping the metadata while parts remain billable.
        for _ in range(3):
            try:remaining=self.list_parts(key,upload_id)
            except StorageError as exc:
                if 'no longer available' in str(exc):return
                raise
            if not remaining:return
            self.call('abort_multipart_upload',Key=key,UploadId=upload_id)
        raise StorageError('Multipart parts are still being released by storage. Cleanup will retry.')

    def put(self,key,data,content_type):
        self.call('put_object',Key=key,Body=data,ContentType=content_type,CacheControl='private, max-age=0')

    def read_range(self,key,start,count):
        result=self.call('get_object',Key=key,Range=f'bytes={start}-{start+count-1}')
        if not result:raise StorageError('Uploaded object is missing.')
        try:return result['Body'].read(count)
        finally:result['Body'].close()

    def get_url(self,key,ttl,content_type):
        return self.client.generate_presigned_url('get_object',Params={'Bucket':self.bucket,'Key':key,'ResponseContentType':content_type,'ResponseContentDisposition':'inline','ResponseCacheControl':'private, max-age=0'},ExpiresIn=ttl)

    def probe_source(self,key,ttl):return self.get_url(key,ttl,'video/mp4')

    def delete_prefix(self,prefix):
        # Delete versions too, otherwise versioned buckets retain billable private copies.
        while os.getenv('HAYSUB_S3_VERSIONED','0')=='1':
            page=self.call('list_object_versions',Prefix=prefix)
            objects=[{'Key':v['Key'],'VersionId':v['VersionId']} for v in page.get('Versions',[])+page.get('DeleteMarkers',[])]
            if objects:
                result=self.call('delete_objects',Delete={'Objects':objects,'Quiet':True})
                if result.get('Errors'):raise StorageError('Storage did not delete all media objects. Check delete-version permissions and retry cleanup.')
            if not page.get('IsTruncated'):break
            # Restart at the prefix after deleting a batch. A deleted VersionId
            # is not a reliable pagination cursor on every compatible provider.
        # Some S3-compatible stores do not version objects. Also remove current keys.
        while True:
            page=self.call('list_objects_v2',Prefix=prefix,MaxKeys=1000)
            objects=[{'Key':v['Key']} for v in page.get('Contents',[])]
            if not objects:break
            result=self.call('delete_objects',Delete={'Objects':objects,'Quiet':True})
            if result.get('Errors'):raise StorageError('Media deletion is incomplete. Retry cleanup after checking storage permissions.')


class LocalStore:
    def __init__(self):
        self.root=Path(os.getenv('HAYSUB_LOCAL_MEDIA_DIR','data/local-media')).resolve()
        self.secret=os.getenv('HAYSUB_LOCAL_MEDIA_SECRET','')
        if len(self.secret)<32:raise StorageError('Local development requires HAYSUB_LOCAL_MEDIA_SECRET with at least 32 characters.')
        self.root.mkdir(parents=True,exist_ok=True)
        self.identity='local:'+hashlib.sha256((str(self.root)+os.getenv('HAYSUB_S3_PREFIX','haysub-media')).encode()).hexdigest()

    def path(self,key):
        path=(self.root/key).resolve()
        if not path.is_relative_to(self.root) or path==self.root:raise StorageError('Invalid local media path.')
        return path

    def create(self,key):
        identity=uuid4().hex
        folder=self.path('_uploads/'+identity);folder.mkdir(parents=True)
        (folder/'key.json').write_text(json.dumps(key),encoding='utf-8')
        return identity

    def upload_folder(self,key,upload_id):
        if not re.fullmatch('[a-f0-9]{32}',upload_id):raise StorageError('Invalid upload.')
        folder=self.path('_uploads/'+upload_id)
        if not (folder/'key.json').exists() or json.loads((folder/'key.json').read_text())!=key:
            raise StorageError('Multipart upload is no longer available. Start a new upload.')
        return folder

    def signed(self,operation,key,ttl,**values):
        values={'operation':operation,'key':key,'expires':int(time.time())+ttl,**values}
        data=urlencode(values)
        return '/dev-media?'+data+'&signature='+hmac.new(self.secret.encode(),data.encode(),hashlib.sha256).hexdigest()

    def verify(self,values):
        data=dict(values);signature=data.pop('signature','');encoded=urlencode(data)
        try:valid=0<int(data.get('expires','0'))-time.time()<=21600
        except ValueError:valid=False
        if not valid or not hmac.compare_digest(signature,hmac.new(self.secret.encode(),encoded.encode(),hashlib.sha256).hexdigest()):
            raise StorageError('Local media link expired or is invalid.')
        return data

    def part_url(self,key,upload_id,number,ttl):return self.signed('part',key,ttl,upload_id=upload_id,number=number)

    def list_parts(self,key,upload_id):
        folder=self.upload_folder(key,upload_id);result=[]
        for path in sorted(folder.glob('*.part'),key=lambda p:int(p.stem)):
            metadata=path.with_suffix('.etag')
            if not metadata.exists():continue
            etag=metadata.read_text(encoding='ascii')
            result.append({'number':int(path.stem),'etag':etag,'size':path.stat().st_size})
        return result

    def complete(self,key,upload_id,parts):
        folder=self.upload_folder(key,upload_id);target=self.path(key);target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_suffix('.assembling')
        try:
            with temp.open('wb') as destination:
                for part in parts:
                    with (folder/(str(part['number'])+'.part')).open('rb') as source:shutil.copyfileobj(source,destination,1024*1024)
            os.replace(temp,target)
        finally:temp.unlink(missing_ok=True)
        self.abort(key,upload_id)

    def head(self,key):
        path=self.path(key)
        return {'size':path.stat().st_size} if path.is_file() else None

    def abort(self,key,upload_id):
        try:folder=self.upload_folder(key,upload_id)
        except StorageError:return
        self.purge_folder(folder)

    def put(self,key,data,content_type):
        path=self.path(key);path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
        try:temp.write_bytes(data);os.replace(temp,path)
        finally:temp.unlink(missing_ok=True)

    def read_range(self,key,start,count):
        with self.path(key).open('rb') as stream:stream.seek(start);return stream.read(count)

    def get_url(self,key,ttl,content_type):return self.signed('get',key,ttl,content_type=content_type)
    def probe_source(self,key,ttl):return str(self.path(key))

    def delete_prefix(self,prefix):
        folder=self.path(prefix)
        if not folder.exists():return
        self.purge_folder(folder)

    def purge_folder(self,folder):
        source=self.path(str(folder.relative_to(self.root)))
        paths=sorted(source.rglob('*'),key=lambda path:len(path.parts),reverse=True)
        # Check every resolved target before removing anything; never follow a
        # symlink outside the configured media root or touch another directory.
        for path in paths:self.path(str(path.relative_to(self.root)))
        for path in paths:
            if path.is_symlink() or path.is_file():path.unlink()
            elif path.is_dir():path.rmdir()
        source.rmdir()

    def move_to_bin(self,folder):
        source=self.path(str(folder.relative_to(self.root)))
        destination=self.path('bin/'+uuid4().hex+'/'+folder.name)
        destination.parent.mkdir(parents=True,exist_ok=True)
        # Both resolved paths are confined to the configured local storage root.
        source.rename(destination)
