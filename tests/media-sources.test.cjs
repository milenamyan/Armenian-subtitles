const {test}=require('node:test');
const assert=require('node:assert/strict');
const {srtToVtt}=require('../static/media-sources.js');

test('cloud SRT keeps cue timing, Unicode and line breaks while escaping markup',()=>{
  const vtt=srtToVtt('\ufeff1\r\n00:00:01,250 --> 00:00:03,500\r\n\u0532\u0561\u0580\u0587 <script> &\r\nSecond line');
  assert.equal(vtt,'WEBVTT\n\n1\n00:00:01.250 --> 00:00:03.500\n\u0532\u0561\u0580\u0587 &lt;script&gt; &amp;\nSecond line\n');
});

test('subtitle offsets clamp the start and drop cues entirely before playback',()=>{
  const srt='1\n00:00:01,000 --> 00:00:02,000\nFirst\n\n2\n00:00:02,000 --> 00:00:04,000\nSecond';
  const vtt=srtToVtt(srt,-2);
  assert.doesNotMatch(vtt,/First/);assert.match(vtt,/00:00:00.000 --> 00:00:02.000\nSecond/);
});

test('existing WebVTT is retained and invalid timestamps cannot become an active track',()=>{
  assert.equal(srtToVtt('WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello'),'WEBVTT\n\n00:00:01.000 --> 00:00:03.000\nHello\n');
  assert.throws(()=>srtToVtt('invalid captions'),/Invalid cloud/);
});
