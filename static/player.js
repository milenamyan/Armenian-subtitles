// Pure timing helpers shared with the Node tests. End boundaries are exclusive.
(function(root){
  const music=typeof module!=='undefined'?require('./music.js'):root.HaySubMusic;
  function activeCues(cues, seconds, offset=0){
    const t=seconds-offset;
    return cues.filter(c=>c.start<=t && t<c.end && !music.isMusicOnly(c.source||c.text)).map(c=>typeof c.source==='string'?{...c,source:music.withoutMusicLines(c.source)}:c);
  }
  function subtitleState(cues, translated, seconds, offset=0){
    const active=activeCues(cues,seconds,offset);
    return {active,waiting:active.some(c=>!translated[String(c.id)])};
  }
  const helpers={activeCues,subtitleState,...music};
  if(typeof module!=='undefined') module.exports=helpers;
  else root.SubtitleTiming=helpers;
})(globalThis);
