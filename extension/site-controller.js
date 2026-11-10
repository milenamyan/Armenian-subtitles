/* Top-frame route cleanup for an activated video in a cross-origin frame.
   This timer checks only the URL. Subtitle time still comes from the video. */
(() => {
  globalThis.__haySubSiteController?.dispose();
  let previous=location.href;
  function check(){if(location.href!==previous){previous=location.href;chrome.runtime.sendMessage({type:'HAYSUB_SITE_NAVIGATED',url:previous}).catch(()=>{});}}
  window.addEventListener('popstate',check);window.addEventListener('hashchange',check);
  window.navigation?.addEventListener('currententrychange',check);
  const timer=setInterval(check,500);
  globalThis.__haySubSiteController={dispose(){clearInterval(timer);window.removeEventListener('popstate',check);window.removeEventListener('hashchange',check);window.navigation?.removeEventListener('currententrychange',check);}};
})();
