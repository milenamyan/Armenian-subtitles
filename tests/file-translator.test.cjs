const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const code=fs.readFileSync('static/file-translator.js','utf8');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('older server without ETA uses active chunk timing',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'rus.vtt',size:20}];
  await h.$('file-translation-form').fire('submit');
  h.setState({...h.initial(),total:1554,completed:1236,active_chunk:{first:1237,last:1248},elapsed:47});
  await h.tick();
  assert.match(h.$('file-translation-status').textContent,/Մոտավոր մնացել է՝ 21 րոպե/);
});
test('remaining estimate updates and disappears on pause',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  assert.match(h.$('file-translation-status').textContent,/Մնացած ժամանակը հաշվարկվում է/);
  h.setState({...h.initial(),completed:12,estimated_remaining_seconds:3780});await h.tick();
  assert.match(h.$('file-translation-status').textContent,/Մոտավոր մնացել է՝ 1 ժամ 3 րոպե/);
  h.setState({...h.initial(),running:false,phase:'cancelled'});await h.tick();
  assert.doesNotMatch(h.$('file-translation-status').textContent,/Մոտավոր մնացել է/);
});
function harness(fetchOverride){
  const nodes=new Map(),timers=new Map(),session=new Map(),calls=[];
  let current={id:'abc',filename:'test.srt',total:24,completed:0,running:true,ready:false,error:'',active_chunk:null,download_url:null};
  let nextTimer=0;
  const $=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',hidden:false,disabled:false,files:[],attributes:{},listeners:new Map(),classList:{toggle(){}},reset(){},focus(){},showModal(){this.open=true;},close(){this.open=false;},removeAttribute(name){delete this[name];},addEventListener(name,fn){this.listeners.set(name,fn);},async fire(name){await this.listeners.get(name)?.({preventDefault(){}});}});return nodes.get(id);};
  const context=vm.createContext({document:{getElementById:$},sessionStorage:{setItem:(k,v)=>session.set(k,v),getItem:k=>session.get(k),removeItem:k=>session.delete(k)},
    FormData:class{append(){}},setTimeout:fn=>{timers.set(++nextTimer,fn);return nextTimer;},clearTimeout:id=>timers.delete(id),
    fetch:async(url,options)=>{calls.push([url,options?.method]);return fetchOverride?fetchOverride(url,options,current):{ok:true,json:async()=>({...current})};}
  });
  vm.runInContext(code,context);
  return {$,calls,timers,setState:s=>current=s,initial:()=>({...current}),tick:async()=>{const all=[...timers.values()];timers.clear();for(const fn of all)await fn();}};
}
test('temporary provider failures show automatic retry and keep polling',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  h.setState({...h.initial(),completed:12,phase:'retrying',retry_after_seconds:28});
  await h.tick();
  assert.match(h.$('file-translation-status').textContent,/Ավտոմատ կրկին կփորձենք 28/);
  assert.equal(h.$('file-translation-progress').value,12);
  assert.equal(h.$('file-translation-retry').hidden,true);
  assert.equal(h.$('file-translation-cancel').hidden,false);
  assert.equal(h.$('translate-file-submit').disabled,true);
  assert.equal(h.timers.size,1);
});
test('file-only form shows real progress then download, no player required',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  assert.equal(h.calls[0][0],'/api/subtitle-files');assert.equal(h.$('translate-file-submit').disabled,true);
  assert.equal(h.$('file-download').hidden,true);
  h.setState({...h.initial(),completed:12,active_chunk:{first:13,last:24},elapsed:8});await h.tick();
  assert.equal(h.$('file-translation-progress').value,12);assert.match(h.$('file-translation-status').textContent,/13–24/);
  h.setState({...h.initial(),completed:24,running:false,ready:true,download_url:'/api/subtitle-files/abc/download'});await h.tick();
  assert.equal(h.$('file-download').hidden,false);assert.equal(h.$('file-download').href,'/api/subtitle-files/abc/download');
  assert.equal(h.$('translate-file-submit').disabled,false);assert.equal(h.timers.size,0);
});

test('an outdated poll failure cannot overwrite the removal status',async()=>{
  let rejectPoll;
  const h=harness(async(url,options,current)=>{
    if(!options?.method)return new Promise((resolve,reject)=>{rejectPoll=reject;});
    return {ok:true,json:async()=>({...current})};
  });
  h.$('file-translation-form').reset=()=>{};
  h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  const polling=h.tick();
  await h.$('file-translation-remove').fire('click');
  const status=h.$('file-translation-status').textContent;
  rejectPoll(Error('stale request failed'));
  await polling;
  assert.equal(h.$('file-translation-status').textContent,status);
  assert.equal(h.$('file-translation-retry').hidden,true);
  assert.equal(h.timers.size,0);
});

test('missing restored jobs clear the session and hide unusable retry',async()=>{
  const h=harness(async(url,options,current)=>options?.method
    ?{ok:true,json:async()=>({...current})}
    :{ok:false,status:404,json:async()=>({detail:'Job not found'})});
  h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  await h.tick();
  assert.equal(h.$('file-translation-retry').hidden,true);
  assert.equal(h.$('file-translation-remove').hidden,true);
  assert.equal(h.$('translate-file-submit').disabled,false);
  assert.equal(h.timers.size,0);
});

