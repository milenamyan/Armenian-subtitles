(() => {
  'use strict';
  const $=id=>document.getElementById(id),progress=globalThis.HaySubProgress;
  const stateKey='haysub:catalog:v1';
  let items=[],loaded=false,state={scroll:0};
  try{const saved=JSON.parse(sessionStorage.getItem(stateKey));if(saved)state={scroll:Number.isFinite(saved.scroll)?saved.scroll:0};}catch{}
  function remember(){try{sessionStorage.setItem(stateKey,JSON.stringify({scroll:window.scrollY}));}catch{}}
  function element(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
  function durationText(seconds){const total=Math.floor(seconds),hours=Math.floor(total/3600),minutes=Math.floor(total%3600/60);return hours?hours+':'+String(minutes).padStart(2,'0')+':'+String(total%60).padStart(2,'0'):minutes+':'+String(total%60).padStart(2,'0');}
  function card(item){
    const link=element('a',undefined,'movie-card');link.href='/watch/'+encodeURIComponent(item.id);link.setAttribute('aria-label',item.title);link.title=item.title;link.addEventListener('click',remember);
    const thumbnail=element('div',undefined,'movie-thumbnail'),image=element('img');
    image.alt='';image.loading='lazy';image.width=240;image.height=360;
    image.src=item.poster_url||'/static/poster-fallback.svg';
    image.addEventListener('error',()=>{image.src='/static/poster-fallback.svg';},{once:true});thumbnail.append(image);
    const saved=progress.read(item.id,item.duration),duration=item.duration||progress.duration(item.id)||saved?.duration;
    const badge=element('span',Number.isFinite(duration)&&duration>0?durationText(duration):'—:—','movie-duration');
    if(!duration&&progress.loadDuration)void (async()=>{
      try{
        const response=await fetch('/api/public/hosted/'+encodeURIComponent(item.id)+'/playback',{cache:'no-store'});
        if(!response.ok)return;
        const access=await response.json(),length=access.duration||await progress.loadDuration(item.id,access.video_url);
        if(length){item.duration=length;badge.textContent=durationText(length);}
      }catch{}
    })();
    thumbnail.append(badge);
    if(saved){const bar=element('span',undefined,'movie-progress'),fill=element('span');fill.style.width=(saved.position/saved.duration*100)+'%';bar.setAttribute('aria-hidden','true');bar.append(fill);thumbnail.append(bar);}
    if(item.is_new===true)thumbnail.append(element('span','ՆՈՐ','movie-new-badge'));
    link.append(thumbnail,element('h3',item.title));return link;
  }
  function render(){
    if(!loaded)return;
    $('public-videos').replaceChildren(...items.map(card));
    $('catalog-section').hidden=!items.length;
    $('public-video-status').textContent=!items.length?'Դեռ հրապարակված ֆիլմեր չկան։ Նոր ֆիլմերը կհայտնվեն այստեղ։':'';
    $('public-video-status').hidden=!!items.length;
  }
  window.addEventListener('pagehide',remember);
  window.addEventListener('pageshow',event=>{render();if(event?.persisted)void load();});
  window.addEventListener('focus',()=>{if(loaded)void load();});
  window.addEventListener('storage',render);
  async function load(){
    try{
      const restoreScroll=!loaded;
      const response=await fetch('/api/public/videos',{cache:'no-store'});
      if(!response.ok)throw Error('Չհաջողվեց բեռնել ֆիլմերը։ Փորձիր կրկին։');
      items=(await response.json()).sort((a,b)=>(b.published_at||0)-(a.published_at||0));loaded=true;render();
      if(restoreScroll)requestAnimationFrame(()=>window.scrollTo(0,Math.max(0,state.scroll)));
    }catch(error){$('public-video-status').hidden=false;$('public-video-status').textContent=error.message;}
  }
  void load();
})();
