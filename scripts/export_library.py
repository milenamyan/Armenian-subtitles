"""Export only prepared Armenian files for the owner's move to hosting.

This ZIP is private owner material, not the extension or a package for friends.
No API key, source subtitle cache, database or password is exported.
"""
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app import storage


def export(output):
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    items=storage.list_library()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        manifest=[]
        for item in items:
            saved=storage.library_item(item['id'])
            title=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',item['title']).strip(' .')[:100] or 'HaySub'
            filename=item['id']+'_'+title+'_hy.srt'
            archive.writestr(filename,('\ufeff'+saved['srt']).encode('utf-8'))
            manifest.append({'file':filename,'title':item['title'],'cue_count':item['cue_count']})
        archive.writestr('titles.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        archive.writestr('OWNER-ONLY.txt','Extract the SRT files. Import them at your hosted /admin page using Import Armenian file (no Gemini). Rename from titles.json if needed, then publish chosen files. Do not send this ZIP as the extension.\n')
    return len(items)


if __name__=='__main__':
    target=ROOT/'dist'/'owner-translations.zip'
    print(f'Exported {export(target)} completed Armenian translations to {target}')
