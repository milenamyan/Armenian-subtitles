/* Popup-only activation. Access starts with activeTab; embedded hosts are optional. */
(() => {
  const C=globalThis.HaySubCore;
  const isYouTube=url=>{try{return ['youtube.com','www.youtube.com','m.youtube.com'].includes(new URL(url).hostname);}catch{return false;}};
  const validUrl=value=>{let u;try{u=new URL(value);}catch{throw Error('Բացիր տեսանյութի կայքը և սեղմիր HaySub-ը։');}if(!['http:','https:'].includes(u.protocol))throw Error('Chrome-ի ներքին կամ սահմանափակ էջում HaySub-ը չի աշխատում։ Բացիր տեսանյութի կայքը։');return u;};
  async function register(tab,frameId,frameUrl,videoIndex,key){
    await chrome.runtime.sendMessage({type:'HAYSUB_SITE_REGISTER',tabId:tab.id,context:{topUrl:tab.url,frameId,frameUrl,videoIndex,key}});
  }
  async function activate(tab,{frameId=0,frameUrl=tab.url,videoIndex=null}={}){
    validUrl(tab.url);validUrl(frameUrl);
    if(frameId===0&&isYouTube(tab.url)){
      try{return {frameId:0,site:false,status:await chrome.tabs.sendMessage(tab.id,{type:'HAYSUB_STATUS'},{frameId:0})};}
      catch{await chrome.scripting.executeScript({target:{tabId:tab.id,frameIds:[0]},files:['core.js','translation-client.js','content.js']});
        return {frameId:0,site:false,status:await chrome.tabs.sendMessage(tab.id,{type:'HAYSUB_STATUS'},{frameId:0})};}
    }
    const target={tabId:tab.id,frameIds:[frameId]};
    const scan=await chrome.scripting.executeScript({target,func:()=>({url:location.href,players:Array.from(document.querySelectorAll('video')).map((v,index)=>{const r=v.getBoundingClientRect();return {index,width:Math.round(r.width),height:Math.round(r.height),playing:!v.paused&&!v.ended};})})});
    const found=scan[0]?.result;
    if(!found)throw Error('Չհաջողվեց կարդալ նվագարկիչը։ Կայքը կարող է սահմանափակել հավելման հասանելիությունը։');
    frameUrl=found.url;validUrl(frameUrl);
    if(videoIndex===null)videoIndex=[...found.players].sort((a,b)=>Number(b.playing)-Number(a.playing)||(b.width*b.height-a.width*a.height))[0]?.index||0;
    const key=await C.pageKey(tab.url,frameUrl,videoIndex);
    // Do not re-inject an already-active instance or lose its media-change guard.
    try{
      const existing=await chrome.tabs.sendMessage(tab.id,{type:'HAYSUB_STATUS'},{frameId});
      if(existing.site&&existing.videoId===key){await register(tab,frameId,frameUrl,videoIndex,key);return {site:true,frameId,frameUrl,status:existing,players:found.players,videoIndex};}
    }catch{}
    await chrome.scripting.executeScript({target,func:config=>{globalThis.HaySubSiteConfig=config;},args:[{key,topUrl:tab.url,frameUrl,videoIndex}]});
    await chrome.scripting.executeScript({target,files:['core.js','translation-client.js','content.js']});
    await chrome.scripting.executeScript({target:{tabId:tab.id,frameIds:[0]},files:['site-controller.js']});
    await register(tab,frameId,frameUrl,videoIndex,key);
    return {site:true,frameId,frameUrl,players:found.players,videoIndex,status:await chrome.tabs.sendMessage(tab.id,{type:'HAYSUB_STATUS'},{frameId})};
  }
  async function connect(tab){
    validUrl(tab.url);
    const saved=await chrome.runtime.sendMessage({type:'HAYSUB_SITE_CONTEXT',tabId:tab.id});
    if(saved?.context?.topUrl===tab.url){try{const active=await activate(tab,saved.context);if(active.status?.hasVideo)return active;}catch{}}
    const main=await activate(tab);
    if(main.status?.hasVideo||!main.site)return main;
    // Previously allowed embedded players can reconnect without another prompt.
    const frames=await discover(tab);
    const player=frames.find(f=>f.frameId!==0&&f.players?.length);
    return player?activate(tab,{frameId:player.frameId,frameUrl:player.url}):main;
  }
  async function discover(tab){
    if(!await chrome.permissions.contains({permissions:['webNavigation']}))return [];
    const frames=(await chrome.webNavigation.getAllFrames({tabId:tab.id})||[]).filter(f=>/^https?:\/\//.test(f.url));
    for(const f of frames){
      if(f.frameId===0)continue;
      // Probe only hosts already granted by the user, never request every iframe.
      if(!await chrome.permissions.contains({origins:[new URL(f.url).origin+'/*']}))continue;
      try{
        const result=await chrome.scripting.executeScript({target:{tabId:tab.id,frameIds:[f.frameId]},func:()=>({players:Array.from(document.querySelectorAll('video')).map(v=>({playing:!v.paused&&!v.ended}))})});
        f.players=result[0]?.result?.players||[];
      }catch{f.players=[];}
    }
    return frames.sort((a,b)=>Number(!!b.players?.length)-Number(!!a.players?.length)||Number(a.frameId===0)-Number(b.frameId===0));
  }
  globalThis.HaySubPageAccess={activate,connect,discover};
})();
