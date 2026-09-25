(function contextHelp(){
  'use strict';

  const SOURCE_SELECTOR = [
    '.ui-help-text',
    '.pl-sub',
    '.pl-help',
    '.pl-field-help',
    '.form-hint',
    '.help-text',
    '.form-help',
    '.panel-description',
    '.page-subtitle',
    '.tls-tags-help',
    'p.subtitle',
    'p.description',
    '.pl-protection-note',
    '.qr-instructions'
  ].join(',');

  let popover;
  let activeButton = null;

  function ensurePopover(){
    if (popover) return popover;
    popover = document.createElement('div');
    popover.className = 'ui-help-popover';
    popover.setAttribute('role','tooltip');
    popover.id = 'globalContextHelp';
    document.body.appendChild(popover);
    return popover;
  }

  function closeHelp(){
    if (!popover) return;
    popover.classList.remove('show','above');
    if (activeButton) activeButton.setAttribute('aria-expanded','false');
    activeButton = null;
  }

  function positionPopover(button){
    const p = ensurePopover();
    const r = button.getBoundingClientRect();
    const gap = 9;
    const pagePad = 10;
    const width = Math.min(330, window.innerWidth - 24);
    p.style.width = `${width}px`;
    p.style.left = '0px';
    p.style.top = '0px';
    p.classList.remove('above');

    const measured = p.getBoundingClientRect();
    const height = measured.height || 70;
    let left = r.left + r.width / 2 - width / 2;
    left = Math.max(pagePad, Math.min(left, window.innerWidth - width - pagePad));

    const roomBelow = window.innerHeight - r.bottom;
    const useAbove = roomBelow < height + 20 && r.top > height + 20;
    let top = useAbove ? r.top - height - gap : r.bottom + gap;
    top = Math.max(pagePad, Math.min(top, window.innerHeight - height - pagePad));

    p.style.left = `${left}px`;
    p.style.top = `${top}px`;
    p.style.setProperty('--ui-help-arrow-x', `${Math.max(12, Math.min(width - 22, r.left + r.width/2 - left - 5))}px`);
    p.classList.toggle('above', useAbove);
  }

  function openHelp(button){
    const text = button.dataset.helpText || '';
    if (!text) return;
    const p = ensurePopover();
    const wasActive = activeButton === button && p.classList.contains('show');
    closeHelp();
    if (wasActive) return;

    p.textContent = text;
    activeButton = button;
    button.setAttribute('aria-expanded','true');
    p.classList.add('show');
    requestAnimationFrame(() => positionPopover(button));
  }

  function preferredAnchor(source){
    const field = source.closest('.pl-field,.form-group,.form-field,.field-group,.input-group-wrapper,.setting-item,.config-item');
    if (field) {
      const label = field.querySelector('label');
      if (label && !label.closest('.pl-switch')) return label;
    }

    const header = source.closest('.pl-hero,.page-header,.panel-header,.section-header,.card-header,.modal-header,.pl-modal-head,.tls-tags-header');
    if (header) {
      const title = header.querySelector('h1,h2,h3,h4,.pl-title,.page-title');
      if (title) return title;
    }

    const modalRoot = source.closest('.pl-modal,.modal,.modal-overlay[id],.custom-modal-overlay,.rf-modal,.tls-tags-modal');
    if (modalRoot) {
      const title = modalRoot.querySelector('.pl-modal-head h1,.pl-modal-head h2,.modal-header h1,.modal-header h2,.modal-header h3,.tls-tags-header h2,.rf-modal-header h3');
      if (title) return title;
    }

    const parent = source.parentElement;
    if (parent) {
      const title = parent.querySelector(':scope > h1,:scope > h2,:scope > h3,:scope > h4,:scope > label,:scope > .pl-title');
      if (title) return title;
    }
    return null;
  }

  function compact(source){
    if (!(source instanceof HTMLElement)) return;
    if (source.dataset.uiHelpDone === '1' || source.dataset.uiHelpIgnore === '1') return;
    if (source.closest('.toast,.alert,.validation-error,.errorlist,.messages')) return;
    /* Valores originais são dados úteis, não texto de instrução. */
    if (source.matches('.form-hint.original:not(.info-hint)')) return;

    const text = (source.textContent || '').replace(/\s+/g,' ').trim();
    if (!text || text.length < 12) return;

    source.dataset.uiHelpDone = '1';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'ui-help-button';
    btn.textContent = 'i';
    btn.dataset.helpText = text;
    btn.setAttribute('aria-label','Mostrar informação');
    btn.setAttribute('aria-expanded','false');
    btn.setAttribute('aria-controls','globalContextHelp');

    const anchor = preferredAnchor(source);
    if (anchor) anchor.appendChild(btn);
    else source.parentNode?.insertBefore(btn, source);

    source.classList.add('ui-help-source-collapsed');
    source.setAttribute('aria-hidden','true');
  }

  function scan(root){
    if (!root || !root.querySelectorAll) return;
    if (root.matches?.(SOURCE_SELECTOR)) compact(root);
    root.querySelectorAll(SOURCE_SELECTOR).forEach(compact);
  }

  document.addEventListener('click', e => {
    const btn = e.target.closest('.ui-help-button');
    if (btn) {
      e.preventDefault();
      e.stopPropagation();
      openHelp(btn);
      return;
    }
    if (!e.target.closest('.ui-help-popover')) closeHelp();
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeHelp();
  });
  window.addEventListener('resize', () => activeButton && positionPopover(activeButton), {passive:true});
  window.addEventListener('scroll', () => activeButton && positionPopover(activeButton), {passive:true,capture:true});

  function init(){
    ensurePopover();
    scan(document);
    new MutationObserver(mutations => {
      for (const m of mutations) m.addedNodes.forEach(node => {
        if (node.nodeType === 1) scan(node);
      });
    }).observe(document.body,{childList:true,subtree:true});
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
