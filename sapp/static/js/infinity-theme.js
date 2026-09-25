/* INFINITY STOCK 12.1 - gerenciador global de tema */
(() => {
  'use strict';

  const STORAGE_KEY = 'infinity-theme';
  const THEMES = ['midnight', 'clarity'];
  const DEFAULT_THEME = 'midnight';

  const normalizeTheme = value => THEMES.includes(value) ? value : DEFAULT_THEME;

  const readStoredTheme = () => {
    try {
      return normalizeTheme(localStorage.getItem(STORAGE_KEY));
    } catch (_) {
      return DEFAULT_THEME;
    }
  };

  const cssVar = name => {
    const target = document.body || document.documentElement;
    return getComputedStyle(target).getPropertyValue(name).trim();
  };

  const chartInstances = () => {
    if (!window.Chart) return [];
    const instances = window.Chart.instances;
    if (!instances) return [];
    if (instances instanceof Map) return Array.from(instances.values());
    return Object.values(instances).filter(Boolean);
  };

  function syncCharts() {
    if (!window.Chart) return;

    const text = cssVar('--theme-chart-text') || (currentTheme() === 'midnight' ? '#9bb2a7' : '#5b6a61');
    const grid = cssVar('--theme-chart-grid') || 'rgba(100,120,110,.12)';
    const tooltip = cssVar('--theme-tooltip') || '#17271d';
    const tooltipText = cssVar('--theme-tooltip-text') || '#f8fff9';
    const border = cssVar('--theme-border') || '#dbe5de';

    try {
      window.Chart.defaults.color = text;
      window.Chart.defaults.borderColor = grid;
    } catch (_) {}

    chartInstances().forEach(chart => {
      try {
        chart.options = chart.options || {};
        chart.options.color = text;

        const scales = chart.options.scales || {};
        Object.values(scales).forEach(scale => {
          if (!scale || typeof scale !== 'object') return;
          scale.ticks = scale.ticks || {};
          scale.ticks.color = text;
          scale.grid = scale.grid || {};
          scale.grid.color = grid;
          scale.border = scale.border || {};
          scale.border.color = border;
          if (scale.title) scale.title.color = text;
          if (scale.pointLabels) scale.pointLabels.color = text;
        });

        chart.options.plugins = chart.options.plugins || {};
        const plugins = chart.options.plugins;

        if (plugins.legend) {
          plugins.legend.labels = plugins.legend.labels || {};
          plugins.legend.labels.color = text;
        }

        plugins.tooltip = plugins.tooltip || {};
        plugins.tooltip.backgroundColor = tooltip;
        plugins.tooltip.titleColor = tooltipText;
        plugins.tooltip.bodyColor = tooltipText;
        plugins.tooltip.borderColor = border;
        plugins.tooltip.borderWidth = 1;

        if (plugins.title) plugins.title.color = text;
        if (plugins.subtitle) plugins.subtitle.color = text;

        chart.update('none');
      } catch (error) {
        // Um gráfico específico não deve impedir a troca de tema do sistema.
        console.debug('[InfinityTheme] gráfico não atualizado', error);
      }
    });
  }

  function currentTheme() {
    return normalizeTheme(document.documentElement.dataset.theme || readStoredTheme());
  }

  function themeCopy(theme) {
    if (theme === 'midnight') {
      return {
        current: 'Neon',
        next: 'Claro',
        glyph: '☀',
        label: 'Ativar tema claro',
        meta: '#04141d'
      };
    }
    return {
      current: 'Claro',
      next: 'Neon',
      glyph: '☾',
      label: 'Ativar tema Neon',
      meta: '#0a2e1c'
    };
  }

  function syncControls(theme) {
    const copy = themeCopy(theme);
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.setAttribute('aria-label', copy.label);
      button.setAttribute('title', copy.label);
      const glyph = button.querySelector('[data-theme-glyph]');
      if (glyph) glyph.textContent = copy.glyph;
      const current = button.querySelector('[data-theme-current]');
      if (current) current.textContent = copy.current;
      const next = button.querySelector('[data-theme-next]');
      if (next) next.textContent = copy.next;
    });

    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', copy.meta);
  }

  function applyTheme(theme, { persist = true, notify = true } = {}) {
    theme = normalizeTheme(theme);
    document.documentElement.dataset.theme = theme;
    if (document.body) document.body.dataset.theme = theme;

    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, theme); } catch (_) {}
    }

    syncControls(theme);

    // Deixa os estilos assentarem antes de recalcular Chart.js.
    requestAnimationFrame(() => {
      syncCharts();
      setTimeout(syncCharts, 80);
    });

    if (notify) {
      window.dispatchEvent(new CustomEvent('infinity:themechange', { detail: { theme } }));
    }
    return theme;
  }

  function toggleTheme() {
    return applyTheme(currentTheme() === 'midnight' ? 'clarity' : 'midnight');
  }

  function bindControls(root = document) {
    root.querySelectorAll?.('[data-theme-toggle]').forEach(button => {
      if (button.dataset.themeBound === '1') return;
      button.dataset.themeBound = '1';
      button.addEventListener('click', event => {
        event.preventDefault();
        toggleTheme();
      });
    });
    syncControls(currentTheme());
  }

  window.InfinityTheme = {
    themes: [...THEMES],
    get: currentTheme,
    set: theme => applyTheme(theme),
    toggle: toggleTheme,
    syncCharts,
    bindControls
  };

  // O tema já é aplicado no <head> para evitar flash. Aqui sincronizamos o DOM.
  const boot = () => {
    applyTheme(currentTheme(), { persist: false, notify: false });
    bindControls(document);
    setTimeout(syncCharts, 250);
    setTimeout(syncCharts, 900);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }

  new MutationObserver(mutations => {
    for (const mutation of mutations) {
      if (mutation.addedNodes?.length) {
        bindControls(document);
        break;
      }
    }
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
