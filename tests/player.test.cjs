const assert=require('node:assert/strict');
const {activeCues,subtitleState}=require('../static/player.js');
const cues=[{id:1,start:1,end:3},{id:2,start:3,end:5}];
assert.deepEqual(activeCues(cues,0),[]);
assert.deepEqual(activeCues(cues,3).map(c=>c.id),[2]);
assert.deepEqual(activeCues(cues,5),[]);
assert.deepEqual(activeCues(cues,4,1).map(c=>c.id),[2]);
// Seek forward to an untranslated cue, then backward to a translated cue.
assert.equal(subtitleState(cues,{'1':'Բարև'},4).waiting,true);
assert.equal(subtitleState(cues,{'1':'Բարև'},2).waiting,false);
assert.deepEqual(subtitleState(cues,{'1':'Բարև'},8).active,[]);
console.log('Playback boundaries, offsets and seeking checks passed.');
