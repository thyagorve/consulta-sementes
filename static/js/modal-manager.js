(function modalManager(){
  'use strict';

  const ROOT_SELECTOR = [
    '.modal',
    '.modal-overlay[id]',
    '.custom-modal-overlay',
    '.rf-modal',
    '.pl-modal',
    '#modalRenovarOverlay',
    '#avisosOverlay',
    '.tls-tags-modal',
    '.appui-backdrop'
  ].join(',');

  let locked = false;
  let scrollY = 0;
  let raf = 0;
  let activeRoot = null;

  function isVisible(el){
    if (!el || !el.isConnected) return false;
    if (el.id === 'sidebarOverlay') return false;
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    if (el.getAttribute('aria-hidden') === 'true' && !el.classList.contains('show') && !el.classList.contains('active') && !el.classList.contains('is-open')) return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function roots(){
    return Array.from(document.querySelectorAll(ROOT_SELECTOR)).filter(el => el.id !== 'sidebarOverlay');
  }

  function portalize(el){
    if (!el || el.parentElement === document.body) return;
    /*
      position:fixed pode ficar preso a um ancestral transformado. Colocar a raiz
      diretamente no body faz o modal realmente usar a viewport como referência.
    */
    document.body.appendChild(el);
    el.dataset.modalPortal = '1';
  }

  function lock(){
    if (locked) return;
    locked = true;
    scrollY = window.scrollY || window.pageYOffset || 0;
    document.documentElement.classList.add('app-modal-open');
    document.body.classList.add('app-modal-open');
    document.body.style.position = 'fixed';
    document.body.style.top = `-${scrollY}px`;
    document.body.style.left = '0';
    document.body.style.right = '0';
  }

  function unlock(){
    if (!locked) return;
    locked = false;
    document.documentElement.classList.remove('app-modal-open');
    document.body.classList.remove('app-modal-open');
    document.body.style.removeProperty('position');
    document.body.style.removeProperty('top');
    document.body.style.removeProperty('left');
    document.body.style.removeProperty('right');
    /* scripts legados costumam escrever overflow diretamente no body */
    document.body.style.removeProperty('overflow');
    window.scrollTo(0, scrollY);
  }

  function focusModal(root){
    if (!root) return;
    if (root.contains(document.activeElement)) return;
    const dialog = root.querySelector('.modal-dialog,.modal-content,.modal-box,.custom-modal-box,.modal-renovar-dialog,.rf-modal-box,.pl-dialog,.tls-tags-dialog,.appui-dialog') || root;
    const target = dialog.querySelector('[autofocus],input:not([type="hidden"]):not([disabled]),select:not([disabled]),textarea:not([disabled]),button:not([disabled]),a[href]');
    if (target) {
      setTimeout(() => { try { target.focus({preventScroll:true}); } catch(_) { target.focus(); } }, 20);
    } else {
      if (!dialog.hasAttribute('tabindex')) dialog.setAttribute('tabindex','-1');
      setTimeout(() => { try { dialog.focus({preventScroll:true}); } catch(_) { dialog.focus(); } }, 20);
    }
  }

  function sync(){
    raf = 0;
    const all = roots();
    const visible = all.filter(isVisible);

    visible.forEach(portalize);

    if (visible.length) {
      lock();
      const top = visible[visible.length - 1];
      if (top !== activeRoot) {
        activeRoot = top;
        focusModal(top);
      }
    } else {
      activeRoot = null;
      unlock();
    }
  }

  function schedule(){
    if (raf) return;
    raf = requestAnimationFrame(sync);
  }

  function scanAndPortalizeKnownRoots(){
    roots().forEach(el => {
      /* modais podem ser movidos antecipadamente, inclusive ocultos */
      portalize(el);
    });
    schedule();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scanAndPortalizeKnownRoots, {once:true});
  } else {
    scanAndPortalizeKnownRoots();
  }

  const observer = new MutationObserver(mutations => {
    let needsScan = false;
    for (const m of mutations) {
      if (m.type === 'childList' && m.addedNodes.length) needsScan = true;
      if (m.type === 'attributes') needsScan = true;
    }
    if (needsScan) {
      roots().forEach(portalize);
      schedule();
    }
  });

  observer.observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ['class','style','aria-hidden','open']
  });

  window.addEventListener('pageshow', schedule);
  window.addEventListener('resize', schedule, {passive:true});

  /* API opcional para scripts novos. Os antigos continuam funcionando. */
  window.AppModalManager = {
    sync: schedule,
    lock,
    unlock,
    portalize
  };
})();
