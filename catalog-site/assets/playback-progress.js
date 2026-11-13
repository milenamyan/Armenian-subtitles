/* Browser-local progress shared by the catalog and native player. */
(() => {
  'use strict';
  const prefix='haysub:progress:v1:';
  const openedIds=new Set();
  function markOpened(id){
    if(!id)return;
    openedIds.add(id);
    try{localStorage.setItem(prefix+'opened:'+id,'1');}catch{}
  }
  function hasOpened(id){
    if(openedIds.has(id))return true;
    try{return localStorage.getItem(prefix+'opened:'+id)==='1';}catch{return false;}
  }
  function read(id,duration){
    try{
      const entry=JSON.parse(localStorage.getItem(prefix+id));
      if(!entry||!Number.isFinite(entry.position)||entry.position<=0||!Number.isFinite(entry.duration)||entry.duration<=0||!Number.isFinite(entry.updated))return null;
      const length=Number.isFinite(duration)&&duration>0?duration:entry.duration;
      const position=Math.min(entry.position,length);
      return length-position<=30?null:{position,duration:length,updated:entry.updated};
    }catch{return null;}
  }
  function clear(id){try{localStorage.removeItem(prefix+id);}catch{}}
  function save(id,position,duration){
    if(!Number.isFinite(position)||position<0||!Number.isFinite(duration)||duration<=0)return;
    position=Math.min(position,duration);
    if(duration-position<=30){clear(id);return;}
    if(position===0)return;
    try{localStorage.setItem(prefix+id,JSON.stringify({position,duration,updated:Date.now()}));}catch{}
  }
  function rememberDuration(id,duration){if(Number.isFinite(duration)&&duration>0)try{localStorage.setItem(prefix+'duration:'+id,String(duration));}catch{}}
  function duration(id){try{const value=Number(localStorage.getItem(prefix+'duration:'+id));return Number.isFinite(value)&&value>0?value:null;}catch{return null;}}
  const probes=new Map();
  function loadDuration(id,url){
    const cached=duration(id);if(cached)return Promise.resolve(cached);
    if(probes.has(id))return probes.get(id);
    const probe=new Promise(resolve=>{
      const video=document.createElement('video');video.preload='metadata';video.muted=true;
      let timer;
      function finish(value){
        clearTimeout(timer);video.removeEventListener('loadedmetadata',loaded);video.removeEventListener('error',failed);
        video.removeAttribute('src');video.load();
        if(value)rememberDuration(id,value);resolve(value);
      }
      function loaded(){finish(Number.isFinite(video.duration)&&video.duration>0?video.duration:null);}
      function failed(){finish(null);}
      video.addEventListener('loadedmetadata',loaded);video.addEventListener('error',failed);
      timer=setTimeout(failed,15000);video.src=url;video.load();
    });
    probes.set(id,probe);probe.then(()=>probes.delete(id));return probe;
  }
  globalThis.HaySubProgress={read,save,clear,rememberDuration,duration,loadDuration,markOpened,hasOpened};
})();
