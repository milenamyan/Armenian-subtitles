const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const labels={'Rename':'Վերանվանել','Ready with subtitles':'Պատրաստ է՝ ենթագրերով','Without subtitles':'Առանց ենթագրերի','Processing':'Մշակվում է','No saved translations yet':'Դեռ պահված թարգմանություններ չկան'};
function assertLabel(actual,expected){assert.ok(actual===expected||actual===labels[expected],`Expected ${expected}, got ${actual}`);}
function harness(){
  const nodes=new Map(),timers=[],calls=[],events=new Map(),played=[],library=[{id:"sub",title:"Prepared Armenian subtitles"}];let fail=false;
  const data=[{id:'a'.repeat(32),title:'Film one',size:100,state:'ready',can_preview:true,published:false,has_subtitles:false,subtitle_offset:0,uploaded_bytes:100,preview_url:'/preview/one',updated:1}];
  function node(tag,id){return {tag,id,children:[],listeners:new Map(),value:'',files:[],textContent:'',hidden:false,disabled:false,dataset:{},classList:{toggle(){}},
    append(...children){for(const child of children){child.remove();child.parentElement=this;this.children.push(child);}},
    remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(child=>child!==this);this.parentElement=null;},
    replaceChildren(){for(const child of [...this.children])child.remove();},setAttribute(){},addEventListener(name,fn){this.listeners.set(name,fn);},async fire(name){await this.listeners.get(name)?.({preventDefault(){}});},
    reset(){this.didReset=true;$('hosted-title').value='';$('hosted-file').value='';},scrollIntoView(){this.scrolled=true;},focus(){this.focused=true;}};}
  const $=id=>{if(!nodes.has(id))nodes.set(id,node('div',id));return nodes.get(id);};
  vm.runInNewContext(fs.readFileSync('static/media-owner.js','utf8'),{document:{getElementById:$,createElement:tag=>node(tag),hidden:false},window:{addEventListener:(name,fn)=>events.set(name,fn),dispatchEvent:event=>played.push(event),confirm:()=>true},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options?.detail;}},location:{origin:'http://localhost:8000'},FormData,AbortController,HaySubMediaUpload:{},setInterval:fn=>timers.push(fn),fetch:async(path,options)=>{
    calls.push([path,options]);
    if(path.endsWith('/config'))return {ok:true,json:async()=>({configured:true,storage:'local',worker_online:true,max_bytes:100000})};
    if(path==='/api/library')return {ok:true,json:async()=>library.map(item=>({...item}))};
    if(path.endsWith('/subtitles')){
      if(fail)return {ok:false,json:async()=>({detail:'Subtitle could not be attached'})};
      const id=path.split('/')[4];const index=data.findIndex(item=>item.id===id);
      data[index]={...data[index],has_subtitles:true,updated:data[index].updated+1};
      return {ok:true,json:async()=>({...data[index]})};
    }
    if(options.method==='PATCH'){
      if(fail)return {ok:false,json:async()=>({detail:'Title could not be saved'})};
      data[0]={...data[0],...JSON.parse(options.body),updated:2};return {ok:true,json:async()=>({...data[0]})};
    }
    return {ok:true,json:async()=>data.map(item=>({...item}))};
  }});
  return {$,timers,calls,data,library,events,played,fail:()=>fail=true};
}
test('saved posters appear in the header after refreshing media',async()=>{
  const h=harness();await flush();
  const card=h.$('hosted-completed-videos').children[0],poster=card.children[0].children[1].children[2];
  assert.equal(poster.hidden,true);
  h.data[0].poster_url='/api/owner/media/one/poster';h.data[0].updated=2;
  await h.$('hosted-refresh').fire('click');
  assert.equal(poster.hidden,false);assert.equal(poster.src,'/api/owner/media/one/poster?v=2');
  const form=card.children[0].children[1];
  assert.equal(form.children[1].hidden,true);
  assert.equal(form.children[1].dataset.saved,'true');
  assert.equal(form.children[3].textContent,'');
  await h.$('hosted-refresh').fire('click');
  assert.equal(form.children[1].dataset.saved,'true');
});

test('poster controls explain why Save is disabled before selecting an image',async()=>{
  const h=harness();await flush();
  const form=h.$('hosted-completed-videos').children[0].children[0].children[1];
  assert.equal(form.children[1].disabled,true);
  assert.equal(form.children[3].textContent,'Նախ ընտրիր պաստառի նկարը։');
  await form.fire('submit');
  assert.equal(h.calls.some(([path])=>path.endsWith('/poster')),false);
});

