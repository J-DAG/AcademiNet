// ── Utilidades globales ────────────────────────────────────────

let toastTimer = null;

function showToast(msg, success = true) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast';
    toast.style.background = success ? '#10b981' : '#ef4444';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.add('hidden'), 3500);
}

function toggleForm(id) {
    const el = document.getElementById(id);
    el.classList.toggle('hidden');
}

// ── Confirmar acciones destructivas ──────────────────────────
function confirmAction(msg, fn) {
    if (window.confirm(msg)) fn();
}
