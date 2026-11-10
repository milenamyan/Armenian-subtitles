const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const elements=new Map();
function node(){return {value:'',textContent:'',hidden:false,style:{},classList:{toggle(){}},append(){},replaceChildren(){},before(n){elements.set(n.id,n);}};}
const get=id=>{if(!elements.has(id))elements.set(id,node());return elements.get(id);};
get('mode').value='hy';get('offset').value='0';
let options,created=0,destroyed=0,loads=[];
const context=vm.createContext({window:{},location:{origin:'http://127.0.0.1:8000'},document:{getElementById:get,createElement:node,querySelector:()=>node()},
  SubtitleTiming:require('../static/player.js'),setInterval(){},
  fetch:async path=>({ok:true,json:async()=>path==='/api/config'?{configured:true}:[]}),
  YT:{Player:function(id,config){created++;options=config;return {getCurrentTime:()=>90,getPlayerState:()=>3,getVideoLoadedFraction:()=>0.05,destroy(){destroyed++;},playVideo(){},loadVideoById(args){loads.push(args);}};}}
});
vm.runInContext(fs.readFileSync('static/app.js','utf8'),context);
const run=code=>vm.runInContext(code,context);
(async()=>{
  await new Promise(resolve=>setImmediate(resolve));
  run("apiReady=true; job={video:'abcdefghijk',phase:'ready',cues:[{id:1,start:0,end:200,source:'Hello'}],translated:{'1':'Բարև'}}; identity='job'; mountPlayer();");
  options.events.onReady();
  assert.equal(created,1);
  run('mountPlayer();');
  assert.equal(created,1,'Changing subtitles for the same video must reuse the iframe');
  assert.equal(destroyed,0);
  run('bufferingSince=Date.now()-16000; updatePlaybackStatus();');
  assert.match(get('playback-status').textContent,/buffering.*16s/);
  assert.equal(get('reload-player').hidden,false);
  get('reload-player').onclick();
  assert.equal(created,2);assert.equal(destroyed,1);
  options.events.onReady();
  assert.equal(loads.length,1);
  assert.equal(loads[0].startSeconds,90,'Recovery must preserve the playback timestamp');
  options.events.onStateChange({data:1});
  assert.equal(run('bufferingSince'),null);
  options.events.onError({data:153});
  assert.match(get('playback-status').textContent,/153/);
  run('job={...job,error:"Translation failed"};');
  assert.match(get('playback-status').textContent,/153/,'Playback errors are separate from translation errors');
  console.log('Iframe reuse, buffering status, timestamp-preserving reload and player error checks passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
