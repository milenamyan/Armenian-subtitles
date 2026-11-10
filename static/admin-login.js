(() => {
  const form=document.getElementById('owner-login'),note=document.getElementById('login-status');
  form.addEventListener('submit',async event=>{
    event.preventDefault();const button=form.querySelector('button');button.disabled=true;
    try{
      const response=await fetch('/api/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:document.getElementById('owner-token').value})});
      if(!response.ok){const body=await response.json();throw Error(body.detail||'Մուտքը չհաջողվեց։');}
      document.getElementById('owner-token').value='';location.replace('/admin');
    }catch(error){note.textContent=error.message;}
    finally{button.disabled=false;}
  });
})();
