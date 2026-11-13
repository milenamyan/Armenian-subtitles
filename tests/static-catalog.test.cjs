const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const model=require('../catalog-site/catalog-model.js'),media=require('../static/media-sources.js');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const film={id:'film-1',title:'Հայերեն <film>',video_url:'https://media.example.org/movie.mp4',subtitle_url:'https://media.example.org/captions.srt',subtitle_offset:2};

test('manifest accepts public media and rejects credential-bearing links and duplicate ids',()=>{
  assert.equal(model.validate({version:1,films:[film]})[0].title,film.title);
  assert.throws(()=>model.validate({version:1,films:[film,film]}),/unique/);
  for(const video_url of ['javascript:alert(1)','http://localhost/movie.mp4','https://owner:secret@example.org/video.mp4','https://account.r2.cloudflarestorage.com/bucket/movie.mp4','https://media.example.org/video.mp4?X-Amz-Signature=secret'])assert.throws(()=>model.validate({version:1,films:[{...film,video_url}]}));
});

test('hidden films stay in JSON but are excluded from catalog and playback selection',async()=>{
  const hidden={...film,published:false};
  const manifest={version:1,films:[hidden]};
  assert.equal(manifest.films.length,1);
  assert.deepEqual(model.validate(manifest),[]);
  assert.equal(model.validate({version:1,films:[{...hidden,published:true}]})[0].id,film.id);
  assert.throws(()=>model.validate({version:1,films:[{...film,published:'false'}]}),/true or false/);
  const h=harness({entry:hidden});await flush();
  assert.deepEqual(h.requests,['catalog.json']);assert.equal(h.node('hosted-player').src,undefined);
  assert.match(h.node('watch-title').textContent,/հասանելի չէ/);
});

test('offset WebVTT preserves cue markup/settings and removes cues shifted before zero',()=>{
  const vtt='WEBVTT\n\nfirst\n00:00.000 --> 00:01.000\nDrop\n\nsecond\n00:01.000 --> 00:04.000 align:start\n<b>Հայերեն</b>\n';
  const shifted=media.srtToVtt(vtt,-2);
  assert.doesNotMatch(shifted,/Drop/);assert.match(shifted,/00:00:00.000 --> 00:00:02.000 align:start/);assert.match(shifted,/<b>Հայերեն<\/b>/);
});

function harness({entry=film,subtitleFails=false}={}){
  const nodes=new Map(),events={},requests=[],writes=[],blobs=[];
  function node(id){if(!nodes.has(id))nodes.set(id,{value:id==='speed'?'1':'hy',hidden:true,textContent:'',listeners:new Map(),paused:true,currentTime:0,duration:900,playbackRate:1,
    addEventListener(name,fn,opts){const list=this.listeners.get(name)||[];list.push({fn,once:opts?.once});this.listeners.set(name,list);},
    async fire(name){const list=this.listeners.get(name)||[];this.listeners.set(name,list.filter(item=>!item.once));for(const item of list)await item.fn();},
    pause(){this.paused=true;},load(){},removeAttribute(name){delete this[name];},async requestFullscreen(){this.fullscreen=true;}});return nodes.get(id);}
  const track=node('armenian-track');track.track={mode:'disabled',cues:[]};node('hosted-player').textTracks={addEventListener(name,fn){events['tracks:'+name]=fn;}};
  vm.runInNewContext(fs.readFileSync('catalog-site/player.js','utf8'),{URLSearchParams,URL:class extends URL{static createObjectURL(blob){blobs.push(blob);return 'blob:captions';}static revokeObjectURL(){}},Blob,
    location:{search:'?id=film-1'},document:{getElementById:node,addEventListener(name,fn){events[name]=fn;}},window:{addEventListener(name,fn){events[name]=fn;}},
    HaySubCatalog:model,HaySubMediaSources:media,HaySubProgress:{read:()=>({position:120,duration:900}),save:(...args)=>writes.push(args),rememberDuration(){},clear(){}},
    fetch:async url=>{requests.push(url);return url==='catalog.json'?{ok:true,json:async()=>({version:1,films:[entry]})}:{ok:!subtitleFails,text:async()=> '1\n00:00:01,000 --> 00:00:03,000\nՀայերեն'};}});
  return {node,events,requests,writes,blobs};
}

