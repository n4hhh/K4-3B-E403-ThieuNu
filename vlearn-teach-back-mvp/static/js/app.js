// app.js — global helpers and the "Start session" form handler.

(function () {
    "use strict";

    /**
     * Tiny fetch wrapper that throws on non-2xx responses.
     */
    async function apiFetch(url, options = {}) {
        const response = await fetch(url, {
            headers: { "Content-Type": "application/json" },
            ...options,
        });
        if (!response.ok) {
            const text = await response.text();
            throw new Error(`Request failed: ${response.status} ${text}`);
        }
        return response.json();
    }

    // The "Bắt đầu phiên học" form is bound by session_intro.html itself,
    // which also drives the button's spinner. Binding it here as well
    // would submit twice and create two sessions per click.

    // Expose for other scripts that want to use it.
    window.VLearn = { apiFetch };
})();
