fetch('/api/public/config').then(response=>response.json()).then(config=>{
  if(config.contact_email)document.getElementById('privacy-contact').textContent='Գաղտնիության կամ աջակցության հարցերով կապվիր՝ '+config.contact_email+'.';
}).catch(()=>{});
