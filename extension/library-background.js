/* Read-only public catalog bridge. Never sends page URLs, clocks or local files. */
(() => {
  const C=globalThis.HaySubCore,config=globalThis.HaySubRelease||{apiBase:'http://127.0.0.1:8000'};
  const queues=new Map();
  async function request(path){
    let response;
    try{response=await fetch(config.apiBase+path,{credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(15000)});}
    catch{throw Error('Գրադարանը հասանելի չէ։ Ստուգիր կապը և փորձիր կրկին։ Պահված ենթագրերը շարունակում են աշխատել։');}
    if(!response.ok)throw Error(response.status===404?'Թարգմանությունը հեռացվել է գրադարանից։ Թարմացրու ցանկը։':'Չհաջողվեց ստանալ գրադարանը։ Փորձիր կրկին։');
    return response;
  }
  async function boundedText(response){
    if(!response.body?.getReader){const text=await response.text();if(C.bytes(text)>C.MAX_FILE_BYTES)throw Error('Ֆայլը չափազանց մեծ է։');return text;}
    const reader=response.body.getReader(),chunks=[];let count=0;
    try{while(true){const {done,value}=await reader.read();if(done)break;count+=value.length;if(count>C.MAX_FILE_BYTES)throw Error('Ֆայլը չափազանց մեծ է։');chunks.push(value);}}
    finally{await reader.cancel();}
    const raw=new Uint8Array(count);let offset=0;for(const chunk of chunks){raw.set(chunk,offset);offset+=chunk.length;}
    return new TextDecoder('utf-8',{fatal:true}).decode(raw);
  }
  async function handle(message){
    if(message.type==='HAYSUB_LIBRARY_LIST'){
      const query=String(message.query||'').slice(0,200),offset=Number(message.offset)||0;
      if(!Number.isInteger(offset)||offset<0||offset>100000)throw Error('Սխալ էջ։');
      const response=await request('/api/public/library?q='+encodeURIComponent(query)+'&offset='+offset);
      const items=await response.json();
      if(!Array.isArray(items)||items.length>50||items.some(item=>!(/^[a-f0-9]{32}$/).test(item.id)||typeof item.title!=='string'||item.title.length>200))throw Error('Գրադարանի պատասխանը սխալ է։');
      return {ok:true,items};
    }
    const id=message.videoId;
    if(!/^[\w-]{11}$/.test(id||'')&&!/^page:[a-f0-9]{64}$/.test(id||''))throw Error('Նախ ընտրիր նվագարկիչը։');
    if(!/^[a-f0-9]{32}$/.test(message.identity||''))throw Error('Սխալ թարգմանություն։');
    const response=await request('/api/public/library/'+message.identity+'/download');
    const text=await boundedText(response),parsed=C.parse(text);
    if(!parsed.cues.length)throw Error('Ֆայլում ցուցադրվող ենթագրեր չկան։');
    const record={version:1,name:String(message.title||'HaySub').slice(0,190)+'_hy.srt',text,language:'hy',libraryId:message.identity,selectionId:'library:'+message.identity+':'+Date.now(),updatedAt:Date.now()};
    const key=C.FILE_PREFIX+id,jobKey=C.JOB_PREFIX+id;
    const used=await chrome.storage.local.getBytesInUse(null),old=await chrome.storage.local.getBytesInUse([key,jobKey]);
    if(used-old+C.recordBytes(key,record)>C.SAVE_BUDGET)throw Error('Հիշողությունը լցվել է։ Մաքրիր հին ենթագրերը և կրկնիր։');
    // Save first: storage failure must preserve the previous file and job.
    await chrome.storage.local.set({[key]:record});
    await chrome.storage.local.remove(jobKey);
    return {ok:true,cueCount:parsed.cues.length};
  }
  chrome.runtime.onMessage.addListener((message,sender,reply)=>{
    if(sender.id!==chrome.runtime.id||!['HAYSUB_LIBRARY_LIST','HAYSUB_LIBRARY_USE'].includes(message?.type))return;
    const id=message.videoId,run=message.type==='HAYSUB_LIBRARY_USE'?(queues.get(id)||Promise.resolve()).catch(()=>{}).then(()=>handle(message)):handle(message);
    if(message.type==='HAYSUB_LIBRARY_USE'){queues.set(id,run);run.finally(()=>{if(queues.get(id)===run)queues.delete(id);}).catch(()=>{});}
    run.then(reply).catch(error=>reply({ok:false,error:error.message||'Չհաջողվեց ընտրել ենթագրերը։'}));return true;
  });
})();
