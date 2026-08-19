(() => {
  const STORAGE_KEY = 'firsat-ai-theme';
  const root = document.documentElement;
  const preferred = () => window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const saved = localStorage.getItem(STORAGE_KEY);
  root.dataset.theme = saved || preferred();

  const updateLabels = () => {
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      const dark = root.dataset.theme === 'dark';
      button.setAttribute('aria-label', dark ? 'Açık temaya geç' : 'Koyu temaya geç');
      button.title = dark ? 'Açık tema' : 'Koyu tema';
    });
  };

  document.addEventListener('click', (event) => {
    const button = event.target.closest('[data-theme-toggle]');
    if (!button) return;
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem(STORAGE_KEY, root.dataset.theme);
    updateLabels();
  });

  document.addEventListener('click', (event) => {
    document.querySelectorAll('details.mega-menu[open]').forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute('open');
    });
  });
  updateLabels();
})();