test('Add to page inserts the saved video into completed videos immediately and scrolls to it',async()=>{
  const h=harness();await flush();
  const item={...h.data[0],id:'b'.repeat(32),title:'New cloud movie',source_type:'cloud',published:true,has_subtitles:true,share_url:'/watch/new'};
  h.events.get('haysub-media-updated')({detail:{item}});
  const completed=h.$('hosted-completed-videos'),card=completed.children[1];
  assert.equal(completed.children.length,2);
  assert.equal(card.children[0].children[0].children[0].children[0].textContent,'New cloud movie');
  assert.equal(card.scrolled,true);assert.equal(h.$('hosted-empty').hidden,true);
  h.events.get('haysub-media-updated')({detail:{item:{...item,title:'Updated title',updated:2}}});
  assert.equal(completed.children.length,2);
  assert.equal(card.children[0].children[0].children[0].children[0].textContent,'Updated title');
});

test('Rename opens only a title form, saves the title and closes',async()=>{
  const h=harness();await flush();const card=h.$('hosted-completed-videos').children[0],form=card.children[2],actions=card.children[0].children[0].children[2],rename=actions.children[5];
  assert.equal(form.hidden,true);assertLabel(rename.textContent,'Rename');
  assert.deepEqual(form.children.map(child=>child.tag),['input','button','button']);
  await rename.fire('click');assert.equal(form.hidden,false);assert.equal(form.children[0].value,'Film one');
  form.children[0].value='New title';await form.fire('submit');
  assert.equal(card.children[0].children[0].children[0].children[0].textContent,'New title');assert.equal(form.hidden,true);assert.equal(rename.hidden,false);
  assert.equal(actions.children[0].hidden,false);
  assert.equal(h.calls.some(([path])=>path.endsWith('/subtitles')),false);
});

test('cancel and failed rename preserve the video title',async()=>{
  const h=harness();await flush();const card=h.$('hosted-completed-videos').children[0],form=card.children[2],rename=card.children[0].children[0].children[2].children[5];
  await rename.fire('click');form.children[0].value='Discard';await form.children[2].fire('click');
  assert.equal(form.hidden,true);assert.equal(card.children[0].children[0].children[0].children[0].textContent,'Film one');
  await rename.fire('click');assert.equal(form.children[0].value,'Film one');
  h.fail();form.children[0].value='Retry title';await form.fire('submit');
  assert.equal(form.hidden,false);assert.equal(form.children[0].value,'Retry title');assert.equal(card.children[0].children[0].children[0].children[0].textContent,'Film one');
  assert.match(h.$('video-owner-status').textContent,/could not be saved/);
  assert.equal(form.children[1].disabled,false);
});

test('ready videos remain visible while bin and deleting entries are excluded on refresh',async()=>{
  const h=harness();await flush();
  const original=h.$('hosted-completed-videos').children[0];
  for(const [id,state] of [['b','bin'],['c','deleting'],['d','processing']])h.data.push({...h.data[0],id:id.repeat(32),state});
  await h.$('hosted-refresh').fire('click');
  assert.equal(h.$('hosted-completed-videos').children.length,1);
  assert.equal(h.$('hosted-videos').children.length,1);
  h.data[3].state='ready';h.data[3].updated=2;
  await h.$('hosted-refresh').fire('click');
  assert.equal(h.$('hosted-completed-videos').children.length,2);
  assert.equal(h.$('hosted-videos').children.length,0);
  h.data[0].state='bin';h.data[0].updated=3;
  await h.$('hosted-refresh').fire('click');
  assert.equal(original.parentElement,null);
  assert.equal(h.$('hosted-completed-videos').children.length,1);
});


test('missing subtitle status is shown and attaching subtitles hides the status',async()=>{
  const h=harness();await flush();const card=h.$('hosted-completed-videos').children[0],form=card.children[4],select=form.children[0].children[0],attach=form.children[1];
  assertLabel(card.children[0].children[0].children[1].textContent,'Without subtitles');
  assert.equal(form.hidden,false);assert.equal(attach.disabled,true);
  assert.equal(select.children[1].textContent,'Prepared Armenian subtitles');
  select.value='sub';await select.fire('change');assert.equal(attach.disabled,false);
  h.data[0].subtitle_offset=1.5;await h.$('hosted-refresh').fire('click');
  await form.fire('submit');
  const request=h.calls.find(([path])=>path.endsWith('/subtitles'));
  assert.equal(request[1].method,'POST');assert.equal(request[1].body.get('library_id'),'sub');assert.equal(request[1].body.get('offset'),'1.5');
  assert.equal(card.children[0].children[0].children[1].textContent,'');assert.equal(card.children[0].children[0].children[1].hidden,true);
  assert.equal(card.children[0].children[0].children[2].children[1].hidden,false,'Publish is available after subtitles are attached');
  assert.equal(form.hidden,true,'The subtitle picker disappears once a track is attached');assert.equal(select.value,'');
  await h.$('hosted-refresh').fire('click');assert.equal(card.children[0].children[0].children[1].textContent,'');assert.equal(card.children[0].children[0].children[1].hidden,true);
});

