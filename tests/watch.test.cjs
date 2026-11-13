const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));

test('saved film height survives native fullscreen without enabling disabled captions',async()=>{
  const h=harness(200,false,true,false,false,{subtitleHeight:12});await flush();
  const video=h.$('hosted-player'),captions=video.textTracks[0],cue={};captions.cues=[cue];
  await h.$('armenian-track').fire('load');assert.equal(cue.line,88);
  await video.fire('webkitbeginfullscreen');assert.equal(cue.line,88);assert.equal(captions.mode,'showing');
  captions.mode='disabled';await video.fire('webkitendfullscreen');assert.equal(captions.mode,'disabled');assert.equal(cue.line,88);
});

test('only the active owner preview accepts unsaved height adjustments, and each film loads its saved height',async()=>{
  const h=harness(200,true,true,false,false,{subtitleHeight:14});await flush();
  const cue={};h.$('hosted-player').textTracks[0].cues=[cue];await h.$('armenian-track').fire('load');assert.equal(cue.line,86);
  h.handlers.get('haysub-subtitle-height')({detail:{id:'a'.repeat(32),height:18}});assert.equal(cue.line,82);
  h.handlers.get('haysub-subtitle-height')({detail:{id:'b'.repeat(32),height:30}});assert.equal(cue.line,82);
  const viewer=harness(200,false,true,false,false,{subtitleHeight:14});await flush();
  const replacement={};viewer.$('hosted-player').textTracks[0].cues=[replacement];await viewer.$('armenian-track').fire('load');assert.equal(replacement.line,86);
  viewer.handlers.get('haysub-subtitle-height')({detail:{id:'a'.repeat(32),height:30}});assert.equal(replacement.line,86);
});

