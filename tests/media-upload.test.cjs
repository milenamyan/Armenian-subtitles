const {test}=require('node:test'),assert=require('node:assert/strict');
globalThis.crypto=require('node:crypto').webcrypto;
const U=require('../static/media-upload.js');
function file(){const data=new Blob(['abcdefghij']);data.name='original.mp4';data.lastModified=123;return data;}
async function harness(parts=[]){
  const selected=file(),session={id:'a'.repeat(32),size:10,part_size:4,part_count:3,state:'uploading',fingerprint:await U.fingerprint(selected),parts},calls=[],sent=[];
  const api=async(path,options)=>{calls.push([path,options]);if(path.endsWith('/resume'))return session;if(path.endsWith('/part-url'))return {url:'https://storage.test/part/'+options.body.number};if(path.endsWith('/complete'))return {...session,state:'finalizing'};return {ok:true};};
  const sendPart=async(url,blob,signal,progress)=>{sent.push([url,await blob.text()]);progress(blob.size);return '"etag"';};
  return {selected,session,calls,sent,api,sendPart};
}
test('resuming skips acknowledged parts and sends only bounded Blob slices directly to storage',async()=>{
  const h=await harness([{number:1,etag:'"one"'}]),progress=[];
  const result=await U.upload(h.selected,h.session,{api:h.api,sendPart:h.sendPart,onProgress:(sent,total)=>progress.push([sent,total])});
  assert.equal(result.state,'finalizing');assert.deepEqual(h.sent.map(v=>v[1]),['efgh','ij']);
  assert.deepEqual(progress[0],[4,10]);assert.deepEqual(progress.at(-1),[10,10]);
  assert.ok(h.calls.every(([,options])=>!options?.body||!(options.body instanceof Blob)),'Control requests never contain video bytes');
});
test('wrong file fingerprint is rejected before requesting a part URL',async()=>{
  const h=await harness();h.selected.name='different.mp4';
  await assert.rejects(U.upload(h.selected,h.session,{api:h.api,sendPart:h.sendPart}),/Սա սկզբնական ընտրված ֆայլը չէ/);
  assert.equal(h.calls.length,0);
});
test('pause aborts before another upload and does not complete an unfinished file',async()=>{
  const h=await harness(),controller=new AbortController();
  await assert.rejects(U.upload(h.selected,h.session,{api:h.api,signal:controller.signal,sendPart:async(...args)=>{const etag=await h.sendPart(...args);controller.abort();return etag;}}),{name:'AbortError'});
  assert.equal(h.sent.length,1);assert.equal(h.calls.some(([path])=>path.endsWith('/complete')),false);
});
test('network failure leaves acknowledged work available for the next resume',async()=>{
  const h=await harness();
  await assert.rejects(U.upload(h.selected,h.session,{api:h.api,sendPart:async()=>{throw Error('network');}}),/network/);
  assert.equal(h.calls.some(([path])=>path.endsWith('/complete')),false);
});
