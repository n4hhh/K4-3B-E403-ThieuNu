// teaching.js — Teaching session interaction

(function () {
    "use strict";

    const form = document.getElementById("teaching-form");
    if (!form) return;

    const chatArea = document.getElementById("chat-area");
    const messageInput = document.getElementById("message-input");
    const sendBtn = document.getElementById("send-btn");
    const nextChunkBtn = document.getElementById("next-chunk-btn");
    const hintRow = document.getElementById("hint-row");
    const typingIndicator = document.getElementById("typing-indicator");

    const messageUrl = form.dataset.messageUrl;
    const nextUrl = form.dataset.nextUrl;
    const sessionId = form.dataset.sessionId;

    // Current question index for the quiz
    let currentQuestionIndex = 0;

    // ------------------------------------------------------------------
    // Helper: Append a message to the chat area
    // ------------------------------------------------------------------
    function appendMessage(author, content, isHtml = false) {
        if (!chatArea) return;

        const wrapper = document.createElement("div");
        wrapper.className = `msg ${author}`;

        const avatar = author === "agent" ? "🤖" : "👤";
        const avatarHtml = `<div class="avatar">${avatar}</div>`;

        let bubbleContent;
        if (isHtml) {
            bubbleContent = content;
        } else {
            bubbleContent = escapeHtml(content).replace(/\n/g, "<br>");
        }

        wrapper.innerHTML = `
            ${avatarHtml}
            <div class="bubble">${bubbleContent}</div>
        `;

        // Insert before typing indicator
        if (typingIndicator && typingIndicator.style.display !== "none") {
            chatArea.insertBefore(wrapper, typingIndicator);
        } else {
            chatArea.appendChild(wrapper);
        }

        // Scroll to bottom
        chatArea.scrollTop = chatArea.scrollHeight;

        return wrapper;
    }

    // ------------------------------------------------------------------
    // Helper: Show typing indicator
    // ------------------------------------------------------------------
    function showTyping() {
        if (typingIndicator) {
            typingIndicator.style.display = "flex";
            chatArea.scrollTop = chatArea.scrollHeight;
        }
    }

    // ------------------------------------------------------------------
    // Helper: Hide typing indicator
    // ------------------------------------------------------------------
    function hideTyping() {
        if (typingIndicator) {
            typingIndicator.style.display = "none";
        }
    }

    // ------------------------------------------------------------------
    // Helper: Enable/disable send button
    // ------------------------------------------------------------------
    function setSendEnabled(enabled) {
        if (sendBtn) {
            sendBtn.disabled = !enabled;
        }
        if (messageInput) {
            messageInput.disabled = !enabled;
        }
    }

    // ------------------------------------------------------------------
    // Helper: Show next chunk button
    // ------------------------------------------------------------------
    function enableNextChunk() {
        if (nextChunkBtn) {
            nextChunkBtn.disabled = false;
            nextChunkBtn.classList.remove("btn-outline-secondary");
            nextChunkBtn.classList.add("btn-success");
        }
    }

    // ------------------------------------------------------------------
    // Helper: Escape HTML
    // ------------------------------------------------------------------
    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // ------------------------------------------------------------------
    // Handle form submission
    // ------------------------------------------------------------------
    form.addEventListener("submit", async function (event) {
        event.preventDefault();

        const content = (messageInput?.value || "").trim();
        if (!content) return;

        // Disable input while sending
        setSendEnabled(false);

        // Add user message immediately
        appendMessage("user", content);
        messageInput.value = "";

        // Show typing indicator
        showTyping();

        try {
            const payload = await window.VLearn.apiFetch(messageUrl, {
                method: "POST",
                body: JSON.stringify({ content }),
            });

            // Hide typing indicator
            hideTyping();

            // Add agent message
            const agentMsg = payload.agent_message;
            if (agentMsg) {
                appendMessage("agent", agentMsg.content);
            }

            // Check validation result
            const validation = payload.validation;
            if (validation) {
                if (validation.passed) {
                    // Chunk passed!
                    appendSystemMessage("✓ Phần này hoàn thành!");
                    enableNextChunk();

                    // Check if all chunks are done
                    const session = payload.session;
                    if (session && session.status === "completed") {
                        showLessonCompleteModal();
                    } else {
                        showChunkCompleteModal();
                    }
                } else if (validation.missing_points && validation.missing_points.length > 0) {
                    // Show gap badge
                    const gapMsg = appendMessage("agent", 
                        `<strong>💡 Tôi cần làm rõ:</strong> ${validation.missing_points.join(", ")}` +
                        `<div class="gap-badge"><i class="bi bi-exclamation-triangle"></i> Cần bổ sung</div>`
                    );
                    if (gapMsg) {
                        gapMsg.querySelector(".bubble").innerHTML = gapMsg.querySelector(".bubble").innerHTML;
                    }
                }
            }

        } catch (err) {
            console.error(err);
            hideTyping();
            appendMessage("agent", "⚠️ " + err.message);
        } finally {
            // Re-enable input
            setSendEnabled(true);
            messageInput?.focus();
        }
    });

    // ------------------------------------------------------------------
    // Handle next chunk button
    // ------------------------------------------------------------------
    if (nextChunkBtn) {
        nextChunkBtn.addEventListener("click", async function () {
            nextChunkBtn.disabled = true;
            nextChunkBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Đang tải...';

            try {
                const response = await window.VLearn.apiFetch(nextUrl, {
                    method: "POST",
                });

                // Check if session is complete
                if (response.status === "completed") {
                    window.location.href = `/session/${sessionId}/result`;
                } else {
                    // Reload page to show new chunk
                    window.location.reload();
                }
            } catch (err) {
                console.error(err);
                alert("Không thể chuyển phần: " + err.message);
                nextChunkBtn.disabled = false;
                nextChunkBtn.innerHTML = '<i class="bi bi-arrow-right me-1"></i>Sang phần tiếp theo';
            }
        });
    }

    // ------------------------------------------------------------------
    // Enter = send, Shift+Enter = newline
    // ------------------------------------------------------------------
    if (messageInput) {
        messageInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event("submit"));
            }
        });

        // Auto-resize textarea
        messageInput.addEventListener("input", function () {
            this.style.height = "auto";
            this.style.height = Math.min(this.scrollHeight, 120) + "px";
        });
    }

    // ------------------------------------------------------------------
    // Hint chips
    // ------------------------------------------------------------------
    window.insertHint = function (text) {
        if (messageInput) {
            const current = messageInput.value.trim();
            messageInput.value = current ? current + " " + text : text;
            messageInput.focus();
        }
    };

    // ------------------------------------------------------------------
    // System message helper
    // ------------------------------------------------------------------
    function appendSystemMessage(content) {
        if (!chatArea) return;

        const wrapper = document.createElement("div");
        wrapper.className = "msg system";

        wrapper.innerHTML = `
            <div class="bubble">
                <i class="bi bi-check-circle-fill me-2"></i>
                ${content}
            </div>
        `;

        chatArea.appendChild(wrapper);
        chatArea.scrollTop = chatArea.scrollHeight;

        return wrapper;
    }

    // ------------------------------------------------------------------
    // Modal helpers
    // ------------------------------------------------------------------
    function showChunkCompleteModal() {
        const modalEl = document.getElementById("chunkCompleteModal");
        if (modalEl && typeof bootstrap !== "undefined") {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    function showLessonCompleteModal() {
        const modalEl = document.getElementById("lessonCompleteModal");
        if (modalEl && typeof bootstrap !== "undefined") {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }

    // Handle proceed-next-btn in chunk complete modal
    const proceedNextBtn = document.getElementById("proceed-next-btn");
    if (proceedNextBtn) {
        proceedNextBtn.addEventListener("click", function () {
            if (nextChunkBtn) {
                nextChunkBtn.click();
            }
        });
    }

    // ------------------------------------------------------------------
    // Scroll to bottom on load
    // ------------------------------------------------------------------
    if (chatArea) {
        chatArea.scrollTop = chatArea.scrollHeight;
    }

})();