test('startup media errors stay in loading state; errors from the assigned media still surface',async()=>{
  let respond;
  const h=harness(200,false,true,false,false,{fetch:()=>new Promise(resolve=>{respond=resolve;})});
  const video=h.$('hosted-player'),track=h.$('armenian-track');
  video.error={code:4};track.readyState=3;
  await video.fire('error');await track.fire('error');
  assert.match(h.$('watch-status').textContent,/Բեռնվում է տեսանյութը/);
  video.error=null;track.readyState=0;
  respond({ok:true,json:async()=>({title:'Film',video_url:'/film.mp4',subtitle_url:'/captions.vtt',expires_in:14400})});await flush();
  await video.fire('error');await track.fire('error');
  assert.match(h.$('watch-status').textContent,/Բեռնվում են տեսանյութի տվյալները/);
  await video.fire('loadedmetadata');
  video.error={code:2};await video.fire('error');assert.match(h.$('watch-status').textContent,/Չհաջողվեց նվագարկել/);
  track.readyState=3;await track.fire('error');assert.match(h.$('watch-status').textContent,/ենթագրերը չեն բեռնվել/);
});
function harness(status=200,preview=false,hasSubtitles=true,cloud=false,inline=false,overrides={}){
  const nodes=new Map(),timers=[],calls=[],blobs=[],events=[],handlers=new Map();
  const $=id=>{if(overrides.minimal&&['watch-controls','watch-speed','watch-subtitles','watch-fullscreen','watch-retry','watch-restart','watch-visibility'].includes(id))return null;if(overrides.readOnly&&['watch-url-form','watch-save-form'].includes(id))return null;if(!nodes.has(id))nodes.set(id,{attributes:{'data-media-source':cloud?'cloud':'local','data-url-player':(inline||overrides.inline)?'true':null,'data-owner-controls':overrides.readOnly?'false':null},getAttribute(name){return this.attributes[name]||null;},parentElement:null,children:[],get nextSibling(){if(!this.parentElement)return null;return this.parentElement.children[this.parentElement.children.indexOf(this)+1]||null;},remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(child=>child!==this);this.parentElement=null;},append(...children){for(const child of children){child.remove();child.parentElement=this;this.children.push(child);}},prepend(child){child.remove();child.parentElement=this;this.children.unshift(child);},insertBefore(child,before){if(child===before)return;child.remove();child.parentElement=this;const index=this.children.indexOf(before);if(index<0)this.children.push(child);else this.children.splice(index,0,child);},after(child){this.parentElement?.insertBefore(child,this.nextSibling);},hidden:true,textContent:'',value:id==='watch-speed'?'1':'hy',currentTime:0,paused:true,playbackRate:1,duration:60,textTracks:[{mode:'disabled'}],listeners:new Map(),classList:{toggle(){}},addEventListener(name,fn,options){const list=this.listeners.get(name)||[];list.push({fn,once:options?.once});this.listeners.set(name,list);},async fire(name){const list=this.listeners.get(name)||[];this.listeners.set(name,list.filter(v=>!v.once));for(const item of list)await item.fn({preventDefault(){}});},removeAttribute(name){delete this[name];},load(){},scrollIntoView(){this.scrolled=true;},pause(){this.paused=true;},async play(){this.paused=false;},async requestFullscreen(){this.fullscreen=true;}});return nodes.get(id);};
  if(inline||overrides.inline)$('cloud-url-player').append($('watch-status'),$('watch-player-stage'));
  vm.runInNewContext(fs.readFileSync('static/watch.js','utf8'),{Date:overrides.Date||Date,localStorage:overrides.storage,HaySubProgress:overrides.progress,document:{getElementById:$,title:''},location:{origin:'http://127.0.0.1:8000',pathname:(inline||overrides.inline)?'/':(preview?'/preview/':'/watch/')+'a'.repeat(32)},window:{addEventListener:(name,fn)=>handlers.set(name,fn),dispatchEvent:event=>{events.push(event.type);handlers.get(event.type)?.(event);}},CustomEvent:class{constructor(type){this.type=type;}},HaySubMediaSources:require('../static/media-sources.js'),Blob,URL:class extends URL{static createObjectURL(blob){blobs.push(blob);return 'blob:captions';}static revokeObjectURL(){}},setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout(){},fetch:async(url,options)=>{calls.push([url,options]);if(overrides.fetch)return overrides.fetch(url,options);if(url==='/api/owner/media/cloud')return {ok:true,json:async()=>({id:'saved',title:JSON.parse(options.body).title,published:true,share_url:'/watch/saved'})};if(url==='https://cdn.test/captions.vtt')return {ok:true,text:async()=> 'WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello'};if(url==='https://cloud.test/data/subtitles/Film/armenian.srt')return {ok:true,text:async()=> '1\n00:00:01,000 --> 00:00:03,000\nHello'};return {ok:status===200,status,json:async()=>({title:'<script>Film</script>',video_url:'https://private.test/video?signature=one',subtitle_url:hasSubtitles?'https://private.test/subtitles?signature=two':null,cloud_video_url:'https://cloud.test/data/videos/Film.mp4',cloud_subtitle_url:hasSubtitles?'https://cloud.test/data/subtitles/Film/armenian.srt':null,subtitle_offset:2,subtitle_height:overrides.subtitleHeight??0,expires_in:14400})};}});
  return {$,calls,timers,blobs,events,handlers};
}
test('watch uses direct media and native Armenian track without inserting subtitle HTML',async()=>{
  const h=harness();await flush();
  assert.equal(h.$('watch-title').textContent,'<script>Film</script>');
  assert.match(h.$('watch-status').textContent,/Բեռնվում են տեսանյութի տվյալները/);
  await h.$('hosted-player').fire('loadedmetadata');
  assert.equal(h.$('watch-status').textContent,'');assert.equal(h.$('watch-status').hidden,true);
  assert.match(h.$('hosted-source').src,/private.test\/video/);assert.match(h.$('armenian-track').src,/private.test\/subtitles/);
  await h.$('armenian-track').fire('load');assert.equal(h.$('hosted-player').textTracks[0].mode,'showing');
  h.$('watch-subtitles').value='off';await h.$('watch-subtitles').fire('change');assert.equal(h.$('hosted-player').textTracks[0].mode,'disabled');
  h.$('watch-speed').value='1.5';await h.$('watch-speed').fire('change');assert.equal(h.$('hosted-player').playbackRate,1.5);
});

