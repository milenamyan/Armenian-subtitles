const $=id=>document.getElementById(id);
let player,playerReady=false,apiReady=false,job=null,identity=null,configured=false,started=false,submitting=false,polling=false,lastPosition=-10,renderKey='';
let mountedVideo=null,bufferingSince=null,playbackError='',resumeAt=null;
const setText=(node,text)=>{if(node.textContent!==text)node.textContent=text;};
const notice=(text,error=false)=>{$('notice').textContent=text;$('notice').classList.toggle('error',error);};
async function request(path,options){const r=await fetch(path,options);if(!r.ok){let e=await r.json();throw Error(typeof e.detail==='string'?e.detail:'Հարցումը չի հաջողվել։');}return r.json();}
window.onYouTubeIframeAPIReady=()=>{apiReady=true;};
function mountPlayer(force=false){
  if(!apiReady){notice('YouTube նվագարկիչը դեռ բեռնվում է։ Ստուգիր կապը և կրկնիր։',true);return;}
  if(!force&&player&&playerReady&&mountedVideo===job.video){
    // Changing subtitle files must not restart an already-playing video.
    started=true;lastPosition=-10;sync();return;
  }
  bufferingSince=null;playbackError='';mountedVideo=job.video;
  $('empty').style.display='none';playerReady=false;
  if(player){player.destroy();const node=document.createElement('div');node.id='player';document.querySelector('.screen').append(node);}
  player=new YT.Player('player',{videoId:job.video,playerVars:{playsinline:1,origin:location.origin},events:{
    onReady:()=>{playerReady=true;if(resumeAt!==null){const time=resumeAt;resumeAt=null;started=true;player.loadVideoById({videoId:job.video,startSeconds:time});}else maybeStart();},
    onStateChange:e=>{if(e.data===3){if(bufferingSince===null)bufferingSince=Date.now();}else bufferingSince=null;updatePlaybackStatus();sync();},
    onError:e=>{playbackError=`YouTube player error ${e.data}. `+(({100:'Տեսանյութը հեռացված է կամ մասնավոր է։',101:'Հեղինակն արգելել է ներկառուցված դիտումը։',150:'Հեղինակն արգելել է ներկառուցված դիտումը։',153:'YouTube-ը չի ճանաչել դիտման աղբյուրը։ Բացիր հավելվածը localhost հասցեով։'})[e.data]||'YouTube playback failed.');updatePlaybackStatus();},
    onAutoplayBlocked:()=>notice('Ենթագրերը պատրաստ են։ Սեղմիր նվագարկիչի Play կոճակը։')
  }});
}
function maybeStart(){
  if(started||!playerReady||!job)return;
  if(job.phase==='retrieving')return;
  // Never interrupt native play/pause/buffering with another autoplay command.
  if([1,2,3].includes(player.getPlayerState?.())){started=true;return;}
  const first=job.cues.slice(0,12);
  if(!first.length || !configured || first.every(c=>job.translated[String(c.id)])){
    started=true;player.playVideo();
  }
}
function sync(){
  if(!job||!playerReady)return;
  const time=player.getCurrentTime()||0,offset=Number($('offset').value)||0;
  const state=SubtitleTiming.subtitleState(job.cues,job.translated,time,offset),mode=$('mode').value;
  if(!job.cues.length){$('subtitle').textContent=job.phase==='retrieving'?'Փնտրվում են անգլերեն ենթագրեր…':'Ենթագրերը հասանելի չեն։ Վերբեռնիր .srt կամ .vtt ֆայլ։';$('original').textContent='';return;}
  setText($('subtitle'),(mode==='source')?state.active.map(c=>c.source).join('\n'):state.waiting?'Այս պահի հայերեն ենթագրերը դեռ պատրաստ չեն…':state.active.map(c=>SubtitleTiming.withoutMusicLines(job.translated[String(c.id)]||'')).join('\n'));
  setText($('original'),mode==='both'?state.active.map(c=>c.source).join('\n'):'');
  if(Math.abs(time-lastPosition)>2){lastPosition=time;request(`/api/videos/${identity}/position`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({seconds:Math.max(0,time-offset)})}).catch(()=>{});}
}
function transcript(){
  const key=identity+':'+job.cues.length+':'+Object.keys(job.translated).length+':'+$('mode').value;
  if(key===renderKey)return;renderKey=key;$('transcript').replaceChildren();
  for(const cue of job.cues){if(SubtitleTiming.isMusicOnly(cue.source))continue;const row=document.createElement('div');row.className='cue';const b=document.createElement('button');b.textContent=new Date(cue.start*1000).toISOString().slice(11,19);b.onclick=()=>{if(playerReady){player.seekTo(Math.max(0,cue.start+(Number($('offset').value)||0)),true);lastPosition=-10;sync();}};const p=document.createElement('p');p.textContent=($('mode').value==='source')?SubtitleTiming.withoutMusicLines(cue.source):(SubtitleTiming.withoutMusicLines(job.translated[String(cue.id)]||'')||'Սպասում է թարգմանությանը…')+($('mode').value==='both'?'\n'+SubtitleTiming.withoutMusicLines(cue.source):'');row.append(b,p);$('transcript').append(row);}
}
async function history(){const items=await request('/api/videos');$('history').replaceChildren();if(!items.length){$('history').textContent='Դեռևս տեսանյութեր չկան։';return;}for(const item of items){const b=document.createElement('button');b.textContent='▶ '+item.video;const small=document.createElement('small');small.textContent=item.created;b.append(small);b.onclick=async()=>{try{if(!apiReady)throw Error('YouTube API-ն դեռ հասանելի չէ։ Ստուգիր կապը և կրկնիր։');job=await request('/api/videos/'+item.id);identity=item.id;started=false;lastPosition=-10;if(!configured)$('mode').value='source';if(!job.cues.length)job.phase='retrieving';$('upload-fallback').hidden=true;mountPlayer();transcript();if(configured||!job.cues.length)await request(`/api/videos/${identity}/retry`,{method:'POST'});}catch(e){notice(e.message,true);}};$('history').append(b);}}
$('file').onchange=()=>{$('filename').textContent=$('file').files[0]?.name||'Ավելացնել ենթագրեր';};
$('form').onsubmit=async e=>{e.preventDefault();if(submitting)return;if(!apiReady){notice('YouTube API-ն դեռ հասանելի չէ։ Ստուգիր կապը և կրկնիր։',true);return;}submitting=true;$('submit').disabled=true;try{const data=new FormData($('form'));job=await request('/api/videos',{method:'POST',body:data});identity=job.id;started=false;lastPosition=-10;renderKey='';$('upload-fallback').hidden=true;if(!configured)$('mode').value='source';mountPlayer();transcript();await history();notice(job.phase==='retrieving'?'Ստացվում են անգլերեն ենթագրեր…':configured?'Թարգմանվում է առաջին հատվածը…':'Բնագրի դիտում։ Հայերեն թարգմանության համար լրացրու .env կարգավորումը։');}catch(e){notice(e.message,true);}finally{submitting=false;$('submit').disabled=false;}};
$('retry').onclick=async()=>{if(!identity)return;try{await request(`/api/videos/${identity}/retry`,{method:'POST'});notice(job.cues.length?'Թարգմանության նոր փորձ…':'Ենթագրերի ստացման նոր փորձ…');}catch(e){notice(e.message,true);}};
$('size').oninput=()=>{$('subtitle').style.fontSize=$('size').value+'px';};
$('mode').onchange=()=>{if(job){transcript();sync();}};$('offset').oninput=()=>{lastPosition=-10;sync();};
setInterval(sync,250);
setInterval(async()=>{if(!identity||polling)return;polling=true;const id=identity;try{const current=await request('/api/videos/'+id);if(id!==identity)return;job=current;const count=Object.keys(job.translated).length;$('progress').textContent=`${count} / ${job.cues.length} ենթագիր`;
  $('retry').hidden=false;
  $('retry').textContent=job.cues.length?'Կրկնել թարգմանությունը':'Կրկնել ենթագրերի ստացումը';
  $('upload-fallback').hidden=!(job.error && !job.cues.length);
  if(job.phase==='retrieving'){$('progress').textContent='Փնտրվում են ենթագրեր…';notice('Ստացվում են անգլերեն ենթագրեր․ նախ՝ հեղինակի, ապա՝ ավտոմատ։');}
  else if(job.error)notice(job.error,true);else if(job.running){
    const section=job.active_chunk?` · cues ${job.active_chunk.first}–${job.active_chunk.last} · ${job.chunk_elapsed_seconds||0}s elapsed`:'';
    notice(`Translating · ${count} / ${job.cues.length} subtitles ready${section}`);
  }else if(count && count===job.cues.length)notice('Հայերեն ենթագրերը պատրաստ են։');
  else if(job.cues.length && !configured)notice('Անգլերեն ենթագրերը պատրաստ են։ Հայերեն թարգմանության համար լրացրու GEMINI_API_KEY և GEMINI_MODEL-ը .env-ում։');
  transcript();maybeStart();sync();
}catch(e){notice('Սերվերի կապը ընդհատվել է։ '+e.message,true);}finally{polling=false;}},1000);
request('/api/config').then(c=>{configured=c.configured;notice(configured?'Gemini-ն կարգավորված է։ Ավելացրու տեսանյութ և ենթագրեր։':'Հայերեն թարգմանության համար .env-ում լրացրու GEMINI_API_KEY և GEMINI_MODEL։ Բնագրի դիտումը հասանելի է։');}).catch(e=>notice(e.message,true));history().catch(e=>notice(e.message,true));

