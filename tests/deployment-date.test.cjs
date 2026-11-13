const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('deployment label uses the build timestamp in Yerevan time, not the visit date',async()=>{
  const label={hidden:true},requests=[];
  vm.runInNewContext(fs.readFileSync('catalog-site/deployment-date.js','utf8'),{
    document:{getElementById:()=>label},Intl,Date,
    fetch:async(url,options)=>{requests.push([url,options.cache]);return {ok:true,json:async()=>({updated_at:'2026-11-14T22:30:00Z'})};}
  });await flush();
  assert.equal(label.hidden,false);assert.match(label.textContent,/15\/11\/2026.*02:30/);
  assert.equal(label.dateTime,'2026-11-14T22:30:00.000Z');assert.deepEqual(requests,[['deployment.json','no-store']]);
});
test('an unavailable deployment timestamp stays hidden',async()=>{
  const label={hidden:true};
  vm.runInNewContext(fs.readFileSync('catalog-site/deployment-date.js','utf8'),{
    document:{getElementById:()=>label},fetch:async()=>({ok:false})
  });await flush();assert.equal(label.hidden,true);
});