test('minimal public player loads native Armenian subtitles without supplemental controls',async()=>{
  const h=harness(200,false,true,false,false,{readOnly:true,minimal:true});await flush();
  assert.match(h.$('hosted-source').src,/private.test/);
  await h.$('hosted-player').fire('loadedmetadata');await h.$('armenian-track').fire('load');
  assert.equal(h.$('hosted-player').textTracks[0].mode,'showing');
  assert.equal(h.$('hosted-player').hidden,false);assert.equal(h.$('hosted-player').paused,true);
});

test('public status is visible only while loading or on error without changing playback',async()=>{
  const h=harness(200,false,true,false,false,{readOnly:true,minimal:true});await flush();
  const video=h.$('hosted-player'),status=h.$('watch-status'),source=h.$('hosted-source');
  assert.equal(status.hidden,false);
  await video.fire('loadedmetadata');assert.equal(status.hidden,true);
  const src=source.src;video.currentTime=25;
  await video.fire('waiting');assert.equal(status.hidden,false);
  await video.fire('canplay');assert.equal(status.hidden,true);
  await video.fire('playing');assert.equal(status.textContent,'');assert.equal(status.hidden,true);
  video.error={code:2};await video.fire('error');assert.equal(status.hidden,false);
  const error=status.textContent;await video.fire('canplay');await video.fire('playing');
  assert.equal(status.textContent,error);assert.equal(status.hidden,false);
  assert.equal(h.$('hosted-player'),video);assert.equal(source.src,src);assert.equal(video.currentTime,25);
});

test('resume waits for metadata, never autoplays or saves initialization zero, and saves lifecycle events',async()=>{
  let saved={position:120,duration:900,updated:1};const writes=[];
  const progress={read:()=>saved,save:(id,position,duration)=>writes.push({id,position,duration}),clear:()=>{saved=null;}};
  const h=harness(200,false,true,false,false,{progress});await flush();const video=h.$('hosted-player');video.duration=900;
  await video.fire('pause');assert.equal(writes.length,0);assert.equal(video.currentTime,0);
  await video.fire('loadedmetadata');assert.equal(video.currentTime,120);assert.equal(video.paused,true);assert.equal(h.$('watch-restart').hidden,false);
  video.currentTime=180;await video.fire('pause');await video.fire('seeked');h.handlers.get('pagehide')();assert.equal(writes.length,3);assert.equal(writes[0].position,180);
  await h.$('watch-restart').fire('click');assert.equal(video.currentTime,0);assert.equal(saved,null);assert.equal(h.$('watch-restart').hidden,true);
  saved={position:850,duration:900,updated:2};await video.fire('ended');assert.equal(saved,null);
});

