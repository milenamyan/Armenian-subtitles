/* Privileged translation bridge. Public releases disable translation requests.
   API keys and Gemini calls remain in Python. No service-worker polling timer. */
importScripts('core.js','config.js','site-background.js','library-background.js');
(() => {
  'use strict';
  const C=globalThis.HaySubCore,BASE=globalThis.HaySubRelease?.apiBase||'http://127.0.0.1:8000',PUBLIC=!!globalThis.HaySubRelease?.publicMode;
  const supported=new Set(['HAYSUB_TRANSLATE_START','HAYSUB_TRANSLATE_POLL','HAYSUB_TRANSLATE_RETRY','HAYSUB_TRANSLATE_CANCEL']);
  const queues=new Map();
  function validId(id){if(!/^[\w-]{11}$/.test(id||'')&&!/^page:[a-f0-9]{64}$/.test(id||''))throw Error('Տեսանյութի կամ էջի ID-ն սխալ է։');return id;}
  async function jobFor(id){return (await chrome.storage.local.get(C.JOB_PREFIX+id))[C.JOB_PREFIX+id];}
  function path(job,suffix){if(!/^[a-f0-9]{32}$/.test(job?.backendId||''))throw Error('Թարգմանության աշխատանքը չի գտնվել։ Նորից ընտրիր ֆայլը կամ YouTube ենթագրերը։');return `/api/${job.kind==='file'?'subtitle-files':'videos'}/${job.backendId}${suffix}`;}
  async function api(resource,options={}){
    let response;
    try{response=await fetch(BASE+resource,{...options,credentials:'omit',cache:'no-store',signal:AbortSignal.timeout(15000)});}
    catch{throw Error('HaySub սերվերը հասանելի չէ։ Գործարկիր Python սերվերը՝ http://127.0.0.1:8000 հասցեով։');}
    const data=await response.json();
    if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Սերվերի հարցումը ձախողվեց։ Փորձիր կրկին։');
    return data;
  }
  async function putFile(id,record,job){
    const fileKey=C.FILE_PREFIX+id,jobKey=C.JOB_PREFIX+id;
    const used=await chrome.storage.local.getBytesInUse(null);
    const old=await chrome.storage.local.getBytesInUse([fileKey,jobKey]);
    if(used-old+C.recordBytes(fileKey,record)+C.recordBytes(jobKey,job)>C.SAVE_BUDGET)throw Error('Տեղային հիշողությունը լցվել է։ Մաքրիր պահված ենթագրերը և կրկնիր։');
    try{await chrome.storage.local.set({[fileKey]:record,[jobKey]:job});}
    catch{throw Error('Չհաջողվեց պահպանել թարգմանությունը։ Մաքրիր տեղային հիշողությունը և կրկնիր։');}
  }
  async function cancel(id,forget=false){
    const job=await jobFor(id);
    if(job?.backendId&&!PUBLIC){try{await api(path(job,'/cancel'),{method:'POST'});}catch{/* Clearing local files must still work offline. */}}
    if(forget)await chrome.storage.local.remove(C.JOB_PREFIX+id);
    else if(job)await chrome.storage.local.set({[C.JOB_PREFIX+id]:{...job,running:false,cancelled:true,error:''}});
    return {ok:true};
  }
  async function start(message){
    const id=validId(message.videoId);
    const generic=id.startsWith('page:');
    if(generic&&message.text===undefined)throw Error('Այս կայքի համար ընտրիր SRT/VTT ֆայլ։ Ավտոմատ ենթագրերի ստացումը հասանելի է միայն YouTube-ում։');
    if(message.text!==undefined){C.parse(message.text);if(!/\.(srt|vtt)$/i.test(message.name||''))throw Error('Ընտրիր SRT կամ VTT ֆայլ։');}
    const config=await api('/api/config');
    if(!config.configured)throw Error('Լրացրու GEMINI_API_KEY և GEMINI_MODEL-ը Python նախագծի .env ֆայլում, ապա վերագործարկիր սերվերը։');
    await cancel(id,true);
    const body=new FormData();
    if(!generic){body.append('url',`https://www.youtube.com/watch?v=${id}`);
      body.append('native_captions','true');body.append('summary','true');}
    if(message.text!==undefined)body.append('subtitles',new Blob([message.text],{type:'text/plain;charset=utf-8'}),message.name.slice(0,200));
    const created=await api(generic?'/api/subtitle-files':'/api/videos',{method:'POST',body});
    const job={backendId:created.id,kind:generic?'file':'video',videoId:id,running:true,phase:created.phase||'translating',completed:0,total:0,error:'',source:message.text!==undefined?'uploaded':'youtube',name:message.name||'YouTube',updatedAt:Date.now()};
    const record={version:1,name:(message.name||id).replace(/\.(srt|vtt)$/i,'')+'_hy.srt',text:'',selectionId:job.backendId,pendingTranslation:true,language:'hy',updatedAt:Date.now()};
    try{await putFile(id,record,job);}
    catch(error){try{await api(path(job,'/cancel'),{method:'POST'});}catch{}throw error;}
    return {ok:true,job};
  }
  async function poll(id,position){
    const job=await jobFor(id);
    if(!job || job.cancelled)return {ok:true,running:false};
    if(Number.isFinite(position)&&position>=0&&position<=604800){
      await api(path(job,'/position'),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seconds:position})});
    }
    const state=await api(path(job,'/translated-subtitles'));
    if(state.needs_resume){state.error='Սերվերը վերագործարկվել է։ Սեղմիր «Կրկնել»՝ պահված ենթագրերը շարունակելու համար։';state.phase='error';}
    // A file upload may have replaced the automatic-caption job while this request was in flight.
    const latest=await jobFor(id);
    if(latest?.backendId!==job.backendId || latest.cancelled)return {ok:true,running:!!latest?.running};
    const next={...job,...state,cues:undefined,updatedAt:Date.now()};delete next.cues;
    if(state.completed!==job.completed || state.phase!==job.phase){
      if(!Array.isArray(state.cues)||state.cues.some(c=>typeof c.text!=='string'||!c.text.trim()||(!/[\u0531-\u0587]/.test(c.text)&&/\p{L}/u.test(c.text))))throw Error('Սերվերը չի վերադարձրել վավեր հայերեն ենթագրեր։');
      const previous=(await chrome.storage.local.get(C.FILE_PREFIX+id))[C.FILE_PREFIX+id];
      const record={version:1,name:previous?.name||id+'_hy.srt',text:C.toSrt(state.cues),selectionId:previous?.selectionId||job.backendId,pendingTranslation:state.running,language:'hy',updatedAt:Date.now()};
      try{await putFile(id,record,next);}
      catch(error){try{await api(path(job,'/cancel'),{method:'POST'});}catch{}throw error;}
    }else await chrome.storage.local.set({[C.JOB_PREFIX+id]:next});
    return {ok:true,running:state.running};
  }
  async function handle(message){
    const id=validId(message.videoId);
    if(PUBLIC&&message.type!=='HAYSUB_TRANSLATE_CANCEL')throw Error('Այս տարբերակում ընտրիր պատրաստ հայերեն ենթագրերը գրադարանից կամ վերբեռնիր տեղային ֆայլ։');
    if(message.type==='HAYSUB_TRANSLATE_START')return start(message);
    if(message.type==='HAYSUB_TRANSLATE_CANCEL')return cancel(id,!!message.forget);
    if(message.type==='HAYSUB_TRANSLATE_RETRY'){
      const job=await jobFor(id),body=new FormData();body.append('native_captions','true');
      await api(path(job,'/retry'),{method:'POST',body});
      await chrome.storage.local.set({[C.JOB_PREFIX+id]:{...job,running:true,cancelled:false,error:''}});
      return {ok:true,running:true};
    }
    return poll(id,message.position);
  }
  chrome.runtime.onMessage.addListener((message,sender,respond)=>{
    if(!supported.has(message?.type)||sender.id!==chrome.runtime.id)return;
    const id=message.videoId;
    const operation=()=>handle(message);
    const run=message.type==='HAYSUB_TRANSLATE_START'||message.type==='HAYSUB_TRANSLATE_CANCEL'
      ? (queues.get(id)||Promise.resolve()).catch(()=>{}).then(operation) : operation();
    if(message.type==='HAYSUB_TRANSLATE_START'||message.type==='HAYSUB_TRANSLATE_CANCEL'){
      queues.set(id,run);run.finally(()=>{if(queues.get(id)===run)queues.delete(id);}).catch(()=>{});
    }
    run.then(respond).catch(async error=>{
      if(message.type==='HAYSUB_TRANSLATE_POLL'){
        const job=await jobFor(id);
        if(job)await chrome.storage.local.set({[C.JOB_PREFIX+id]:{...job,running:false,error:error.message}});
      }
      respond({ok:false,error:error.message||'Թարգմանությունը ձախողվեց։'});
    });
    return true;
  });
})();
