(() => {
  'use strict';
  const $=id=>document.getElementById(id),U=globalThis.HaySubMediaUpload;
  let settings=null,selected=null,controller=null,busy=false,rows=new Map(),refreshing=false,library=[],libraryLoading=false;
  const size=bytes=>(bytes/1024**3).toFixed(2)+' GiB';
  function note(text){$('video-owner-status').textContent=text;}
  async function api(path,options={}){
    const config={...options,cache:'no-store'};
    if(options.body&&!(options.body instanceof FormData)){config.headers={'Content-Type':'application/json'};config.body=JSON.stringify(options.body);}
    const response=await fetch(path,config);const data=await response.json();
    const sync=response.headers?.get('X-HaySub-Catalog-Sync'),syncStatus=$('static-catalog-sync-status');
    if(sync&&syncStatus){
      syncStatus.hidden=false;
      syncStatus.classList.toggle('error',sync==='error');
      syncStatus.textContent=sync==='error'
        ?'Your library change was saved, but the static catalog could not be updated. Check folder permissions; refreshing the library retries the export.'
        :sync==='warning'
          ?'Static catalog updated. Some films were skipped: they need permanent public Cloud links. Commit and push catalog-site to update the live website.'
          :'Static catalog and covers updated locally. Commit and push catalog-site to update the live website.';
    }
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Հարցումը չհաջողվեց։ Եթե մուտքի ժամկետն ավարտվել է, կրկին մուտք գործիր /admin էջում։');return data;
  }
  function element(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
  function button(text,action){const node=element('button',text,'secondary');node.type='button';node.addEventListener('click',async()=>{node.disabled=true;try{await action();}catch(error){note(error.message);}finally{node.disabled=false;}});return node;}
  function closeRowPreview(row){
    const stage=$('watch-player-stage');
    if(stage&&row?.root.contains?.(stage))window.dispatchEvent(new CustomEvent('haysub-close-video'));
  }
  function resetUpload(){
    if(busy||!$('hosted-upload-form'))return;
    selected=null;$('hosted-upload-form').reset();$('hosted-upload-submit').textContent='Վերբեռնել տեսանյութ';
    $('hosted-progress').value=0;$('hosted-progress').hidden=true;$('hosted-progress-label').textContent='';
  }
  function apply(row,item){
    if(Number(item.updated)<Number(row.item.updated))return;
    row.item=item;row.title.textContent=item.title;
    if(!row.posterDirty){
      row.posterPreview.hidden=!item.poster_url;
      if(item.poster_url)row.posterPreview.src=item.poster_url+'?v='+encodeURIComponent(item.updated);
      if(item.poster_url){
        row.posterSave.hidden=true;row.posterSave.dataset.saved='true';
        row.posterStatus.textContent='';
      }
    }
    row.title.href=item.published?item.share_url:item.preview_url;
    const destination=$(item.state==='ready'?'hosted-completed-videos':'hosted-videos');
    if(row.root.parentElement!==destination)destination.append(row.root);
    const phases={uploading:'Վերբեռնվում է',allocating:'Վերբեռնումը նախապատրաստվում է',importing:'Ներմուծվում է',finalizing:'Վերբեռնումն ավարտվում է',processing:'Մշակվում է',error:'Ուշադրություն է պահանջվում'};
    const status=item.state==='ready'?(item.has_subtitles?'':'Առանց ենթագրերի'):(phases[item.state]||item.state);
    if(row.state.textContent!==status)row.state.textContent=status;
    row.state.hidden=!status;
    row.state.setAttribute('data-subtitles',item.state==='ready'?(item.has_subtitles?'ready':'missing'):'pending');
    subtitleControls(row);
    row.error.textContent=item.error||'';
    row.preview.hidden=!item.can_preview;
    row.publish.hidden=item.state!=='ready'||(!item.has_subtitles&&item.source_type!=='cloud');
    row.publish.textContent=item.published?'Հանել հրապարակումից':'Հրապարակել և ստեղծել դիտման հղում';
    row.share.hidden=true;row.share.href=item.share_url||'#';row.share.textContent='';
    row.resume.hidden=item.state!=='uploading'||!$('hosted-upload-form');row.retry.hidden=!['error','deleting'].includes(item.state)||!item.error;
    row.remove.hidden=false;
    row.rename.disabled=['bin','deleting'].includes(item.state);
    row.error.hidden=!row.error.textContent;
  }
  function subtitleControls(row){
    row.subtitleForm.hidden=row.item.state!=='ready'||row.item.has_subtitles;
    row.subtitleSelect.disabled=row.attaching||!library.length;
    row.attach.disabled=row.attaching||!row.subtitleSelect.value||row.item.state!=='ready'||row.item.has_subtitles;
    row.attach.textContent=row.attaching?'Ենթագրերն ավելացվում են…':'Ավելացնել ենթագրեր';
  }
  function subtitleChoices(row){
    const selected=row.subtitleSelect.value;
    row.subtitleSelect.replaceChildren();
    const placeholder=element('option',library.length?'Ընտրիր պահված թարգմանություն':'Դեռ պահված թարգմանություններ չկան');placeholder.value='';row.subtitleSelect.append(placeholder);
    for(const entry of library){const option=element('option',entry.title);option.value=entry.id;row.subtitleSelect.append(option);}
    row.subtitleSelect.value=library.some(entry=>entry.id===selected)?selected:'';
    subtitleControls(row);
  }
  async function refreshLibrary(){
    if(libraryLoading)return;libraryLoading=true;
    try{library=await api('/api/library');for(const row of rows.values())subtitleChoices(row);}
    catch(error){note(error.message);}finally{libraryLoading=false;}
  }
  function card(item){
    const root=element('article',undefined,'hosted-video-card'),heading=element('h3'),title=element('a',undefined,'hosted-video-title'),state=element('p',undefined,'hosted-video-status'),error=element('p',undefined,'notice error');
    heading.append(title);
    const header=element('div',undefined,'hosted-video-header');
    const posterForm=element('form'),posterLabel=element('label',undefined,'poster-picker'),posterInput=element('input');
    posterInput.type='file';posterInput.accept='image/png,image/jpeg,image/webp';posterInput.setAttribute('aria-label','Ընտրել պաստառ');
    const posterIcon=element('span','↑','poster-picker-icon');posterIcon.setAttribute('aria-hidden','true');
    posterLabel.append(posterInput,posterIcon,element('span','Ընտրել պաստառ'));
    const posterSave=element('button','Պահպանել պաստառը','secondary');posterSave.type='submit';posterForm.append(posterLabel,posterSave);
    posterForm.className='hosted-poster-form';
    let editedPoster=null;
    const posterPreview=element('img');posterPreview.className='poster-preview';posterPreview.alt='Պաստառի նախադիտում';posterPreview.hidden=true;posterForm.append(posterPreview);
    const posterStatus=element('p','','poster-save-status');
    posterStatus.setAttribute('role','status');posterStatus.setAttribute('aria-live','polite');posterForm.append(posterStatus);
    function posterNote(text,error=false){posterStatus.textContent=text;posterStatus.classList.toggle('error',error);}
    posterSave.disabled=true;posterSave.hidden=true;
    posterInput.addEventListener('change',async()=>{
      const file=posterInput.files?.[0];posterInput.value='';if(!file)return;
      if(file.size>2*1024*1024){posterNote('Պաստառը պետք է լինի առավելագույնը 2 ՄԲ։',true);return;}
      posterInput.disabled=true;posterSave.disabled=true;
      try{
        const blob=await globalThis.HaySubPosterEditor.edit(file);
        if(blob){
          editedPoster=blob;
          rows.get(item.id).posterDirty=true;
          if(posterPreview.dataset.url)URL.revokeObjectURL(posterPreview.dataset.url);
          posterPreview.dataset.url=URL.createObjectURL(blob);posterPreview.src=posterPreview.dataset.url;posterPreview.hidden=false;
          posterSave.hidden=false;posterSave.dataset.saved='false';posterSave.textContent='Պահպանել պաստառը';posterNote('Նկարը պատրաստ է պահպանման։');
        }
      }catch{posterNote('Չհաջողվեց բացել նկարը։ Ընտրիր PNG, JPEG կամ WebP ֆայլ։',true);}
      finally{posterInput.disabled=false;posterSave.disabled=!editedPoster;}
    });
    posterForm.addEventListener('submit',async event=>{
      event.preventDefault();const file=editedPoster;if(!file||posterSave.disabled)return;
      if(file.size>2*1024*1024){posterNote('Պաստառը պետք է լինի առավելագույնը 2 ՄԲ։',true);return;}
      posterSave.disabled=true;posterInput.disabled=true;posterSave.textContent='Պահպանվում է…';posterNote('Պաստառը պահպանվում է…');
      try{const body=new FormData();body.append('poster',file,'cover.jpg');const saved=await api('/api/owner/media/'+item.id+'/poster',{method:'POST',body});if(editedPoster===file){editedPoster=null;rows.get(item.id).posterDirty=false;}apply(rows.get(item.id),saved);posterSave.hidden=true;posterNote('');}
      catch(error){posterSave.textContent='Կրկին պահպանել';posterNote(error.message,true);}finally{posterInput.disabled=false;posterSave.disabled=!editedPoster;}
    });

    function openInline(event){
      if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
      if(!$('cloud-url-player'))return;
      event.preventDefault();
      const current=rows.get(item.id)?.item;
      if(!current?.can_preview){note('This video is not ready to play yet.');return;}
      window.dispatchEvent(new CustomEvent('haysub-play-video',{detail:{id:current.id,owner:true,anchor:heading}}));
    }
    title.addEventListener('click',openInline);
    state.setAttribute('role','status');state.setAttribute('aria-live','polite');
    const actions=element('div',undefined,'file-translation-actions');
    const form=element('form',undefined,'library-rename');form.hidden=true;
    const input=element('input');input.type='text';input.required=true;input.maxLength=200;input.setAttribute('aria-label','Տեսանյութի վերնագիր');
    const rename=button('Վերանվանել',()=>{input.value=rows.get(item.id).item.title;form.hidden=false;rename.hidden=true;input.focus();});
    const save=element('button','Պահպանել','secondary');save.type='submit';
    function closeRename(){form.hidden=true;rename.hidden=false;rename.focus();}
    const cancel=button('Չեղարկել',closeRename);
    form.append(input,save,cancel);
    form.addEventListener('submit',async event=>{
      event.preventDefault();const value=input.value.trim();
      if(!value){note('Մուտքագրիր տեսանյութի վերնագիրը։');input.focus();return;}
      save.disabled=true;cancel.disabled=true;
      try{
        const saved=await api('/api/owner/media/'+item.id,{method:'PATCH',body:{title:value}});
        apply(rows.get(item.id),saved);closeRename();note('Տեսանյութը վերանվանված է։');
      }catch(error){note(error.message);}finally{save.disabled=false;cancel.disabled=false;}
    });
    const resume=button('Շարունակել վերբեռնումը',async()=>{selected=item.id;$('hosted-title').value=rows.get(item.id).item.title;note('Վերևում ընտրիր նույն սկզբնական տեսանյութը, ապա սեղմիր «Շարունակել ընտրված վերբեռնումը»։');$('hosted-upload-submit').textContent='Շարունակել ընտրված վերբեռնումը';$('hosted-file').focus();});
    const preview=element('a','Մասնավոր նախադիտում','secondary');preview.href=item.preview_url;preview.addEventListener('click',openInline);
    const publish=button('Հրապարակել',async()=>{const current=rows.get(item.id).item;await api('/api/owner/media/'+item.id,{method:'PATCH',body:{published:!current.published}});await refresh();});
    const retry=button('Կրկնել մշակումը / մաքրումը',async()=>{await api('/api/owner/media/'+item.id+'/retry',{method:'POST'});await refresh();});
    const remove=button('Ջնջել տեսանյութը',async()=>{
      const cloud=rows.get(item.id).item.source_type==='cloud',folderBin=!cloud&&settings?.folder_bin;
      const question=cloud?'Remove this Cloud link from the page? The original Cloud files will stay.':folderBin?'Տեղափոխե՞լ տեսանյութը data/bin պանակ։ Վերականգնելու համար ֆայլը հետ տեղափոխիր data/videos՝ առանց անունը փոխելու։':'Ջնջե՞լ այս տեսանյութը կայքից։ Պահված ֆայլերը կմաքրվեն 24 ժամ հետո։';
      if(!window.confirm(question))return;
      await api('/api/owner/media/'+item.id,{method:'DELETE'});
      closeRowPreview(rows.get(item.id));
      rows.get(item.id)?.root.remove();rows.delete(item.id);if(selected===item.id)resetUpload();
      note(cloud?'Cloud link removed. The original files are unchanged.':folderBin?'Տեսանյութը տեղափոխված է data/bin։ Վերականգնելու համար ֆայլը տեղափոխիր data/videos։':'Տեսանյութը ջնջված է կայքից։');await refresh();
    });
    const share=element('a',undefined,'share-video-link');share.target='_blank';share.rel='noopener';
    const subtitleForm=element('form',undefined,'video-subtitle-picker');
    const subtitleSelect=element('select');subtitleSelect.required=true;subtitleSelect.setAttribute('aria-label','Պահված թարգմանություն՝ '+item.title);
    const subtitleLabel=element('label','Քո պահված թարգմանություններից');subtitleLabel.append(subtitleSelect);
    const attach=element('button','Ավելացնել ենթագրեր','secondary');attach.type='submit';
    subtitleForm.append(subtitleLabel,attach);
    subtitleSelect.addEventListener('change',()=>subtitleControls(rows.get(item.id)));
    subtitleForm.addEventListener('submit',async event=>{
      event.preventDefault();const row=rows.get(item.id);
      if(row.attaching||!subtitleSelect.value||row.item.state!=='ready'||row.item.has_subtitles)return;
      row.attaching=true;subtitleControls(row);
      try{
        const body=new FormData();body.append('library_id',subtitleSelect.value);body.append('offset',String(row.item.subtitle_offset||0));
        const saved=await api('/api/owner/media/'+item.id+'/subtitles',{method:'POST',body});
        if(rows.get(item.id)!==row)return;
        apply(row,saved);subtitleSelect.value='';note('Ենթագրերն ավելացված են՝ '+saved.title+'։ Պատրաստ է՝ ենթագրերով։');
      }catch(error){note(error.message);}finally{row.attaching=false;subtitleControls(row);}
    });
    actions.append(preview,publish,resume,retry,remove,rename);
    const headerBody=element('div',undefined,'hosted-video-header-body');
    headerBody.append(heading,state,actions);
    header.append(headerBody,posterForm);
    root.append(header,error,form,share,subtitleForm);$('hosted-videos').append(root);
    const row={root,title,state,error,preview,publish,share,resume,retry,remove,form,rename,subtitleForm,subtitleSelect,attach,attaching:false,posterPreview,posterSave,posterStatus,posterDirty:false,item};rows.set(item.id,row);subtitleChoices(row);apply(row,item);
  }
  async function refresh(){
    if(refreshing)return;refreshing=true;
    try{
      const items=(await api('/api/owner/media')).filter(item=>!['bin','deleting'].includes(item.state)),ids=new Set(items.map(item=>item.id));
      for(const [id,row] of rows)if(!ids.has(id)){closeRowPreview(row);row.root.remove();rows.delete(id);}
      for(const item of items){if(rows.has(item.id))apply(rows.get(item.id),item);else card(item);}
      $('hosted-empty').hidden=!!items.length;
    }catch(error){note(error.message);}finally{refreshing=false;}
  }
  $('hosted-upload-form')?.addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;
    const file=$('hosted-file').files[0];if(!file){note('Նախ ընտրիր MP4 ֆայլը։');return;}
    if(!/\.mp4$/i.test(file.name)){note('Ընտրիր MP4 ֆայլ։ Այլ ձևաչափերը պետք է փոխարկել վերբեռնելուց առաջ․ ֆայլի վերանվանումը չի փոխում ձևաչափը։');return;}
    if(!settings?.configured){note(settings?.setup_message||'Նախ կարգավորիր պահոցը։');return;}
    if(file.size>settings.max_bytes){note('Տեսանյութը գերազանցում է սերվերի վերբեռնման սահմանաչափը՝ '+size(settings.max_bytes));return;}
    busy=true;controller=new AbortController();$('hosted-upload-submit').disabled=true;$('hosted-pause').hidden=false;
    try{
      note('Ստուգվում է ֆայլի նմուշը՝ վերբեռնումը հետագայում շարունակելու համար…');
      let item=selected?await api('/api/owner/media/'+selected):await api('/api/owner/media',{method:'POST',body:{title:$('hosted-title').value,size:file.size,fingerprint:await U.fingerprint(file)}});
      selected=item.id;
      const result=await U.upload(file,item,{api,signal:controller.signal,onProgress:(sent,total)=>{$('hosted-progress').hidden=false;$('hosted-progress').max=total;$('hosted-progress').value=sent;$('hosted-progress-label').textContent=`${(sent/total*100).toFixed(1)}% · ${size(sent)} / ${size(total)}`;},onPhase:note});
      note(result.state==='ready'?'Տեսանյութը պատրաստ է։':'Ֆայլը ստացված է։ Այն կավարտվի և կստուգվի ֆոնային մշակման ընթացքում։');
      selected=null;$('hosted-upload-submit').textContent='Վերբեռնել տեսանյութ';$('hosted-file').value='';
    }catch(error){note(error.message+(selected?' Վերբեռնման ընթացքը պահպանված է․ շարունակելու համար ընտրիր նույն ֆայլը։':''));$('hosted-upload-submit').textContent=selected?'Շարունակել ընտրված վերբեռնումը':'Վերբեռնել տեսանյութ';}
    finally{busy=false;controller=null;$('hosted-upload-submit').disabled=false;$('hosted-pause').hidden=true;await refresh();}
  });
  $('hosted-pause')?.addEventListener('click',()=>controller?.abort());
  $('hosted-new')?.addEventListener('click',()=>{if(busy)return;resetUpload();note('Կարող ես վերբեռնել հաջորդ տեսանյութը։ Նախորդները ստորև են։');});
  $('hosted-refresh')?.addEventListener('click',async()=>{await Promise.all([refresh(),refreshLibrary()]);});
  $('hosted-scan-folder')?.addEventListener('click',async()=>{
    try{const result=await api('/api/owner/media/scan-local',{method:'POST'});note(`${result.added} նոր տեսանյութ է գրանցվել։ ${result.waiting} ֆայլ դեռ պատրաստվում է։ `+result.skipped.join(' '));await refresh();}
    catch(error){note(error.message);}
  });
  async function init(){
    try{
      settings=await api('/api/owner/media/config');
      if($('hosted-upload-submit'))$('hosted-upload-submit').disabled=!settings.configured;
      if($('hosted-folder-controls'))$('hosted-folder-controls').hidden=!settings.video_folder;
      await Promise.all([refresh(),refreshLibrary()]);
    }catch(error){note(error.message);}
    setInterval(()=>{if(!document.hidden)void refresh();},5000);
  }
  window.addEventListener('haysub-library-updated',refreshLibrary);
  window.addEventListener('haysub-media-updated',event=>{
    const item=event.detail?.item;
    if(!item){void refresh();return;}
    if(rows.has(item.id))apply(rows.get(item.id),item);else card(item);
    $('hosted-empty').hidden=true;
    rows.get(item.id).root.scrollIntoView({behavior:'smooth',block:'start'});
  });
  window.addEventListener('focus',refreshLibrary);
  void init();
})();