test('time updates save at five-second intervals and ignore unfinished seeks',async()=>{
  let now=0;const writes=[];
  const h=harness(200,false,true,false,false,{Date:{now:()=>now},progress:{read:()=>null,save:(...args)=>writes.push(args)}});
  await flush();const video=h.$('hosted-player');video.duration=900;await video.fire('loadedmetadata');video.currentTime=100;
  now=4900;await video.fire('timeupdate');assert.equal(writes.length,0);
  now=5100;await video.fire('timeupdate');assert.equal(writes.length,1);
  video.seeking=true;now=11000;await video.fire('timeupdate');assert.equal(writes.length,1);
  video.seeking=false;await video.fire('seeked');assert.equal(writes.length,2);
});
test('expiring access renews through authorization and preserves playback position and speed',async()=>{
  const h=harness();await flush();await h.$('hosted-player').fire('loadedmetadata');
  const video=h.$('hosted-player');video.currentTime=25;video.paused=false;video.playbackRate=1.5;
  await h.timers[0]();await video.fire('loadedmetadata');
  assert.equal(video.currentTime,25);assert.equal(video.playbackRate,1.5);assert.equal(video.paused,false);assert.equal(h.calls.length,2);
});
test('unpublished and owner-only preview errors are useful and do not expose a media source',async()=>{
  const missing=harness(404);await flush();assert.equal(missing.$('hosted-source').src,undefined);assert.match(missing.$('watch-status').textContent,/հասանելի չէ/);
  const privatePage=harness(401,true);await flush();assert.match(privatePage.calls[0][0],/^\/api\/owner\/media\//);assert.match(privatePage.$('watch-status').textContent,/admin/);
});

 test('owner can preview a video without subtitles',async()=>{const h=harness(200,true,false);await flush();assert.match(h.$('hosted-source').src,/private.test\/video/);assert.equal(h.$('armenian-track').src,undefined);assert.equal(h.$('watch-subtitles').disabled,true);});


test('local playback never fetches cloud alternatives even when cloud URLs are available',async()=>{
  const h=harness();await flush();
  assert.equal(h.calls.length,1);assert.equal(h.blobs.length,0);
  assert.equal(h.$('hosted-player').src,undefined,'The video uses its local source tag');
  assert.match(h.$('hosted-source').src,/private.test/);
});

test('uncommented cloud tags select cloud video and convert its SRT to a native track in memory',async()=>{
  const h=harness(200,true,true,true);await flush();
  assert.equal(h.$('hosted-source').src,'https://cloud.test/data/videos/Film.mp4');
  assert.equal(h.$('armenian-track').src,'blob:captions');assert.equal(h.blobs.length,1);
  const vtt=await h.blobs[0].text();assert.match(vtt,/WEBVTT/);assert.match(vtt,/00:00:03.000 --> 00:00:05.000/);
  assert.equal(h.calls[1][0],'https://cloud.test/data/subtitles/Film/armenian.srt');
});


test('URL player opens without fetching a library item and loads pasted video and SRT captions',async()=>{
  const h=harness(200,false,true,false,true);await flush();assert.equal(h.calls.length,0);
  h.$('watch-video-url').value='https://cloud.test/data/videos/Film.mp4';
  h.$('watch-subtitle-url').value='https://cloud.test/data/subtitles/Film/armenian.srt';
  await h.$('watch-url-form').fire('submit');await h.$('hosted-player').fire('loadedmetadata');
  assert.equal(h.$('hosted-source').src,'https://cloud.test/data/videos/Film.mp4');
  assert.equal(h.$('armenian-track').src,'blob:captions');assert.equal(h.$('hosted-player').hidden,false);
  assert.equal(h.$('hosted-player').paused,false);assert.equal(h.$('watch-controls').hidden,false);
  assert.equal(h.$('watch-subtitles').disabled,false);assert.equal(h.$('hosted-player').textTracks[0].mode,'showing');
  assert.match(await h.blobs[0].text(),/00:00:01.000 --> 00:00:03.000/);
  assert.equal(h.calls.length,1);assert.equal(h.$('watch-url-load').disabled,false);
});

test('pasted VTT captions use the native track and can be replaced by a video without subtitles',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  h.$('watch-video-url').value='https://cdn.test/one.mp4';h.$('watch-subtitle-url').value='https://cdn.test/captions.vtt';
  await h.$('watch-url-form').fire('submit');assert.match(await h.blobs[0].text(),/^WEBVTT/);
  h.$('watch-video-url').value='https://cdn.test/two.mp4';h.$('watch-subtitle-url').value='';
  await h.$('watch-url-form').fire('submit');
  assert.equal(h.$('hosted-source').src,'https://cdn.test/two.mp4');assert.equal(h.$('armenian-track').src,undefined);
  assert.equal(h.$('watch-subtitles').disabled,true);assert.equal(h.$('hosted-player').paused,false);
});

test('invalid or credential-bearing URLs cannot change the player source',async()=>{
  const h=harness(200,false,true,false,true);await flush();h.$('watch-subtitle-url').value='';
  for(const value of ['javascript:alert(1)','file:///C:/movie.mp4','https://user:secret@cdn.test/video.mp4','not a URL']){
    h.$('watch-video-url').value=value;await h.$('watch-url-form').fire('submit');
    assert.equal(h.$('hosted-source').src,undefined);assert.equal(h.calls.length,0);
  }
});

test('a subtitle request failure leaves the current video intact and allows another attempt',async()=>{
  const h=harness(200,false,true,false,true,{fetch:async()=>({ok:false})});await flush();
  h.$('watch-video-url').value='https://cdn.test/one.mp4';h.$('watch-subtitle-url').value='';await h.$('watch-url-form').fire('submit');
  h.$('watch-video-url').value='https://cdn.test/two.mp4';h.$('watch-subtitle-url').value='https://cdn.test/missing.vtt';await h.$('watch-url-form').fire('submit');
  assert.equal(h.$('hosted-source').src,'https://cdn.test/one.mp4');assert.equal(h.$('watch-url-load').disabled,false);
  assert.match(h.$('watch-status').textContent,/Could not load subtitles/);
});

