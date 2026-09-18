// teaching.js — Teaching session interaction
//
// The server owns every decision: what the agent says, whether the chunk
// passed, and which badge the bubble carries. This file only renders
// what came back. In particular it must never display validation
// internals such as `missing_points` — those name the very thing the
// student is supposed to work out, so printing them would hand over the
// answer that the agent just carefully avoided giving.

(function () {
    "use strict";

    const form = document.getElementById("teaching-form");
    if (!form) return;

    const chatArea = document.getElementById("chat-area");
    const messageInput = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    const nextChunkBtn = document.getElementById("next-chunk-btn");
    const typingIndicator = document.getElementById("typing-indicator");

    const messageUrl = form.dataset.messageUrl;
    const nextUrl = form.dataset.nextUrl;
    const sessionId = form.dataset.sessionId;

    // ------------------------------------------------------------------
    // Rendering helpers
    // ------------------------------------------------------------------

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // The same tiny Markdown subset the server-side `md_light` filter
    // renders, so a message looks identical before and after a reload.
    function renderContent(text) {
        return escapeHtml(text || "")
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/^&gt;\s?(.*)$/gm, '<span class="msg-quote">$1</span>')
            .replace(/\n/g, "<br>");
    }

    function appendMessage(author, content, options) {
        if (!chatArea) return null;
        const opts = options || {};

        const wrapper = document.createElement("div");
        wrapper.className = "msg " + author;
        if (opts.kind) wrapper.classList.add("msg--" + opts.kind);

        let inner = "";
        if (opts.badge) {
            inner +=
                '<div class="gap-badge"><i class="bi bi-question-circle"></i> ' +
                escapeHtml(opts.badge) +
                "</div>";
        } else if (opts.kind === "validation") {
            inner +=
                '<div class="pass-badge"><i class="bi bi-check-circle"></i> ' +
                "Đạt tiêu chí phần này</div>";
        }
        inner += renderContent(content);

        wrapper.innerHTML =
            '<div class="avatar">' +
            (author === "agent" ? "🤖" : "👤") +
            "</div>" +
            '<div class="bubble">' +
            inner +
            "</div>";

        if (typingIndicator && typingIndicator.style.display !== "none") {
            chatArea.insertBefore(wrapper, typingIndicator);
        } else {
            chatArea.appendChild(wrapper);
        }
        chatArea.scrollTop = chatArea.scrollHeight;
        return wrapper;
    }

    function appendSystemMessage(content) {
        if (!chatArea) return null;
        const wrapper = document.createElement("div");
        wrapper.className = "msg system";
        wrapper.innerHTML =
            '<div class="bubble"><i class="bi bi-check-circle-fill me-2"></i>' +
            escapeHtml(content) +
            "</div>";
        chatArea.appendChild(wrapper);
        chatArea.scrollTop = chatArea.scrollHeight;
        return wrapper;
    }

    function showTyping() {
        if (!typingIndicator) return;
        typingIndicator.style.display = "flex";
        chatArea.scrollTop = chatArea.scrollHeight;
    }

    function hideTyping() {
        if (typingIndicator) typingIndicator.style.display = "none";
    }

    function setSendEnabled(enabled) {
        if (sendBtn) sendBtn.disabled = !enabled;
        if (messageInput) messageInput.disabled = !enabled;
    }

    function enableNextChunk() {
        if (!nextChunkBtn) return;
        nextChunkBtn.disabled = false;
        nextChunkBtn.classList.remove("btn-outline-secondary");
        nextChunkBtn.classList.add("btn-success");
    }

    // ------------------------------------------------------------------
    // Submit an explanation
    // ------------------------------------------------------------------

    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const content = (messageInput?.value || "").trim();
        if (!content) return;

        setSendEnabled(false);
        appendMessage("student", content, { kind: "explanation" });
        messageInput.value = "";
        messageInput.style.height = "auto";
        showTyping();

        try {
            const payload = await window.VLearn.apiFetch(messageUrl, {
                method: "POST",
                body: JSON.stringify({ content: content }),
            });

            hideTyping();

            const agentMsg = payload.agent_message;
            if (agentMsg) {
                appendMessage("agent", agentMsg.content, {
                    kind: agentMsg.kind,
                    badge: agentMsg.badge,
                });
            }

            const validation = payload.validation || {};
            const session = payload.session || {};

            if (validation.passed) {
                appendSystemMessage(
                    validation.needs_review
                        ? "Phần này được đánh dấu để xem lại — bạn có thể đi tiếp."
                        : "✓ Phần này hoàn thành!"
                );
                enableNextChunk();
                setSendEnabled(false);

                if (session.status === "completed") {
                    showModal("lessonCompleteModal");
                } else {
                    showModal("chunkCompleteModal");
                }
            } else {
                // Not passed: the agent's question is already on screen.
                // Nothing further is rendered — no key points, no score.
                setSendEnabled(true);
                messageInput?.focus();
            }
        } catch (err) {
            console.error(err);
            hideTyping();
            appendMessage("agent", "⚠️ " + err.message);
            setSendEnabled(true);
            messageInput?.focus();
        }
    });

    // ------------------------------------------------------------------
    // Move to the next chunk
    // ------------------------------------------------------------------

    if (nextChunkBtn) {
        nextChunkBtn.addEventListener("click", async function () {
            nextChunkBtn.disabled = true;
            nextChunkBtn.innerHTML =
                '<span class="spinner-border spinner-border-sm me-2"></span>Đang tải...';

            try {
                const response = await window.VLearn.apiFetch(nextUrl, {
                    method: "POST",
                });
                if (response.status === "completed") {
                    window.location.href = "/session/" + sessionId + "/result";
                } else {
                    window.location.reload();
                }
            } catch (err) {
                console.error(err);
                alert("Không thể chuyển phần: " + err.message);
                nextChunkBtn.disabled = false;
                nextChunkBtn.innerHTML =
                    '<i class="bi bi-arrow-right me-1"></i>Sang phần tiếp theo';
            }
        });
    }

    // ------------------------------------------------------------------
    // Composer behaviour
    // ------------------------------------------------------------------

    if (messageInput) {
        messageInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                form.requestSubmit ? form.requestSubmit() : form.dispatchEvent(new Event("submit"));
            }
        });

        messageInput.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = Math.min(this.scrollHeight, 120) + "px";
        });
    }

    window.insertHint = function (text) {
        if (!messageInput) return;
        const current = messageInput.value.trim();
        messageInput.value = current ? current + " " + text : text;
        messageInput.focus();
    };

    // ------------------------------------------------------------------
    // Modals
    // ------------------------------------------------------------------

    function showModal(id) {
        const el = document.getElementById(id);
        if (el && typeof bootstrap !== "undefined") {
            new bootstrap.Modal(el).show();
        }
    }

    const proceedNextBtn = document.getElementById("proceed-next-btn");
    if (proceedNextBtn && nextChunkBtn) {
        proceedNextBtn.addEventListener("click", function () {
            nextChunkBtn.click();
        });
    }

    // ------------------------------------------------------------------
    // Exit confirmation — a session in progress should not vanish on a
    // stray click (FE spec §21).
    // ------------------------------------------------------------------

    const exitLink = document.getElementById("exit-session");
    if (exitLink) {
        exitLink.addEventListener("click", function (e) {
            const hasProgress = chatArea && chatArea.querySelectorAll(".msg.student").length > 0;
            if (hasProgress && !window.confirm("Bạn muốn thoát phiên dạy lại? Tiến trình hiện tại vẫn được lưu.")) {
                e.preventDefault();
            }
        });
    }

    if (chatArea) {
        chatArea.scrollTop = chatArea.scrollHeight;
    }
})();
