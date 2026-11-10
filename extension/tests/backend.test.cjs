const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const C=require('../core.js');
const source=fs.readFileSync(path.join(__dirname,'../background.js'),'utf8');
const VIDEO='abcdefghijk',ID='1'.repeat(32);
const SRT='1\n00:00:01,000 --> 00:00:03,000\nHello';
function harness(publicMode=false){
  const data={},calls=[];let listener,number=0,quota=false,configured=true,failed=false,defer=null;
  let state={cues:[{id:1,start:1,end:3,text:'Բարև'}],total:2,completed:1,running:true,error:'',phase:'translating',source:'uploaded'};
  const chrome={runtime:{id:'extension-id',onMessage:{addListener:fn=>listener=fn}},storage:{local:{
    get:async keys=>Object.fromEntries((keys===null?Object.keys(data):Array.isArray(keys)?keys:[keys]).filter(k=>k in data).map(k=>[k,data[k]])),
    set:async obj=>Object.assign(data,JSON.parse(JSON.stringify(obj))),remove:async keys=>{for(const k of Array.isArray(keys)?keys:[keys])delete data[k];},
    getBytesInUse:async keys=>quota&&keys===null?C.SAVE_BUDGET+100:Object.entries(data).filter(([k])=>keys===null||(Array.isArray(keys)?keys:[keys]).includes(k)).reduce((sum,[k,v])=>sum+C.recordBytes(k,v),0)
  }}};
  const context=vm.createContext({HaySubCore:C,HaySubRelease:{apiBase:'http://127.0.0.1:8000',publicMode},chrome,importScripts(){},FormData,Blob,AbortSignal,
    fetch:async(url,options)=>{
      calls.push({url,options});assert.ok(url.startsWith('http://127.0.0.1:8000/api/'));
      if(failed)throw Error('network');
      if(url.endsWith('/api/config'))return {ok:true,json:async()=>({configured})};
      if(url.endsWith('/api/videos')||url.endsWith('/api/subtitle-files'))return {ok:true,json:async()=>({id:String(++number).repeat(32),phase:'translating'})};
      if(url.endsWith('/translated-subtitles')){if(defer)await defer;return {ok:true,json:async()=>state};}
      return {ok:true,json:async()=>({ok:true})};
    }
  });
  vm.runInContext(source,context);
  const send=message=>new Promise(resolve=>listener({videoId:VIDEO,...message},{id:'extension-id'},resolve));
  return {send,data,calls,setState:s=>state=s,quota:()=>quota=true,offline:()=>failed=true,unconfigured:()=>configured=false,defer:p=>defer=p};
}
test('uploaded text creates a backend job and incremental Armenian SRT, never English fallback',async()=>{
  const h=harness();assert.equal((await h.send({type:'HAYSUB_TRANSLATE_START',text:SRT,name:'test.srt'})).ok,true);
  const post=h.calls.find(c=>c.url.endsWith('/api/videos'));
  assert.equal(post.options.body.get('url'),'https://www.youtube.com/watch?v='+VIDEO);
  assert.equal(post.options.body.get('native_captions'),'true');
  assert.equal(await post.options.body.get('subtitles').text(),SRT);
  assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,'');
  await h.send({type:'HAYSUB_TRANSLATE_POLL',position:2});
  const record=h.data[C.FILE_PREFIX+VIDEO];
  assert.equal(C.parse(record.text).cues[0].text,'Բարև');assert.equal(record.language,'hy');assert.equal(record.pendingTranslation,true);
  assert.equal(JSON.parse(h.calls.find(c=>c.url.endsWith('/position')).options.body).seconds,2);
  assert.doesNotMatch(record.text,/Hello/);
  h.setState({cues:[{id:1,start:1,end:3,text:'Բարև'},{id:2,start:4,end:5,text:'Ցտեսություն'}],total:2,completed:2,running:false,error:'',phase:'ready'});
  const result=await h.send({type:'HAYSUB_TRANSLATE_POLL'});assert.equal(result.running,false);
  assert.equal(C.parse(h.data[C.FILE_PREFIX+VIDEO].text).cues.length,2);
});