test('URL retry preserves position and speed without returning to local playback',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  h.$('watch-video-url').value='https://cdn.test/one.mp4';h.$('watch-subtitle-url').value='';await h.$('watch-url-form').fire('submit');await h.$('hosted-player').fire('loadedmetadata');
  const video=h.$('hosted-player');video.currentTime=25;video.playbackRate=1.5;
  await h.$('watch-retry').fire('click');await video.fire('loadedmetadata');
  assert.equal(video.currentTime,25);assert.equal(video.playbackRate,1.5);assert.equal(video.paused,false);assert.equal(h.calls.length,0);
});

test('a slow local playback response cannot overwrite a newly loaded pasted URL',async()=>{
  let resolve;
  const h=harness(200,false,true,false,false,{fetch:()=>new Promise(done=>{resolve=done;})});await flush();
  h.$('watch-video-url').value='https://cdn.test/manual.mp4';h.$('watch-subtitle-url').value='';await h.$('watch-url-form').fire('submit');
  resolve({ok:true,json:async()=>({title:'Old local film',video_url:'/old.mp4',subtitle_url:null,expires_in:14400})});await flush();
  assert.equal(h.$('hosted-source').src,'https://cdn.test/manual.mp4');assert.equal(h.$('watch-title').textContent,'manual.mp4');
});


test('home-page cloud inputs play inline without opening a new page or loading a library item',async()=>{
  const h=harness(200,false,true,false,false,{inline:true});await flush();
  assert.equal(h.calls.length,0);assert.equal(h.$('watch-title').textContent,'Cloud video');
  h.$('watch-video-url').value='https://cdn.test/inline.mp4';h.$('watch-subtitle-url').value='https://cdn.test/captions.vtt';
  await h.$('watch-url-form').fire('submit');await h.$('hosted-player').fire('loadedmetadata');
  assert.equal(h.$('hosted-source').src,'https://cdn.test/inline.mp4');assert.equal(h.$('hosted-player').hidden,false);
  assert.equal(h.$('hosted-player').paused,false);assert.equal(h.$('armenian-track').src,'blob:captions');
});


test('blocked subtitle fetch explains the storage CORS setting and identifies the page origin',async()=>{
  const h=harness(200,false,true,false,true,{fetch:async()=>{throw TypeError('Failed to fetch');}});await flush();
  h.$('watch-video-url').value='https://cdn.test/video.mp4';h.$('watch-subtitle-url').value='https://cdn.test/captions.vtt';
  await h.$('watch-url-form').fire('submit');
  assert.match(h.$('watch-status').textContent,/CORS policy/);
  assert.match(h.$('watch-status').textContent,/http:\/\/127\.0\.0\.1:8000/);
  assert.equal(h.$('watch-url-load').disabled,false);
  assert.equal(h.$('hosted-source').src,undefined);
});


