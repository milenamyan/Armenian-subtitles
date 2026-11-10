const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function harness(confirmed=true){
  const nodes=new Map(),events=new Map(),calls=[];
  let data=[{id:'one',title:'<script>Film</script>',source_filename:'original.srt',cue_count:1,created:'2026-11-08'}],failure=false;
  function element(tag){return {tag,children:[],value:'',textContent:'',listeners:new Map(),classList:{toggle(){},add(){}},append(...children){this.children.push(...children);},replaceChildren(){this.children=[];},attributes:{},setAttribute(name,value){this.attributes[name]=value;},show(){this.open=true;},showModal(){this.open=true;},close(){this.open=false;this.listeners.get('close')?.();},focus(){},addEventListener(name,fn){this.listeners.set(name,fn);},async fire(name){await this.listeners.get(name)?.({preventDefault(){}});}};}
  const $=id=>{if(!nodes.has(id))nodes.set(id,element('div'));return nodes.get(id);};
  vm.runInNewContext(fs.readFileSync('static/translation-library.js','utf8'),{document:{getElementById:$,createElement:element},window:{confirm:()=>confirmed,addEventListener:(name,fn)=>events.set(name,fn)},fetch:async(url,options)=>{
    calls.push([url,options]);
    if(options?.method==='DELETE'){
      if(failure)return {ok:false,json:async()=>({detail:'Storage unavailable'})};
      data=[];return {ok:true,json:async()=>({deleted:true})};
    }
    if(options?.method==='PATCH'){
      if(failure)return {ok:false,json:async()=>({detail:'Storage unavailable'})};
      if(url.endsWith('/publication')){data[0].published=JSON.parse(options.body).published;return {ok:true,json:async()=>({id:data[0].id,published:data[0].published})};}
      data[0].title=JSON.parse(options.body).title;
      return {ok:true,json:async()=>({...data[0]})};
    }
    return {ok:true,json:async()=>data.map(item=>({...item}))};
  }});
  return {$,events,calls,fail:()=>failure=true};
}
test('library renders literal titles, searches original filenames, and refreshes after translation',async()=>{
  const h=harness();await flush();
  const card=h.$('saved-translations').children[0];
  assert.equal(card.children[0].children[0].textContent,'<script>Film</script>');
  assert.equal(card.children[1].children[0].href,'/api/library/one/download');
  h.$('library-search').value='missing';await h.$('library-search').fire('input');
  assert.equal(h.$('saved-translations').children[0].tag,'p');
  h.$('library-search').value='ORIGINAL';await h.$('library-search').fire('input');
  assert.equal(h.$('saved-translations').children[0].tag,'article');
  await h.events.get('haysub-library-updated')();assert.equal(h.calls.length,2);
});
test('rename sends metadata, updates title, and remains after refresh',async()=>{
  const h=harness();await flush();
  const card=h.$('saved-translations').children[0],form=card.children[2];
  await card.children[1].children[1].fire('click');assert.equal(form.hidden,false);
  form.children[0].children[0].value=' Armenian film ';
  await form.fire('submit');assert.equal(form.hidden,true);
  assert.equal(card.children[0].children[0].textContent,'Armenian film');
  assert.equal(h.calls[1][1].method,'PATCH');
  await h.events.get('haysub-library-updated')();await flush();
  assert.equal(h.$('saved-translations').children[0].children[0].children[0].textContent,'Armenian film');
});
test('failed rename keeps original title and offers correction',async()=>{
  const h=harness();await flush();h.fail();
  const card=h.$('saved-translations').children[0],form=card.children[2];
  await card.children[1].children[1].fire('click');form.children[0].children[0].value='New';
  await form.fire('submit');assert.equal(form.hidden,false);
  assert.equal(form.children[3].textContent,'Storage unavailable');
  assert.equal(card.children[0].children[0].textContent,'<script>Film</script>');
  assert.equal(form.children[1].disabled,false);
});

test('subtitle history offers download, rename and delete',async()=>{
  const h=harness();await flush();
  const actions=h.$('saved-translations').children[0].children[1];
  assert.equal(actions.children.length,3);
  assert.equal(actions.children[0].tag,'a');
  assert.ok(actions.children.every(action=>!action.textContent.includes('??????????')));
});

test('confirmed deletion removes the item and stays removed after refresh',async()=>{
  const h=harness();await flush();
  await h.$('saved-translations').children[0].children[1].children[2].fire('click');
  assert.equal(h.calls.length,1);
  const panel=h.$('saved-translations').children[0].children[3];
  assert.equal(panel.hidden,false);
  assert.equal(panel.tag,'dialog');
  assert.equal(panel.open,true);
  await panel.children[2].children[1].fire('click');
  assert.equal(h.calls[1][1].method,'DELETE');
  assert.equal(h.$('saved-translations').children[0].tag,'p');
  await h.events.get('haysub-library-updated')();await flush();
  assert.equal(h.$('saved-translations').children[0].tag,'p');
});

test('cancelled deletion sends no request; failed deletion keeps item and allows retry',async()=>{
  const cancelled=harness(false);await flush();
  await cancelled.$('saved-translations').children[0].children[1].children[2].fire('click');
  const cancelledPanel=cancelled.$('saved-translations').children[0].children[3];
  await cancelledPanel.children[2].children[0].fire('click');
  assert.equal(cancelledPanel.hidden,true);
  assert.equal(cancelledPanel.open,false);
  assert.equal(cancelled.calls.length,1);
  const h=harness();await flush();h.fail();
  const remove=h.$('saved-translations').children[0].children[1].children[2];
  await remove.fire('click');
  const panel=h.$('saved-translations').children[0].children[3];
  await panel.children[2].children[1].fire('click');
  assert.equal(h.$('saved-translations').children[0].tag,'article');
  assert.equal(panel.children[3].textContent,'Storage unavailable');
  assert.equal(panel.children[2].children[1].disabled,false);
});


test('history arrow opens downward and toggles closed with accessible state',async()=>{
  const h=harness();await flush();
  const toggle=h.$('library-open'),history=h.$('translation-library');
  await toggle.fire('click');
  assert.equal(history.open,true);
  assert.equal(toggle.attributes['aria-expanded'],'true');
  await toggle.fire('click');
  assert.equal(history.open,false);
  assert.equal(toggle.attributes['aria-expanded'],'false');
  await toggle.fire('click');
  await toggle.fire('click');
  assert.equal(history.open,false);
  assert.equal(toggle.attributes['aria-expanded'],'false');
});
