(function(root){
  'use strict';
  function publicUrl(value,optional=false){
    if(optional&&!value)return '';
    let url;try{url=new URL(value);}catch{throw Error('A complete public HTTPS media URL is required.');}
    if(url.protocol!=='https:'||url.username||url.password||['localhost','127.0.0.1'].includes(url.hostname)||url.hostname.endsWith('.r2.cloudflarestorage.com'))throw Error('Use a public HTTPS delivery URL, without credentials.');
    if([...url.searchParams.keys()].some(key=>/signature|token|credential|secret|api.?key/i.test(key)))throw Error('Use a permanent public URL, not a signed or secret URL.');
    return url.href;
  }
  function validate(data){
    if(data?.version!==1||!Array.isArray(data.films))throw Error('Invalid catalog.json format.');
    const ids=new Set();
    return data.films.map(item=>{
      if(!item||typeof item.id!=='string'||!/^[a-zA-Z0-9_-]{1,100}$/.test(item.id)||ids.has(item.id))throw Error('Each film needs a unique id.');
      ids.add(item.id);
      if(typeof item.title!=='string'||!item.title.trim())throw Error('Each film needs a title.');
      const poster=item.poster_url||'';
      if(poster&&!/^assets\/posters\/[a-zA-Z0-9_-]+\.(png|jpg|webp)$/.test(poster))publicUrl(poster);
      const offset=item.subtitle_offset??0;if(!Number.isFinite(offset)||Math.abs(offset)>86400)throw Error('Invalid subtitle offset.');
      return {...item,title:item.title.trim(),video_url:publicUrl(item.video_url),subtitle_url:publicUrl(item.subtitle_url,true),poster_url:poster,subtitle_offset:offset};
    });
  }
  function durationText(seconds){if(!Number.isFinite(seconds)||seconds<=0)return '—:—';const total=Math.floor(seconds),hours=Math.floor(total/3600),minutes=Math.floor(total%3600/60);return (hours?hours+':'+String(minutes).padStart(2,'0'):minutes)+':'+String(total%60).padStart(2,'0');}
  const model={validate,publicUrl,durationText};
  if(typeof module!=='undefined')module.exports=model;else root.HaySubCatalog=model;
})(globalThis);
