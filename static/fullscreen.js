// Expand the page player, keeping its controls and captions in the same DOM.
(() => {
  'use strict';
  const video=document.getElementById('hosted-player');
  if(!video)return;
  const frame=document.createElement('div');
  frame.className='player-frame';
  video.before(frame);
  frame.append(video);
  const height=document.getElementById('watch-subtitle-up')?.parentElement;
  if(height)frame.append(height);
  const controls=document.getElementById('watch-controls');
  if(controls)frame.append(controls);
  let button=document.getElementById('watch-fullscreen')||document.getElementById('fullscreen');
  if(!button){
    button=document.createElement('button');
    button.type='button';button.className='secondary';
    frame.append(button);
  }
  const enterLabel=button.textContent||'Լիաէկրան';
  let expanded=false,previousOverflow='';
  function update(active){
    expanded=active;
    frame.classList.toggle('player-expanded',active);
    button.textContent=active?'Փակել լիաէկրանը':enterLabel;
    button.setAttribute('aria-pressed',String(active));
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
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&expanded)void exit();});
  document.getElementById('watch-close')?.addEventListener('click',()=>{if(expanded)void exit();});
  window.addEventListener('haysub-close-video',()=>{if(expanded)void exit();});
  // Use the page's fullscreen button instead of entering native video fullscreen.
  video.controlsList?.add('nofullscreen');
})();
