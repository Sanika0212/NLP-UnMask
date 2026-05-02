// ── Font loading (avoids CSP issues with @import) ─────────────────────────
(function () {
  var link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap';
  document.head.appendChild(link);
})();

// ── Apply Inter to every text node Chainlit/MUI renders ───────────────────
(function applyFont() {
  var style = document.createElement('style');
  style.textContent = `
    body, body *, html {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }
    code, pre, kbd, samp,
    [class*="mono"], [class*="Mono"],
    [class*="code"], [class*="Code"] {
      font-family: 'JetBrains Mono', 'Courier New', monospace !important;
    }
  `;
  document.head.appendChild(style);
})();

// ── Hide "Selected: X" echo messages from AskActionMessage ────────────────
(function () {
  function hideSelectionEchoes() {
    document.querySelectorAll('[class*="message"], [class*="Message"]').forEach(function(el) {
      var text = el.textContent.trim();
      if (text.startsWith('Selected:') && text.length < 120) {
        el.style.display = 'none';
      }
    });
  }
  var observer = new MutationObserver(hideSelectionEchoes);
  observer.observe(document.body, { childList: true, subtree: true });
  hideSelectionEchoes();
})();
