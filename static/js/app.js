async function addToCart(e) {
    e.preventDefault();
    const form = e.target;
    const data = new FormData(form);
    try {
        const res = await fetch(form.action, { method: 'POST', body: data });
        const payload = await res.json();
        if (payload.ok) {
            alert('Added to cart');
        } else {
            alert(payload.message || 'Error');
        }
    } catch (err) {
        alert('Network error');
    }
    return false;
}

async function pollStatus() {
    if (!window.ORDER_ID) return;
    const el = document.getElementById('status');
    const url = `/api/order/${window.ORDER_ID}/status`;
    try {
        const res = await fetch(url);
        const payload = await res.json();
        if (payload.ok) {
            el.textContent = payload.status;
        }
    } catch (e) {
        // ignore
    } finally {
        setTimeout(pollStatus, window.POLL_MS || 5000);
    }
}
window.addEventListener('DOMContentLoaded', pollStatus);