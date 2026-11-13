(() => {
  'use strict';
  const $=id=>document.getElementById(id),progress=globalThis.HaySubProgress,model=globalThis.HaySubCatalog;
  let films=[];
  const stateKey='haysub:static-catalog:scroll';
  function element(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
  function card(item){
    const link=element('a',undefined,'movie-card');link.href='watch.html?id='+encodeURIComponent(item.id);link.title=item.title;
    const thumbnail=element('div',undefined,'movie-thumbnail'),image=element('img');image.alt='';image.loading='lazy';image.width=240;image.height=360;image.src=item.poster_url||'assets/poster-fallback.svg';
    image.addEventListener('error',()=>{image.src='assets/poster-fallback.svg';},{once:true});thumbnail.append(image);
    const saved=progress.read(item.id,item.duration),duration=item.duration||progress.duration(item.id)||saved?.duration;
    const badge=element('span',model.durationText(duration),'movie-duration');thumbnail.append(badge);
    if(!duration)progress.loadDuration?.(item.id,item.video_url).then(length=>{
      if(length){item.duration=length;badge.textContent=model.durationText(length);}
    });
    if(saved){const bar=element('span',undefined,'movie-progress'),fill=element('span');fill.style.width=Math.min(100,saved.position/saved.duration*100)+'%';bar.setAttribute('aria-hidden','true');bar.append(fill);thumbnail.append(bar);}
    if(item.is_new===true)thumbnail.append(element('span','ՆՈՐ','movie-new-badge'));
    link.append(thumbnail,element('h3',item.title));return link;
  }
  function render(){
    const query=$('search').value.trim().toLocaleLowerCase(),shown=films.filter(item=>item.title.toLocaleLowerCase().includes(query));
    $('public-videos').replaceChildren(...shown.map(card));
    $('catalog-status').hidden=shown.length>0;
    $('catalog-status').textContent=films.length?'Ֆիլմ չի գտնվել։':'Դեռ հրապարակված ֆիլմեր չկան։';
  }
  $('search').addEventListener('input',render);
  window.addEventListener('pagehide',()=>{try{sessionStorage.setItem(stateKey,String(window.scrollY));}catch{}});
  window.addEventListener('pageshow',()=>{if(films.length)render();});window.addEventListener('storage',()=>{if(films.length)render();});
  (async()=>{try{
    const response=await fetch('catalog.json',{cache:'no-store'});if(!response.ok)throw Error();
    films=model.validate(await response.json());render();
    try{const scroll=Number(sessionStorage.getItem(stateKey));if(Number.isFinite(scroll))requestAnimationFrame(()=>window.scrollTo(0,Math.max(0,scroll)));}catch{}
  }catch{$('catalog-status').hidden=false;$('catalog-status').textContent='Չհաջողվեց բեռնել ֆիլմերը։ Թարմացրու էջը կամ փորձիր ավելի ուշ։';}})();
})();
