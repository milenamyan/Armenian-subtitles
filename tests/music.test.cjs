const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const web=require('../static/player.js');
const extension=require('../extension/core.js');
const cases=JSON.parse(fs.readFileSync('tests/music-cases.json','utf8'));
test('web and extension agree on music-only labels without hiding dialogue or lyrics',()=>{
  for(const api of [web,extension])for(const c of cases)assert.equal(api.isMusicOnly(c.text),c.silent,c.text);
});
test('cached music is hidden during overlap and does not cause a waiting state',()=>{
  const cues=[{id:1,start:0,end:5,source:'[music]'},{id:2,start:2,end:3,source:'Hello'}];
  assert.deepEqual(web.subtitleState(cues,{},1),{active:[],waiting:false});
  assert.deepEqual(web.activeCues(cues,2).map(c=>c.id),[2]);
  const timeline=extension.timeline(cues.map(c=>({...c,text:c.id===1?'Երաժշտություն':'Hello'})));
  assert.deepEqual(timeline.at(1),[]);assert.equal(timeline.at(2)[0].text,'Hello');
  assert.equal(extension.withoutMusicLines('[music]\nHello'),'Hello');
});
