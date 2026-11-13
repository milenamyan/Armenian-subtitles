// Expand the page player, keeping its controls and captions in the same DOM.
(() => {
  'use strict';
  const video=document.getElementById('hosted-player');
  if(!video)return;
  const frame=document.createElement('div');
  frame.className='player-frame';
  video.before(frame);
  const surface=document.createElement('div');
  surface.className='player-surface';
  frame.append(surface);
  surface.append(video);
  let height=document.getElementById('watch-subtitle-up')?.parentElement;
  const options=document.createElement('button');
  options.type='button';options.className='player-options-toggle';
  options.innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="5" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="12" cy="19" r="1.5"/></svg>';
  options.setAttribute('aria-label','Ենթագրերի կարգավորումներ');
  options.setAttribute('title','Ենթագրերի կարգավորումներ');
  options.setAttribute('aria-expanded','false');
  options.setAttribute('aria-controls','player-subtitle-options');
  const panel=document.createElement('div');
  panel.id='player-subtitle-options';panel.className='player-options-panel';panel.hidden=true;
  if(!height){
    height=document.createElement('div');height.className='subtitle-position';
    const title=document.createElement('span');title.textContent='Ենթագրերի բարձրություն';height.append(title);
    const up=document.createElement('button'),down=document.createElement('button');
    up.type=down.type='button';up.textContent='↑ Վերև';down.textContent='↓ Ներքև';
    height.append(up);height.append(down);
    const key='haysub-subtitle-height-buttons';let value=10;
    try{const saved=globalThis.localStorage?.getItem(key);if(saved!==null&&saved!==undefined&&Number.isFinite(Number(saved)))value=Math.max(0,Math.min(40,Number(saved)));}catch{}
    function position(){
      up.disabled=value>=40;down.disabled=value<=0;
      for(const item of video.textTracks||[])for(const cue of item.cues||[]){cue.snapToLines=value===0;cue.line=value===0?-1:100-value;cue.lineAlign='end';}
    }
    function move(amount){value=Math.max(0,Math.min(40,value+amount));position();try{globalThis.localStorage?.setItem(key,String(value));}catch{}}
    up.addEventListener('click',()=>move(2));down.addEventListener('click',()=>move(-2));
    document.getElementById('armenian-track')?.addEventListener('load',position);
    video.textTracks?.addEventListener?.('addtrack',position);
    position();
  }
  panel.append(height);surface.append(panel);surface.append(options);
  function closeOptions(focus=false){panel.hidden=true;options.setAttribute('aria-expanded','false');if(focus)options.focus();}
  options.addEventListener('click',()=>{panel.hidden=!panel.hidden;options.setAttribute('aria-expanded',String(!panel.hidden));});
  document.addEventListener('pointerdown',event=>{if(!panel.hidden&&!panel.contains(event.target)&&!options.contains(event.target))closeOptions();});
  const controls=document.getElementById('watch-controls');
  if(controls)frame.append(controls);
  let button=document.getElementById('watch-fullscreen')||document.getElementById('fullscreen');
  if(!button){
    button=document.createElement('button');
    button.type='button';
  }
  button.className='player-fullscreen-toggle';
  surface.append(button);
  const expandIcon='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/></svg>';
  const collapseIcon='<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 8h5V3m8 0v5h5M8 21v-5H3m18 0h-5v5"/></svg>';
  function label(active){
    const text=active?'Փակել լիաէկրանը':'Լիաէկրան';
    button.textContent='';button.innerHTML=active?collapseIcon:expandIcon;
    button.setAttribute('aria-label',text);button.setAttribute('title',text);
    button.setAttribute('aria-pressed',String(active));
  }
  label(false);
  let expanded=false,previousOverflow='';
  function update(active){
    closeOptions();
    expanded=active;
    frame.classList.toggle('player-expanded',active);
    label(active);
    if(active){previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';}
    else document.body.style.overflow=previousOverflow;
  }
  async function exit(){
    if(document.fullscreenElement===frame)await document.exitFullscreen();
    else if(document.webkitFullscreenElement===frame)document.webkitExitFullscreen();
    if(expanded)update(false);
  }
  button.addEventListener('click',async()=>{
    if(expanded){await exit();return;}
    update(true);
    try{
      if(frame.requestFullscreen)await frame.requestFullscreen();
      else if(frame.webkitRequestFullscreen)await frame.webkitRequestFullscreen();
      // Otherwise the fixed page layout provides fullscreen on mobile Safari.
    }catch{/* Keep the expanded page layout if native fullscreen is unavailable. */}
  });
  function changed(){
    if(expanded&&document.fullscreenElement!==frame&&document.webkitFullscreenElement!==frame)update(false);
  }
  document.addEventListener('fullscreenchange',changed);
  document.addEventListener('webkitfullscreenchange',changed);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){if(!panel.hidden){event.preventDefault?.();closeOptions(true);}else if(expanded)void exit();}});
  document.getElementById('watch-close')?.addEventListener('click',()=>{if(expanded)void exit();});
  window.addEventListener('haysub-close-video',()=>{if(expanded)void exit();});
  // Use the page's fullscreen button instead of entering native video fullscreen.
  video.controlsList?.add('nofullscreen');
})();
