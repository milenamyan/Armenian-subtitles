const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
function harness(){
  const nodes=[],draws=[],revoked=[];
  const context={URL:{createObjectURL:()=> 'blob:source',revokeObjectURL:url=>revoked.push(url)},Image:class{naturalWidth=1200;naturalHeight=800;async decode(){}},document:{body:{append(){}},createElement(tag){
    const node={tag,children:[],listeners:{},value:'',append(...children){this.children.push(...children);},setAttribute(){},addEventListener(event,fn){this.listeners[event]=fn;},showModal(){this.open=true;},close(){this.open=false;this.listeners.close();},remove(){this.removed=true;},getContext(){return {fillRect(){},drawImage(...args){draws.push(args.slice(1));}};},toBlob(fn,type,quality){this.export={type,quality};fn({size:123,type});}};
    nodes.push(node);return node;
  }}};
  vm.runInNewContext(fs.readFileSync('static/poster-editor.js','utf8'),context);return {editor:context.HaySubPosterEditor,nodes,draws,revoked};
}
test('cover editor fits the whole image in a 2:3 frame and zooms only when requested',async()=>{
  const h=harness(),pending=h.editor.edit({});await new Promise(resolve=>setImmediate(resolve));
  const dialog=h.nodes.find(n=>n.tag==='dialog'),canvas=h.nodes.find(n=>n.tag==='canvas'),sliders=h.nodes.filter(n=>n.tag==='input');
  assert.equal(dialog.open,true);assert.deepEqual(h.revoked,['blob:source']);
  assert.equal(canvas.width,640);assert.equal(canvas.height,960);
  const initial=h.draws.at(-1);
  assert.deepEqual(initial.slice(0,4),[0,0,1200,800]);
  assert.ok(initial[4]===0);assert.ok(initial[5]>0);
  assert.equal(initial[6],640);assert.ok(initial[5]+initial[7]<=960);
  sliders[0].value=2;sliders[1].value=1;sliders[2].value=0;sliders[0].listeners.input();
  const zoomed=h.draws.at(-1);
  assert.deepEqual(zoomed.slice(0,5),[0,0,1200,800,-640]);assert.ok(zoomed[5]===0);
  assert.equal(zoomed[6],1280);assert.ok(Math.abs(zoomed[7]-800*640/600)<1e-9);
  h.nodes.find(n=>n.textContent==='Օգտագործել պաստառը').listeners.click();
  assert.equal((await pending).type,'image/jpeg');assert.equal(dialog.removed,true);assert.deepEqual(canvas.export,{type:'image/jpeg',quality:.9});
});
test('portrait, square and landscape sources fit completely at default zoom',()=>{
  const h=harness();
  const exact=h.editor.cropBounds(800,1200,1,.5,.5);
  assert.equal(exact.x,0);assert.equal(exact.y,0);assert.equal(exact.width,800);assert.equal(exact.height,1200);
  const tall=h.editor.cropBounds(600,1200,1,1,1);
  assert.equal(tall.x,-200);assert.equal(tall.y,0);assert.equal(tall.width,800);assert.equal(tall.height,1200);
  for(const [width,height] of [[600,600],[1200,800],[600,1200]]){
    const frame=h.editor.cropBounds(width,height,1,.5,.5);
    assert.ok(frame.x<=0&&frame.y<=0);
    assert.ok(frame.x+frame.width>=width&&frame.y+frame.height>=height);
  }
});
test('cancel discards edits without exporting a cover',async()=>{
  const h=harness(),pending=h.editor.edit({});await new Promise(resolve=>setImmediate(resolve));
  h.nodes.find(n=>n.textContent==='Չեղարկել').listeners.click();assert.equal(await pending,null);
  assert.equal(h.nodes.find(n=>n.tag==='canvas').export,undefined);
});
