/* Pure helpers, usable in Chrome and Node. No server, DOM, or API keys.
   Timing follows the web app's static/player.js: start <= time < end. */
(function (root) {
  'use strict';
  const MAX_FILE_BYTES = 2 * 1024 * 1024;
  const SAVE_BUDGET = 8 * 1024 * 1024; // Leave headroom below Chrome local storage quota.
  const SETTINGS_KEY = 'haysub:settings';
  const FILE_PREFIX = 'haysub:file:';
  const OFFSET_PREFIX = 'haysub:offset:';
  const JOB_PREFIX = 'haysub:job:';
  const TRANSLATE_KEY = 'haysub:translate-enabled';
  const musicLabels=new Set(['music','background music','instrumental','instrumental music','music playing','music continues','music fades','music swells','soft music','gentle music','dramatic music','upbeat music','sad music','tense music','ominous music','loud music','quiet music','classical music','orchestral music','romantic music','suspenseful music','cheerful music','музыка','звучит музыка','играет музыка','фоновая музыка','тихая музыка','тревожная музыка','лирическая музыка','весёлая музыка','веселая музыка','грустная музыка','музыка продолжается','երաժշտություն','երաժշտութիւն','երաժշտությւոն','հնչում է երաժշտություն','ֆոնային երաժշտություն','մեղմ երաժշտություն']);
  function musicLine(text){
    const raw=text.replace(/<[^>]*>/g,'').replace(/&(?:gt|lt);/g,' ').trim().toLowerCase();
    const normalized=raw.replace(/[\[\](){}♪♫♬♩🎵🎶.։…!?:\s>«»\-—–]+/g,' ').trim().replace(/\s+/g,' ');
    return musicLabels.has(normalized)||(!normalized&&/[♪♫♬♩🎵🎶]/.test(raw));
  }
  const withoutMusicLines=text=>String(text||'').split(/\r?\n/).filter(line=>!musicLine(line)).join('\n').trim();
  function isMusicOnly(text){const lines=String(text||'').split(/\r?\n/).filter(line=>line.trim());return lines.length>0&&lines.every(musicLine);}
  const defaults = Object.freeze({enabled:true, fontSize:28, textColor:'#ffffff', backgroundOpacity:0.65, verticalPosition:12});
  const clamp = (n, min, max, fallback) => Number.isFinite(Number(n)) ? Math.min(max, Math.max(min, Number(n))) : fallback;

  function settings(value={}) {
    if (!value || typeof value !== 'object') value={};
    return {
      enabled: typeof value.enabled === 'boolean' ? value.enabled : true,
      fontSize: clamp(value.fontSize, 14, 64, defaults.fontSize),
      textColor: /^#[0-9a-f]{6}$/i.test(value.textColor || '') ? value.textColor : defaults.textColor,
      backgroundOpacity: clamp(value.backgroundOpacity, 0, 1, defaults.backgroundOpacity),
      verticalPosition: clamp(value.verticalPosition, 0, 80, defaults.verticalPosition)
    };
  }
  const offset = n => clamp(n, -120, 120, 0);
  const bytes = value => new TextEncoder().encode(value).byteLength;
  const recordBytes = (key, value) => bytes(key) + bytes(JSON.stringify(value));
  const savedKeys = all => Object.keys(all).filter(k => k.startsWith(FILE_PREFIX) || k.startsWith(OFFSET_PREFIX) || k.startsWith(JOB_PREFIX));

  function videoId(url) {
    try {
      const u = new URL(url);
      if (u.protocol !== 'https:' || !['www.youtube.com','youtube.com','m.youtube.com'].includes(u.hostname)) return null;
      const id = u.pathname === '/watch' ? u.searchParams.get('v') : u.pathname.match(/^\/shorts\/([\w-]{11})\/?$/)?.[1];
      return /^[\w-]{11}$/.test(id || '') ? id : null;
    } catch { return null; }
  }

  async function pageKey(pageUrl,frameUrl=pageUrl,videoIndex=0){
    const canonical=value=>{const url=new URL(value);if(!['http:','https:'].includes(url.protocol))throw Error('Այս էջում հավելումը հասանելի չէ։');return url.href;};
    const data=JSON.stringify([canonical(pageUrl),canonical(frameUrl),Number(videoIndex)||0]);
    const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(data));
    return 'page:'+Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');
  }

  function timestamp(text) {
    const match = text.match(/^(?:(\d{2,}):)?(\d{2}):(\d{2})[.,](\d{3})$/);
    if (!match || Number(match[2]) > 59 || Number(match[3]) > 59) throw Error('Ժամանակի ձևաչափը սխալ է։ Օրինակ՝ 00:01:02,500։');
    return Number(match[1] || 0)*3600 + Number(match[2])*60 + Number(match[3]) + Number(match[4])/1000;
  }

  function plainText(text) {
    // Strip VTT/SRT formatting before decoding entities. Never interpret HTML.
    const named = {amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:' ',lrm:'\u200e',rlm:'\u200f'};
    return text.replace(/<[^>]*>/g, '').replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp|lrm|rlm);/gi, (whole, entity) => {
      if (!entity.startsWith('#')) return named[entity.toLowerCase()] ?? whole;
      const n = entity[1].toLowerCase() === 'x' ? parseInt(entity.slice(2),16) : Number(entity.slice(1));
      return n > 0 && n <= 0x10ffff && !(n >= 0xd800 && n <= 0xdfff) ? String.fromCodePoint(n) : '\ufffd';
    }).trim();
  }

  function parse(text) {
    if (typeof text !== 'string' || !text.trim() || bytes(text) > MAX_FILE_BYTES) throw Error('Ընտրիր ոչ դատարկ SRT/VTT ֆայլ՝ մինչև 2 ՄԲ։');
    if (text.includes('\0')) throw Error('Ֆայլը տեքստային ենթագրերի ֆայլ չէ։ Պահպանիր այն UTF-8 ձևաչափով։');
    text = text.replace(/^\ufeff/, '').replace(/\r\n?/g, '\n');
    const cues=[];
    let ignored=0;
    const blocks=text.trim().split(/\n[\t ]*\n+/);
    for (let i=0; i<blocks.length; i++) {
      const lines=blocks[i].trim().split('\n');
      if (/^(WEBVTT(?:\s|$)|NOTE(?:\s|$)|STYLE$|REGION$)/.test(lines[0])) continue;
      const row=lines.slice(0,2).findIndex(line=>line.includes('-->'));
      if (row < 0) throw Error(`Հատված ${i+1}․ ժամանակային տողը բացակայում է։`);
      const times=lines[row].match(/^\s*(\S+)\s+-->\s+(\S+)(?:\s+.*)?$/);
      if (!times) throw Error(`Հատված ${i+1}․ ժամանակային տողը սխալ է։`);
      let start,end;
      try { start=timestamp(times[1]); end=timestamp(times[2]); }
      catch (error) { throw Error(`Հատված ${i+1}․ ${error.message}`); }
      if (end < start) throw Error(`Հատված ${i+1}․ ավարտը սկզբից շուտ է։`);
      const content=plainText(lines.slice(row+1).join('\n'));
      if (!content || end === start) { ignored++; continue; }
      if (content.length > 5000) throw Error(`Հատված ${i+1}․ տեքստը չափազանց երկար է (առավելագույնը՝ 5000 նիշ)։`);
      cues.push({id:cues.length+1,start,end,text:content});
      if (cues.length > 10000) throw Error('Ֆայլը կարող է պարունակել առավելագույնը 10 000 հատված։');
    }
    if (!cues.length) throw Error('Ֆայլում ցուցադրվող ենթագրեր չեն գտնվել։');
    // Stable sort also supports files whose overlapping cues are not start-sorted.
    cues.sort((a,b)=>a.start-b.start || a.id-b.id);
    return {cues,ignored};
  }

  function timeline(cues) {
    // Prefix maximum end times keep long overlapping cues discoverable on seeks.
    const ordered=[...cues].sort((a,b)=>a.start-b.start || a.id-b.id);
    const maxEnds=[];
    ordered.forEach((c,i)=>maxEnds.push(Math.max(c.end, maxEnds[i-1] ?? -Infinity)));
    return {
      at(seconds, delay=0) {
        const t=Number(seconds)-Number(delay);
        if (!Number.isFinite(t)) return [];
        let lo=0,hi=ordered.length;
        while(lo<hi) { const mid=(lo+hi)>>>1; if(ordered[mid].start<=t)lo=mid+1;else hi=mid; }
        const active=[];
        for(let i=lo-1;i>=0 && maxEnds[i]>t;i--) if(ordered[i].end>t&&!isMusicOnly(ordered[i].text))active.push(ordered[i]);
        return active.reverse();
      }
    };
  }

  function pictureRect(video, parent, intrinsicWidth, intrinsicHeight, fit='contain') {
    let {left,top,width,height}=video;
    if (width<=0 || height<=0 || parent.width<=0 || parent.height<=0) return {left:0,top:0,width:0,height:0};
    if (intrinsicWidth>0 && intrinsicHeight>0 && ['contain','scale-down'].includes(fit)) {
      let scale=Math.min(width/intrinsicWidth,height/intrinsicHeight);
      if (fit==='scale-down') scale=Math.min(scale,1);
      const w=intrinsicWidth*scale,h=intrinsicHeight*scale;
      left+=(width-w)/2; top+=(height-h)/2; width=w; height=h;
    }
    const x=Math.max(left,parent.left),y=Math.max(top,parent.top);
    return {left:x-parent.left,top:y-parent.top,width:Math.max(0,Math.min(left+width,parent.left+parent.width)-x),height:Math.max(0,Math.min(top+height,parent.top+parent.height)-y)};
  }

  function toSrt(cues){
    const time=seconds=>{let ms=Math.round(seconds*1000);const h=Math.floor(ms/3600000);ms%=3600000;const m=Math.floor(ms/60000);ms%=60000;return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(Math.floor(ms/1000)).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;};
    return cues.map((c,i)=>`${i+1}\n${time(c.start)} --> ${time(c.end)}\n${c.text.replace(/\r\n?/g,'\n').replace(/\n\s*\n/g,'\n')}`).join('\n\n');
  }
  const api={MAX_FILE_BYTES,SAVE_BUDGET,SETTINGS_KEY,FILE_PREFIX,OFFSET_PREFIX,JOB_PREFIX,TRANSLATE_KEY,defaults,settings,offset,bytes,recordBytes,savedKeys,videoId,pageKey,timestamp,plainText,parse,timeline,pictureRect,toSrt,isMusicOnly,withoutMusicLines};
  if(typeof module!=='undefined' && module.exports)module.exports=api;
  else root.HaySubCore=api;
})(globalThis);
