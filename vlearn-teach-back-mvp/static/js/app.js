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

    /**
     * "Start teaching" button on session_intro.html.
     * Posts to /api/teaching-sessions then redirects.
     */
    function bindStartSessionForm() {
        const form = document.getElementById("start-session-form");
        if (!form) return;

        form.addEventListener("submit", async (event) => {
            event.preventDefault();
            const lessonId = form.dataset.lessonId;
            const createUrl = form.dataset.createUrl;
            const redirectPattern = form.dataset.redirectPattern || "/session/{id}";
            const button = form.querySelector("button[type='submit']");
            if (button) button.disabled = true;

            try {
                const session = await apiFetch(createUrl, {
                    method: "POST",
                    body: JSON.stringify({ lesson_id: lessonId }),
                });
                window.location.href = redirectPattern.replace("{id}", session.id);
            } catch (err) {
                console.error(err);
                alert("Could not start the session: " + err.message);
                if (button) button.disabled = false;
            }
        });
    }

    document.addEventListener("DOMContentLoaded", bindStartSessionForm);

    // Expose for other scripts that want to use it.
    window.VLearn = { apiFetch };
})();
