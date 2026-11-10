/* A content-page coordinator keeps incremental translations flowing when the
   popup closes. The service worker only makes short, privileged localhost calls. */
(() => {
  'use strict';
  globalThis.HaySubTranslationClient?.dispose();
  const C=globalThis.HaySubCore;
  let active=null,clock=()=>0,timer=null,inFlight=false,generation=0,disposed=false;
  function stop(){if(timer!==null)clearTimeout(timer);timer=null;}
  async function tick(){
    timer=null;if(!active||inFlight||disposed)return;
    const id=active,version=generation;inFlight=true;
    try{
      const stored=await chrome.storage.local.get(C.JOB_PREFIX+id),job=stored[C.JOB_PREFIX+id];
      if(!job?.running||job.cancelled)return;
      const response=await chrome.runtime.sendMessage({type:'HAYSUB_TRANSLATE_POLL',videoId:id,position:Math.max(0,Number(clock())||0)});
      if(response?.ok&&response.running&&version===generation)timer=setTimeout(tick,2000);
    }catch{/* Popup offers retry; do not spin indefinitely when extension/backend disappears. */}
    finally{inFlight=false;if(version!==generation&&active&&!disposed&&!timer)timer=setTimeout(tick,0);}
  }
  function activate(id,getTime=()=>0){
    clock=getTime;if(id===active)return;
    generation++;active=id;stop();if(id)timer=setTimeout(tick,0);
  }
  function changed(changes,area){
    if(area==='local'&&active&&changes[C.JOB_PREFIX+active]&&!inFlight&&!timer)timer=setTimeout(tick,0);
  }
  chrome.storage.onChanged.addListener(changed);
  function dispose(){disposed=true;generation++;stop();chrome.storage.onChanged.removeListener(changed);}
  globalThis.HaySubTranslationClient={activate,dispose};
})();
