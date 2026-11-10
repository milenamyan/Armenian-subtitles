/* Frame selection is tab-local and session-only. No site data goes to the backend. */
(() => {
  const key=tabId=>'haysub:site-context:'+tabId;
  async function get(tabId){return (await chrome.storage.session.get(key(tabId)))[key(tabId)];}
  async function deactivate(tabId,frameId){try{await chrome.tabs.sendMessage(tabId,{type:'HAYSUB_DEACTIVATE'},{frameId});}catch{}}
  chrome.runtime.onMessage.addListener((msg,sender,reply)=>{
    if(sender.id!==chrome.runtime.id||!['HAYSUB_SITE_REGISTER','HAYSUB_SITE_CONTEXT','HAYSUB_SITE_NAVIGATED'].includes(msg?.type))return;
    (async()=>{
      if(msg.type==='HAYSUB_SITE_NAVIGATED'){
        if(!sender.tab||sender.frameId!==0)return {ok:false};
        const old=await get(sender.tab.id);
        if(old&&old.topUrl!==msg.url){await deactivate(sender.tab.id,old.frameId);await chrome.storage.session.remove(key(sender.tab.id));}
        return {ok:true};
      }
      if(!Number.isInteger(msg.tabId))return {ok:false};
      if(msg.type==='HAYSUB_SITE_CONTEXT')return {context:await get(msg.tabId)};
      const c=msg.context;
      if(!c||!/^page:[a-f0-9]{64}$/.test(c.key)||!Number.isInteger(c.frameId)||!/^https?:\/\//.test(c.topUrl))return {ok:false};
      const old=await get(msg.tabId);
      if(old&&(old.frameId!==c.frameId||old.key!==c.key))await deactivate(msg.tabId,old.frameId);
      await chrome.storage.session.set({[key(msg.tabId)]:c});return {ok:true};
    })().then(reply).catch(()=>reply({ok:false,error:'Չհաջողվեց ակտիվացնել էջը։'}));
    return true;
  });
  chrome.tabs.onRemoved?.addListener(tabId=>{void chrome.storage.session.remove(key(tabId));});
})();
