const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const C=require('../core.js');
const code=fs.readFileSync(path.join(__dirname,'../translation-client.js'),'utf8');
test('content coordinator polls without popup, uses video time, stops on navigation and completion',async()=>{
  const timers=new Map(),calls=[],listeners=new Set(),data={[C.JOB_PREFIX+'abcdefghijk']:{running:true}};
  let sequence=0,running=true,time=53.25;
  const context=vm.createContext({HaySubCore:C,setTimeout:fn=>{timers.set(++sequence,fn);return sequence;},clearTimeout:id=>timers.delete(id),chrome:{storage:{local:{get:async key=>({[key]:data[key]})},onChanged:{addListener:fn=>listeners.add(fn),removeListener:fn=>listeners.delete(fn)}},runtime:{sendMessage:async msg=>{calls.push(msg);return {ok:true,running};}}}});
  vm.runInContext(code,context);const client=context.HaySubTranslationClient;
  async function tick(){const copy=[...timers.values()];timers.clear();for(const fn of copy)await fn();}
  client.activate('abcdefghijk',()=>time);await tick();
  assert.equal(calls[0].position,53.25);assert.equal(timers.size,1);
  time=100;await tick();assert.equal(calls.at(-1).position,100);
  client.activate(null);assert.equal(timers.size,0);
  client.activate('abcdefghijk',()=>time);running=false;await tick();assert.equal(timers.size,0);
  client.dispose();assert.equal(listeners.size,0);
});
