// Odoo Pulse — shared JS utilities
window.OdooPulse = {
  copyToClipboard(text, btn, successMsg = 'Copiado') {
    navigator.clipboard.writeText(text).then(() => {
      const orig = btn.textContent;
      btn.textContent = successMsg;
      setTimeout(() => { btn.textContent = orig; }, 2000);
    });
  },
};
