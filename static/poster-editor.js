/* Fit the full image inside a portrait 2:3 frame; zooming is optional. */
(() => {
  'use strict';
  function cropBounds(width,height,zoom,x,y){
    const cropWidth=Math.max(width,height*2/3)/zoom,cropHeight=cropWidth*3/2;
    return {x:(width-cropWidth)*x,y:(height-cropHeight)*y,width:cropWidth,height:cropHeight};
  }
  async function edit(file){
    const url=URL.createObjectURL(file),image=new Image();
    try{image.src=url;await image.decode();}finally{URL.revokeObjectURL(url);}
    return new Promise(resolve=>{
      const make=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node;};
      const dialog=make('dialog');dialog.className='poster-editor';
      const title=make('h2','Կարգավորել պաստառը');title.id='poster-editor-title';dialog.setAttribute('aria-labelledby',title.id);
      const hint=make('p','Նկարն ամբողջությամբ տեղավորվում է 2:3 շրջանակում։ Ցանկության դեպքում մեծացրու կամ փոխիր դիրքը։');
      const canvas=make('canvas');canvas.width=640;canvas.height=960;canvas.setAttribute('aria-label','Պաստառի նախադիտում՝ 2:3');
      const controls=make('div'),actions=make('div');actions.className='poster-editor-actions';
      function slider(label,min,max,value,step){
        const wrapper=make('label',label),input=make('input');input.type='range';input.min=min;input.max=max;input.step=step;input.value=value;
        wrapper.append(input);controls.append(wrapper);input.addEventListener('input',draw);return input;
      }
      const zoom=slider('Չափ',1,4,1,.01),horizontal=slider('Հորիզոնական դիրք',0,1,.5,.001),vertical=slider('Ուղղահայաց դիրք',0,1,.5,.001);
      function draw(){
        const box=cropBounds(image.naturalWidth,image.naturalHeight,Number(zoom.value),Number(horizontal.value),Number(vertical.value));
        const ctx=canvas.getContext('2d');ctx.fillStyle='#1b1b22';ctx.fillRect(0,0,canvas.width,canvas.height);
        const scale=canvas.width/box.width;
        ctx.drawImage(image,0,0,image.naturalWidth,image.naturalHeight,-box.x*scale,-box.y*scale,image.naturalWidth*scale,image.naturalHeight*scale);
      }
      let drag=null;
      canvas.addEventListener('pointerdown',event=>{if(event.button!==0)return;canvas.setPointerCapture(event.pointerId);drag={x:event.clientX,y:event.clientY,h:Number(horizontal.value),v:Number(vertical.value)};});
      canvas.addEventListener('pointermove',event=>{
        if(!drag)return;
        const box=cropBounds(image.naturalWidth,image.naturalHeight,Number(zoom.value),0,0),scale=box.width/canvas.getBoundingClientRect().width;
        const clamp=value=>Math.max(0,Math.min(1,value));
        horizontal.value=image.naturalWidth>box.width?clamp(drag.h-(event.clientX-drag.x)*scale/(image.naturalWidth-box.width)):.5;
        vertical.value=image.naturalHeight>box.height?clamp(drag.v-(event.clientY-drag.y)*scale/(image.naturalHeight-box.height)):.5;draw();
      });
      canvas.addEventListener('lostpointercapture',()=>{drag=null;});
      function button(text,action){const node=make('button',text);node.type='button';node.className='secondary';node.addEventListener('click',action);actions.append(node);return node;}
      button('Սկզբնական դիրք',()=>{zoom.value=1;horizontal.value=vertical.value=.5;draw();});
      button('Չեղարկել',()=>dialog.close());
      const status=make('p');status.setAttribute('role','status');
      const use=button('Օգտագործել պաստառը',()=>{
        use.disabled=true;
        canvas.toBlob(blob=>{if(blob){result=blob;dialog.close();}else{status.textContent='Չհաջողվեց պատրաստել պաստառը։ Փորձիր կրկին։';use.disabled=false;}},'image/jpeg',.9);
      });
      let result=null;
      dialog.addEventListener('close',()=>{dialog.remove();resolve(result);},{once:true});
      dialog.append(title,hint,canvas,controls,status,actions);document.body.append(dialog);draw();dialog.showModal();
    });
  }
  globalThis.HaySubPosterEditor={edit,cropBounds};
})();
