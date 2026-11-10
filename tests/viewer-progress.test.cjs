const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function progressHarness(){
  const data=new Map(),storage={getItem:key=>data.get(key)||null,setItem:(key,value)=>data.set(key,value),removeItem:key=>data.delete(key)};
  const context={localStorage:storage};vm.runInNewContext(fs.readFileSync('static/playback-progress.js','utf8'),context);
  return {progress:context.HaySubProgress,data,context};
}
test('two stable movie IDs retain separate positions; zero and invalid values cannot overwrite progress',()=>{
  const {progress:p}=progressHarness();p.save('a',120,900);p.save('b',240,1200);
  p.save('a',0,900);p.save('a',NaN,900);p.save('a',20,Infinity);
  assert.equal(p.read('a').position,120);assert.equal(p.read('b').position,240);
  p.clear('a');assert.equal(p.read('a'),null);assert.equal(p.read('b').position,240);
});
test('completion and out-of-range positions clear resume, invalid persisted data is ignored',()=>{
  const {progress:p,data}=progressHarness();p.save('a',100,900);p.save('a',870,900);assert.equal(p.read('a'),null);
  p.save('a',1000,900);assert.equal(p.read('a'),null);
  for(const entry of ['bad','null','{}','{"position":-2,"duration":900,"updated":1}','{"position":9000,"duration":900,"updated":1}']){
    data.set('haysub:progress:v1:a',entry);assert.equal(p.read('a'),null);
  }
  p.save('a',400,900);assert.equal(p.read('a',420),null,'changed duration makes the saved point completed');
  p.rememberDuration('a',900);p.clear('a');assert.equal(p.duration('a'),900);
});
test('blocked browser storage never prevents playback helpers',()=>{
  const {progress:p,context}=progressHarness();context.localStorage={getItem(){throw Error();},setItem(){throw Error();},removeItem(){throw Error();}};
  assert.doesNotThrow(()=>{p.save('a',50,900);p.clear('a');p.rememberDuration('a',900);});assert.equal(p.read('a'),null);assert.equal(p.duration('a'),null);
});
test('catalog uses safe same-tab cards, publication order and refreshes on return',async()=>{
  const {progress:p,data}=progressHarness();p.save('a',90,900);p.save('b',120,1200);
  for(const [id,updated] of [['a',100],['b',200]]){const key='haysub:progress:v1:'+id,entry=JSON.parse(data.get(key));entry.updated=updated;data.set(key,JSON.stringify(entry));}
  const nodes=new Map(),events=new Map(),session=new Map();let scroll;
  const node=tag=>({tag,children:[],listeners:new Map(),style:{},value:'',append(...c){this.children.push(...c);},replaceChildren(...c){this.children=c;},setAttribute(k,v){this[k]=v;},addEventListener(k,v){this.listeners.set(k,v);}});
  const $=id=>{if(!nodes.has(id))nodes.set(id,node('div'));return nodes.get(id);};
  vm.runInNewContext(fs.readFileSync('static/public-catalog.js','utf8'),{
    HaySubProgress:p,document:{getElementById:$,createElement:node},sessionStorage:{getItem:k=>session.get(k),setItem:(k,v)=>session.set(k,v)},
    window:{scrollY:321,scrollTo:(x,y)=>scroll=y,addEventListener:(k,v)=>events.set(k,v)},requestAnimationFrame:fn=>fn(),
    fetch:async()=>({ok:true,json:async()=>[{id:'a',title:'ԱՐԵՎ <script>',duration:900,published_at:1},{id:'b',title:'Բարև',duration:1200,published_at:2}]})
  });
  await new Promise(resolve=>setImmediate(resolve));
  let cards=$('public-videos').children;assert.equal(cards[0].href,'/watch/b');assert.equal(cards[1].href,'/watch/a');assert.equal(cards[1].children[1].textContent,'ԱՐԵՎ <script>');assert.equal(cards[1].target,undefined);
  assert.equal(nodes.has('continue-videos'),false);
  assert.equal(nodes.has('continue-section'),false);
  assert.equal(cards[1].children[0].children[2].children[0].style.width,'10%');
  assert.equal(nodes.has('public-query'),false);assert.equal(nodes.has('public-search'),false);
  $('public-videos').children[0].listeners.get('click')();assert.equal(JSON.parse(session.values().next().value).scroll,321);
  p.clear('a');events.get('pageshow')();assert.equal($('public-videos').children[1].children[0].children.length,2);
  assert.equal(scroll,0);
});

test('fresh catalog restores scroll and shows all movies despite a previously stored search',async()=>{
  const {progress}=progressHarness(),nodes=new Map();let restoredScroll;
  const node=()=>({value:'',children:[],style:{},append(...c){this.children.push(...c);},replaceChildren(...c){this.children=c;},addEventListener(){},setAttribute(){}});
  const $=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
  vm.runInNewContext(fs.readFileSync('static/public-catalog.js','utf8'),{
    HaySubProgress:progress,document:{getElementById:$,createElement:node},
    sessionStorage:{getItem:()=>JSON.stringify({query:'Հայ',scroll:410})},
    window:{addEventListener(){},scrollTo:(x,y)=>restoredScroll=y},requestAnimationFrame:fn=>fn(),
    fetch:async()=>({ok:true,json:async()=>[{id:'a',title:'Հայաստան',duration:900},{id:'b',title:'Other',duration:900}]})
  });
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(nodes.has('public-query'),false);assert.equal($('public-videos').children.length,2);assert.equal(restoredScroll,410);
});
