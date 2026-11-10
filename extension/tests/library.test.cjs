const {test}=require('node:test');
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const C=require('../core.js');
const ID='a'.repeat(32),VIDEO='abcdefghijk',BASE='https://haysub.onrender.com';
const SRT='1\n00:00:01,000 --> 00:00:03,000\nԲարև աշխարհ';
function harness(){
  const data={[C.FILE_PREFIX+VIDEO]:{text:'previous'},[C.JOB_PREFIX+VIDEO]:{running:true}},calls=[];
  let listener,offline=false,quota=false,missing=false,body=SRT;
  const local={get:async key=>({[key]:data[key]}),set:async value=>Object.assign(data,value),remove:async key=>delete data[key],getBytesInUse:async keys=>quota&&keys===null?C.SAVE_BUDGET+1:0};
  vm.runInNewContext(fs.readFileSync('extension/library-background.js','utf8'),{
    HaySubCore:C,HaySubRelease:{apiBase:BASE,publicMode:true},AbortSignal,TextDecoder,Uint8Array,
    chrome:{runtime:{id:'ext',onMessage:{addListener:fn=>listener=fn}},storage:{local}},
    fetch:async(url,options)=>{
      calls.push({url,options});if(offline)throw Error('offline');
      if(url.includes('/download'))return {ok:!missing,status:missing?404:200,text:async()=>body};
      return {ok:true,json:async()=>[{id:ID,title:'<script>Film</script>',cue_count:1}]};
    }
  });
  const send=message=>new Promise(resolve=>listener(message,{id:'ext'},resolve));
  return {send,data,calls,offline:()=>offline=true,quota:()=>quota=true,missing:()=>missing=true,body:text=>body=text,listener:()=>listener};
}
test('catalog only sends a bounded search phrase, never browsing URLs or playback position',async()=>{
  const h=harness(),result=await h.send({type:'HAYSUB_LIBRARY_LIST',query:'Film & episode',position:123,url:'https://private.test/film'});
  assert.equal(result.ok,true);assert.equal(result.items[0].title,'<script>Film</script>');
  assert.equal(h.calls[0].url,BASE+'/api/public/library?q=Film%20%26%20episode&offset=0');
  assert.equal(h.calls[0].options.credentials,'omit');assert.equal(h.calls[0].options.referrerPolicy,'no-referrer');
  assert.equal(h.calls[0].options.body,undefined);
});
test('ready Armenian library file becomes a local per-video association without a translation job',async()=>{
  const h=harness(),response=await h.send({type:'HAYSUB_LIBRARY_USE',videoId:VIDEO,identity:ID,title:'My film'});
  assert.equal(response.ok,true);assert.equal(response.cueCount,1);
  assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,SRT);assert.equal(h.data[C.FILE_PREFIX+VIDEO].language,'hy');
  assert.equal(h.data[C.FILE_PREFIX+VIDEO].libraryId,ID);assert.equal(h.data[C.JOB_PREFIX+VIDEO],undefined);
  assert.equal(h.calls.length,1);assert.equal(h.calls[0].url,BASE+'/api/public/library/'+ID+'/download');
});
for(const mode of ['offline','quota','missing'])test(mode+' failure preserves the previous subtitle file',async()=>{
  const h=harness();h[mode]();
  const result=await h.send({type:'HAYSUB_LIBRARY_USE',videoId:VIDEO,identity:ID,title:'Film'});
  assert.equal(result.ok,false);assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,'previous');
});
test('invalid identity and video IDs cannot create arbitrary network paths',async()=>{
  const h=harness();
  assert.equal((await h.send({type:'HAYSUB_LIBRARY_USE',videoId:VIDEO,identity:'../../admin'})).ok,false);
  assert.equal((await h.send({type:'HAYSUB_LIBRARY_USE',videoId:'https://private.test',identity:ID})).ok,false);
  assert.equal(h.calls.length,0);
  assert.equal(h.listener()({type:'HAYSUB_LIBRARY_LIST'},{id:'untrusted'},()=>assert.fail()),undefined);
});
test('oversized and malformed subtitle downloads are rejected',async()=>{
  const h=harness();h.body('x'.repeat(C.MAX_FILE_BYTES+1));
  assert.equal((await h.send({type:'HAYSUB_LIBRARY_USE',videoId:VIDEO,identity:ID})).ok,false);
  h.body('not an SRT');
  assert.equal((await h.send({type:'HAYSUB_LIBRARY_USE',videoId:VIDEO,identity:ID})).ok,false);
  assert.equal(h.data[C.FILE_PREFIX+VIDEO].text,'previous');
});