test('failed attachment preserves the selection and does not claim the video has subtitles',async()=>{
  const h=harness();await flush();h.fail();
  const card=h.$('hosted-completed-videos').children[0],form=card.children[4],select=form.children[0].children[0],attach=form.children[1];
  select.value='sub';await select.fire('change');await form.fire('submit');
  assertLabel(card.children[0].children[0].children[1].textContent,'Without subtitles');assert.equal(select.value,'sub');
  assert.equal(attach.disabled,false);assert.equal(select.disabled,false);
  assert.match(h.$('video-owner-status').textContent,/Subtitle could not be attached/);
});

test('translation library updates refresh the choices while preserving a valid selection',async()=>{
  const h=harness();await flush();const card=h.$('hosted-completed-videos').children[0],form=card.children[4],select=form.children[0].children[0];
  select.value='sub';h.library[0].title='Renamed translation';h.library.push({id:'new',title:'New completed translation'});
  await h.events.get('haysub-library-updated')();
  assert.equal(select.value,'sub');assert.equal(select.children[1].textContent,'Renamed translation');assert.equal(select.children[2].value,'new');
  h.library.splice(0);await h.events.get('haysub-library-updated')();
  assert.equal(select.value,'');assert.equal(select.disabled,true);assert.equal(form.children[1].disabled,true);
  assertLabel(select.children[0].textContent,'No saved translations yet');
});

test('processing videos keep their actual status until ready and cannot attach subtitles yet',async()=>{
  const h=harness();await flush();h.data[0].state='processing';h.data[0].has_subtitles=true;h.data[0].updated=2;
  await h.$('hosted-refresh').fire('click');const card=h.$('hosted-videos').children[0];
  assertLabel(card.children[0].children[0].children[1].textContent,'Processing');assert.equal(card.children[4].hidden,true);
  h.data[0].state='ready';h.data[0].updated=3;await h.$('hosted-refresh').fire('click');
  assert.equal(card.children[0].children[0].children[1].textContent,'');assert.equal(card.children[0].children[0].children[1].hidden,true);assert.equal(card.children[4].hidden,true);
});


test('videos that already have subtitles hide the picker and do not attach another track',async()=>{
  const h=harness();await flush();h.data[0].has_subtitles=true;h.data[0].updated=2;
  await h.$('hosted-refresh').fire('click');
  const card=h.$('hosted-completed-videos').children[0],form=card.children[4],select=form.children[0].children[0];
  assert.equal(card.children[0].children[0].children[1].textContent,'');assert.equal(card.children[0].children[0].children[1].hidden,true);assert.equal(form.hidden,true);
  select.value='sub';await form.fire('submit');
  assert.equal(h.calls.some(([path])=>path.endsWith('/subtitles')),false);
  await h.events.get('haysub-library-updated')();assert.equal(form.hidden,true);
});


test('ready video names are clickable and link to their player',async()=>{
  const h=harness();await flush();const heading=h.$('hosted-completed-videos').children[0].children[0].children[0].children[0];
  const link=heading.children[0];assert.equal(link.tag,'a');assert.equal(link.href,'/preview/one');assert.notEqual(link.target,'_blank');
  await link.fire('click');assert.equal(h.played[0].type,'haysub-play-video');assert.equal(h.played[0].detail.id,'a'.repeat(32));assert.equal(h.played[0].detail.owner,true);
  h.data[0].published=true;h.data[0].share_url='/watch/example';h.data[0].updated=2;
  await h.$('hosted-refresh').fire('click');assert.equal(link.href,'/watch/example');
  assert.equal(h.$('hosted-completed-videos').children[0].children[3].hidden,true,'The standalone URL is hidden');
});


test('Private preview opens the existing inline player instead of a new page',async()=>{
  const h=harness();await flush();const card=h.$('hosted-completed-videos').children[0],preview=card.children[0].children[0].children[2].children[0];
  assert.notEqual(preview.target,'_blank');assert.equal(preview.href,'/preview/one');
  await preview.fire('click');
  assert.equal(h.played.length,1);assert.equal(h.played[0].type,'haysub-play-video');
  assert.equal(h.played[0].detail.id,'a'.repeat(32));assert.equal(h.played[0].detail.owner,true);assert.equal(h.played[0].detail.anchor,card.children[0].children[0].children[0]);
});