test('static player reads JSON and R2 only, converts SRT, resumes without autoplay and respects native captions off',async()=>{
  const h=harness();await flush();const video=h.node('hosted-player'),track=h.node('armenian-track');
  assert.deepEqual(h.requests,['catalog.json',film.subtitle_url]);assert.equal(video.src,film.video_url);assert.equal(track.src,'blob:captions');
  assert.match(await h.blobs[0].text(),/00:00:03.000 --> 00:00:05.000/);
  await video.fire('pause');assert.equal(h.writes.length,0);
  await video.fire('loadedmetadata');assert.equal(video.currentTime,120);assert.equal(video.paused,true);assert.equal(track.track.mode,'showing');
  track.track.mode='disabled';h.events['tracks:change']();
  await track.fire('load');assert.equal(track.track.mode,'disabled');
  await video.fire('pause');assert.equal(h.writes[0][1],120);
  assert.equal(h.node('watch-title').textContent,film.title);
});

test('direct VTT remains an HTTP native track without blob conversion',async()=>{
  const entry={...film,subtitle_url:'https://media.example.org/subtitles.vtt',subtitle_offset:0},h=harness({entry});await flush();
  assert.deepEqual(h.requests,['catalog.json']);assert.equal(h.node('armenian-track').src,entry.subtitle_url);assert.equal(h.blobs.length,0);
});

test('subtitle failure keeps video playable and reports the caption failure',async()=>{
  const h=harness({subtitleFails:true});await flush();await h.node('hosted-player').fire('loadedmetadata');
  assert.equal(h.node('hosted-player').src,film.video_url);assert.equal(h.node('hosted-player').hidden,false);
  assert.match(h.node('watch-status').textContent,/R2 CORS/);assert.equal(h.node('watch-status').hidden,false);
});

test('native subtitle cues use the saved film height without viewer controls',async()=>{
  const h=harness({entry:{...film,subtitle_height:18}});await flush();
  const track=h.node('armenian-track');track.track.cues=[{}];await track.fire('load');
  assert.equal(track.track.cues[0].line,82);assert.equal(track.track.cues[0].snapToLines,false);
});

test('catalog renders searchable film links and literal titles without backend requests',async()=>{
  const nodes=new Map(),requests=[],probes=[],entry={...film,is_new:true};
  function element(tag){return {tag,children:[],listeners:{},style:{},value:'',hidden:true,textContent:'',append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},setAttribute(){},addEventListener(name,fn){this.listeners[name]=fn;}};}
  const node=id=>{if(!nodes.has(id))nodes.set(id,element('div'));return nodes.get(id);};
  vm.runInNewContext(fs.readFileSync('catalog-site/catalog.js','utf8'),{
    document:{getElementById:node,createElement:element},window:{addEventListener(){},scrollTo(){}},sessionStorage:{getItem:()=>null},requestAnimationFrame:fn=>fn(),
    HaySubCatalog:model,HaySubProgress:{read:()=>null,duration:()=>null,loadDuration:async(id,url)=>{probes.push([id,url]);return 6278;}},fetch:async url=>{requests.push(url);return {ok:true,json:async()=>({version:1,films:[entry]})};}});
  await flush();
  assert.deepEqual(requests,['catalog.json']);assert.equal(node('public-videos').children.length,1);
  const link=node('public-videos').children[0];assert.equal(link.href,'watch.html?id=film-1');assert.equal(link.children[1].textContent,film.title);
  assert.deepEqual(probes,[[film.id,film.video_url]]);assert.equal(link.children[0].children[1].textContent,'1:44:38');
  assert.equal(link.children[0].children.at(-1).className,'movie-new-badge');
  node('search').value='missing film';node('search').listeners.input();assert.equal(node('public-videos').children.length,0);assert.equal(node('catalog-status').hidden,false);
  node('search').value='ՀԱՅԵՐԵՆ';node('search').listeners.input();assert.equal(node('public-videos').children.length,1);
});
