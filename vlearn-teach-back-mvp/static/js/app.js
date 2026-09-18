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

    /**
     * Collapsible wrappers — used for description, transcript, objectives,
     * and chunks overview on the lesson detail page.
     *
     * Supported wrappers:
     *   - `.collapsible-text`  → text/paragraph content (e.g. description, transcript)
     *   - `.collapsible-list`  → list/grid content (e.g. objectives, chunks overview)
     *
     * Behavior:
     *   - If the content fits within `data-lines` (default 6 for text,
     *     default 4 for list) lines, the block shows in full and no
     *     toggle appears.
     *   - If it overflows, the block is collapsed and a `.toggle-text-btn`
     *     is shown next to / inside it. Clicking the toggle:
     *       * expands the block to its full height,
     *       * changes the label "Xem thêm" → "Thu gọn",
     *       * rotates the chevron icon 180°,
     *       * updates `aria-expanded` for screen readers.
     *
     * Lookup strategy for the toggle button:
     *   1. If the block is inside `.transcript-box`, the toggle button lives
     *      inside the same box and carries the `toggle-text-btn--inline`
     *      modifier. We locate it by class.
     *   2. Otherwise (Description, Objectives, Chunks Overview), the toggle
     *      sits as the next sibling of the block (`.nextElementSibling`).
     */
    function bindCollapsibles() {
        const COLLAPSE_CLASS = "collapsed";
        const TEXT_LINE_HEIGHT_FALLBACK = 1.75; // matches .collapsible-text p
        const PADDING_BUFFER_PX = 4; // tiny margin so the last line isn't flush
        const LIST_DEFAULT_LINES = 4; // fallback if data-lines is missing

        const blocks = document.querySelectorAll(
            ".collapsible-text, .collapsible-list"
        );
        if (!blocks.length) return;

        blocks.forEach((block) => {
            const isList = block.classList.contains("collapsible-list");
            const requestedLines = parseInt(block.dataset.lines, 10) ||
                (isList ? LIST_DEFAULT_LINES : 6);

            // ── 2) Measure overflow ─────────────────────────────────────────
            // Temporarily remove the cap, measure scrollHeight, then re-apply.
            block.style.maxHeight = "none";
            block.style.overflow = "visible";

            let perLineHeightPx;
            if (isList) {
                // For lists, the "line" height is the height of a single item
                // (li.list-group-item or div.chunk-row), including margin/gap.
                const firstItem =
                    block.querySelector("li, .chunk-row, .chunk-preview > *");
                if (firstItem) {
                    const itemRect = firstItem.getBoundingClientRect();
                    const itemStyle = getComputedStyle(firstItem);
                    const marginBottom = parseFloat(itemStyle.marginBottom) || 0;
                    // If we have a wrapper (chunk-preview) we may want gap; ignore for simplicity.
                    perLineHeightPx = itemRect.height + marginBottom;
                } else {
                    perLineHeightPx = 60; // safe fallback
                }
            } else {
                const lineHeight =
                    parseFloat(getComputedStyle(block).lineHeight) ||
                    parseFloat(getComputedStyle(block).fontSize) *
                        TEXT_LINE_HEIGHT_FALLBACK;
                perLineHeightPx = lineHeight;
            }

            const maxHeightPx = perLineHeightPx * requestedLines + PADDING_BUFFER_PX;
            const overflows = block.scrollHeight > maxHeightPx + 1; // +1 sub-pixel safety

            // ── 3) Apply collapsed / expanded state ────────────────────────
            if (!overflows) {
                block.classList.remove(COLLAPSE_CLASS);
                block.style.maxHeight = "none";
                block.style.overflow = "visible";
            } else {
                block.style.maxHeight = `${maxHeightPx}px`;
                block.style.overflow = "hidden";
            }

            // Restore inline styles we just set — CSS rules under
            // `.collapsible-text.collapsed` / `.collapsible-list.collapsed`
            // will take over from here.
            block.style.removeProperty("max-height");
            block.style.removeProperty("overflow");

            // ── 4) Find the toggle button ──────────────────────────────────
            const transcriptBox = block.closest(".transcript-box");
            let toggleBtn = null;

            if (transcriptBox) {
                // Transcript: button lives inside the same .transcript-box.
                toggleBtn = transcriptBox.querySelector(".toggle-text-btn");
            } else {
                // Description / Objectives / Chunks Overview: button is the
                // next sibling of the block (markup contract).
                const sibling = block.nextElementSibling;
                if (
                    sibling &&
                    sibling.classList &&
                    sibling.classList.contains("toggle-text-btn")
                ) {
                    toggleBtn = sibling;
                }
            }

            if (!toggleBtn) {
                return; // No toggle for this block — skip.
            }

            const isInlineToggle = toggleBtn.classList.contains(
                "toggle-text-btn--inline"
            );

            // ── 5) Short content → hide toggle entirely ────────────────────
            if (!overflows) {
                toggleBtn.classList.add("d-none");
                if (transcriptBox) {
                    transcriptBox.classList.remove("has-overflow");
                    toggleBtn.classList.remove("toggle-text-btn--overlay");
                }
                if (isList) {
                    block.classList.remove("has-overflow");
                }
                return;
            }

            // Show the toggle.
            toggleBtn.classList.remove("d-none");

            // Toggle the overflow hint:
            //   - For transcript: the wrapper `.transcript-box` shows the fade.
            //   - For lists: the `.collapsible-list` itself uses a CSS `::after`
            //     pseudo-element when `.has-overflow` is set.
            if (transcriptBox) {
                transcriptBox.classList.add("has-overflow");
            }
            if (isList) {
                block.classList.add("has-overflow");
            }

            // ── 6) Bind click handler ───────────────────────────────────────
            toggleBtn.addEventListener("click", () => {
                const isCollapsed = block.classList.contains(COLLAPSE_CLASS);
                const label = toggleBtn.querySelector(".toggle-label");

                if (isCollapsed) {
                    // ── Expand ───────────────────────────────────────────────
                    // - block drops `collapsed` (CSS removes the max-height cap)
                    // - toggle aria-expanded = true → icon rotates 180°
                    // - label "Xem thêm" → "Thu gọn"
                    // - transcript: fade hidden, button becomes inline under text
                    block.classList.remove(COLLAPSE_CLASS);
                    toggleBtn.classList.add("expanded");
                    toggleBtn.setAttribute("aria-expanded", "true");
                    if (label) label.textContent = "Thu gọn";

                    if (transcriptBox) {
                        transcriptBox.classList.remove("has-overflow");
                        toggleBtn.classList.remove("toggle-text-btn--overlay");
                    }
                    if (isList) {
                        block.classList.remove("has-overflow");
                    }
                } else {
                    // ── Collapse ─────────────────────────────────────────────
                    // - block gets `collapsed` again (CSS re-applies the cap)
                    // - toggle aria-expanded = false → icon rotates back
                    // - label "Thu gọn" → "Xem thêm"
                    // - transcript: fade shown, button becomes overlay again
                    block.classList.add(COLLAPSE_CLASS);
                    toggleBtn.classList.remove("expanded");
                    toggleBtn.setAttribute("aria-expanded", "false");
                    if (label) label.textContent = "Xem thêm";

                    if (transcriptBox) {
                        transcriptBox.classList.add("has-overflow");
                        if (isInlineToggle) {
                            toggleBtn.classList.add("toggle-text-btn--overlay");
                        }
                    }
                    if (isList) {
                        block.classList.add("has-overflow");
                    }

                    // Smooth scroll so the user doesn't get lost in long text.
                    requestAnimationFrame(() => {
                        toggleBtn.scrollIntoView({
                            behavior: "smooth",
                            block: "nearest",
                        });
                    });
                }
            });

            // ── 7) Transcript + overflow → start in overlay state ──────────
            if (isInlineToggle && overflows) {
                toggleBtn.classList.add("toggle-text-btn--overlay");
            }
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        bindStartSessionForm();
        bindCollapsibles();
    });

    // Expose for other scripts that want to use it.
    window.VLearn = { apiFetch };
})();
