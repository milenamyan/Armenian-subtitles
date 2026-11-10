/* Conservative annotation detection. Keep aligned with extension/core.js and
   app/subtitles.py; tests/music-cases.json exercises all three implementations. */
(function(root){
  const labels=new Set(['music','background music','instrumental','instrumental music','music playing','music continues','music fades','music swells','soft music','gentle music','dramatic music','upbeat music','sad music','tense music','ominous music','loud music','quiet music','classical music','orchestral music','romantic music','suspenseful music','cheerful music','музыка','звучит музыка','играет музыка','фоновая музыка','тихая музыка','тревожная музыка','лирическая музыка','весёлая музыка','веселая музыка','грустная музыка','музыка продолжается','երաժշտություն','երաժշտութիւն','երաժշտությւոն','հնչում է երաժշտություն','ֆոնային երաժշտություն','մեղմ երաժշտություն']);
  function musicLine(text){
    const raw=text.replace(/<[^>]*>/g,'').replace(/&(?:gt|lt);/g,' ').trim().toLowerCase();
    const normalized=raw.replace(/[\[\](){}♪♫♬♩🎵🎶.։…!?:\s>«»\-—–]+/g,' ').trim().replace(/\s+/g,' ');
    return labels.has(normalized)||(!normalized&&/[♪♫♬♩🎵🎶]/.test(raw));
  }
  const withoutMusicLines=text=>String(text||'').split(/\r?\n/).filter(line=>!musicLine(line)).join('\n').trim();
  function isMusicOnly(text){const lines=String(text||'').split(/\r?\n/).filter(line=>line.trim());return lines.length>0&&lines.every(musicLine);}
  const api={isMusicOnly,withoutMusicLines};
  if(typeof module!=='undefined')module.exports=api;else root.HaySubMusic=api;
})(globalThis);
