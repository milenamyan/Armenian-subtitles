(() => {
  'use strict';
  const label=document.getElementById('deployment-date');
  if(!label)return;
  (async()=>{
    try{
      const response=await fetch('deployment.json',{cache:'no-store'});
      if(!response.ok)return;
      const metadata=await response.json(),date=new Date(metadata.updated_at);
      if(!Number.isFinite(date.getTime()))return;
      const formatted=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Yerevan',day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(date);
      label.textContent='Թարմացումը՝ '+formatted;
      label.dateTime=date.toISOString();label.hidden=false;
    }catch{}
  })();
})();
