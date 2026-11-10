const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const C=require('../core.js');
const source=fs.readFileSync(path.join(__dirname,'../content.js'),'utf8');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

class Events {
  constructor(){this.listeners=new Map();}
  addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
  removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
  fire(name){for(const fn of [...(this.listeners.get(name)||[])])fn({type:name});}
  count(name){return this.listeners.get(name)?.size||0;}
}
class Element extends Events {
  constructor(){super();this.style={position:''};this.dataset={};this.children=[];this.classList=new Set();this.rect={left:0,top:0,width:960,height:540};this.scrollHeight=50;this.textContent='';this.isConnected=true;}
  append(...nodes){for(const n of nodes){n.parentElement=this;n.isConnected=true;this.children.push(n);}}
  remove(){this.isConnected=false;if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(n=>n!==this);}
  setAttribute(){}
  attachShadow(){this.shadow=new Element();return this.shadow;}
  querySelectorAll(){return this.children.filter(n=>n.dataset.haysubOverlay);}
  getBoundingClientRect(){return this.rect;}
  closest(){return this.parentElement;}
}
function harness(){
  const player=new Element(),video=new Element(),doc=new Events(),win=new Events();
  video.classList.contains=video.classList.has;player.classList.contains=player.classList.has;
  Object.assign(video,{currentTime:2,paused:true,ended:false,readyState:4,videoWidth:1920,videoHeight:1080});player.append(video);
  const data={[C.FILE_PREFIX+'abcdefghijk']:{name:'a.srt',text:'1\n00:00:01,000 --> 00:00:10,000\nԲարև\nHello\n\n2\n00:00:03,000 --> 00:00:05,000\nOverlap'}};
  const storageListeners=new Set(),messageListeners=new Set(),frames=new Map();let number=0;
  doc.documentElement=new Element();doc.createElement=()=>new Element();doc.querySelector=()=>video;doc.hidden=false;
  const observers=[];
  class Observer {constructor(fn){this.fn=fn;this.active=false;observers.push(this);}observe(){this.active=true;}disconnect(){this.active=false;}}
  const context=vm.createContext({HaySubCore:C,document:doc,window:win,location:{href:'https://www.youtube.com/watch?v=abcdefghijk'},ResizeObserver:Observer,MutationObserver:Observer,
    getComputedStyle:n=>({position:'relative',objectFit:'contain'}),
    requestAnimationFrame:fn=>{frames.set(++number,fn);return number;},cancelAnimationFrame:id=>frames.delete(id),
    chrome:{storage:{local:{get:async keys=>Object.fromEntries(keys.filter(k=>k in data).map(k=>[k,data[k]]))},onChanged:{addListener:fn=>storageListeners.add(fn),removeListener:fn=>storageListeners.delete(fn)}},runtime:{onMessage:{addListener:fn=>messageListeners.add(fn),removeListener:fn=>messageListeners.delete(fn)}}}
  });
  const run=()=>vm.runInContext(source,context);
  const frame=()=>{const pending=[...frames.values()];frames.clear();for(const fn of pending)fn();};
  const host=()=>player.children.find(n=>n.dataset.haysubOverlay);
  const caption=()=>host()?.shadow.children[1].children[0];
  const change=async key=>{for(const fn of storageListeners)fn({[key]:{}},'local');await flush();};
  return {player,video,doc,win,data,context,frames,run,frame,host,caption,change,storageListeners,messageListeners,observers};
}