test('non-JSON server errors display the HTTP status',async()=>{
  const h=harness(async()=>({ok:false,status:502,statusText:'Bad Gateway',json:async()=>{throw SyntaxError('Unexpected token');}}));
  h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  assert.match(h.$('file-translation-status').textContent,/HTTP 502: Bad Gateway/);
  assert.equal(h.$('translate-file-submit').disabled,false);
});
test('failure hides download and enables manual retry without endless polling',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.srt',size:20}];await h.$('file-translation-form').fire('submit');
  h.setState({...h.initial(),completed:12,error:'Gemini unavailable',running:false});await h.tick();
  assert.equal(h.$('file-translation-retry').hidden,false);assert.equal(h.$('file-download').hidden,true);assert.equal(h.timers.size,0);
  h.setState({...h.initial(),completed:24,error:'',running:false,ready:true,download_url:'/done'});
  await h.$('file-translation-retry').fire('click');
  assert.ok(h.calls.some(([url,method])=>url==='/api/subtitle-files/abc/retry'&&method==='POST'));
  assert.equal(h.$('file-download').hidden,false);
});
test('invalid file never starts translation',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.txt',size:20}];await h.$('file-translation-form').fire('submit');
  assert.equal(h.calls.length,0);assert.match(h.$('file-translation-status').textContent,/SRT\/VTT/);
});

test('cancel stops polling, preserves progress and allows retry',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  assert.equal(h.$('file-translation-cancel').hidden,false);
  h.setState({...h.initial(),completed:12,running:false,phase:'cancelled'});
  await h.$('file-translation-cancel').fire('click');
  assert.ok(h.calls.some(([url,method])=>url==='/api/subtitle-files/abc/cancel'&&method==='POST'));
  assert.equal(h.$('file-translation-progress').value,12);
  assert.equal(h.$('file-translation-cancel').hidden,true);
  assert.equal(h.$('file-translation-retry').hidden,false);
  assert.equal(h.$('translate-file-submit').disabled,false);
  assert.equal(h.timers.size,0);
  h.setState({...h.initial(),running:true,phase:'translating'});
  await h.$('file-translation-retry').fire('click');
  assert.equal(h.$('file-translation-cancel').hidden,false);
});
test('restored cache count is shown immediately before processing missing cues',async()=>{
  const h=harness();h.setState({...h.initial(),completed:12,restored_cues:12,cache_cues:12,compatible_cache_cues:12});
  h.$('translate-file').files=[{name:'test.srt',size:20}];await h.$('file-translation-form').fire('submit');
  assert.equal(h.$('file-translation-progress').value,12);
  assert.match(h.$('file-cache-status').textContent,/12 \/ 24/);
  assert.match(h.$('file-cache-status').textContent,/նախորդ տարբերակի/);
});


test('selecting a file submits the unified upload form automatically',async()=>{
  const h=harness();let submitted=false;
  h.$('file-translation-form').requestSubmit=()=>{submitted=true;};
  h.$('translate-file').files=[{name:'prepared.srt',size:20}];
  await h.$('translate-file').fire('change');
  assert.equal(submitted,true);
});

test('a prepared Armenian upload shows download immediately without polling',async()=>{
  const h=harness();h.setState({...h.initial(),completed:24,running:false,ready:true,phase:'ready',download_url:'/ready'});
  h.$('translate-file').files=[{name:'prepared.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  assert.equal(h.$('file-download').hidden,false);
  assert.equal(h.$('file-download').href,'/ready');
  assert.equal(h.$('translate-file-submit').disabled,false);
  assert.equal(h.timers.size,0);
});


test('completed translation opens confirmation; OK clears progress without deleting history',async()=>{
  const h=harness();h.$('translate-file').files=[{name:'test.srt',size:20}];
  await h.$('file-translation-form').fire('submit');
  assert.equal(h.$('file-complete-dialog').open,undefined);
  h.setState({...h.initial(),completed:24,running:false,ready:true,download_url:'/done'});
  await h.tick();
  assert.equal(h.$('file-complete-dialog').open,true);
  assert.equal(h.$('file-download').href,'/done');
  await h.$('file-complete-ok').fire('click');
  assert.equal(h.$('file-complete-dialog').open,false);
  assert.equal(h.$('file-translation-progress').hidden,true);
  assert.equal(h.$('file-translation-remove').hidden,true);
  assert.equal(h.$('file-download').hidden,true);
  assert.equal(h.$('file-translation-name').textContent,'');
  assert.equal(h.$('file-cache-status').textContent,'');
  assert.equal(h.$('file-translation-status').textContent,'');
  assert.equal(h.$('translate-file-submit').disabled,false);
  assert.equal(h.calls.some(([,method])=>method==='DELETE'),false);
  assert.equal(h.timers.size,0);
});
