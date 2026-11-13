/* Local catalog visits only; anonymous per-tab sessions expire after 30 idle minutes. */
(() => {
  'use strict';
  if(!['/','/catalog'].includes(location.pathname)&&!/^\/watch\/[a-f0-9]{32}$/.test(location.pathname))return;
  if(navigator.doNotTrack==='1'||navigator.globalPrivacyControl)return;
  const key='haysub:visit:v1',idle=30*60*1000;
  let visit;
  try{visit=JSON.parse(sessionStorage.getItem(key));}catch{}
  function fresh(){return {id:crypto.randomUUID().replaceAll('-',''),seconds:0,lastSeen:Date.now()};}
  function expired(){return !visit||!/^[a-f0-9]{32}$/.test(visit.id)||!Number.isFinite(visit.seconds)||visit.seconds<0||!Number.isFinite(visit.lastSeen)||Date.now()-visit.lastSeen>idle;}
  if(expired())visit=fresh();
  let visible=!document.hidden,lastTick=performance.now();
  function send(){
    const body=JSON.stringify({id:visit.id,active_seconds:Math.min(172800,visit.seconds)});
    try{
      if(navigator.sendBeacon?.('/api/visits',new Blob([body],{type:'application/json'})))return;
      void fetch('/api/visits',{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true}).catch(()=>{});
    }catch{}
  }
  function checkpoint(){
    const now=performance.now();
    if(visible)visit.seconds+=Math.min(30,Math.max(0,now-lastTick)/1000);
    lastTick=now;visit.lastSeen=Date.now();
    try{sessionStorage.setItem(key,JSON.stringify(visit));}catch{}
    send();
  }
  function resume(){
    if(expired())visit=fresh();
    visible=!document.hidden;lastTick=performance.now();checkpoint();
  }
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden){checkpoint();visible=false;}else resume();
  });
  window.addEventListener('pagehide',()=>{checkpoint();visible=false;});
  window.addEventListener('pageshow',event=>{if(event.persisted)resume();});
  setInterval(()=>{if(visible&&!document.hidden)checkpoint();},15000);
  checkpoint();
})();
