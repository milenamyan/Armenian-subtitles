const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const C=require('../core.js');
const source=fs.readFileSync(path.join(__dirname,'../page-access.js'),'utf8');
test('frame discovery prioritizes allowed video frames and never probes unapproved hosts',async()=>{
  const probed=[];
  const context=vm.createContext({HaySubCore:C,URL,chrome:{permissions:{contains:async request=>request.permissions?.includes('webNavigation')||request.origins?.[0]==='https://player.test/*'},webNavigation:{getAllFrames:async()=>[
    {frameId:0,url:'https://movies.test/film'},
    {frameId:2,url:'https://ads.test/embed'},
    {frameId:9,url:'https://player.test/film'}
  ]},scripting:{executeScript:async args=>{probed.push(args.target.frameIds[0]);return [{result:{players:[{playing:true}]}}];}}}});
  vm.runInContext(source,context);
  const result=await context.HaySubPageAccess.discover({id:7});
  assert.equal(result[0].frameId,9);
  assert.deepEqual(probed,[9]);
});

test('frame discovery does not enumerate frames before optional permission is granted',async()=>{
  const context=vm.createContext({HaySubCore:C,URL,chrome:{permissions:{contains:async()=>false},webNavigation:{getAllFrames:async()=>assert.fail('No permission')}}});
  vm.runInContext(source,context);
  assert.equal((await context.HaySubPageAccess.discover({id:7})).length,0);
});
test('click activation injects only the selected frame and keeps page key stable',async()=>{
  const scripts=[],messages=[];let config;
  const tab={id:8,url:'https://movies.test/watch/one'};
  const context=vm.createContext({HaySubCore:C,URL,chrome:{runtime:{sendMessage:async msg=>{messages.push(msg);return {ok:true};}},tabs:{sendMessage:async()=>config?{videoId:config.key,site:true,hasVideo:true}:{videoId:null}},scripting:{executeScript:async args=>{
    scripts.push(args);
    if(args.func&&args.args){config=args.args[0];return [];}
    if(args.func)return [{result:{url:'https://player.test/embed/one',players:[{index:0,width:100,height:100,playing:false},{index:1,width:960,height:540,playing:true}]}}];
    return [];
  }}}});
  vm.runInContext(source,context);
  const result=await context.HaySubPageAccess.activate(tab,{frameId:9,frameUrl:'https://player.test/embed/one'});
  assert.equal(result.frameId,9);assert.equal(result.videoIndex,1);assert.match(result.status.videoId,/^page:/);
  assert.ok(scripts.some(s=>s.files?.includes('content.js')&&s.target.frameIds[0]===9));
  assert.ok(scripts.every(s=>!s.target.allFrames),'Never inject indiscriminately into all advertisement frames');
  assert.equal(messages.at(-1).type,'HAYSUB_SITE_REGISTER');
});
test('restricted Chrome pages are rejected before script injection',async()=>{
  const context=vm.createContext({HaySubCore:C,URL,chrome:{runtime:{sendMessage:async()=>({})},scripting:{executeScript:()=>assert.fail('Must not inject')}}});
  vm.runInContext(source,context);
  await assert.rejects(context.HaySubPageAccess.connect({id:1,url:'chrome://extensions'}),/[\u0531-\u0587]/);
});
test('site session coordinator removes an old iframe overlay on top-page navigation',async()=>{
  let listener;const saved={},sent=[];
  const session={get:async key=>({[key]:saved[key]}),set:async obj=>Object.assign(saved,obj),remove:async key=>delete saved[key]};
  const context=vm.createContext({chrome:{runtime:{id:'ext',onMessage:{addListener:fn=>listener=fn}},storage:{session},tabs:{sendMessage:async(...args)=>sent.push(args)}}});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../site-background.js'),'utf8'),context);
  const send=(msg,sender={id:'ext'})=>new Promise(resolve=>listener(msg,sender,resolve));
  await send({type:'HAYSUB_SITE_REGISTER',tabId:7,context:{topUrl:'https://movies.test/one',frameId:9,frameUrl:'https://player.test/one',key:'page:'+'a'.repeat(64)}});
  await send({type:'HAYSUB_SITE_NAVIGATED',url:'https://movies.test/two'},{id:'ext',frameId:0,tab:{id:7}});
  assert.equal(sent[0][0],7);assert.equal(sent[0][1].type,'HAYSUB_DEACTIVATE');assert.equal(sent[0][2].frameId,9);
  assert.equal(Object.keys(saved).length,0);
});
