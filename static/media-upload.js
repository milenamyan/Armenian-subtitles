/* Bounded-memory, sequential multipart uploads. A video never goes to FastAPI. */
((root)=>{
  'use strict';
  function aborted(){return Object.assign(Error('Վերբեռնումը դադարեցված է։ Շարունակելու համար ընտրիր նույն ֆայլը։'),{name:'AbortError'});}
  async function fingerprint(file){
    if(!globalThis.crypto?.subtle)throw Error('Ֆայլի անվտանգ նույնականացման համար անհրաժեշտ է HTTPS կամ localhost։ Բացիր HaySub-ը HTTPS հասցեով։');
    const sample=1024*1024,first=new Uint8Array(await file.slice(0,sample).arrayBuffer()),last=new Uint8Array(await file.slice(Math.max(0,file.size-sample)).arrayBuffer());
    const meta=new TextEncoder().encode(JSON.stringify([file.name,file.size,file.lastModified]));
    const all=new Uint8Array(meta.length+first.length+last.length);all.set(meta);all.set(first,meta.length);all.set(last,meta.length+first.length);
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',all)),b=>b.toString(16).padStart(2,'0')).join('');
  }
  function put(url,blob,signal,progress){
    return new Promise((resolve,reject)=>{
      if(signal?.aborted){reject(aborted());return;}
      const xhr=new XMLHttpRequest(),cancel=()=>xhr.abort();
      const finish=()=>signal?.removeEventListener('abort',cancel);
      xhr.open('PUT',url);xhr.withCredentials=false;xhr.timeout=30*60*1000;
      xhr.upload.onprogress=event=>{if(event.lengthComputable)progress(Math.min(event.loaded,blob.size));};
      xhr.onload=()=>{finish();if(xhr.status<200||xhr.status>=300){reject(Error('Պահոցը մերժել է ֆայլի հատվածը։ Ստուգիր CORS կանոններն ու թույլտվությունները, ապա շարունակիր։'));return;}
        const etag=xhr.getResponseHeader('ETag');if(!etag){reject(Error('Պահոցը չի տրամադրել ETag-ը։ Պահոցի CORS ExposeHeaders կարգավորման մեջ ավելացրու ETag, ապա շարունակիր։'));return;}resolve(etag);};
      xhr.onerror=()=>{finish();reject(Error('Չհաջողվեց վերբեռնել պահոց։ Ստուգիր կապը և CORS կարգավորումները, ապա շարունակիր։'));};
      xhr.ontimeout=()=>{finish();reject(Error('Հատվածի վերբեռնման ժամանակը սպառվել է։ Շարունակիր կայուն կապով։'));};
      xhr.onabort=()=>{finish();reject(aborted());};
      signal?.addEventListener('abort',cancel,{once:true});xhr.send(blob);
    });
  }
  async function upload(file,session,{api,onProgress=()=>{},onPhase=()=>{},signal,sendPart=put}={}){
    const id=session.id,base='/api/owner/media/'+id;
    if(file.size!==session.size||await fingerprint(file)!==session.fingerprint)throw Error('Սա սկզբնական ընտրված ֆայլը չէ։ Շարունակելու համար ընտրիր նույն անունով, չափով, փոփոխման ամսաթվով և բովանդակությամբ ֆայլը։');
    session=await api(base+'/resume');
    if(session.state!=='uploading')return session;
    const completed=new Set(session.parts.map(p=>p.number));let saved=0;
    for(const number of completed)saved+=Math.min(session.part_size,file.size-(number-1)*session.part_size);
    onProgress(saved,file.size);
    for(let number=1;number<=session.part_count;number++){
      if(completed.has(number))continue;
      if(signal?.aborted)throw aborted();
      const blob=file.slice((number-1)*session.part_size,Math.min(number*session.part_size,file.size));
      onPhase(`Վերբեռնվում է ${number} / ${session.part_count} հատվածը`);
      const permission=await api(base+'/part-url',{method:'POST',body:{number}});
      if(signal?.aborted)throw aborted();
      const etag=await sendPart(permission.url,blob,signal,loaded=>onProgress(saved+loaded,file.size));
      if(signal?.aborted)throw aborted();
      await api(base+'/ack',{method:'POST',body:{number,etag}});
      saved+=blob.size;onProgress(saved,file.size);
    }
    if(signal?.aborted)throw aborted();
    onPhase('Ֆայլը ստացված է։ Վերջնական մշակումն ու ստուգումը հերթագրված են։');
    return api(base+'/complete',{method:'POST'});
  }
  const api={fingerprint,put,upload};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.HaySubMediaUpload=api;
})(globalThis);
