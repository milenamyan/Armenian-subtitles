const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const C=require('../core.js');
const source=fs.readFileSync(path.join(__dirname,'../popup.js'),'utf8');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function harness(translate=false,site=false,connectionError=null,publicMode=false){
  const fields=new Map(),data={unrelated:'keep',[C.TRANSLATE_KEY]:translate},writes=[],messages=[];
  let status={videoId:site?'page:'+'a'.repeat(64):'abcdefghijk',hasVideo:true,site},quota=false;
  const get=id=>{if(!fields.has(id))fields.set(id,{value:'',checked:false,disabled:false,files:[],children:[],append(child){this.children.push(child);},replaceChildren(){this.children=[];},textContent:'',classList:{toggle(){}},listeners:new Map(),addEventListener(name,fn){this.listeners.set(name,fn);},async fire(name){await this.listeners.get(name)?.();}});return fields.get(id);};
  const storage={
    get:async keys=>{if(keys===null)return {...data};return Object.fromEntries((Array.isArray(keys)?keys:[keys]).filter(k=>k in data).map(k=>[k,data[k]]));},
    getBytesInUse:async keys=>{if(quota&&keys===null)return C.SAVE_BUDGET+100;return Object.entries(data).filter(([key])=>keys===null||key===keys).reduce((n,[key,value])=>n+C.recordBytes(key,value),0);},
    set:async obj=>{writes.push(obj);Object.assign(data,obj);},remove:async keys=>{for(const key of keys)delete data[key];}
  };
  const makeNode=()=>({children:[],listeners:new Map(),append(...nodes){this.children.push(...nodes);},addEventListener(name,fn){this.listeners.set(name,fn);},async fire(name){await this.listeners.get(name)?.();}});
  const context=vm.createContext({HaySubCore:C,HaySubRelease:{publicMode},URL,HaySubPageAccess:site?{connect:async()=>({site:true,frameId:9,frameUrl:'https://player.test/embed',players:[],videoIndex:0})}:undefined,document:{getElementById:get,createElement:makeNode},location:{reload(){context.reloaded=true;}},TextDecoder,chrome:{permissions:{request:async()=>false},webNavigation:{getAllFrames:async()=>assert.fail('Do not read frames without permission')},runtime:{sendMessage:async message=>{messages.push(message);return {ok:true};}},storage:{local:storage,onChanged:{addListener(){}}},tabs:{query:async()=>[{id:7,url:site?'https://movies.test/movie':'https://www.youtube.com/watch?v=abcdefghijk'}],sendMessage:async()=>status}}});
  if(connectionError)context.HaySubPageAccess.connect=async()=>{throw Error(connectionError);};
  vm.runInContext(source,context);
  const upload=async(text,name='test.srt')=>{const bytes=new TextEncoder().encode(text);get('file').files=[{name,size:bytes.length,arrayBuffer:async()=>bytes.buffer}];await get('file').fire('change');};
  return {get,data,writes,messages,upload,context,setStatus:s=>status=s,setQuota:q=>quota=q};
}
const srt='1\n00:00:01,000 --> 00:00:03,000\nԲարև\nHello';
test('popup saves UTF-8 subtitles by video, settings, offset and allows clearing',async()=>{
  const h=harness();await flush();await h.upload(srt);
  assert.equal(h.data[C.FILE_PREFIX+'abcdefghijk'].text,srt);
  assert.match(h.get('status').textContent,/Պատրաստ է/);
  h.get('fontSize').value='40';h.get('offset').value='-2';await h.get('offset').fire('change');await flush();
  assert.equal(h.data[C.SETTINGS_KEY].fontSize,40);assert.equal(h.data[C.OFFSET_PREFIX+'abcdefghijk'],-2);
  await h.get('clear-current').fire('click');assert.equal(h.data[C.FILE_PREFIX+'abcdefghijk'],undefined);assert.equal(h.data.unrelated,'keep');
  await h.upload(srt);h.data[C.FILE_PREFIX+'zyxwvutsrqp']={text:srt};
  await h.get('clear-all').fire('click');assert.equal(C.savedKeys(h.data).length,0);assert.ok(h.data[C.SETTINGS_KEY]);assert.equal(h.data.unrelated,'keep');
});
test('quota failure preserves previous subtitle association',async()=>{
  const h=harness();await flush();await h.upload(srt,'old.srt');
  h.setQuota(true);await h.upload(srt+'\nnew text','new.srt');
  assert.equal(h.data[C.FILE_PREFIX+'abcdefghijk'].name,'old.srt');assert.match(h.get('status').textContent,/հիշողությունը լցվել/);
});
test('navigation prevents an upload being attached to a different video',async()=>{
  const h=harness();await flush();h.setStatus({videoId:'zyxwvutsrqp',hasVideo:true});await h.upload(srt);
  assert.equal(C.savedKeys(h.data).length,0);assert.match(h.get('status').textContent,/Տեսանյութը փոխվել/);
});
test('invalid UTF-8 and wrong file extensions are explained in Armenian',async()=>{
  const h=harness();await flush();await h.upload(srt,'bad.txt');assert.match(h.get('status').textContent,/միայն .srt/);
  h.get('file').files=[{name:'bad.srt',size:1,arrayBuffer:async()=>new Uint8Array([255]).buffer}];await h.get('file').fire('change');
  assert.match(h.get('status').textContent,/UTF-8/);assert.equal(C.savedKeys(h.data).length,0);
});
test('translation-enabled popup auto-starts YouTube captions, then prioritizes uploaded file',async()=>{
  const h=harness(true);await flush();
  assert.equal(h.messages[0].type,'HAYSUB_TRANSLATE_START');assert.equal(h.messages[0].text,undefined);
  await h.upload(srt);
  const last=h.messages.at(-1);assert.equal(last.type,'HAYSUB_TRANSLATE_START');assert.equal(last.text,srt);assert.equal(last.name,'test.srt');
  assert.equal(h.data[C.FILE_PREFIX+'abcdefghijk'],undefined,'English source must not be silently saved as Armenian');
});
test('other sites default to local subtitles and never auto-fetch captions',async()=>{
  const h=harness(true,true);await flush();
  assert.equal(h.get('translate-enabled').checked,false);
  assert.equal(h.get('translate-youtube').hidden,true);assert.equal(h.messages.length,0);
  await h.upload(srt);assert.equal(h.data[C.FILE_PREFIX+'page:'+'a'.repeat(64)].text,srt);
  assert.ok(h.messages.every(msg=>msg.type==='HAYSUB_TRANSLATE_CANCEL'));
});
test('denied frame permission is explained without listing or injecting frames',async()=>{
  const h=harness(false,true);await flush();await h.get('site-embedded').fire('click');
  assert.match(h.get('status').textContent,/թույլտվությունը չի տրվել/);
});

