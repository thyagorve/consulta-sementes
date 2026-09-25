(function routeTransitions(){
  'use strict';
  const body=document.body;
  if(!body)return;

  let navigating=false;
  let safetyTimer=null;

  function reveal(){
    if(safetyTimer) window.clearTimeout(safetyTimer);
    requestAnimationFrame(()=>{
      body.classList.remove('app-route-loading');
      body.classList.add('app-route-ready');
    });
  }

  function cover(){
    body.classList.remove('app-route-ready');
    body.classList.add('app-route-loading');
  }

  /* Sem aguardar fontes, imagens ou fetches: a página aparece assim que o DOM existe. */
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',()=>setTimeout(reveal,28),{once:true});
  }else{
    setTimeout(reveal,0);
  }

  window.addEventListener('pageshow',()=>{
    navigating=false;
    reveal();
  });

  window.addEventListener('beforeunload',cover);

  document.addEventListener('submit',event=>{
    const form=event.target;
    if(event.defaultPrevented||!(form instanceof HTMLFormElement))return;
    if(form.dataset.noPageTransition==='1')return;
    requestAnimationFrame(cover);
  });

  document.addEventListener('click',event=>{
    if(navigating||event.defaultPrevented||event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    const link=event.target.closest('a[href]');
    if(!link||link.target==='_blank'||link.hasAttribute('download')||link.dataset.noPageTransition==='1')return;

    const href=(link.getAttribute('href')||'').trim();
    if(!href||href.startsWith('#')||href.startsWith('javascript:')||href.startsWith('mailto:')||href.startsWith('tel:'))return;

    let url;
    try{url=new URL(link.href,window.location.href)}catch(_){return}
    if(url.origin!==window.location.origin)return;
    if(url.pathname===window.location.pathname&&url.search===window.location.search&&url.hash)return;

    navigating=true;
    event.preventDefault();
    cover();
    /* 95 ms: tempo suficiente para perceber a transição, sem sensação de peso. */
    setTimeout(()=>window.location.assign(url.href),95);
  });

  /* Nunca deixa a camada presa se algum script da página falhar. */
  safetyTimer=setTimeout(()=>{if(!navigating)reveal()},650);
})();
