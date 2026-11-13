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

test('duration metadata loads without playing, shares requests, caches and releases media on success or failure',async()=>{
  const {progress:p,context}=progressHarness(),videos=[];let timeout;
  context.setTimeout=fn=>{timeout=fn;return 1;};context.clearTimeout=()=>{};
  context.document={createElement(tag){
    assert.equal(tag,'video');const events=new Map(),video={duration:6278,loads:0,
      addEventListener:(name,fn)=>events.set(name,fn),removeEventListener:name=>events.delete(name),
      removeAttribute(name){delete this[name];},load(){this.loads++;},fire:name=>events.get(name)()};
    videos.push(video);return video;
  }};
  const result=p.loadDuration('new','https://cdn.test/new.mp4');
  assert.equal(p.loadDuration('new','https://cdn.test/new.mp4'),result);
  assert.equal(videos[0].preload,'metadata');assert.equal(videos[0].muted,true);
  videos[0].fire('loadedmetadata');assert.equal(await result,6278);
  assert.equal(videos[0].src,undefined);assert.equal(videos[0].loads,2);
  assert.equal(await p.loadDuration('new','https://cdn.test/new.mp4'),6278);assert.equal(videos.length,1);
  const failed=p.loadDuration('bad','https://cdn.test/bad.mp4');videos[1].fire('error');assert.equal(await failed,null);
  const slow=p.loadDuration('slow','https://cdn.test/slow.mp4');timeout();assert.equal(await slow,null);
  assert.equal(videos[2].src,undefined);assert.equal(p.read('new'),null);
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

test('returning to the catalog reloads the owner New flag and removes its badge when unchecked',async()=>{
  const {progress}=progressHarness(),nodes=new Map(),events=new Map();let isNew=false,scrolls=0;
  const element=()=>({children:[],style:{},append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;},addEventListener(){},setAttribute(){}});
  const $=id=>{if(!nodes.has(id))nodes.set(id,element());return nodes.get(id);};
  vm.runInNewContext(fs.readFileSync('static/public-catalog.js','utf8'),{
    HaySubProgress:progress,document:{getElementById:$,createElement:element},sessionStorage:{getItem:()=>null},
    window:{addEventListener:(name,fn)=>events.set(name,fn),scrollTo:()=>scrolls++},requestAnimationFrame:fn=>fn(),
    fetch:async()=>({ok:true,json:async()=>[{id:'a',title:'Film',duration:900,is_new:isNew}]})
  });
  const flush=()=>new Promise(resolve=>setImmediate(resolve));await flush();
  const badges=()=>$('public-videos').children[0].children[0].children.filter(item=>item.className==='movie-new-badge');
  assert.equal(badges().length,0);
  isNew=true;events.get('focus')();await flush();assert.equal(badges().length,1);assert.equal(badges()[0].textContent,'ՆՈՐ');
  isNew=false;events.get('pageshow')({persisted:true});await flush();assert.equal(badges().length,0);
  assert.equal(scrolls,1);
});
