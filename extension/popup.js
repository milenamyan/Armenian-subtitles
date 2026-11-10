/* The popup imports files and changes local data. content.js owns video playback UI. */
(() => {
  'use strict';
  const C=globalThis.HaySubCore,$=id=>document.getElementById(id);
  const optionNames=Object.keys(C.defaults);
  const PUBLIC=!!globalThis.HaySubRelease?.publicMode;
  let libraryOffset=0,libraryLoading=false;
  let tabId=null,videoId=null,record=null,busy=false,pending=Promise.resolve(),frameId=0,isSite=false,activeTab=null,siteAccess=null,embeddedFrames=[];
  function status(text,isError=false){$('status').textContent=text;$('status').classList.toggle('error',isError);}
  function labels(){
    $('fontSize-value').textContent=$('fontSize').value+' px';
    $('backgroundOpacity-value').textContent=Math.round(Number($('backgroundOpacity').value)*100)+'%';
    $('verticalPosition-value').textContent=$('verticalPosition').value+'%';
  }
  async function current(){
    if(tabId===null)throw Error('Բացիր YouTube տեսանյութը և նորից բացիր HaySub-ը։');
    let result;
    try{result=await chrome.tabs.sendMessage(tabId,{type:'HAYSUB_STATUS'},{frameId});}
    catch{throw Error('Այս էջում HaySub-ը հասանելի չէ։ Բացիր կամ թարմացրու YouTube-ի էջը և փորձիր կրկին։');}
    if(!result?.videoId || result.navigating)throw Error('Էջը կամ տեսանյութը փոխվել է։ Փակիր և նորից բացիր HaySub-ը։');
    if(videoId && result.videoId!==videoId)throw Error('Տեսանյութը փոխվել է։ Փակիր և կրկին բացիր HaySub-ը՝ ճիշտ ֆայլին կապելու համար։');
    return result;
  }
  async function usage(){
    const all=await chrome.storage.local.get(null);
    const used=await chrome.storage.local.getBytesInUse(null);
    const count=Object.keys(all).filter(key=>key.startsWith(C.FILE_PREFIX)).length;
    $('storage').textContent=`Պահված ֆայլեր՝ ${count} · ${(used/1024/1024).toFixed(2)} ՄԲ / 8 ՄԲ սահմանաչափ`;
  }
  function showFile(){
    $('file-label').textContent=record?.name?`Պահված ֆայլ՝ ${record.name}`:'Այս տեսանյութի համար ֆայլ ընտրված չէ։';
    $('clear-current').disabled=!record||!videoId||busy;
  }
  async function backend(type,extra={}){
    const response=await chrome.runtime.sendMessage({type,videoId,...extra});
    if(!response?.ok)throw Error(response?.error||'Չհաջողվեց միանալ HaySub սերվերին։');
    return response;
  }
  async function refreshTranslation(){
    if(!videoId)return;
    const saved=await chrome.storage.local.get([C.JOB_PREFIX+videoId,C.FILE_PREFIX+videoId]);
    record=saved[C.FILE_PREFIX+videoId]||null;showFile();
    const job=saved[C.JOB_PREFIX+videoId];
    $('translation-progress').hidden=!job;
    $('translation-retry').hidden=!job?.error&&!job?.cancelled;
    $('translation-stop').hidden=!job?.running;
    $('translate-youtube').disabled=busy||!!job?.running;
    if(!job)return;
    $('translation-progress').max=job.total||1;$('translation-progress').value=job.completed||0;
    if(job.error)status(job.error,true);
    else if(job.cancelled)status('Թարգմանությունը դադարեցված է։ Պատրաստ հատվածները պահպանված են։');
    else if(job.phase==='retrieving')status('Ստացվում են YouTube-ի ենթագրերը…');
    else if(job.running)status(`Թարգմանվում է հայերեն՝ ${job.completed||0} / ${job.total||'…'} հատված։`);
    else status(`Հայերեն ենթագրերը պատրաստ են՝ ${job.completed} հատված։`);
  }
  async function beginTranslation(text,name){
    await current();status('Միացվում է հայերեն թարգմանությունը…');
    await backend('HAYSUB_TRANSLATE_START',text!==undefined?{text,name}:{});
    await refreshTranslation();
  }
  async function saveOptions(snapshot,id,delay){
    const values={[C.SETTINGS_KEY]:snapshot};
    if(id)values[C.OFFSET_PREFIX+id]=delay;
    try{await chrome.storage.local.set(values);}
    catch{throw Error('Չհաջողվեց պահպանել կարգավորումները։ Մաքրիր պահված ֆայլերից մի քանիսը։');}
  }
  function queueOptions(){
    labels();
    const snapshot={};
    for(const name of optionNames)snapshot[name]=name==='enabled'?$('enabled').checked:$(name).value;
    const normalized=C.settings(snapshot),id=videoId,delay=C.offset($('offset').value);
    const enqueue=()=>{pending=pending.catch(()=>{}).then(()=>saveOptions(normalized,id,delay)).catch(error=>status(error.message,true));};
    // A popup can close before a debounce fires, so persist each actual change.
    enqueue();
  }
  for(const name of [...optionNames,'offset']) {
    $(name).addEventListener('input',labels);
    $(name).addEventListener('change',queueOptions);
  }
  $('file').addEventListener('change',async()=>{
    const file=$('file').files[0];if(!file||busy)return;
    busy=true;$('file').disabled=true;showFile();
    try{
      await current();
      if(!/\.(srt|vtt)$/i.test(file.name))throw Error('Ընտրիր միայն .srt կամ .vtt ֆայլ։');
      if(!file.size || file.size>C.MAX_FILE_BYTES)throw Error('Ֆայլը պետք է լինի ոչ դատարկ և մինչև 2 ՄԲ։');
      status('Ֆայլը ստուգվում է…');
      let text;
      try{text=new TextDecoder('utf-8',{fatal:true}).decode(await file.arrayBuffer());}
      catch{throw Error('Ֆայլը պետք է լինի UTF-8 ձևաչափով։ Վերապահպանիր և փորձիր կրկին։');}
      const parsed=C.parse(text);
      await current(); // Do not associate a file with a new video after SPA navigation.
      if(!PUBLIC&&$('translate-enabled').checked){await beginTranslation(text,file.name);return;}
      await backend('HAYSUB_TRANSLATE_CANCEL',{forget:true});
      const next={version:1,name:file.name.slice(0,200),text,selectionId:'local:'+Date.now()+':'+Math.random(),updatedAt:Date.now()};
      const key=C.FILE_PREFIX+videoId;
      const used=await chrome.storage.local.getBytesInUse(null);
      const old=await chrome.storage.local.getBytesInUse(key);
      if(used-old+C.recordBytes(key,next)>C.SAVE_BUDGET)throw Error('Տեղային հիշողությունը լցվել է։ Մաքրիր պահված ենթագրերը և փորձիր կրկին։ Նախորդ ֆայլը պահպանված է։');
      try{await chrome.storage.local.set({[key]:next});}
      catch{throw Error('Չհաջողվեց պահել ֆայլը․ հիշողության սահմանաչափը կարող է լրացած լինել։ Մաքրիր պահված ֆայլերը և կրկնիր։');}
      record=next;
      status(`Պատրաստ է՝ ${parsed.cues.length} հատված։`+(parsed.ignored?` Բաց է թողնվել ${parsed.ignored} դատարկ կամ զրոյական հատված։`:''));
      await usage();
    }catch(error){status(error.message||'Չհաջողվեց մշակել ֆայլը։',true);}
    finally{busy=false;$('file').disabled=!videoId;$('file').value='';showFile();}
  });
  $('clear-current').addEventListener('click',async()=>{
    try{
      await current();await pending;
      await backend('HAYSUB_TRANSLATE_CANCEL',{forget:true});
      await chrome.storage.local.remove([C.FILE_PREFIX+videoId,C.OFFSET_PREFIX+videoId]);
      record=null;$('offset').value='0';showFile();status('Այս տեսանյութի ենթագրերը մաքրված են։');await usage();
    }catch{status('Չհաջողվեց մաքրել ֆայլը։ Թարմացրու էջը և փորձիր կրկին։',true);}
  });
  $('clear-all').addEventListener('click',async()=>{
    if(busy){status('Սպասիր ֆայլի մշակման ավարտին և փորձիր կրկին։',true);return;}
    try{
      await pending;
      const all=await chrome.storage.local.get(null);
      for(const key of Object.keys(all).filter(k=>k.startsWith(C.JOB_PREFIX))){
        const response=await chrome.runtime.sendMessage({type:'HAYSUB_TRANSLATE_CANCEL',videoId:key.slice(C.JOB_PREFIX.length),forget:true});
        if(!response?.ok)throw Error('cancel failed');
      }
      await chrome.storage.local.remove(C.savedKeys(all));
      record=null;$('offset').value='0';showFile();status('Բոլոր պահված ենթագրերն ու դրանց շեղումները մաքրված են։ Տեսքի կարգավորումները պահպանված են։');await usage();
    }catch{status('Չհաջողվեց մաքրել պահված ֆայլերը։ Փորձիր կրկին։',true);}
  });

  $('translate-enabled').addEventListener('change',async()=>{
    try{await chrome.storage.local.set({[C.TRANSLATE_KEY]:$('translate-enabled').checked});
      if(!$('translate-enabled').checked){await backend('HAYSUB_TRANSLATE_CANCEL');await refreshTranslation();}
    }catch(error){status(error.message,true);}
  });
  $('translate-youtube').addEventListener('click',async()=>{
    if(busy)return;busy=true;
    try{
      $('translate-enabled').checked=true;await chrome.storage.local.set({[C.TRANSLATE_KEY]:true});
      await beginTranslation(record?.language!=='hy'?record?.text:undefined,record?.name);
    }catch(error){status(error.message,true);}finally{busy=false;showFile();$('translate-youtube').disabled=false;}
  });
  $('translation-retry').addEventListener('click',async()=>{
    try{await current();await backend('HAYSUB_TRANSLATE_RETRY');await refreshTranslation();}catch(error){status(error.message,true);}
  });
  $('translation-stop').addEventListener('click',async()=>{
    try{await backend('HAYSUB_TRANSLATE_CANCEL');await refreshTranslation();}catch(error){status(error.message,true);}
  });
  chrome.storage.onChanged?.addListener((changes,area)=>{
    if(area==='local'&&videoId&&(changes[C.JOB_PREFIX+videoId]||changes[C.FILE_PREFIX+videoId]))void refreshTranslation();
  });

  async function init(){
    try{
      const saved=await chrome.storage.local.get(C.SETTINGS_KEY),options=C.settings(saved[C.SETTINGS_KEY]);
      for(const name of optionNames){if(name==='enabled')$('enabled').checked=options[name];else $(name).value=options[name];}
      labels();await usage();
      $('translation-controls').hidden=PUBLIC;
      const [tab]=await chrome.tabs.query({active:true,currentWindow:true});tabId=tab?.id??null;
      activeTab=tab;
      // Keep iframe recovery available even if activation of the main page fails.
      isSite=!!tab?.url&&/^https?:\/\//.test(tab.url)&&!['youtube.com','www.youtube.com','m.youtube.com'].includes(new URL(tab.url).hostname);
      $('site-controls').hidden=!isSite;$('translate-youtube').hidden=isSite;
      if(isSite){
        $('video-label').textContent=`HaySub · ${new URL(tab.url).hostname}`;
        $('translate-enabled').checked=false;
        $('site-status').textContent='Եթե ֆայլի ընտրությունն անհասանելի է, ընտրիր ներկառուցված նվագարկիչը ստորև։';
      }
      if(globalThis.HaySubPageAccess){siteAccess=await globalThis.HaySubPageAccess.connect(tab);frameId=siteAccess.frameId;isSite=siteAccess.site;}
      const result=await current();videoId=result.videoId;
      $('video-label').textContent=isSite?`HaySub · ${new URL(tab.url).hostname}`:`YouTube · ${videoId}`;
      $('site-controls').hidden=!isSite;$('translate-youtube').hidden=isSite;
      if(isSite&&siteAccess){
        const players=siteAccess.players||[];
        $('site-video-label').hidden=players.length<=1;$('site-video').replaceChildren();
        for(const p of players){const opt=document.createElement('option');opt.value=p.index;opt.textContent=`${p.index+1} · ${p.width} × ${p.height}${p.playing?' · նվագարկվում է':''}`;$('site-video').append(opt);}
        $('site-video').value=siteAccess.videoIndex||0;
        $('site-status').textContent=result.mediaChanged?'Տեսանյութը փոխվել է․ ընտրիր համապատասխան ենթագրերի ֆայլը կրկին։':result.hasVideo?'Ենթագրերը կհայտնվեն ընտրված տեսանյութի ներքևում։':'Այս frame-ում տեսանյութ չի գտնվել։ Նախ սկսիր տեսանյութը կամ ընտրիր ներկառուցված նվագարկիչը։';
      }
      const stored=await chrome.storage.local.get([C.FILE_PREFIX+videoId,C.OFFSET_PREFIX+videoId]);
      record=stored[C.FILE_PREFIX+videoId]||null;$('offset').value=C.offset(stored[C.OFFSET_PREFIX+videoId]);
      const preference=await chrome.storage.local.get(C.TRANSLATE_KEY);
      $('translate-enabled').checked=PUBLIC||isSite?false:preference[C.TRANSLATE_KEY]!==false;
      $('file').disabled=false;$('offset').disabled=false;showFile();
      if(result.error)status(result.error,true);
      else if(!result.hasVideo)status(isSite?'Այս էջում տեսանյութ չի գտնվել։ Սեղմիր «Գտնել ներկառուցված նվագարկիչները», ընտրիր ֆիլմի frame-ը և թույլատրի՛ր այն։ Պահված ֆայլը միայնակ չի միացնում նվագարկիչը։':'Նվագարկիչը դեռ բեռնվում է։ Կարող ես ֆայլ ընտրել․ այն կհայտնվի տեսանյութի բեռնումից հետո։');
      else status(record?'Պահված ենթագրերը պատրաստ են։':'Ընտրիր ենթագրերի ֆայլը։');
      $('translate-youtube').disabled=false;
      const savedJob=(await chrome.storage.local.get(C.JOB_PREFIX+videoId))[C.JOB_PREFIX+videoId];
      if(savedJob&&!PUBLIC)await refreshTranslation();
      else if(!PUBLIC&&!isSite&&$('translate-enabled').checked&&record?.language!=='hy'){
        await beginTranslation(record?.text,record?.name);
      }
    }catch(error){if(!videoId&&!isSite)$('video-label').textContent='Բացիր տեսանյութի էջը';status(error.message||'Չհաջողվեց բացել կարգավորումները։',true);}
  }
  $('site-embedded').addEventListener('click',async()=>{
    try{
      // Must be called directly from this user gesture; frame URLs are tab-scoped.
      if(!await chrome.permissions.request({permissions:['webNavigation']}))throw Error('Ներկառուցված frame-ների ցանկի թույլտվությունը չի տրվել։');
      embeddedFrames=await globalThis.HaySubPageAccess.discover(activeTab);
      $('site-frame').replaceChildren();
      for(const f of embeddedFrames){const opt=document.createElement('option');opt.value=f.frameId;const u=new URL(f.url);opt.textContent=`${f.players?.length?'▶ ':''}${f.frameId===0?'Հիմնական էջ':`Frame ${f.frameId}`} · ${u.origin}${u.pathname.slice(0,55)}`;$('site-frame').append(opt);}
      if(embeddedFrames.length)$('site-frame').value=embeddedFrames[0].frameId;
      $('site-frame-controls').hidden=false;
      $('site-status').textContent='Ընտրիր հենց տեսանյութի frame-ը։ Հասանելիություն կխնդրվի միայն ընտրված domain-ի համար։';
    }catch(error){status(error.message,true);}
  });
  $('site-frame-allow').addEventListener('click',async()=>{
    try{
      const selected=embeddedFrames.find(f=>f.frameId===Number($('site-frame').value));if(!selected)throw Error('Նախ ընտրիր նվագարկիչը։');
      const origin=new URL(selected.url).origin+'/*';
      if(selected.frameId!==0&&!await chrome.permissions.request({origins:[origin]}))throw Error('Այս նվագարկիչի domain-ի թույլտվությունը չի տրվել։');
      const previous=videoId?await current():{hasVideo:false};
      const connected=await globalThis.HaySubPageAccess.activate(activeTab,{frameId:selected.frameId,frameUrl:selected.url});
      if(!connected.status?.hasVideo)throw Error('Ընտրված frame-ում տեսանյութ չկա։ Սկսիր ֆիլմը, հետո ընտրիր այլ frame (ոչ գովազդի frame-ը) և կրկին թույլատրի՛ր։');
      // A file uploaded before discovering the iframe belongs to this same page.
      // Copy it only when the old target had no video and the new target has none saved.
      if(!previous.hasVideo&&record&&videoId!==connected.status.videoId){
        const key=C.FILE_PREFIX+connected.status.videoId;
        if(!(await chrome.storage.local.get(key))[key]){
          const next={...record,selectionId:'frame:'+Date.now(),updatedAt:Date.now()};
          const used=await chrome.storage.local.getBytesInUse(null);
          if(used+C.recordBytes(key,next)>C.SAVE_BUDGET)throw Error('Հիշողությունը լցվել է։ Մաքրիր հին ֆայլերը և ընտրիր ենթագրերը նոր նվագարկիչի համար։');
          await chrome.storage.local.set({[key]:next,[C.OFFSET_PREFIX+connected.status.videoId]:C.offset($('offset').value)});
        }
      }
      location.reload();
    }catch(error){status(error.message,true);}
  });
  $('site-video').addEventListener('change',async()=>{
    try{await globalThis.HaySubPageAccess.activate(activeTab,{frameId,frameUrl:siteAccess?.frameUrl||activeTab.url,videoIndex:Number($('site-video').value)});location.reload();}
    catch(error){status(error.message,true);}
  });
  async function loadLibrary(reset=true){
    if(libraryLoading)return;libraryLoading=true;$('library-panel').hidden=false;
    if(reset){libraryOffset=0;$('extension-library-results').replaceChildren();}
    $('extension-library-status').textContent='Բեռնվում է գրադարանը…';
    try{
      const response=await chrome.runtime.sendMessage({type:'HAYSUB_LIBRARY_LIST',query:$('extension-library-query').value,offset:libraryOffset});
      if(!response?.ok)throw Error(response?.error||'Գրադարանը հասանելի չէ։');
      for(const item of response.items){
        const row=document.createElement('div');row.className='library-item';
        const title=document.createElement('p');title.textContent=item.title;
        const choose=document.createElement('button');choose.type='button';choose.textContent='Դիտել այս ենթագրերով';
        choose.addEventListener('click',async()=>{
          if(busy)return;busy=true;choose.disabled=true;
          try{
            const player=await current();
            if(!player.hasVideo)throw Error('Նախ միացրու տեսանյութի նվագարկիչը՝ «Գտնել ներկառուցված նվագարկիչները» կոճակով։');
            status('Ստացվում են հայերեն ենթագրերը…');
            await backend('HAYSUB_TRANSLATE_CANCEL',{forget:true});
            const applied=await backend('HAYSUB_LIBRARY_USE',{identity:item.id,title:item.title});
            await current();record=(await chrome.storage.local.get(C.FILE_PREFIX+videoId))[C.FILE_PREFIX+videoId];
            showFile();await usage();status(`Պատրաստ է՝ ${applied.cueCount} հատված։ Փակիր այս պատուհանը և դիտիր։`);
          }catch(error){status(error.message,true);}
          finally{busy=false;choose.disabled=false;showFile();}
        });
        row.append(title,choose);$('extension-library-results').append(row);
      }
      libraryOffset+=response.items.length;$('extension-library-more').hidden=response.items.length<50;
      $('extension-library-status').textContent=libraryOffset?`${libraryOffset} հայերեն թարգմանություն։ Ընտրիր ֆիլմի ճիշտ տարբերակը։`:'Այս անունով պատրաստ թարգմանություն չկա։';
    }catch(error){$('extension-library-status').textContent=error.message;}
    finally{libraryLoading=false;}
  }
  $('library-open').addEventListener('click',()=>loadLibrary());
  $('extension-library-search').addEventListener('submit',event=>{event.preventDefault();void loadLibrary();});
  $('extension-library-more').addEventListener('click',()=>loadLibrary(false));
  void init();
})();