test('video clock handles pauses, buffering, speed and bidirectional seeks, with overlapping text',async()=>{
  const h=harness();h.run();await flush();
  assert.equal(h.caption().textContent,'Բարև\nHello');
  assert.equal(h.host().style.pointerEvents,'none');
  h.video.currentTime=4;h.video.fire('seeking');
  assert.equal(h.caption().textContent,'Բարև\nHello\nOverlap');
  h.video.paused=false;h.video.fire('play');assert.equal(h.frames.size,1);
  h.video.playbackRate=2;h.video.fire('ratechange');h.frame();
  assert.equal(h.caption().textContent,'Բարև\nHello\nOverlap'); // no independent advancement
  h.video.fire('waiting');h.frame();assert.equal(h.caption().textContent,'Բարև\nHello\nOverlap');
  h.video.currentTime=8;h.video.fire('seeked');assert.equal(h.caption().textContent,'Բարև\nHello');
  h.video.currentTime=4;h.video.fire('seeked');assert.match(h.caption().textContent,/Overlap/);
  h.video.paused=true;h.video.fire('pause');assert.equal(h.frames.size,0);
  h.video.currentTime=10;h.video.fire('timeupdate');assert.equal(h.host().style.display,'none');
  h.context.__haySubOverlay.dispose();
});
test('SPA navigation removes old captions/listeners and restores only per-video files',async()=>{
  const h=harness();h.run();await flush();const old=h.host();
  h.doc.fire('yt-navigate-start');assert.equal(old.isConnected,false);assert.equal(h.video.count('play'),0);
  h.context.location.href='https://www.youtube.com/watch?v=zyxwvutsrqp';h.doc.fire('yt-navigate-finish');h.frame();await flush();
  assert.equal(h.host().style.display,'none');assert.equal(h.video.count('play'),1);
  const key=C.FILE_PREFIX+'zyxwvutsrqp';h.data[key]={name:'b.vtt',text:'WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nNew video'};
  await h.change(key);assert.equal(h.caption().textContent,'New video');
  h.doc.fire('yt-navigate-start');h.context.location.href='https://www.youtube.com/watch?v=abcdefghijk';
  h.doc.fire('yt-navigate-finish');h.frame();await flush();
  assert.equal(h.caption().textContent,'Բարև\nHello','Returning restores only the first video association');
  h.run();await flush();
  assert.equal(h.player.querySelectorAll().length,1);assert.equal(h.video.count('play'),1);
  assert.equal(h.doc.count('yt-navigate-start'),1);assert.equal(h.messageListeners.size,1);
  assert.equal(h.storageListeners.size,1);
  h.context.__haySubOverlay.dispose();assert.equal(h.video.count('play'),0);assert.ok(h.observers.every(o=>!o.active));
});
test('settings, offset, ads, clear and fullscreen layout stay separate from YouTube controls',async()=>{
  const h=harness();const native=new Element();h.player.append(native);h.run();await flush();
  h.data[C.SETTINGS_KEY]={enabled:false};await h.change(C.SETTINGS_KEY);assert.equal(h.host().style.display,'none');
  h.data[C.SETTINGS_KEY]={enabled:true,textColor:'#ffcc00',backgroundOpacity:0.3,verticalPosition:30};await h.change(C.SETTINGS_KEY);
  assert.equal(h.caption().style.color,'#ffcc00');assert.equal(h.caption().style.backgroundColor,'rgba(0,0,0,0.3)');
  h.data[C.OFFSET_PREFIX+'abcdefghijk']=2;await h.change(C.OFFSET_PREFIX+'abcdefghijk');assert.equal(h.host().style.display,'none');
  h.video.currentTime=4;h.video.fire('timeupdate');assert.equal(h.caption().textContent,'Բարև\nHello');
  h.player.classList.add('ad-showing');h.video.fire('timeupdate');assert.equal(h.host().style.display,'none');
  h.player.classList.delete('ad-showing');h.video.fire('timeupdate');assert.equal(h.host().style.display,'block');
  h.video.rect=h.player.rect={left:0,top:0,width:1920,height:1080};h.doc.fire('fullscreenchange');
  assert.equal(h.host().shadow.children[1].style.width,'1920px');assert.ok(h.player.children.includes(native));
  delete h.data[C.FILE_PREFIX+'abcdefghijk'];await h.change(C.FILE_PREFIX+'abcdefghijk');assert.equal(h.host().style.display,'none');
  h.context.__haySubOverlay.dispose();
});
test('generic HTML5 page overlays use video time and guard source replacement',async()=>{
  const h=harness(),key='page:'+'a'.repeat(64),url='https://example.test/movie';
  h.context.HaySubSiteConfig={key,topUrl:url,frameUrl:url,videoIndex:0};h.context.location.href=url;
  h.doc.querySelectorAll=()=>[h.video];h.video.currentSrc='blob:first';
  h.data[C.FILE_PREFIX+key]={name:'movie.srt',text:'1\n00:00:01,000 --> 00:00:05,000\nԲարև',updatedAt:1};
  h.run();await flush();assert.equal(h.caption().textContent,'Բարև');
  h.video.currentTime=6;h.video.fire('seeking');assert.equal(h.host().style.display,'none');
  h.video.currentTime=2;h.video.fire('seeked');assert.equal(h.host().style.display,'block');
  h.video.currentSrc='blob:second';h.video.fire('loadedmetadata');assert.equal(h.host().style.display,'none');
  h.data[C.FILE_PREFIX+key]={...h.data[C.FILE_PREFIX+key],updatedAt:2};await h.change(C.FILE_PREFIX+key);
  assert.equal(h.host().style.display,'block');
  const old=h.host();h.context.location.href=url+'#other';
  h.doc.fire('timeupdate');h.video.fire('timeupdate');assert.equal(old.style.display,'none');
  h.context.__haySubOverlay.dispose();
});
test('incremental output from an old job cannot unlock subtitles on a changed video',async()=>{
  const h=harness(),key='page:'+'b'.repeat(64),url='https://example.test/movie';
  h.context.HaySubSiteConfig={key,topUrl:url,frameUrl:url,videoIndex:0};h.context.location.href=url;
  h.doc.querySelectorAll=()=>[h.video];h.video.currentSrc='blob:original';
  h.data[C.FILE_PREFIX+key]={name:'movie.srt',text:'1\n00:00:01,000 --> 00:00:05,000\nԲարև',selectionId:'job-one',updatedAt:1};
  h.run();await flush();h.video.currentSrc='blob:different';h.video.fire('loadedmetadata');
  h.data[C.FILE_PREFIX+key]={...h.data[C.FILE_PREFIX+key],updatedAt:2};await h.change(C.FILE_PREFIX+key);
  assert.equal(h.host().style.display,'none');
  h.data[C.FILE_PREFIX+key]={...h.data[C.FILE_PREFIX+key],selectionId:'new-file',updatedAt:3};await h.change(C.FILE_PREFIX+key);
  assert.equal(h.host().style.display,'block');h.context.__haySubOverlay.dispose();
});
