/* Overlay adapter: only reads the video clock. It never plays, pauses or seeks. */
(() => {
  'use strict';
  globalThis.__haySubOverlay?.dispose();
  const C=globalThis.HaySubCore;
  const site=globalThis.HaySubSiteConfig||null;
  let mediaChanged=false,mediaSource='',lastFileStamp=null;
  const identity=()=>site?(location.href===site.frameUrl?site.key:null):C.videoId(location.href);
  let disposed=false,navigating=false,videoId=null,video=null,container=null,host=null,region=null,caption=null;
  let options=C.settings(),delay=0,record=null,index=C.timeline([]),error='',ignored=0;
  let frame=0,reconcileFrame=0,revision=0,lastText=null,lastGeometry='',restorePosition=null;
  let resizeObserver=null,adObserver=null;
  const videoListeners=[];
  const mediaEvents=['play','pause','playing','waiting','stalled','seeking','seeked','ratechange','timeupdate','loadedmetadata','durationchange','emptied','ended','resize'];

  function hide() { if(host)host.style.display='none'; }
  function stopFrame() { if(frame)cancelAnimationFrame(frame);frame=0; }
  function detach() {
    stopFrame();
    for(const [name,fn] of videoListeners)video?.removeEventListener(name,fn);
    videoListeners.length=0;
    resizeObserver?.disconnect();adObserver?.disconnect();resizeObserver=adObserver=null;
    host?.remove();
    if(container && restorePosition!==null)container.style.position=restorePosition;
    restorePosition=null;video=container=host=region=caption=null;lastText=null;lastGeometry='';
  }

  function layout() {
    const rect=C.pictureRect(video.getBoundingClientRect(),container.getBoundingClientRect(),video.videoWidth,video.videoHeight,getComputedStyle(video).objectFit);
    if(rect.width<=0 || rect.height<=0){hide();return false;}
    const bottom=Math.min(Math.max(48,rect.height*options.verticalPosition/100),Math.max(0,rect.height-24));
    const font=Math.min(options.fontSize,Math.max(12,rect.width/12));
    const signature=JSON.stringify([rect,bottom,font,options]);
    if(signature!==lastGeometry) {
      lastGeometry=signature;
      Object.assign(region.style,{left:`${rect.left}px`,top:`${rect.top}px`,width:`${rect.width}px`,height:`${rect.height}px`});
      Object.assign(caption.style,{bottom:`${bottom}px`,fontSize:`${font}px`,color:options.textColor,backgroundColor:`rgba(0,0,0,${options.backgroundOpacity})`,maxHeight:`${Math.max(12,rect.height-bottom-8)}px`});
    }
    return true;
  }

  function render() {
    if(!video || !host || navigating || mediaChanged || identity()!==videoId || !options.enabled || !record || error || video.readyState===0 || container.classList.contains('ad-showing') || container.classList.contains('ad-interrupting')) {hide();return;}
    // No wall-clock extrapolation: buffering, speed changes and seeks use this same clock.
    const active=index.at(video.currentTime,delay);
    const text=active.map(c=>C.withoutMusicLines(c.text)).filter(Boolean).join('\n');
    if(!text){hide();return;}
    if(text!==lastText){caption.textContent=text;lastText=text;lastGeometry='';}
    if(!layout())return;
    host.style.display='block';
    // Shrink unusually long/multiline overlaps to stay within the picture.
    const maxHeight=parseFloat(caption.style.maxHeight);
    if(caption.scrollHeight>maxHeight){
      const size=parseFloat(caption.style.fontSize);
      caption.style.fontSize=`${Math.max(8,size*maxHeight/caption.scrollHeight)}px`;
    }
  }

  function tick() {
    frame=0;render();
    if(video && !video.paused && !video.ended && !document.hidden)frame=requestAnimationFrame(tick);
  }
  function sync() {
    stopFrame();render();
    if(video && !video.paused && !video.ended && !document.hidden)frame=requestAnimationFrame(tick);
  }

  function attach(next) {
    detach();video=next;
    container=site&&document.fullscreenElement&&document.fullscreenElement!==video&&document.fullscreenElement.contains(video)
      ?document.fullscreenElement:(video.closest('#movie_player') || video.parentElement);
    if(!container){video=null;return;}
    if(getComputedStyle(container).position==='static'){restorePosition=container.style.position;container.style.position='relative';}
    // Remove only our stale host, never any YouTube caption elements.
    container.querySelectorAll('[data-haysub-overlay]').forEach(n=>n.remove());
    host=document.createElement('div');host.dataset.haysubOverlay='true';host.setAttribute('aria-hidden','true');
    Object.assign(host.style,{position:'absolute',inset:'0',pointerEvents:'none',zIndex:'40',overflow:'hidden',display:'none'});
    const shadow=host.attachShadow({mode:'closed'});
    const style=document.createElement('style');
    style.textContent=':host{pointer-events:none!important}.region{position:absolute;overflow:hidden;pointer-events:none}.caption{position:absolute;left:50%;transform:translateX(-50%);width:max-content;max-width:calc(100% - 24px);box-sizing:border-box;padding:.18em .45em;border-radius:5px;white-space:pre-line;overflow-wrap:anywhere;text-align:center;font-family:Arial,"Noto Sans Armenian",sans-serif;font-weight:600;line-height:1.35;text-shadow:0 1px 3px #000;overflow:hidden;pointer-events:none;user-select:none}';
    region=document.createElement('div');region.className='region';
    caption=document.createElement('div');caption.className='caption';
    region.append(caption);shadow.append(style,region);container.append(host);
    if(site&&video.currentSrc&&!mediaSource)mediaSource=video.currentSrc;
    for(const name of [...mediaEvents,'loadstart']){const fn=()=>{
      if(site&&name==='loadedmetadata'&&video.currentSrc){if(mediaSource&&mediaSource!==video.currentSrc){mediaChanged=true;globalThis.HaySubTranslationClient?.activate(null);}mediaSource=video.currentSrc;}
      sync();
    };video.addEventListener(name,fn);videoListeners.push([name,fn]);}
    resizeObserver=new ResizeObserver(()=>{lastGeometry='';render();});resizeObserver.observe(video);resizeObserver.observe(container);
    adObserver=new MutationObserver(()=>sync());adObserver.observe(container,{attributes:true,attributeFilter:['class']});
    sync();
  }

  async function load() {
    const token=++revision,id=videoId;
    try {
      const keys=[C.SETTINGS_KEY,C.FILE_PREFIX+id,C.OFFSET_PREFIX+id];
      const saved=await chrome.storage.local.get(keys);
      if(disposed || id!==videoId || token!==revision)return;
      options=C.settings(saved[C.SETTINGS_KEY]);delay=C.offset(saved[C.OFFSET_PREFIX+id]);
      const next=saved[C.FILE_PREFIX+id];
      if(site&&next&&(next.selectionId||next.updatedAt)!==lastFileStamp){mediaChanged=false;lastFileStamp=next.selectionId||next.updatedAt;mediaSource=video?.currentSrc||'';globalThis.HaySubTranslationClient?.activate(videoId,()=>Math.max(0,(video?.currentTime||0)-delay));}
      if(next && typeof next.text==='string') {
        if(!record || record.text!==next.text){const parsed=next.text?C.parse(next.text):{cues:[],ignored:0};index=C.timeline(parsed.cues);ignored=parsed.ignored;}
        record=next;
      } else {record=null;index=C.timeline([]);ignored=0;}
      error='';lastText=null;lastGeometry='';sync();
    } catch {if(token===revision){error='Չհաջողվեց կարդալ պահպանված ենթագրերը։ Մաքրիր այս տեսանյութի ֆայլը և վերբեռնիր կրկին։';record=null;index=C.timeline([]);hide();}}
  }

  function reconcile() {
    reconcileFrame=0;if(disposed || navigating)return;
    const nextId=identity();
    if(nextId!==videoId){revision++;detach();videoId=nextId;record=null;index=C.timeline([]);error='';globalThis.HaySubTranslationClient?.activate(videoId,()=>Math.max(0,(video?.currentTime||0)-delay));if(videoId)void load();}
    if(!videoId){detach();return;}
    const next=site?document.querySelectorAll('video')[site.videoIndex]:document.querySelector('#movie_player video.html5-main-video') || document.querySelector('video.html5-main-video') || document.querySelector('ytd-player video');
    if(next!==video || (host && !host.isConnected)){if(site&&video&&next!==video){mediaChanged=true;globalThis.HaySubTranslationClient?.activate(null);}if(next)attach(next);else detach();}
  }
  function schedule() {if(!disposed && !reconcileFrame)reconcileFrame=requestAnimationFrame(reconcile);}
  function navigationStart(){navigating=true;revision++;detach();videoId=null;record=null;index=C.timeline([]);globalThis.HaySubTranslationClient?.activate(null);}
  function navigationFinish(){navigating=false;schedule();}
  function resized(){
    if(site&&video){const expected=document.fullscreenElement&&document.fullscreenElement!==video&&document.fullscreenElement.contains(video)?document.fullscreenElement:(video.closest('#movie_player')||video.parentElement);if(expected!==container){const same=video;attach(same);}}
    lastGeometry='';render();schedule();
  }
  function changed(changes,area){if(area==='local' && (changes[C.SETTINGS_KEY] || changes[C.FILE_PREFIX+videoId] || changes[C.OFFSET_PREFIX+videoId]))void load();}
  function message(msg,sender,respond){
    if(msg?.type==='HAYSUB_DEACTIVATE'&&site){dispose();respond({ok:true});return;}
    if(msg?.type!=='HAYSUB_STATUS')return;
    reconcile();
    respond({videoId,site:!!site,mediaChanged,navigating,hasVideo:!!video,fileName:record?.name||null,cueCount:record?indexCount():0,ignored,error});
  }
  function indexCount(){try{return C.parse(record.text).cues.length;}catch{return 0;}}
  const pageObserver=new MutationObserver(schedule);pageObserver.observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('yt-navigate-start',navigationStart);
  document.addEventListener('yt-navigate-finish',navigationFinish);
  window.addEventListener('popstate',navigationFinish);
  window.addEventListener('resize',resized);
  document.addEventListener('fullscreenchange',resized);
  document.addEventListener('visibilitychange',sync);
  chrome.storage.onChanged.addListener(changed);
  chrome.runtime.onMessage.addListener(message);
  function dispose(){
    if(disposed)return;disposed=true;revision++;detach();pageObserver.disconnect();
    globalThis.HaySubTranslationClient?.activate(null);
    if(reconcileFrame)cancelAnimationFrame(reconcileFrame);
    document.removeEventListener('yt-navigate-start',navigationStart);document.removeEventListener('yt-navigate-finish',navigationFinish);
    window.removeEventListener('popstate',navigationFinish);window.removeEventListener('resize',resized);
    document.removeEventListener('fullscreenchange',resized);document.removeEventListener('visibilitychange',sync);
    chrome.storage.onChanged.removeListener(changed);chrome.runtime.onMessage.removeListener(message);
  }
  globalThis.__haySubOverlay={dispose};
  reconcile();
})();
