(function () {
  'use strict';

  const STORAGE_KEY = 'infinity-theme';
  const VALID = ['light', 'carbon'];

  function resolveTheme(value) {
    if (VALID.includes(value)) return value;
    return 'light';
  }

  function setTheme(theme) {
    const applied = resolveTheme(theme);
    document.body.setAttribute('data-theme', applied);
    document.documentElement.setAttribute('data-theme', applied);
    try { localStorage.setItem(STORAGE_KEY, applied); } catch (e) {}

    document.querySelectorAll('[data-theme-choice]').forEach((btn) => {
      const isActive = btn.getAttribute('data-theme-choice') === applied;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    const label = document.querySelector('[data-theme-current-label]');
    if (label) label.textContent = applied === 'carbon' ? 'Carbono' : 'Claro';

    document.dispatchEvent(new CustomEvent('infinity:theme-changed', { detail: { theme: applied } }));
  }

  function initThemeControls() {
    const saved = (() => { try { return localStorage.getItem(STORAGE_KEY); } catch(e) { return null; } })();
    setTheme(saved || document.body.getAttribute('data-theme') || 'light');

    document.querySelectorAll('[data-theme-choice]').forEach((btn) => {
      btn.addEventListener('click', function (event) {
        event.preventDefault();
        setTheme(this.getAttribute('data-theme-choice'));
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeControls);
  } else {
    initThemeControls();
  }

  window.InfinityTheme = { setTheme };
})();
