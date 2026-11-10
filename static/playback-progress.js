/* Browser-local progress shared by the catalog and native player. */
(() => {
  'use strict';
  const prefix='haysub:progress:v1:';
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
  globalThis.HaySubProgress={read,save,clear,rememberDuration,duration};
})();
