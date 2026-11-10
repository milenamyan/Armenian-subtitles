(() => {
  const form=document.getElementById('library-import'),file=document.getElementById('library-import-file'),note=document.getElementById('library-import-status');
  form.addEventListener('submit',async event=>{
    event.preventDefault();const selected=file.files[0];if(!selected)return;
    const button=form.querySelector('button');button.disabled=true;
    try{
      const body=new FormData();body.append('subtitles',selected);
      const response=await fetch('/api/library/import',{method:'POST',body});
      const result=await response.json();if(!response.ok)throw Error(result.detail||'Ներմուծումը չհաջողվեց։');
      note.textContent='Պահպանված է որպես մասնավոր։ Անհրաժեշտության դեպքում վերանվանիր, ապա գրադարանում սեղմիր «Հրապարակել դիտողների համար»։';
      file.value='';window.dispatchEvent(new CustomEvent('haysub-library-updated'));
    }catch(error){note.textContent=error.message;}
    finally{button.disabled=false;}
  });
})();