test('failed site activation keeps embedded player recovery visible',async()=>{
  const h=harness(true,true,'Cannot access player');await flush();
  assert.equal(h.get('site-controls').hidden,false);
  assert.equal(h.get('translate-youtube').hidden,true);
  assert.equal(h.get('translate-enabled').checked,false);
  assert.match(h.get('video-label').textContent,/movies\.test/);
  assert.equal(h.get('status').textContent,'Cannot access player');
  await h.get('site-embedded').fire('click');
  assert.match(h.get('status').textContent,/թույլտվությունը չի տրվել/);
  assert.equal(h.messages.length,0);
});

test('embedded player connection copies a stranded file from a page with no video',async()=>{
  const h=harness(false,true);await flush();
  h.setStatus({videoId:'page:'+'a'.repeat(64),hasVideo:false,site:true});
  await h.upload(srt);
  h.context.chrome.permissions.request=async()=>true;
  h.context.HaySubPageAccess.discover=async()=>[{frameId:12,url:'https://player.test/film'}];
  h.context.HaySubPageAccess.activate=async()=>({status:{hasVideo:true,videoId:'page:'+'b'.repeat(64)}});
  await h.get('site-embedded').fire('click');
  assert.equal(h.get('site-frame').value,12);
  await h.get('site-frame-allow').fire('click');
  assert.equal(h.data[C.FILE_PREFIX+'page:'+'b'.repeat(64)].text,srt);
  assert.equal(h.context.reloaded,true);
});

test('an empty iframe reports a useful error without pretending subtitles are connected',async()=>{
  const h=harness(false,true);await flush();
  h.context.chrome.permissions.request=async()=>true;
  h.context.HaySubPageAccess.discover=async()=>[{frameId:12,url:'https://player.test/ad'}];
  h.context.HaySubPageAccess.activate=async()=>({status:{hasVideo:false}});
  await h.get('site-embedded').fire('click');await h.get('site-frame-allow').fire('click');
  assert.match(h.get('status').textContent,/frame-ում տեսանյութ չկա/);
  assert.equal(h.context.reloaded,undefined);
});

test('public popup hides translation, never auto-translates, and keeps uploads local',async()=>{
  const h=harness(true,false,null,true);await flush();
  assert.equal(h.get('translation-controls').hidden,true);
  assert.equal(h.get('translate-enabled').checked,false);assert.equal(h.messages.length,0);
  await h.upload(srt);assert.equal(h.data[C.FILE_PREFIX+'abcdefghijk'].text,srt);
  assert.ok(h.messages.every(message=>message.type==='HAYSUB_TRANSLATE_CANCEL'));
});

test('public popup lists literal film names and applies the chosen shared subtitle',async()=>{
  const h=harness(false,false,null,true);await flush();
  const requests=[],identity='a'.repeat(32);
  h.context.chrome.runtime.sendMessage=async message=>{
    requests.push(message);
    if(message.type==='HAYSUB_LIBRARY_LIST')return {ok:true,items:[{id:identity,title:'<script>Film</script>'}]};
    if(message.type==='HAYSUB_LIBRARY_USE'){h.data[C.FILE_PREFIX+'abcdefghijk']={text:srt,name:'Film_hy.srt',language:'hy'};return {ok:true,cueCount:1};}
    return {ok:true};
  };
  await h.get('library-open').fire('click');
  const row=h.get('extension-library-results').children[0];
  assert.equal(row.children[0].textContent,'<script>Film</script>');
  await row.children[1].fire('click');
  assert.equal(requests.at(-1).identity,identity);
  assert.match(h.get('status').textContent,/Պատրաստ է/);
  assert.match(h.get('file-label').textContent,/Film_hy.srt/);
});
