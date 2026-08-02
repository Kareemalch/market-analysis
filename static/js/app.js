/* Market Cap — shared JS */

/* ============================================================
   Toast notification system
   window.toast(message, type, duration)
   type: 'success' | 'error' | 'info'
   ============================================================ */
(function () {
  const ICONS = { success: '✓', error: '✕', info: 'ℹ' };

  function getContainer() {
    let c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      c.className = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  window.toast = function (msg, type = 'info', duration = 4000) {
    const container = getContainer();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `
      <span class="toast-icon">${ICONS[type] || ICONS.info}</span>
      <span class="toast-msg">${msg}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">✕</button>`;
    container.appendChild(el);

    setTimeout(() => {
      el.classList.add('hiding');
      setTimeout(() => el.remove(), 220);
    }, duration);
  };
})();

/* ============================================================
   Button loading state helpers
   setLoading(btn, true/false, lightSpinner)
   ============================================================ */
window.setLoading = function (btn, loading, light = false) {
  if (loading) {
    btn.dataset.origText = btn.textContent;
    btn.classList.add('btn-loading');
    if (light) btn.classList.add('light');
    btn.disabled = true;
  } else {
    btn.classList.remove('btn-loading', 'light');
    btn.disabled = false;
    if (btn.dataset.origText) btn.textContent = btn.dataset.origText;
  }
};

/* ============================================================
   Search autocomplete (runs on all pages)
   ============================================================ */
(function () {
  const input    = document.getElementById('search-input');
  const dropdown = document.getElementById('autocomplete');
  if (!input || !dropdown) return;

  let debounceTimer = null;

  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (!q) { dropdown.classList.add('hidden'); return; }
    debounceTimer = setTimeout(() => fetchSuggestions(q), 220);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const val = input.value.trim().toUpperCase();
      if (val) window.location.href = `/stock/${val}`;
    }
    if (e.key === 'Escape') dropdown.classList.add('hidden');
  });

  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.add('hidden');
    }
  });

  async function fetchSuggestions(q) {
    try {
      const res  = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
      const data = await res.json();
      if (!data.length) { dropdown.classList.add('hidden'); return; }
      dropdown.innerHTML = data.map(r => `
        <div class="autocomplete-item" onclick="window.location.href='/stock/${r.ticker}'">
          <span class="autocomplete-ticker">${r.ticker}</span>
          <span class="autocomplete-name">${r.name}</span>
        </div>`).join('');
      dropdown.classList.remove('hidden');
    } catch {
      dropdown.classList.add('hidden');
    }
  }
})();
