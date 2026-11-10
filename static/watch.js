(() => {
  'use strict';
  const $=id=>document.getElementById(id),video=$('hosted-player'),source=$('hosted-source'),track=$('armenian-track');
  // The active HTML tags select the source. Cloud alternatives stay commented out.
  const cloudVideo=source.getAttribute('data-media-source')==='cloud',cloudTrack=track.getAttribute('data-media-source')==='cloud';
  const identity=location.pathname.split('/').pop(),preview=location.pathname.startsWith('/preview/');
  let endpoint=(preview?'/api/owner/media/':'/api/public/hosted/')+identity+'/playback',ownerPlayback=preview,playSelection=false;
  const inline=video.getAttribute('data-url-player')==='true';
  const stage=$('watch-player-stage'),stageHome=stage?.parentElement,status=$('watch-status'),statusHome=status?.parentElement,statusNext=status?.nextSibling;
  const progress=globalThis.HaySubProgress,progressId=!inline&&!preview?identity:null;
  let progressReady=false,lastSave=0;
  function saveProgress(){
    if(!progressId||!progressReady||renewing||video.seeking)return;
    progress?.save(progressId,video.currentTime,video.duration);
    if($('watch-restart'))$('watch-restart').hidden=!progress?.read(progressId,video.duration);
  }
  let timer=null,loading=false,renewing=false,subtitleBlob=null,operation=0,direct=null,saving=false,playerHidden=false,mediaAssigned=false,captionsAssigned=false;
  if(cloudTrack)track.removeAttribute('src');
  let statusError=false;
  function message(text,error=false){statusError=error;status.textContent=text;status.hidden=!text;status.classList.toggle('error',error);}
  const subtitleUp=$('watch-subtitle-up'),subtitleDown=$('watch-subtitle-down');
  const heightKey='haysub-subtitle-height-buttons';
  function validHeight(value){const number=Number(value);return value!=null&&Number.isFinite(number)?Math.max(0,Math.min(40,number)):10;}
  let height=10;
  try{height=validHeight(globalThis.localStorage?.getItem(heightKey));}catch{}
  function positionSubtitles(){
    if(subtitleUp)subtitleUp.disabled=height>=40;
    if(subtitleDown)subtitleDown.disabled=height<=0;
    for(const item of video.textTracks){
      for(const cue of item.cues||[]){
        // Native bottom placement lets the browser make room for playback controls.
        cue.snapToLines=height===0;
        cue.line=height===0?-1:100-height;
        cue.lineAlign='end';
      }
    }
  }
  function subtitles(){
    for(const item of video.textTracks)item.mode=($('watch-subtitles')?.value||'hy')==='hy'?'showing':'disabled';
    positionSubtitles();
  }
  function moveSubtitles(amount){
    height=validHeight(height+amount);positionSubtitles();
    try{globalThis.localStorage?.setItem(heightKey,String(height));}catch{}
  }
  subtitleUp?.addEventListener('click',()=>moveSubtitles(2));
  subtitleDown?.addEventListener('click',()=>moveSubtitles(-2));
  positionSubtitles();
  function returnPlayerHome(){
    if(stage&&stageHome&&stage.parentElement!==stageHome)stageHome.append(stage);
    if(status&&statusHome&&status.parentElement!==statusHome)statusHome.insertBefore(status,statusNext?.parentElement===statusHome?statusNext:null);
  }
  function placePlayer(anchor){
    if(!stage)return;
    if(anchor&&typeof anchor.after==='function'){
      anchor.after(stage);if(status)stage.prepend(status);
    }else returnPlayerHome();
    stage.hidden=false;
  }
  function closePlayer(){
    saveProgress();++operation;clearTimeout(timer);timer=null;renewing=false;loading=false;playSelection=false;
    video.pause();video.hidden=true;if($('watch-controls'))$('watch-controls').hidden=true;playerHidden=true;
    if(stage)stage.hidden=true;
    returnPlayerHome();
    if($('watch-url-load'))$('watch-url-load').disabled=false;
    saveControls();
  }
  function saveControls(){
    if(!$('watch-save-form'))return;
    const available=(inline||preview)&&direct?.loaded&&!playerHidden&&!loading;
    $('watch-save-form').hidden=!available;
    $('watch-save-submit').disabled=!available||saving||!!direct?.saved;
    $('watch-save-title').disabled=saving||!!direct?.saved;
    $('watch-save-submit').textContent=saving?'Saving…':direct?.saved?'Added to page':'Add to page';
  }
  async function prepareCaptions(url,convert=false,offset=0){
    if(!url||!convert)return {url,blob:null};
    let response;
    try{response=await fetch(url,{cache:'no-store',referrerPolicy:'no-referrer'});}
    catch{throw Error('Could not fetch subtitles. Check the URL and network connection, and allow '+(location.origin||'your page origin')+' in your storage CORS policy.');}
    if(!response.ok)throw Error('Could not load subtitles. Check the URL and the storage CORS settings.');
    const text=globalThis.HaySubMediaSources.srtToVtt(await response.text(),offset);
    const blob=URL.createObjectURL(new Blob([text],{type:'text/vtt'}));
    return {url:blob,blob};
  }
  function useCaptions(captions){
    captionsAssigned=!!captions.url;
    const previous=subtitleBlob;subtitleBlob=captions.blob;
    if(captions.url)track.src=captions.url;else track.removeAttribute('src');
    if(previous)URL.revokeObjectURL(previous);
    if($('watch-subtitles'))$('watch-subtitles').disabled=!captions.url;
  }
  function loadMedia(url,captions,position,speed,play,token){
    playerHidden=false;
    progressReady=false;
    video.pause();
    renewing=position>0;
    video.addEventListener('loadedmetadata',()=>{
      if(token!==operation)return;
      const saved=progressId?progress?.read(progressId,video.duration):null;
      const target=position>0?position:saved?.position||0;
      if(target>0&&Number.isFinite(video.duration))video.currentTime=Math.min(target,Math.max(0,video.duration-.1));
      progressReady=true;lastSave=Date.now();
      if(progressId)progress?.rememberDuration?.(progressId,video.duration);
      if($('watch-restart'))$('watch-restart').hidden=!saved;
      video.playbackRate=speed;subtitles();renewing=false;
      if(!direct&&!statusError)message('');
      if(direct){direct.loaded=true;saveControls();}
    },{once:true});
    useCaptions(captions);source.src=url;mediaAssigned=true;
    if(stage)stage.hidden=false;
    video.hidden=false;if($('watch-controls'))$('watch-controls').hidden=false;video.load();
    if(play)video.play().catch(()=>{if(token===operation)message('Video loaded. Click the player’s Play button to start.');});
  }
  function checkedUrl(value,required=false){
    value=value.trim();
    if(!value&&!required)return '';
    let url;try{url=new URL(value);}catch{throw Error('Enter a complete http:// or https:// URL.');}
    if(!['http:','https:'].includes(url.protocol)||url.username||url.password)throw Error('Use an http:// or https:// URL without a username or password.');
    return url.href;
  }
  async function loadDirect(videoInput,subtitleInput,restore=false){
    let videoUrl,subtitleUrl;
    try{videoUrl=checkedUrl(videoInput,true);subtitleUrl=checkedUrl(subtitleInput);}
    catch(error){message(error.message,true);return;}
    if(!restore)placePlayer(null);
    const token=++operation,position=restore?video.currentTime:0,speed=video.playbackRate,play=!restore||!video.paused;
    loading=true;mediaAssigned=false;captionsAssigned=false;$('watch-url-load').disabled=true;$('watch-save-form').hidden=true;message('Loading video and subtitles…');
    try{
      const captions=await prepareCaptions(subtitleUrl,!!subtitleUrl);
      if(token!==operation){if(captions.blob)URL.revokeObjectURL(captions.blob);return;}
      clearTimeout(timer);timer=null;direct={videoUrl,subtitleUrl,loaded:false,saved:restore?direct?.saved:null};
      let title=new URL(videoUrl).pathname.split('/').pop()||'URL video';
      try{title=decodeURIComponent(title);}catch{}
      if(!restore)$('watch-save-title').value=title.replace(/\.[a-z0-9]{1,8}$/i,'').slice(0,200);
      $('watch-title').textContent=title;document.title=title+' · HaySub';if($('watch-visibility'))$('watch-visibility').textContent='';
      loadMedia(videoUrl,captions,position,speed,play,token);
      message('Video loaded.');
    }catch(error){if(token===operation)message(error.message,true);}
    finally{if(token===operation){loading=false;$('watch-url-load').disabled=false;saveControls();}}
  }
  async function connect(restore=false){
    if(loading||direct)return;loading=true;mediaAssigned=false;captionsAssigned=false;clearTimeout(timer);const token=++operation;
    const position=restore?video.currentTime:0,wasPlaying=restore&&!video.paused,speed=video.playbackRate;
    message(restore?'Թարմացվում է դիտման հասանելիությունը…':'Բեռնվում է տեսանյութը…');
    try{
      const response=await fetch(endpoint,{cache:'no-store',referrerPolicy:'no-referrer'});
      if(!response.ok){if(response.status===401)throw Error('Մասնավոր նախադիտման համար մուտք գործիր /admin էջում։');if(response.status===404)throw Error('Տեսանյութը հասանելի չէ կամ հրապարակված չէ։');throw Error('Նվագարկիչն այժմ հասանելի չէ։ Փորձիր կրկին։');}
      const access=await response.json();if(token!==operation)return;
      const subtitleUrl=cloudTrack?access.cloud_subtitle_url:access.subtitle_url;
      const captions=await prepareCaptions(subtitleUrl,!!(subtitleUrl&&(access.source_type==='cloud'||cloudTrack&&/\.srt(?:$|[?#])/i.test(subtitleUrl))),access.subtitle_offset||0);
      if(token!==operation){if(captions.blob)URL.revokeObjectURL(captions.blob);return;}
      $('watch-title').textContent=access.title;document.title=access.title+' · HaySub';
      if($('watch-visibility'))$('watch-visibility').textContent=ownerPlayback?'Մասնավոր նախադիտում․ միայն սեփականատիրոջ համար։':access.visibility==='public'?'': 'Այս տեսանյութը ցանկում հրապարակված չէ․ հղումն ունեցող ցանկացած անձ կարող է դիտել։ Սա գաղտնաբառով պաշտպանություն չէ։';
      loadMedia(cloudVideo?access.cloud_video_url:access.video_url,captions,position,speed,wasPlaying||playSelection,token);
      playSelection=false;
      timer=setTimeout(()=>connect(true),Math.max(1000,(access.expires_in-30)*1000));
      if(!progressReady)message('Բեռնվում են տեսանյութի տվյալները…');
    }catch(error){if(token===operation){message(error.message,true);if(!restore)$('watch-title').textContent='Տեսանյութը հասանելի չէ';}}
    finally{if(token===operation)loading=false;}
  }
  video.addEventListener('waiting',()=>{if(!renewing&&!playerHidden)message('Բեռնվում է տեսանյութի հաջորդ հատվածը…');});
  video.addEventListener('playing',()=>{if(!playerHidden&&!statusError)message(direct?($('watch-subtitles')?.disabled?'Playing video.':'Playing with subtitles.'):'');});
  video.addEventListener('canplay',()=>{if(!inline&&!playerHidden&&!statusError)message('');});
  video.addEventListener('error',()=>{if(!playerHidden&&mediaAssigned&&video.error)message('Չհաջողվեց նվագարկել տեսանյութը։ Ստուգիր կապը և սեղմիր «Կրկին միացնել»։ Պատճառը կարող է լինել նաև չաջակցվող ձևաչափը կամ պահոցի CORS կարգավորումը։',true);});
  track.addEventListener('load',subtitles);
  track.addEventListener('error',()=>{if(!playerHidden&&captionsAssigned&&track.readyState===3)message('Հայերեն ենթագրերը չեն բեռնվել։ Ստուգիր կապը կամ խնդրիր սեփականատիրոջը ստուգել պահոցի CORS-ը։',true);});
  $('watch-speed')?.addEventListener('change',()=>{video.playbackRate=Number($('watch-speed').value);});
  $('watch-subtitles')?.addEventListener('change',subtitles);
  $('watch-url-form')?.addEventListener('submit',event=>{event.preventDefault();return loadDirect($('watch-video-url').value,$('watch-subtitle-url').value);});
  $('watch-save-form')?.addEventListener('submit',async event=>{
    event.preventDefault();if(!direct?.loaded||direct.saved||saving||!(inline||preview))return;
    const title=$('watch-save-title').value.trim();if(!title){message('Enter a video name.',true);return;}
    const selected=direct,selectedOperation=operation;saving=true;saveControls();
    try{
      const response=await fetch('/api/owner/media/cloud',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,video_url:selected.videoUrl,subtitle_url:selected.subtitleUrl||null})});
      const saved=await response.json();if(!response.ok)throw Error(typeof saved.detail==='string'?saved.detail:'Could not add this video to the page.');
      selected.saved=saved;
      if(direct===selected&&operation===selectedOperation){
        closePlayer();
        direct=null;
        $('watch-video-url').value='';$('watch-subtitle-url').value='';$('watch-save-title').value='';
        $('watch-title').textContent='Cloud video';document.title='HaySub';
        message('');
      }
      window.dispatchEvent(new CustomEvent('haysub-media-updated',{detail:{item:saved}}));
    }catch(error){if(direct===selected)message(error.message,true);}
    finally{saving=false;saveControls();}
  });
  $('watch-restart')?.addEventListener('click',()=>{
    if(!progressReady||!progressId)return;
    progress?.clear(progressId);video.currentTime=0;$('watch-restart').hidden=true;
  });
  video.addEventListener('timeupdate',()=>{if(Date.now()-lastSave>=5000){saveProgress();lastSave=Date.now();}});
  video.addEventListener('pause',saveProgress);
  video.addEventListener('seeked',saveProgress);
  video.addEventListener('ended',()=>{if(progressId)progress?.clear(progressId);if($('watch-restart'))$('watch-restart').hidden=true;});
  document.addEventListener?.('visibilitychange',()=>{if(document.hidden)saveProgress();});
  $('catalog-back')?.addEventListener('click',()=>saveProgress());
  window.addEventListener('pageshow',event=>{if(event.persisted&&!inline)void connect(true);});
  $('watch-retry')?.addEventListener('click',()=>direct?loadDirect(direct.videoUrl,direct.subtitleUrl,true):connect(true));
  $('watch-close')?.addEventListener('click',()=>{closePlayer();message('');});
  window.addEventListener('haysub-close-video',()=>{closePlayer();message('');});
  window.addEventListener('haysub-play-video',event=>{
    const selected=event.detail;
    if(!inline||!selected||!/^[a-f0-9]{32}$/.test(selected.id))return;
    saveProgress();video.pause();video.hidden=true;if($('watch-controls'))$('watch-controls').hidden=true;playerHidden=true;
    ++operation;clearTimeout(timer);timer=null;loading=false;direct=null;saveControls();
    ownerPlayback=!!selected.owner&&video.getAttribute('data-owner-controls')!=='false';
    endpoint=(ownerPlayback?'/api/owner/media/':'/api/public/hosted/')+selected.id+'/playback';
    playSelection=true;
    const panel=$('cloud-url-player');
    if(panel)panel.hidden=false;
    placePlayer(selected.anchor);
    (stage||panel)?.scrollIntoView({behavior:'smooth',block:'start'});
    void connect();
  });
  $('watch-fullscreen')?.addEventListener('click',async()=>{try{if(video.webkitEnterFullscreen)video.webkitEnterFullscreen();else if(video.requestFullscreen)await video.requestFullscreen();else message('Օգտագործիր նվագարկիչի լիաէկրանի կոճակը։');}catch{message('Օգտագործիր նվագարկիչի լիաէկրանի կոճակը։');}});
  window.addEventListener('pagehide',()=>{saveProgress();clearTimeout(timer);});
  if(inline){$('watch-title').textContent='Cloud video';message('');}
  else void connect();
})();
