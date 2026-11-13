const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let ids=0;
function harness({storage=new Map(),clock={ms:0},pathname='/catalog',dnt=false}={}){
  const sent=[],events=new Map(),timers=[],document={hidden:false,addEventListener:(name,fn)=>events.set(name,fn)};
  vm.runInNewContext(fs.readFileSync('static/visit-tracker.js','utf8'),{
    location:{pathname},navigator:{doNotTrack:dnt?'1':'0'},document,
    window:{addEventListener:(name,fn)=>events.set(name,fn)},performance:{now:()=>clock.ms},Date:{now:()=>1000000+clock.ms},
    crypto:{randomUUID:()=>String(++ids).padStart(32,'0')},sessionStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
    Blob,setInterval:fn=>timers.push(fn),fetch:async(url,options)=>{sent.push({url,...JSON.parse(options.body)});}
  });
  return {sent,events,timers,document,storage,clock};
}
test('visible time survives catalog-to-player navigation without counting hidden time',()=>{
  const h=harness();assert.equal(h.sent[0].active_seconds,0);const id=h.sent[0].id;
  h.clock.ms=15000;h.timers[0]();assert.equal(h.sent.at(-1).active_seconds,15);
  h.clock.ms=20000;h.document.hidden=true;h.events.get('visibilitychange')();assert.equal(h.sent.at(-1).active_seconds,20);
  h.clock.ms=80000;h.timers[0]();assert.equal(h.sent.length,3);
  h.document.hidden=false;h.events.get('visibilitychange')();assert.equal(h.sent.at(-1).active_seconds,20);
  h.clock.ms=95000;h.events.get('pagehide')();assert.equal(h.sent.at(-1).active_seconds,35);
  const player=harness({storage:h.storage,clock:h.clock,pathname:'/watch/'+'a'.repeat(32)});
  assert.equal(player.sent[0].id,id);assert.equal(player.sent[0].active_seconds,35);
  h.clock.ms+=15000;player.timers[0]();assert.equal(player.sent.at(-1).active_seconds,50);
});
test('a long hidden pause creates a new visit and restores cached pages without counting absence',()=>{
  const h=harness(),id=h.sent[0].id;h.clock.ms=10000;h.events.get('pagehide')();
  h.clock.ms+=31*60*1000;h.events.get('pageshow')({persisted:true});
  assert.notEqual(h.sent.at(-1).id,id);assert.equal(h.sent.at(-1).active_seconds,0);
});
test('admin and preview pages and Do Not Track browsers are excluded',()=>{
  for(const pathname of ['/admin','/admin/analytics','/preview/'+'a'.repeat(32)])assert.equal(harness({pathname}).sent.length,0);
  assert.equal(harness({dnt:true}).sent.length,0);
});
test('a sleeping visible browser does not add the full sleep interval',()=>{
  const h=harness();h.clock.ms=3600000;h.timers[0]();assert.equal(h.sent.at(-1).active_seconds,30);
});
