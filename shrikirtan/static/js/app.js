/* ============================================================
   ShriKirtan — app.js
   ============================================================ */

// Auto-add bottom padding when public tab bar is present
(function () {
  if (document.getElementById('pubTabbar')) {
    document.body.classList.add('sk-has-pub-tabbar');
  }
})();
