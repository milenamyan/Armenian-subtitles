// Exercise real UI state logic with a small DOM stand-in; no YouTube/Gemini calls.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const elements=new Map(), intervals=new Map();
function element(){return {value:'',textContent:'',hidden:false,style:{},children:[],classList:{toggle(){}},append(...nodes){this.children.push(...nodes);},replaceChildren(){this.children=[];},before(node){elements.set(node.id,node);},scrollIntoView(){},click(){this.clicked=true;}};}
const get=id=>{if(!elements.has(id))elements.set(id,element());return elements.get(id);};
get('mode').value='hy';get('offset').value='0';
let responseJob;
const context=vm.createContext({
  window:{},document:{getElementById:get,createElement:element},
  SubtitleTiming:require('../static/player.js'),
  setInterval:(fn,ms)=>{if(!intervals.has(ms))intervals.set(ms,fn);},
  fetch:async path=>({ok:true,json:async()=>path==='/api/config'?{configured:true}:path==='/api/videos'?[]:responseJob})
});
vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
const run=code=>vm.runInContext(code,context);
(async()=>{
  await new Promise(resolve=>setImmediate(resolve));
  run("let plays=0; player={playVideo(){plays++;},getCurrentTime(){return 2;}}; playerReady=true; identity='test'; configured=true; job={phase:'retrieving',cues:[],translated:{}}; maybeStart();");
  assert.equal(run('plays'),0,'Do not start before retrieval completes');
  run('sync(); transcript();');
  assert.match(get('subtitle').textContent,/Փնտրվում/);
  assert.equal(get('transcript').children.length,0);

  responseJob={phase:'translating',cues:[{id:1,start:1,end:3,source:'Hello'}],translated:{},running:true,error:''};
  await intervals.get(1000)();
  assert.equal(run('plays'),0,'Wait for the initial translated window');
  assert.equal(get('transcript').children.length,1,'Refresh transcript when retrieved cues arrive');
  assert.match(get('subtitle').textContent,/դեռ պատրաստ չեն/);

  responseJob={...responseJob,phase:'ready',translated:{'1':'Բարև'},running:false};
  await intervals.get(1000)();
  assert.equal(run('plays'),1);
  assert.equal(get('subtitle').textContent,'Բարև');

  responseJob={phase:'error',cues:[],translated:{},running:false,error:'Missing captions. Upload .srt'};
  await intervals.get(1000)();
  assert.equal(get('upload-fallback').hidden,false);
  assert.equal(get('notice').textContent,responseJob.error);
  get('upload-fallback').onclick();assert.equal(get('file').clicked,true);

  responseJob={phase:'retrieving',cues:[],translated:{},running:true,error:''};
  await intervals.get(1000)();
  assert.equal(get('upload-fallback').hidden,true);
  assert.match(get('progress').textContent,/Փնտրվում/);

  responseJob={phase:'translating',caption_source:'uploaded',cues:[{id:1,start:1,end:3,source:'Uploaded subtitle'}],translated:{},running:true,error:''};
  run("started=false; $('mode').value='hy'; renderKey='';");
  await intervals.get(1000)();
  assert.match(get('subtitle').textContent,/դեռ պատրաստ չեն/);
  assert.equal(get('retry').hidden,false);
  assert.equal(run('plays'),1,'Uploaded English subtitles wait for Armenian translation');
  responseJob={...responseJob,phase:'ready',running:false,translated:{'1':'Բարև'}};
  await intervals.get(1000)();
  assert.equal(get('subtitle').textContent,'Բարև');
  assert.equal(run('plays'),2);
  get('mode').value='both';run('sync();');
  assert.equal(get('original').textContent,'Uploaded subtitle');
  console.log('Caption retrieval, initial playback gating, transcript refresh and upload fallback checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
