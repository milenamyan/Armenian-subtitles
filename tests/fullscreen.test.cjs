const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');

function harness({native=true,reject=false,buttonExists=true}={}){
  const nodes=new Map(),events={},requests=[];
  function node(){return {children:[],textContent:'',style:{},attributes:{},classes:new Set(),listeners:{},
    classList:{toggle(name,active){if(active)this.owner.classes.add(name);else this.owner.classes.delete(name);}},
    append(child){if(child.parentElement)child.parentElement.children=child.parentElement.children.filter(n=>n!==child);this.children.push(child);child.parentElement=this;},
    before(child){this.parentElement.append(child);},setAttribute(name,value){this.attributes[name]=value;},
    addEventListener(name,fn){this.listeners[name]=fn;}};}
  const get=id=>{if(!nodes.has(id)){const n=node();n.classList.owner=n;nodes.set(id,n);}return nodes.get(id);};
  const body=get('body');body.style.overflow='auto';
  const video=get('hosted-player');body.append(video);video.currentTime=42;
  const cues=[{text:'Հայերեն'}];video.textTracks=[{mode:'showing',cues}];
  video.controlsList={add:value=>requests.push(value)};
  const height=get('height');body.append(height);height.append(get('watch-subtitle-up'));
  body.append(get('watch-controls'));
  if(buttonExists){get('watch-controls').append(get('fullscreen'));get('fullscreen').textContent='Fullscreen';}
  const document={body,getElementById:id=>nodes.get(id),createElement(){const n=node();n.classList.owner=n;
    if(native)n.requestFullscreen=async()=>{requests.push(n);if(reject)throw Error('unsupported');document.fullscreenElement=n;events.fullscreenchange();};return n;},
    addEventListener:(name,fn)=>{events[name]=fn;},async exitFullscreen(){document.fullscreenElement=null;events.fullscreenchange();}};
  vm.runInNewContext(fs.readFileSync('static/fullscreen.js','utf8'),{document,window:{addEventListener:(name,fn)=>{events[name]=fn;}}});
  return {get,document,events,requests,video,surface:video.parentElement,frame:video.parentElement.parentElement,button:video.parentElement.children.find(child=>child.className==='player-fullscreen-toggle'),cues};
}

test('fullscreen expands the same video, controls and subtitles and restores page scrolling on exit',async()=>{
  const h=harness();await h.button.listeners.click();
  assert.equal(h.document.fullscreenElement,h.frame);
  assert.equal(h.get('watch-controls').parentElement,h.frame);
  assert.equal(h.get('height').parentElement,h.frame);
  assert.equal(h.button.parentElement,h.surface);
  assert.equal(h.button.className,'player-fullscreen-toggle');
  assert.match(h.button.innerHTML,/<svg/);
  assert.equal(h.button.attributes['aria-label'],'Փակել լիաէկրանը');
  assert.equal(h.video.currentTime,42);assert.equal(h.video.textTracks[0].cues,h.cues);
  assert.equal(h.video.textTracks[0].mode,'showing');
  assert.equal(h.button.attributes['aria-pressed'],'true');assert.equal(h.document.body.style.overflow,'hidden');
  await h.button.listeners.click();
  assert.equal(h.button.textContent,'');assert.equal(h.button.attributes['aria-label'],'Լիաէկրան');assert.equal(h.document.body.style.overflow,'auto');
  assert.equal(h.frame.classes.has('player-expanded'),false);
});

for(const options of [{native:false},{reject:true}])test('mobile fallback preserves page UI when element fullscreen is unavailable '+JSON.stringify(options),async()=>{
  const h=harness(options);await h.button.listeners.click();
  assert.equal(h.frame.classes.has('player-expanded'),true);
  assert.equal(h.requests[0],'nofullscreen');
  h.events.keydown({key:'Escape'});
  assert.equal(h.frame.classes.has('player-expanded'),false);
  assert.equal(h.document.body.style.overflow,'auto');
});

test('browser exit and closing an inline player clear expanded state',async()=>{
  const h=harness();await h.button.listeners.click();await h.document.exitFullscreen();
  assert.equal(h.button.attributes['aria-pressed'],'false');
  await h.button.listeners.click();await h.events['haysub-close-video']();
  assert.equal(h.frame.classes.has('player-expanded'),false);
});

test('player creates its icon over the video when supplemental buttons are absent',async()=>{
  const h=harness({buttonExists:false});
  assert.equal(h.button.parentElement,h.surface);assert.equal(h.get('watch-controls').children.length,0);
  assert.equal(h.button.attributes['aria-label'],'Լիաէկրան');assert.match(h.button.innerHTML,/<svg/);
  await h.button.listeners.click();assert.equal(h.document.fullscreenElement,h.frame);
});
