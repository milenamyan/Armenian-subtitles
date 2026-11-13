(() => {
  'use strict';
  const $=id=>document.getElementById(id),deviceNames={desktop:'Համակարգիչ',phone:'Հեռախոս',tablet:'Պլանշետ'};
  const dates=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Yerevan',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
  let request=0;
  function duration(seconds){
    const n=Math.round(seconds),h=Math.floor(n/3600),m=Math.floor(n%3600/60),s=n%60;
    return h?`${h} ժ ${m} ր`:m?`${m} ր ${s} վ`:`${s} վ`;
  }
  function element(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
  async function load(){
    const token=++request;$('analytics-status').textContent='Բեռնվում է…';$('analytics-status').className='hint';
    try{
      const response=await fetch('/api/owner/analytics?days='+encodeURIComponent($('analytics-period').value),{cache:'no-store'});
      if(!response.ok)throw Error(response.status===404?'Այս բաժինը հասանելի է միայն տեղային HaySub-ում։':'Չհաջողվեց բեռնել այցելությունները։');
      const data=await response.json();if(token!==request)return;
      $('metric-visits').textContent=data.summary.visits;
      $('metric-time').textContent=duration(data.summary.active_seconds);
      $('metric-average').textContent=duration(data.summary.average_seconds);
      $('metric-recent').textContent=data.summary.recent_visits;
      $('analytics-devices').replaceChildren(...Object.entries(deviceNames).map(([type,name])=>{
        const card=element('div',undefined,'analytics-device');card.append(element('span',name),element('strong',data.devices.find(item=>item.device===type)?.visits||0));return card;
      }));
      const rows=data.visits.map(visit=>{
        const row=element('tr');
        for(const value of [deviceNames[visit.device]||'Այլ',visit.browser+' / '+visit.platform,dates.format(new Date(visit.started*1000)),dates.format(new Date(visit.last_seen*1000)),duration(visit.active_seconds)])row.append(element('td',value));
        return row;
      });
      if(!rows.length){const row=element('tr'),cell=element('td','Դեռ այցելություններ չկան։ Բացիր տեղային կատալոգը՝ առաջին այցելությունը գրանցելու համար։','analytics-empty');cell.colSpan=5;row.append(cell);rows.push(row);}
      $('analytics-visits').replaceChildren(...rows);
      $('analytics-status').textContent='Թարմացվել է՝ '+dates.format(new Date());
    }catch(error){if(token===request){$('analytics-status').textContent=error.message;$('analytics-status').className='hint error';}}
  }
  $('analytics-refresh').addEventListener('click',load);$('analytics-period').addEventListener('change',load);
  setInterval(()=>{if(!document.hidden)void load();},30000);
  void load();
})();
