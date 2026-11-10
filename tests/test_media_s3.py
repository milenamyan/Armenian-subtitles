from urllib.parse import urlsplit, parse_qs

import pytest
from botocore.stub import Stubber

from app.media_store import S3Store, StorageError


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv('HAYSUB_S3_BUCKET','private-test-bucket')
    monkeypatch.setenv('HAYSUB_S3_REGION','us-east-1')
    monkeypatch.setenv('HAYSUB_S3_ACCESS_KEY_ID','test-access-not-real')
    monkeypatch.setenv('HAYSUB_S3_SECRET_ACCESS_KEY','test-secret-not-real')
    monkeypatch.setenv('HAYSUB_S3_ENDPOINT','https://storage.test')
    monkeypatch.setenv('HAYSUB_S3_VERSIONED','0')
    return S3Store()


def test_s3_owner_signed_part_and_playback_urls_do_not_include_secret(backend):
    key='haysub-media/'+'a'*32+'/source.mp4'
    url=backend.part_url(key,'multipart-identity',160,900)
    parsed=urlsplit(url);query=parse_qs(parsed.query)
    assert parsed.scheme=='https' and parsed.hostname=='storage.test'
    assert query['partNumber']==['160'] and query['uploadId']==['multipart-identity']
    assert query['X-Amz-Expires']==['900']
    assert 'test-secret-not-real' not in url
    playback=backend.get_url(key,3600,'video/mp4')
    assert parse_qs(urlsplit(playback).query)['response-content-type']==['video/mp4']
    assert 'Range' not in parse_qs(urlsplit(playback).query).get('X-Amz-SignedHeaders',[''])[0]


def test_multipart_create_part_pagination_and_manifest_completion(backend):
    key='haysub-media/video/source.mp4'
    with Stubber(backend.client) as stub:
        stub.add_response('create_multipart_upload',{'UploadId':'upload'}, {'Bucket':backend.bucket,'Key':key,'ContentType':'video/mp4'})
        stub.add_response('list_parts',{'Parts':[{'PartNumber':1,'ETag':'"one"','Size':5*1024**2}],'IsTruncated':True,'NextPartNumberMarker':1}, {'Bucket':backend.bucket,'Key':key,'UploadId':'upload','PartNumberMarker':0})
        stub.add_response('list_parts',{'Parts':[{'PartNumber':2,'ETag':'"two"','Size':123}],'IsTruncated':False}, {'Bucket':backend.bucket,'Key':key,'UploadId':'upload','PartNumberMarker':1})
        stub.add_response('complete_multipart_upload',{}, {'Bucket':backend.bucket,'Key':key,'UploadId':'upload','MultipartUpload':{'Parts':[{'PartNumber':1,'ETag':'"one"'},{'PartNumber':2,'ETag':'"two"'}]}})
        assert backend.create(key)=='upload'
        result=backend.list_parts(key,'upload')
        assert [p['number'] for p in result]==[1,2]
        backend.complete(key,'upload',result)
        stub.assert_no_pending_responses()


def test_unversioned_cleanup_removes_objects_and_handles_missing_upload(backend):
    prefix='haysub-media/video/'
    with Stubber(backend.client) as stub:
        stub.add_client_error('abort_multipart_upload','NoSuchUpload',http_status_code=404,expected_params={'Bucket':backend.bucket,'Key':prefix+'source.mp4','UploadId':'old'})
        stub.add_response('list_objects_v2',{'Contents':[{'Key':prefix+'source.mp4'},{'Key':prefix+'subtitles/one.vtt'}]}, {'Bucket':backend.bucket,'Prefix':prefix,'MaxKeys':1000})
        stub.add_response('delete_objects',{}, {'Bucket':backend.bucket,'Delete':{'Objects':[{'Key':prefix+'source.mp4'},{'Key':prefix+'subtitles/one.vtt'}],'Quiet':True}})
        stub.add_response('list_objects_v2',{}, {'Bucket':backend.bucket,'Prefix':prefix,'MaxKeys':1000})
        backend.abort(prefix+'source.mp4','old');backend.delete_prefix(prefix)
        stub.assert_no_pending_responses()


def test_versioned_cleanup_removes_versions_and_delete_markers(backend,monkeypatch):
    monkeypatch.setenv('HAYSUB_S3_VERSIONED','1');prefix='haysub-media/video/'
    with Stubber(backend.client) as stub:
        stub.add_response('list_object_versions',{'Versions':[{'Key':prefix+'source.mp4','VersionId':'v1'}],'DeleteMarkers':[{'Key':prefix+'source.mp4','VersionId':'delete1'}]}, {'Bucket':backend.bucket,'Prefix':prefix})
        stub.add_response('delete_objects',{}, {'Bucket':backend.bucket,'Delete':{'Objects':[{'Key':prefix+'source.mp4','VersionId':'v1'},{'Key':prefix+'source.mp4','VersionId':'delete1'}],'Quiet':True}})
        stub.add_response('list_objects_v2',{}, {'Bucket':backend.bucket,'Prefix':prefix,'MaxKeys':1000})
        backend.delete_prefix(prefix);stub.assert_no_pending_responses()


def test_successful_abort_is_verified_before_cleanup_is_reported_complete(backend):
    values={'Bucket':backend.bucket,'Key':'haysub-media/video/source.mp4','UploadId':'old'}
    with Stubber(backend.client) as stub:
        stub.add_response('abort_multipart_upload',{},values)
        stub.add_client_error('list_parts','NoSuchUpload',http_status_code=404,expected_params={**values,'PartNumberMarker':0})
        backend.abort(values['Key'],'old');stub.assert_no_pending_responses()


def test_storage_errors_are_sanitized_and_failed_deletes_are_not_reported_as_success(backend):
    prefix='haysub-media/video/'
    with Stubber(backend.client) as stub:
        stub.add_response('list_objects_v2',{'Contents':[{'Key':prefix+'source.mp4'}]}, {'Bucket':backend.bucket,'Prefix':prefix,'MaxKeys':1000})
        stub.add_response('delete_objects',{'Errors':[{'Key':prefix+'source.mp4','Code':'AccessDenied'}]}, {'Bucket':backend.bucket,'Delete':{'Objects':[{'Key':prefix+'source.mp4'}],'Quiet':True}})
        with pytest.raises(StorageError,match='incomplete'):backend.delete_prefix(prefix)
    with Stubber(backend.client) as stub:
        stub.add_client_error('head_object','AccessDenied',service_message='DO-NOT-LEAK-SIGNED-URL',http_status_code=403,expected_params={'Bucket':backend.bucket,'Key':prefix+'source.mp4'})
        with pytest.raises(StorageError) as error:backend.head(prefix+'source.mp4')
        assert 'DO-NOT-LEAK' not in str(error.value)
