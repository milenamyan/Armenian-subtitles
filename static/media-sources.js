/* Cloud SRT files become native WebVTT tracks in memory; no files are copied. */
(function(root){
  'use strict';
  function srtToVtt(raw,offset=0){
    const text=raw.replace(/^\uFEFF/,'').replace(/\r\n?/g,'\n').trim();
    if(/^WEBVTT(?:\s|$)/.test(text))return text+'\n';
    const seconds=value=>value.replace(',','.').split(':').reduce((total,part)=>total*60+Number(part),0);
    const stamp=value=>{
      let milliseconds=Math.max(0,Math.round(value*1000));
      const hours=Math.floor(milliseconds/3600000);milliseconds%=3600000;
      const minutes=Math.floor(milliseconds/60000);milliseconds%=60000;
      return String(hours).padStart(2,'0')+':'+String(minutes).padStart(2,'0')+':'+String(Math.floor(milliseconds/1000)).padStart(2,'0')+'.'+String(milliseconds%1000).padStart(3,'0');
    };
    const escape=value=>value.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    const blocks=['WEBVTT'];
    for(const block of text.split(/\n\s*\n/)){
      const lines=block.split('\n'),index=lines.findIndex(line=>line.includes('-->'));
      const timing=index<0?null:lines[index].match(/^(\d{2,}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+(\d{2,}:\d{2}:\d{2}[,.]\d{3})(?:\s.*)?$/);
      if(!timing)throw Error('Invalid cloud subtitle timestamps.');
      const start=Math.max(0,seconds(timing[1])+offset),end=seconds(timing[2])+offset;
      if(end<=start)continue;
      blocks.push(String(blocks.length)+'\n'+stamp(start)+' --> '+stamp(end)+'\n'+escape(lines.slice(index+1).join('\n')));
    }
    if(blocks.length===1)throw Error('No displayable cloud subtitles.');
    return blocks.join('\n\n')+'\n';
  }
  if(typeof module!=='undefined')module.exports={srtToVtt};
  else root.HaySubMediaSources={srtToVtt};
})(globalThis);
