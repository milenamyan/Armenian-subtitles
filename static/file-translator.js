/* Standalone subtitle upload -> translation job -> UTF-8 Armenian SRT download. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id),form=$('file-translation-form');
  let identity=null,timer=null,busy=false,notified=null,cancelling=false,completedIdentity=null;
  let timingSample=null;
  const completion=$('file-complete-dialog');
  function finish(){
    stop();identity=null;remember(null);notified=null;completedIdentity=null;
    form.reset();
    $('file-translation-name').textContent='';$('file-cache-status').textContent='';
    $('file-translation-progress').hidden=true;$('file-translation-retry').hidden=true;
    $('file-download').hidden=true;$('file-download').removeAttribute('href');
    controls(false);show('');completion.close();
    $('translate-file').focus();
  }
  $('file-complete-ok').addEventListener('click',finish);
  completion.addEventListener('cancel',event=>{event.preventDefault();finish();});
  const show=(text,error=false)=>{$('file-translation-status').textContent=text;$('file-translation-status').classList.toggle('error',error);};
  async function request(url,options){
    const response=await fetch(url,options);
    if(!response.ok){
      let error;try{error=await response.json();}catch{}
      const failure=Error(typeof error?.detail==='string'?error.detail:`HTTP ${response.status}: ${response.statusText||'Չհաջողվեց կատարել հարցումը։'}`);
      failure.status=response.status;throw failure;
    }
    return response.json();
  }
  function remember(id){try{if(id)sessionStorage.setItem('haysub:file-job',id);else sessionStorage.removeItem('haysub:file-job');}catch{}}
  function controls(running){busy=running;$('translate-file-submit').disabled=running;$('translate-file').disabled=running;$('file-translation-remove').hidden=!identity;$('file-translation-remove').disabled=cancelling;$('file-translation-cancel').hidden=!running||!identity;$('file-translation-cancel').disabled=cancelling;}
  function remainingTime(state){
    if(!state.running){timingSample=null;return '';}
    const now=Date.now();
    if(!timingSample||timingSample.id!==state.id||state.completed<timingSample.completed){
      timingSample={id:state.id,completed:state.completed,started:now};
    }
    let seconds=state.estimated_remaining_seconds;
    if(!Number.isFinite(seconds)||seconds<=0){
      // Older running servers may omit ETA. Measure observed progress locally,
      // excluding subtitles already restored before this page was opened.
      const gained=state.completed-timingSample.completed;
      const observed=gained>0?(now-timingSample.started)/1000/gained:0;
      const chunkSize=state.active_chunk?Math.max(1,state.active_chunk.last-state.active_chunk.first+1):0;
      const current=chunkSize&&state.elapsed>0?state.elapsed/chunkSize:0;
      const pace=Math.max(observed,current);
      if(pace>0)seconds=Math.ceil(pace*(state.total-state.completed));
    }
    if(!Number.isFinite(seconds)||seconds<=0)return ' · Մնացած ժամանակը հաշվարկվում է…';
    const minutes=Math.ceil(seconds/60);
    const duration=minutes<60?`${minutes} րոպե`:`${Math.floor(minutes/60)} ժամ${minutes%60?` ${minutes%60} րոպե`:''}`;
    return ` · Մոտավոր մնացել է՝ ${duration}`;
  }
  function render(state){
    $('file-translation-name').textContent=state.filename;
    const restored=state.restored_cues||0;
    $('file-cache-status').textContent=restored?`Պահված աշխատանքից վերականգնվել է ${restored} / ${state.total} հատված։`+(state.compatible_cache_cues?` Դրանցից ${state.compatible_cache_cues}-ը՝ ստուգված նախորդ տարբերակի քեշից։`:''):'Այս ֆայլի համար համընկնող պահված թարգմանություն դեռ չի գտնվել։';
    $('file-translation-progress').max=state.total;
    $('file-translation-progress').value=state.completed;
    $('file-translation-progress').hidden=false;
    $('file-download').hidden=!state.ready;
    if(state.ready){
      $('file-download').href=state.download_url;
      if(notified!==state.id&&typeof window!=='undefined'&&typeof CustomEvent!=='undefined'){
        notified=state.id;window.dispatchEvent(new CustomEvent('haysub-library-updated'));
      }
    }
    else $('file-download').removeAttribute('href');
    const cancelled=state.phase==='cancelled'&&!state.ready;
    $('file-translation-retry').hidden=!state.error&&!cancelled;
    controls(state.running);
    if(cancelled)show(`Թարգմանությունը չեղարկված է։ Պահպանված է ${state.completed} / ${state.total} հատված։ Շարունակելու համար սեղմիր «Կրկնել թարգմանությունը»։`);
    else if(state.error)show(`${state.completed} / ${state.total} հատված պատրաստ է։ ${state.error}`,true);
    else if(state.phase==='retrying')show(`${state.completed} / ${state.total} հատված պատրաստ է։ Gemini ծառայությունը ժամանակավորապես անհասանելի է։ Ավտոմատ կրկին կփորձենք ${state.retry_after_seconds??30} վայրկյանից։ Պատրաստ թարգմանությունները պահպանված են։`);
    else if(state.ready)show(`Պատրաստ է՝ ${state.total} հատված։ Թարգմանությունը պահված է ներքևի ցանկում։ Կարող ես ներբեռնել հայերեն SRT ֆայլը։`);
    else {
      const chunk=state.active_chunk?` · ${state.active_chunk.first}–${state.active_chunk.last} · ${state.elapsed} վրկ`:'';
      show(`Թարգմանվում է՝ ${state.completed} / ${state.total} հատված${chunk}${remainingTime(state)}`);
    }
    if(state.ready&&completedIdentity!==state.id){
      completedIdentity=state.id;
      completion.showModal();
      $('file-complete-ok').focus();
    }
  }
  function stop(){if(timer!==null)clearTimeout(timer);timer=null;}
  async function poll(){
    stop();if(!identity)return;
    const pollingIdentity=identity;
    try{
      const state=await request('/api/subtitle-files/'+identity);if(cancelling||identity!==pollingIdentity)return;render(state);
      if(state.running)timer=setTimeout(poll,1000);
    }catch(error){
      if(cancelling||identity!==pollingIdentity)return;
      if(error.status===404){identity=null;remember(null);}
      controls(false);$('file-translation-retry').hidden=!identity;show(error.message,true);
    }
  }
  $('translate-file').addEventListener('change',()=>{if(!busy&&$('translate-file').files[0])form.requestSubmit();});
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(busy)return;
    const file=$('translate-file').files[0];
    if(!file){show('Նախ ընտրիր SRT կամ VTT ֆայլ։',true);return;}
    if(!/\.(srt|vtt)$/i.test(file.name)||!file.size||file.size>2*1024*1024){show('Ընտրիր ոչ դատարկ SRT/VTT ֆայլ՝ մինչև 2 ՄԲ։',true);return;}
    stop();identity=null;remember(null);completedIdentity=null;controls(true);
    $('file-download').hidden=true;$('file-download').removeAttribute('href');
    $('file-translation-retry').hidden=true;$('file-translation-progress').hidden=true;
    $('file-cache-status').textContent='Ստուգվում են պահված թարգմանությունները…';
    show('Ֆայլը վերբեռնվում է․ ստուգվում են քեշն ու պահված առաջընթացը…');
    try{
      const data=new FormData();data.append('subtitles',file);
      const state=await request('/api/subtitle-files',{method:'POST',body:data});
      identity=state.id;remember(identity);render(state);
      if(state.running)timer=setTimeout(poll,1000);
    }catch(error){controls(false);show(error.message,true);}
  });
  $('file-translation-retry').addEventListener('click',async()=>{
    if(!identity||busy)return;stop();controls(true);$('file-translation-retry').hidden=true;
    try{render(await request(`/api/subtitle-files/${identity}/retry`,{method:'POST'}));await poll();}
    catch(error){controls(false);$('file-translation-retry').hidden=false;show(error.message,true);}
  });
  $('file-translation-cancel').addEventListener('click',async()=>{
    if(!identity||!busy||cancelling)return;
    cancelling=true;stop();controls(true);
    show('Թարգմանությունը չեղարկվում է…');
    try{
      await request(`/api/subtitle-files/${identity}/cancel`,{method:'POST'});
    }catch(error){show(error.message,true);}
    finally{cancelling=false;await poll();}
  });
  $('file-translation-remove').addEventListener('click',async()=>{
    if(!identity||cancelling)return;
    cancelling=true;stop();controls(busy);
    show('Գործընթացը կանգնեցվում և հեռացվում է…');
    try{
      await request(`/api/subtitle-files/${identity}`,{method:'DELETE'});
      identity=null;remember(null);notified=null;form.reset();
      $('file-translation-name').textContent='';$('file-cache-status').textContent='';
      $('file-translation-progress').hidden=true;$('file-translation-retry').hidden=true;
      $('file-download').hidden=true;$('file-download').removeAttribute('href');
      show('Գործընթացը հեռացված է։ Պահված աշխատանքը պահպանված է տեղական bin պանակում։');
    }catch(error){show(error.message,true);}
    finally{cancelling=false;controls(false);if(identity)void poll();}
  });
  try{identity=sessionStorage.getItem('haysub:file-job');}catch{}
  if(identity){controls(true);void poll();}
})();