test('after a pasted video loads, Add to page saves its title and exact loaded URLs once',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  h.$('watch-video-url').value='https://cloud.test/data/videos/Film.mp4';h.$('watch-subtitle-url').value='https://cloud.test/data/subtitles/Film/armenian.srt';
  await h.$('watch-url-form').fire('submit');assert.equal(h.$('watch-save-form').hidden,true);
  await h.$('watch-save-form').fire('submit');assert.equal(h.calls.some(([url])=>url==='/api/owner/media/cloud'),false);
  await h.$('hosted-player').fire('loadedmetadata');assert.equal(h.$('watch-save-form').hidden,false);
  assert.equal(h.$('watch-save-title').value,'Film');h.$('watch-save-title').value='My movie';
  h.$('watch-video-url').value='https://cdn.test/not-loaded.mp4';
  const video=h.$('hosted-player');video.currentTime=25;video.playbackRate=1.5;
  const source=h.$('hosted-source').src,captions=h.$('armenian-track').src;
  await h.$('watch-save-form').fire('submit');
  const saved=h.calls.find(([url])=>url==='/api/owner/media/cloud');const body=JSON.parse(saved[1].body);
  assert.equal(body.title,'My movie');assert.equal(body.video_url,'https://cloud.test/data/videos/Film.mp4');
  assert.equal(body.subtitle_url,'https://cloud.test/data/subtitles/Film/armenian.srt');
  assert.deepEqual(h.events,['haysub-media-updated']);
  assert.equal(video.hidden,true);assert.equal(video.paused,true);
  assert.equal(video.currentTime,25);assert.equal(video.playbackRate,1.5);
  assert.equal(h.$('hosted-source').src,source);assert.equal(h.$('armenian-track').src,captions);
  assert.equal(h.$('watch-player-stage').hidden,true);
  assert.equal(h.$('watch-controls').hidden,true);assert.equal(h.$('watch-save-form').hidden,true);
  assert.equal(h.$('watch-video-url').value,'');assert.equal(h.$('watch-subtitle-url').value,'');
  assert.equal(h.$('watch-save-title').value,'');assert.equal(h.$('watch-title').textContent,'Cloud video');
  assert.equal(h.$('watch-status').textContent,'');
  await h.$('watch-save-form').fire('submit');assert.equal(h.calls.filter(([url])=>url==='/api/owner/media/cloud').length,1);
});

test('a failed save retains the loaded movie and title for retry',async()=>{
  const h=harness(200,false,true,false,true,{fetch:async()=>({ok:false,json:async()=>({detail:'Save unavailable'})})});await flush();
  h.$('watch-video-url').value='https://cdn.test/movie.mp4';h.$('watch-subtitle-url').value='';await h.$('watch-url-form').fire('submit');await h.$('hosted-player').fire('loadedmetadata');
  h.$('watch-save-title').value='Keep this title';await h.$('watch-save-form').fire('submit');
  assert.equal(h.$('watch-save-submit').disabled,false);assert.equal(h.$('watch-save-title').value,'Keep this title');
  assert.equal(h.$('hosted-player').paused,false);assert.match(h.$('watch-status').textContent,/Save unavailable/);
});


test('clicking a saved cloud watch page loads captions without forcing autoplay',async()=>{
  const h=harness(200,false,true,false,false,{fetch:async url=>url.startsWith('/api/')?{ok:true,json:async()=>({title:'Saved Cloud movie',source_type:'cloud',video_url:'https://cdn.test/movie.mp4',subtitle_url:'https://cdn.test/unknown-format',expires_in:14400})}:{ok:true,text:async()=> '1\n00:00:01,000 --> 00:00:03,000\nHello'}});
  await flush();await h.$('hosted-player').fire('loadedmetadata');
  assert.equal(h.$('hosted-source').src,'https://cdn.test/movie.mp4');assert.equal(h.$('armenian-track').src,'blob:captions');
  assert.equal(h.$('hosted-player').paused,true);assert.equal(h.$('watch-save-form').hidden,true);
});


test('a title click loads the selected library movie into the existing player without navigation',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  h.handlers.get('haysub-play-video')({detail:{id:'b'.repeat(32),owner:true}});await flush();await h.$('hosted-player').fire('loadedmetadata');
  assert.equal(h.calls[0][0],'/api/owner/media/'+'b'.repeat(32)+'/playback');
  assert.equal(h.$('hosted-source').src,'https://private.test/video?signature=one');
  assert.equal(h.$('armenian-track').src,'https://private.test/subtitles?signature=two');
  assert.equal(h.$('hosted-player').hidden,false);assert.equal(h.$('hosted-player').paused,false);
  assert.equal(h.$('watch-player-stage').scrolled,true);
});

test('visitor titles play inline using public access without owner-only forms or endpoints',async()=>{
  const h=harness(200,false,true,false,true,{readOnly:true});await flush();
  assert.equal(h.$('watch-url-form'),null);assert.equal(h.$('watch-save-form'),null);
  h.handlers.get('haysub-play-video')({detail:{id:'c'.repeat(32),owner:true}});await flush();
  assert.equal(h.calls[0][0],'/api/public/hosted/'+'c'.repeat(32)+'/playback');
  assert.equal(h.$('hosted-player').paused,false);assert.equal(h.$('cloud-url-player').hidden,false);
});

