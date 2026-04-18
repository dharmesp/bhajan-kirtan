/* ============================================================
   ShriKirtan — app.js
   Global JS: dark/light theme toggle
   (Bhajan-page interactions are inline in bhajan.html for
    performance — no extra network round-trip.)
   ============================================================ */

(function () {
  'use strict';

  // ── Theme (dark / light) ─────────────────────────────────────
  const html   = document.documentElement;
  const toggle = document.getElementById('themeToggle');
  const icon   = document.getElementById('themeIcon');

  function applyTheme(theme) {
    html.setAttribute('data-bs-theme', theme);
    if (icon) {
      icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-stars-fill';
    }
    try { localStorage.setItem('sk_theme', theme); } catch (_) {}
  }

  // Determine initial theme: user preference → system preference
  let initial = 'light';
  try { initial = localStorage.getItem('sk_theme') || initial; } catch (_) {}
  if (!localStorage.getItem('sk_theme')) {
    initial = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  applyTheme(initial);

  toggle?.addEventListener('click', () => {
    applyTheme(html.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark');
  });

  // Keep theme in sync when system preference changes (and user hasn't overridden)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    try {
      if (!localStorage.getItem('sk_theme')) {
        applyTheme(e.matches ? 'dark' : 'light');
      }
    } catch (_) {}
  });
})();
