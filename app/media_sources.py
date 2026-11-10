"""R2 playback selection and cloud paths for managed media."""
import html
import os
from pathlib import PurePosixPath
from urllib.parse import quote

R2_BASE_URL='https://25078dcd2784fd951675dbe4476f3d43.r2.cloudflarestorage.com/huysub-data'


def cloud_selected(identity):
    selected = {value.strip() for value in os.getenv('HAYSUB_CLOUD_VIDEO_IDS', '').split(',')}
    return '*' in selected or identity in selected


def hidden_from_lists(identity):
    if identity not in {value.strip() for value in os.getenv('HAYSUB_HIDDEN_VIDEO_IDS', '').split(',')}:return False
    from app import media_db
    item=media_db.get(identity)
    return not (item and item['list_restored'])


def cloud_url(key):
    if not key:return None
    # The uploaded bucket contains data/videos and data/subtitles, not just videos.
    prefix=os.getenv('HAYSUB_CLOUD_PATH_PREFIX','data').strip('/')
    path=str(PurePosixPath(prefix)/PurePosixPath(key)) if prefix else key
    encoded=quote(path,safe='/').replace('--','%2D%2D')
    return os.getenv('HAYSUB_CLOUD_BASE_URL',R2_BASE_URL).rstrip('/')+'/'+encoded


def source_tag(tag,url,source):
    if not url:return tag
    return tag[:-1]+' data-media-source="'+source+'" src="'+html.escape(url,quote=True)+'">'


def source_pair(tag,local_url,remote_url,*,use_cloud=False):
    """Copy every existing tag attribute into the inactive Cloud alternative."""
    if not local_url:return tag
    local=source_tag(tag,local_url,'local')
    if not remote_url:return local
    cloud=source_tag(tag,remote_url,'cloud')
    if use_cloud:return '<!-- '+local+' -->\n'+cloud
    return local+'\n<!-- '+cloud+' -->'
    # To switch later, comment the return above and uncomment this return:
    # return '<!-- '+local+' -->\n'+cloud