// Keep the existing file-upload flow as the fallback; no new upload pipeline.
const uploadFallback=document.createElement('button');
uploadFallback.id='upload-fallback';uploadFallback.className='secondary';uploadFallback.hidden=true;
uploadFallback.textContent='Վերբեռնել ենթագրեր';
uploadFallback.onclick=()=>{$('form').scrollIntoView({behavior:'smooth'});$('file').click();};
$('retry').before(uploadFallback);

function updatePlaybackStatus(){
  if(!job||!playerReady)return;
  const state=player.getPlayerState?.();
  const elapsed=bufferingSince===null?0:Math.floor((Date.now()-bufferingSince)/1000);
  const labels={'-1':'ready to start',0:'ended',1:'playing',2:'paused',3:'buffering',5:'ready to play'};
  const loaded=player.getVideoLoadedFraction?.();
  const percent=Number.isFinite(loaded)?` · ${Math.round(loaded*100)}% loaded`:'';
  setText($('playback-status'),playbackError||`YouTube: ${labels[state]||'connecting'}${state===3?` · ${elapsed}s`:''}${percent}`);
  $('reload-player').hidden=!playbackError&&!(state===3&&elapsed>=15);
}
$('reload-player').onclick=()=>{
  if(!job||!playerReady)return;
  resumeAt=Math.max(0,player.getCurrentTime()||0);started=false;
  mountPlayer(true);
};
// Playback status is separate from Gemini progress; neither timer controls video playback.
setInterval(updatePlaybackStatus,1000);
