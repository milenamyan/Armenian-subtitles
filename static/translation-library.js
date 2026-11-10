/* Completed translation artifacts live in SQLite. Names are metadata, not paths. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id),list=$('saved-translations');
  const history=$('translation-library');
  $('library-open').addEventListener('click',()=>{
    if(history.open){history.close();return;}
    history.show();
    $('library-open').setAttribute('aria-expanded','true');
    $('library-search').focus();
    void load();
  });
  history.addEventListener('close',()=>{
    $('library-open').setAttribute('aria-expanded','false');
    $('library-open').focus();
  });
  history.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();history.close();}
  });
  history.addEventListener('click',event=>{
    if(event.target!==history)return;
    const bounds=history.getBoundingClientRect();
    if(event.clientX<bounds.left||event.clientX>bounds.right||event.clientY<bounds.top||event.clientY>bounds.bottom)history.close();
  });
  let items=[],loading=false,reloadPending=false;
  function note(text,error=false){$('library-status').textContent=text;$('library-status').classList.toggle('error',error);}
  async function request(url,options){
    const response=await fetch(url,options);
    if(!response.ok){const data=await response.json();throw Error(typeof data.detail==='string'?data.detail:'Չհաջողվեց պահպանել անունը։');}
    return response.json();
  }
  function node(tag,className,text){const el=document.createElement(tag);if(className)el.className=className;if(text!==undefined)el.textContent=text;return el;}
  function draw(){
    const query=$('library-search').value.trim().toLocaleLowerCase();
    const visible=items.filter(item=>(item.title+' '+item.source_filename).toLocaleLowerCase().includes(query));
    list.replaceChildren();
    if(!visible.length){list.append(node('p','hint',items.length?'Այդ անունով թարգմանություն չի գտնվել։':'Դեռ պահված թարգմանություններ չկան։ Ֆայլը թարգմանվելուց հետո այն ինքնաբերաբար կհայտնվի այստեղ։'));return;}
    for(const item of visible){
      const card=node('article','saved-translation');
      const body=node('div','saved-translation-body'),title=node('h3','',item.title);
      body.append(title,node('p','hint',`${item.source_filename} · ${item.cue_count} հատված`),node('p','hint',`Պահված է՝ ${item.created} UTC`));
      const actions=node('div','saved-translation-actions');
      const download=node('a','secondary','Ներբեռնել հայերեն SRT');
      download.href='/api/library/'+encodeURIComponent(item.id)+'/download';download.setAttribute('download','');
      const rename=node('button','secondary','Վերանվանել');rename.type='button';
      const form=node('form','library-rename');form.hidden=true;
      const label=node('label','','Նոր անուն'),input=node('input');input.type='text';input.required=true;input.maxLength=200;input.value=item.title;
      label.append(input);
      const save=node('button','secondary','Պահպանել');save.type='submit';
      const cancel=node('button','secondary','Չեղարկել');cancel.type='button';
      const error=node('p','notice');error.setAttribute('role','status');
      form.append(label,save,cancel,error);
      rename.addEventListener('click',()=>{input.value=item.title;error.textContent='';form.hidden=false;rename.hidden=true;input.focus();});
      cancel.addEventListener('click',()=>{form.hidden=true;rename.hidden=false;});
      form.addEventListener('submit',async event=>{
        event.preventDefault();const value=input.value.trim();
        if(!value){error.textContent='Գրիր նոր անունը։';return;}
        save.disabled=true;cancel.disabled=true;error.textContent='Պահպանվում է…';
        try{
          const updated=await request('/api/library/'+encodeURIComponent(item.id),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:value})});
          Object.assign(item,updated);title.textContent=item.title;form.hidden=true;rename.hidden=false;
          note('Նոր անունը պահպանված է։ Ներբեռնվող ֆայլը նույնպես կունենա այդ անունը։');
        }catch(exc){error.textContent=exc.message;error.classList.add('error');}
        finally{save.disabled=false;cancel.disabled=false;}
      });
      const remove=node('button','secondary library-delete','Ջնջել');remove.type='button';
      const confirmation=node('dialog','library-delete-confirm');confirmation.hidden=true;
      confirmation.setAttribute('aria-modal','true');confirmation.setAttribute('aria-label','Ջնջման հաստատում');
      const question=node('h4','','Ջնջե՞լ թարգմանությունը։');
      const description=node('p','',`«${item.title}» թարգմանությունը կհեռացվի գրադարանից և կտեղափոխվի տեղական bin պանակ։ Ֆայլն ու տվյալները կպահպանվեն համակարգչում։`);
      const confirmActions=node('div','library-delete-actions');
      const keep=node('button','secondary','Չեղարկել');keep.type='button';
      const confirmDelete=node('button','secondary library-delete','Այո, ջնջել');confirmDelete.type='button';
      const deleteError=node('p','library-delete-error');deleteError.setAttribute('role','alert');
      confirmActions.append(keep,confirmDelete);confirmation.append(question,description,confirmActions,deleteError);
      function closeConfirmation(){confirmation.close();confirmation.hidden=true;remove.focus();}
      remove.addEventListener('click',()=>{confirmation.hidden=false;deleteError.textContent='';confirmation.showModal();keep.focus();});
      keep.addEventListener('click',closeConfirmation);
      confirmation.addEventListener('cancel',event=>{event.preventDefault();if(!confirmDelete.disabled)closeConfirmation();});
      confirmDelete.addEventListener('click',async()=>{
        confirmDelete.disabled=true;keep.disabled=true;confirmDelete.textContent='Ջնջվում է…';deleteError.textContent='';
        try{
          await request('/api/library/'+encodeURIComponent(item.id),{method:'DELETE'});
          confirmation.close();items=items.filter(saved=>saved.id!==item.id);draw();
          note('Թարգմանությունը տեղափոխված է տեղական bin պանակ։');
          $('library-search').focus();
        }catch(error){deleteError.textContent=error.message;}
        finally{confirmDelete.disabled=false;keep.disabled=false;confirmDelete.textContent='Այո, ջնջել';}
      });
      actions.append(download,rename,remove);card.append(body,actions,form,confirmation);list.append(card);
    }
  }
  async function load(){
    if(loading){reloadPending=true;return;}loading=true;
    try{items=await request('/api/library');draw();note(`${items.length} պահված հայերեն թարգմանություն։`);}
    catch(error){note(error.message,true);}
    finally{loading=false;if(reloadPending){reloadPending=false;void load();}}
  }
  $('library-search').addEventListener('input',draw);
  window.addEventListener('haysub-library-updated',load);
  window.addEventListener('focus',load);
  void load();
})();
