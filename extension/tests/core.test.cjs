const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const C=require('../core.js');

test('SRT supports BOM, CRLF, Armenian/English multiline text and empty cues',()=>{
  const sample=fs.readFileSync(path.join(__dirname,'../sample.srt'),'utf8');
  const parsed=C.parse('\ufeff'+sample.replace(/\n/g,'\r\n'));
  assert.equal(parsed.cues.length,4);assert.equal(parsed.ignored,1);
  assert.match(parsed.cues[0].text,/Բարև.*\nHello/s);
  assert.equal(parsed.cues[0].start,1);assert.equal(parsed.cues[0].end,5);
});
test('VTT metadata, identifiers, cue settings, inline tags and entities',()=>{
  const {cues}=C.parse('WEBVTT\nKind: captions\nLanguage: en\n\nNOTE author note\nignore\n\nSTYLE\n::cue {color:red}\n\nintro\n00:01.000 --> 00:03.500 align:start position:20%\n<v speaker><b>Hello</b> &amp; &#x0532;\nsecond line');
  assert.equal(cues.length,1);assert.equal(cues[0].text,'Hello & Բ\nsecond line');assert.equal(cues[0].end,3.5);
});
test('formatting removal never creates interpreted HTML',()=>{
  const text=C.plainText('<img src=x onerror=alert(1)>Hello &lt;script&gt;alert(1)&lt;/script&gt;');
  assert.equal(text,'Hello <script>alert(1)</script>');
  assert.equal(C.plainText('&#x110000;'), '\ufffd');
});
test('empty and zero-length cues ignored; broken/all-empty files rejected in Armenian',()=>{
  const parsed=C.parse('1\n00:00:00,000 --> 00:00:01,000\n\n2\n00:00:02,000 --> 00:00:02,000\nHi\n\n3\n00:00:03,000 --> 00:00:04,000\nԲարև');
  assert.equal(parsed.ignored,2);assert.equal(parsed.cues.length,1);
  for(const raw of ['', 'garbage','1\n00:00:00,000 --> 00:00:01,000\n','1\n00:00:02,000 --> 00:00:01,000\nHi','1\n00:70:00,000 --> 00:71:00,000\nHi','x'.repeat(C.MAX_FILE_BYTES+1)])assert.throws(()=>C.parse(raw),/[\u0531-\u0587]/);
});
test('overlaps, unsorted cues, boundaries and seeks retain every active cue',()=>{
  const cues=C.parse('later\n00:00:03,000 --> 00:00:05,000\nB\n\nlong\n00:00:01,000 --> 00:00:10,000\nA\n\nshort\n00:00:02,000 --> 00:00:03,000\nC').cues;
  const t=C.timeline(cues),texts=time=>t.at(time).map(c=>c.text);
  assert.deepEqual(texts(0),[]);assert.deepEqual(texts(2),['A','C']);assert.deepEqual(texts(3),['A','B']);
  assert.deepEqual(texts(9),['A']);assert.deepEqual(texts(10),[]);
  assert.deepEqual(texts(2.5),['A','C']); // backward seek
});
test('positive offsets delay and negative offsets advance, no extrapolated clock',()=>{
  const t=C.timeline([{id:1,start:5,end:7,text:'Hi'}]);
  assert.equal(t.at(5,2).length,0);assert.equal(t.at(7,2).length,1);assert.equal(t.at(9,2).length,0);
  assert.equal(t.at(3,-2).length,1);assert.equal(t.at(5,-2).length,0);
  assert.equal(t.at(NaN).length,0);
});
test('prefix timeline matches full scanning even with deeply overlapping cues',()=>{
  const cues=Array.from({length:200},(_,i)=>({id:i,start:i/4,end:i/4+(i%13)+0.5,text:String(i)}));
  const timeline=C.timeline(cues);
  for(let time=0;time<70;time+=0.3)assert.deepEqual(timeline.at(time,1.25).map(c=>c.id),cues.filter(c=>c.start<=time-1.25&&time-1.25<c.end).map(c=>c.id));
});
test('picture geometry excludes letterboxing and stays inside player',()=>{
  const parent={left:10,top:20,width:1000,height:800};
  assert.deepEqual(C.pictureRect({...parent},parent,1920,1080),{left:0,top:118.75,width:1000,height:562.5});
  assert.deepEqual(C.pictureRect({left:0,top:0,width:1920,height:1080},{left:0,top:0,width:1920,height:1080},1920,1080),{left:0,top:0,width:1920,height:1080});
  assert.equal(C.pictureRect({left:0,top:0,width:0,height:0},parent,0,0).width,0);
});
test('scoped YouTube IDs, setting bounds and local key cleanup',()=>{
  assert.equal(C.videoId('https://www.youtube.com/watch?v=abcdefghijk&list=x'),'abcdefghijk');
  assert.equal(C.videoId('https://www.youtube.com/shorts/abcdefghijk'),'abcdefghijk');
  assert.equal(C.videoId('https://youtube.com.evil.test/watch?v=abcdefghijk'),null);
  assert.equal(C.videoId('https://www.youtube.com/'),null);
  assert.equal(C.settings({textColor:'red;display:none',fontSize:900}).textColor,'#ffffff');
  assert.equal(C.settings({fontSize:900}).fontSize,64);assert.equal(C.offset(-999),-120);
  assert.deepEqual(C.savedKeys({'other':1,[C.FILE_PREFIX+'x']:1,[C.OFFSET_PREFIX+'x']:1,[C.SETTINGS_KEY]:1}),[C.FILE_PREFIX+'x',C.OFFSET_PREFIX+'x']);
  assert.ok(C.recordBytes('key',{text:'Հայերեն'})>10);
});
test('manifest permissions and scripts are self-contained',()=>{
  const dir=path.join(__dirname,'..'),m=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json'),'utf8'));
  assert.equal(m.manifest_version,3);assert.deepEqual(m.permissions,['storage','activeTab','scripting']);
  assert.deepEqual(m.optional_permissions,['webNavigation']);
  assert.deepEqual(m.optional_host_permissions,['https://*/*','http://*/*']);
  assert.deepEqual(m.host_permissions,['http://127.0.0.1/*']);
  assert.equal(m.background.service_worker,'background.js');assert.ok(!m.externally_connectable);
  assert.match(m.content_security_policy.extension_pages,/connect-src http:\/\/127\.0\.0\.1:8000/);
  for(const match of m.content_scripts[0].matches)assert.match(match,/^https:\/\/(www\.|m\.)?youtube\.com\/\*$/);
  for(const file of [...m.content_scripts[0].js,m.action.default_popup,'popup.js','popup.css'])assert.ok(fs.existsSync(path.join(dir,file)),file);
  for(const file of ['core.js','content.js','popup.js'])assert.doesNotMatch(fs.readFileSync(path.join(dir,file),'utf8'),/\b(?:fetch|XMLHttpRequest|eval)\s*\(/);
});
test('generic page identities separate domains, routes, frames and selected videos',async()=>{
  const base='https://example.test/movie/one';
  const key=await C.pageKey(base);assert.match(key,/^page:[a-f0-9]{64}$/);
  assert.equal(key,await C.pageKey(base));
  for(const args of [['https://other.test/movie/one'],[base+'#two'],[base,'https://player.test/embed/one'],[base,base,1]])assert.notEqual(key,await C.pageKey(...args));
  await assert.rejects(C.pageKey('chrome://extensions'),/[\u0531-\u0587]/);
});
