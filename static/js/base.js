document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const btn = document.getElementById('theme-toggle');

  function applyTheme(theme) {
    root.dataset.theme = theme;
    if (btn) {
      btn.innerHTML = theme === 'dark' ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
    }
  }

  const stored = localStorage.getItem('theme');
  if (stored) {
    applyTheme(stored);
  } else {
    applyTheme(root.dataset.theme || 'light');
  }

  if (btn) {
    btn.addEventListener('click', () => {
      const newTheme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', newTheme);
      applyTheme(newTheme);
    });
  }
});
