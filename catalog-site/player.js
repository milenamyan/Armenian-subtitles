(() => {
  'use strict';
  const $=id=>document.getElementById(id),video=$('hosted-player'),track=$('armenian-track'),progress=globalThis.HaySubProgress;
  const id=new URLSearchParams(location.search).get('id');
  let item=null,blob=null,attempt=0,ready=false,lastSave=0,captionError=false;
  function message(text){$('watch-status').textContent=text;$('watch-status').hidden=!text;}
  function subtitles(){if(track.track)track.track.mode=$('subtitle-choice').value==='hy'?'showing':'disabled';}
  function save(){if(ready&&!video.seeking)progress.save(id,video.currentTime,video.duration);}
  function restartButton(){$('restart').hidden=!progress.read(id,video.duration);}
  async function load(){
    const token=++attempt,position=ready?video.currentTime:null;
    save();ready=false;captionError=false;video.pause();message('Բեռնվում է տեսանյութը…');
    $('watch-title').textContent=item.title;document.title=item.title+' · HaySub';
    // Keep the media playable even when a separate subtitle request fails.
    let captions=item.subtitle_url,newBlob=null;
    if(captions&&(!/\.vtt(?:$|[?#])/i.test(captions)||item.subtitle_offset)){
      try{
        const response=await fetch(captions,{referrerPolicy:'no-referrer'});if(!response.ok)throw Error();
        const text=globalThis.HaySubMediaSources.srtToVtt(await response.text(),item.subtitle_offset||0);
        if(token!==attempt)return;
        newBlob=URL.createObjectURL(new Blob([text],{type:'text/vtt'}));captions=newBlob;
      }catch{if(token!==attempt)return;captions='';captionError=true;message('Ենթագրերը չեն բեռնվել։ Ստուգիր ենթագրի հղումը և R2 CORS կարգավորումը։');}
    }
    if(token!==attempt){if(newBlob)URL.revokeObjectURL(newBlob);return;}
    if(captions)track.src=captions;else track.removeAttribute('src');
    const old=blob;blob=newBlob;if(old)URL.revokeObjectURL(old);
    track.default=$('subtitle-choice').value==='hy';$('subtitle-choice').disabled=!captions;
    video.addEventListener('loadedmetadata',()=>{
      if(token!==attempt)return;
      const saved=progress.read(id,video.duration),target=position??saved?.position??0;
      if(Number.isFinite(video.duration)&&target>0)video.currentTime=Math.min(target,Math.max(0,video.duration-.1));
      ready=true;lastSave=Date.now();video.playbackRate=Number($('speed').value);progress.rememberDuration(id,video.duration);restartButton();subtitles();if(!captionError)message('');
    },{once:true});
    video.src=item.video_url;video.hidden=false;$('watch-controls').hidden=false;video.load();
  }
  track.addEventListener('load',subtitles);
  track.addEventListener('error',()=>{captionError=true;message('Ենթագրերը չեն բեռնվել։ Ստուգիր ենթագրի հղումը և R2 CORS կարգավորումը։');});
  $('subtitle-choice').addEventListener('change',subtitles);
  // Reflect native mobile caption-menu choices without forcing captions back on.
  video.textTracks.addEventListener?.('change',()=>{if(track.track)$('subtitle-choice').value=track.track.mode==='showing'?'hy':'off';});
  $('speed').addEventListener('change',()=>{video.playbackRate=Number($('speed').value);});
  $('restart').addEventListener('click',()=>{progress.clear(id);video.currentTime=0;restartButton();});
  $('retry').addEventListener('click',()=>{if(item)void load();});
  video.addEventListener('timeupdate',()=>{if(Date.now()-lastSave>=5000){save();lastSave=Date.now();}});
  video.addEventListener('pause',save);video.addEventListener('seeked',save);
  video.addEventListener('ended',()=>{progress.clear(id);restartButton();});
  video.addEventListener('waiting',()=>{if(!captionError)message('Բեռնվում է տեսանյութի հաջորդ հատվածը…');});
  video.addEventListener('playing',()=>{if(!captionError)message('');});
  video.addEventListener('error',()=>message('Տեսանյութը չի բեռնվել։ Ստուգիր տեսանյութի հղումը, կապը և R2 CORS կարգավորումը։'));
  window.addEventListener('pagehide',save);document.addEventListener('visibilitychange',()=>{if(document.hidden)save();});
  (async()=>{try{
    const response=await fetch('catalog.json',{cache:'no-store'});if(!response.ok)throw Error();
    item=globalThis.HaySubCatalog.validate(await response.json()).find(film=>film.id===id);
    if(!item){$('watch-title').textContent='Ֆիլմը հասանելի չէ';message('Վերադարձիր ֆիլմերի ցանկ։');return;}
    await load();
  }catch{message('Չհաջողվեց բեռնել ֆիլմը։ Թարմացրու էջը կամ փորձիր ավելի ուշ։');}})();
})();