test('selecting a listed title replaces a previously pasted URL and keeps retry on that listed movie',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  h.$('watch-video-url').value='https://cdn.test/manual.mp4';h.$('watch-subtitle-url').value='';await h.$('watch-url-form').fire('submit');
  h.handlers.get('haysub-play-video')({detail:{id:'d'.repeat(32),owner:true}});await flush();
  assert.equal(h.$('hosted-source').src,'https://private.test/video?signature=one');
  await h.$('watch-retry').fire('click');
  assert.equal(h.calls.filter(([url])=>url==='/api/owner/media/'+'d'.repeat(32)+'/playback').length,2);
});


test('saving closes editing and the saved preview can be reopened with the list Private preview action',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  h.$('watch-video-url').value='https://cdn.test/movie.mp4';h.$('watch-subtitle-url').value='';
  await h.$('watch-url-form').fire('submit');await h.$('hosted-player').fire('loadedmetadata');
  await h.$('watch-save-form').fire('submit');
  assert.equal(h.$('hosted-player').hidden,true);assert.equal(h.$('hosted-player').paused,true);
  const savedMessage=h.$('watch-status').textContent;await h.$('hosted-player').fire('playing');await h.$('hosted-player').fire('waiting');
  assert.equal(h.$('watch-status').textContent,savedMessage);
  h.handlers.get('haysub-play-video')({detail:{id:'a'.repeat(32),owner:true}});await flush();await h.$('hosted-player').fire('loadedmetadata');
  assert.equal(h.$('hosted-player').hidden,false);assert.equal(h.$('hosted-player').paused,false);
  assert.equal(h.$('watch-controls').hidden,false);assert.equal(h.$('watch-save-form').hidden,true);
});


test('Private preview is placed directly below its video heading and Close pauses and hides it',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  const card=h.$('selected-card'),heading=h.$('selected-heading');card.append(heading);
  h.handlers.get('haysub-play-video')({detail:{id:'a'.repeat(32),owner:true,anchor:heading}});await flush();
  const stage=h.$('watch-player-stage');assert.equal(card.children[1],stage);assert.equal(stage.parentElement,card);
  assert.equal(stage.hidden,false);assert.equal(h.$('watch-status').parentElement,stage);
  assert.equal(h.$('hosted-player').paused,false);
  await h.$('watch-close').fire('click');
  assert.equal(stage.hidden,true);assert.equal(h.$('hosted-player').paused,true);assert.equal(h.$('hosted-player').hidden,true);
  assert.equal(stage.parentElement,h.$('cloud-url-player'));assert.equal(card.children.length,1);
});

test('opening a second preview moves one shared player below the second heading',async()=>{
  const h=harness(200,false,true,false,true);await flush();
  const first=h.$('first-card'),firstHeading=h.$('first-heading'),second=h.$('second-card'),secondHeading=h.$('second-heading');
  first.append(firstHeading);second.append(secondHeading);
  h.handlers.get('haysub-play-video')({detail:{id:'a'.repeat(32),owner:true,anchor:firstHeading}});await flush();
  h.handlers.get('haysub-play-video')({detail:{id:'b'.repeat(32),owner:true,anchor:secondHeading}});await flush();
  assert.equal(first.children.length,1);assert.equal(second.children[1],h.$('watch-player-stage'));
  assert.equal(h.$('hosted-player').paused,false);
});

test('Close during a slow preview request prevents the player from reappearing',async()=>{
  let resolve;const h=harness(200,false,true,false,true,{fetch:()=>new Promise(done=>{resolve=done;})});await flush();
  const card=h.$('slow-card'),heading=h.$('slow-heading');card.append(heading);
  h.handlers.get('haysub-play-video')({detail:{id:'a'.repeat(32),owner:true,anchor:heading}});
  await h.$('watch-close').fire('click');
  resolve({ok:true,json:async()=>({title:'Slow movie',video_url:'/slow.mp4',subtitle_url:null,expires_in:14400})});await flush();
  assert.equal(h.$('watch-player-stage').hidden,true);assert.equal(h.$('hosted-player').hidden,true);
  assert.equal(h.$('hosted-player').paused,true);assert.equal(h.$('watch-url-load').disabled,false);
});