test('public release never starts, retries or polls paid translation APIs',async()=>{
  const h=harness(true);
  for(const type of ['HAYSUB_TRANSLATE_START','HAYSUB_TRANSLATE_RETRY','HAYSUB_TRANSLATE_POLL']){
    assert.equal((await h.send({type,text:SRT,name:'film.srt'})).ok,false);
  }
  assert.equal((await h.send({type:'HAYSUB_TRANSLATE_CANCEL',forget:true})).ok,true);
  assert.equal(h.calls.length,0);
});
test('automatic caption request has no uploaded file; later upload cancels and replaces it',async()=>{
  const h=harness();await h.send({type:'HAYSUB_TRANSLATE_START'});
  assert.equal(h.calls.find(c=>c.url.endsWith('/api/videos')).options.body.get('subtitles'),null);
  await h.send({type:'HAYSUB_TRANSLATE_START',text:SRT,name:'priority.srt'});
  assert.ok(h.calls.some(c=>c.url.endsWith(`/api/videos/${ID}/cancel`)));
  assert.equal(h.data[C.JOB_PREFIX+VIDEO].backendId,'2'.repeat(32));assert.equal(h.data[C.JOB_PREFIX+VIDEO].source,'uploaded');
});
test('unavailable backend and missing key return useful errors without storing a fake success',async()=>{
  const h=harness();h.offline();const result=await h.send({type:'HAYSUB_TRANSLATE_START'});
  assert.equal(result.ok,false);assert.match(result.error,/Python/);assert.equal(h.data[C.JOB_PREFIX+VIDEO],undefined);
  const k=harness();k.unconfigured();assert.match((await k.send({type:'HAYSUB_TRANSLATE_START'})).error,/GEMINI_API_KEY/);
});
test('storage quota cancels the newly created job instead of running untracked requests',async()=>{
  const h=harness();h.quota();const response=await h.send({type:'HAYSUB_TRANSLATE_START'});
  assert.equal(response.ok,false);assert.ok(h.calls.some(c=>c.url.endsWith('/cancel')));assert.equal(h.data[C.FILE_PREFIX+VIDEO],undefined);
});
test('in-flight old job cannot overwrite a replacement file',async()=>{
  const h=harness();await h.send({type:'HAYSUB_TRANSLATE_START'});
  let resolve;h.defer(new Promise(r=>resolve=r));const polling=h.send({type:'HAYSUB_TRANSLATE_POLL'});
  await new Promise(r=>setImmediate(r));
  h.data[C.JOB_PREFIX+VIDEO]={backendId:'2'.repeat(32),running:true};h.data[C.FILE_PREFIX+VIDEO]={text:'new'};
  resolve();await polling;assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,'new');
});
test('backend source-language text is not persisted as Armenian; symbols remain allowed',async()=>{
  const h=harness();await h.send({type:'HAYSUB_TRANSLATE_START'});
  h.setState({cues:[{id:1,start:1,end:3,text:'Hello'}],total:1,completed:1,running:false,error:'',phase:'ready'});
  assert.equal((await h.send({type:'HAYSUB_TRANSLATE_POLL'})).ok,false);
  assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,'');
  const s=harness();await s.send({type:'HAYSUB_TRANSLATE_START'});
  s.setState({cues:[{id:1,start:1,end:3,text:'♪'}],total:1,completed:1,running:false,error:'',phase:'ready'});
  assert.equal((await s.send({type:'HAYSUB_TRANSLATE_POLL'})).ok,true);
});
test('restored backend job with no hydrated translations offers retry, not false completion',async()=>{
  const h=harness();await h.send({type:'HAYSUB_TRANSLATE_START'});
  h.setState({cues:[],total:10,completed:0,running:false,error:'',phase:'ready',needs_resume:true});
  await h.send({type:'HAYSUB_TRANSLATE_POLL'});
  assert.match(h.data[C.JOB_PREFIX+VIDEO].error,/Կրկնել/);
  assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,'');
});
test('generic pages translate only the uploaded file and never send their URL or fetch video',async()=>{
  const h=harness(),page='page:'+'a'.repeat(64);
  assert.equal((await h.send({type:'HAYSUB_TRANSLATE_START',videoId:page,text:SRT,name:'movie.srt'})).ok,true);
  const post=h.calls.find(c=>c.url.endsWith('/api/subtitle-files'));
  assert.ok(post);assert.equal(post.options.body.get('url'),null);
  assert.equal(h.data[C.JOB_PREFIX+page].kind,'file');
  await h.send({type:'HAYSUB_TRANSLATE_POLL',videoId:page,position:2});
  assert.ok(h.calls.some(c=>c.url.includes('/api/subtitle-files/')&&c.url.endsWith('/translated-subtitles')));
  assert.equal(C.parse(h.data[C.FILE_PREFIX+page].text).cues[0].text,'Բարև');
  const noFile=harness();assert.equal((await noFile.send({type:'HAYSUB_TRANSLATE_START',videoId:page})).ok,false);
  assert.equal(noFile.calls.length,0);
});
