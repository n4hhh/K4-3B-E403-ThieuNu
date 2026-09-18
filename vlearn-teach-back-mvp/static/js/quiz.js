// quiz.js — Quiz interaction

(function () {
    "use strict";

    const quizData = window.__QUIZ_DATA__;
    if (!quizData) {
        console.warn("No quiz data found");
        return;
    }

    const questions = quizData.questions || [];
    let currentIndex = 0;
    let selectedAnswers = {};
    let answered = {};

    // DOM elements
    const questionEl = document.getElementById("quiz-question");
    const optionsEl = document.getElementById("quiz-options");
    const feedbackEl = document.getElementById("quiz-feedback");
    const feedbackTextEl = document.getElementById("feedback-text");
    const progressBar = document.getElementById("quiz-progress-bar");
    const counterEl = document.getElementById("question-counter");
    const prevBtn = document.getElementById("prev-btn");
    const nextBtn = document.getElementById("next-btn");

    // ------------------------------------------------------------------
    // Render current question
    // ------------------------------------------------------------------
    function renderQuestion() {
        const q = questions[currentIndex];
        if (!q) return;

        // Update counter
        if (counterEl) {
            counterEl.textContent = `Câu ${currentIndex + 1} / ${questions.length}`;
        }

        // Update progress bar
        if (progressBar) {
            const pct = ((currentIndex + 1) / questions.length) * 100;
            progressBar.style.width = `${pct}%`;
        }

        // Update question text
        if (questionEl) {
            questionEl.textContent = q.prompt;
        }

        // Render options
        if (optionsEl) {
            optionsEl.innerHTML = q.options.map((opt, i) => `
                <button type="button" class="quiz-option" data-index="${i}">
                    <span class="option-letter">${String.fromCharCode(65 + i)}.</span>
                    ${escapeHtml(opt)}
                </button>
            `).join("");

            // Attach click handlers
            optionsEl.querySelectorAll(".quiz-option").forEach(btn => {
                btn.addEventListener("click", function () {
                    if (answered[currentIndex]) return;
                    handleOptionClick(parseInt(this.dataset.index), currentIndex);
                });
            });
        }

        // Restore previous answer if any
        if (selectedAnswers[currentIndex] !== undefined && answered[currentIndex]) {
            restoreAnswer(currentIndex, selectedAnswers[currentIndex], q.correct_index);
        }

        // Update navigation buttons
        if (prevBtn) {
            prevBtn.disabled = currentIndex === 0;
        }
        if (nextBtn) {
            nextBtn.disabled = !answered[currentIndex];
            
            // Change text on last question
            if (currentIndex === questions.length - 1) {
                nextBtn.textContent = "Hoàn thành";
                nextBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Hoàn thành';
            } else {
                nextBtn.innerHTML = 'Câu tiếp <i class="bi bi-arrow-right ms-1"></i>';
            }
        }

        // Hide feedback
        if (feedbackEl) {
            feedbackEl.classList.remove("show");
        }
    }

    // ------------------------------------------------------------------
    // Handle option click
    // ------------------------------------------------------------------
    function handleOptionClick(optionIndex, qIndex) {
        const q = questions[qIndex];
        if (!q) return;

        answered[qIndex] = true;
        selectedAnswers[qIndex] = optionIndex;

        // Disable all options
        optionsEl.querySelectorAll(".quiz-option").forEach((btn, i) => {
            btn.disabled = true;
            btn.classList.remove("selected");

            if (i === q.correct_index) {
                btn.classList.add("correct");
            } else if (i === optionIndex && optionIndex !== q.correct_index) {
                btn.classList.add("wrong");
            }
        });

        // Mark selected
        const selectedBtn = optionsEl.querySelector(`[data-index="${optionIndex}"]`);
        if (selectedBtn && optionIndex !== q.correct_index) {
            selectedBtn.classList.add("selected");
        }

        // Show feedback
        if (feedbackEl && feedbackTextEl) {
            const isCorrect = optionIndex === q.correct_index;
            feedbackTextEl.innerHTML = isCorrect
                ? `<strong>✓ Chính xác!</strong> ${q.explanation || ""}`
                : `<strong>✗ Chưa đúng.</strong> ${q.explanation || ""}`;
            feedbackEl.classList.add("show");
        }

        // Enable next button
        if (nextBtn) {
            nextBtn.disabled = false;
        }
    }

    // ------------------------------------------------------------------
    // Restore previous answer (when navigating back)
    // ------------------------------------------------------------------
    function restoreAnswer(qIndex, answerIndex, correctIndex) {
        if (!optionsEl) return;

        optionsEl.querySelectorAll(".quiz-option").forEach((btn, i) => {
            btn.disabled = true;

            if (i === correctIndex) {
                btn.classList.add("correct");
            } else if (i === answerIndex) {
                if (answerIndex === correctIndex) {
                    btn.classList.add("correct");
                } else {
                    btn.classList.add("wrong");
                }
            }
        });

        // Show feedback again
        if (feedbackEl && feedbackTextEl) {
            const isCorrect = answerIndex === correctIndex;
            feedbackTextEl.innerHTML = isCorrect
                ? `<strong>✓ Chính xác!</strong> ${questions[qIndex].explanation || ""}`
                : `<strong>✗ Chưa đúng.</strong> ${questions[qIndex].explanation || ""}`;
            feedbackEl.classList.add("show");
        }
    }

    // ------------------------------------------------------------------
    // Navigation: Previous
    // ------------------------------------------------------------------
    if (prevBtn) {
        prevBtn.addEventListener("click", function () {
            if (currentIndex > 0) {
                currentIndex--;
                renderQuestion();
            }
        });
    }

    // ------------------------------------------------------------------
    // Navigation: Next
    // ------------------------------------------------------------------
    if (nextBtn) {
        nextBtn.addEventListener("click", function () {
            if (!answered[currentIndex]) return;

            if (currentIndex < questions.length - 1) {
                currentIndex++;
                renderQuestion();
            } else {
                // Last question - show results
                showResults();
            }
        });
    }

    // ------------------------------------------------------------------
    // Show final results
    // ------------------------------------------------------------------
    function showResults() {
        let correct = 0;
        questions.forEach((q, i) => {
            if (selectedAnswers[i] === q.correct_index) {
                correct++;
            }
        });

        const score = Math.round((correct / questions.length) * 100);
        const passingScore = 70;

        // Create results modal
        const resultsHtml = `
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-body text-center py-5">
                        <div class="mascot-stage mx-auto mb-3" style="width: 120px; height: 120px; ${score >= passingScore ? 'background: linear-gradient(135deg, #ffd700, #ffa500);' : 'background: linear-gradient(135deg, var(--vl-pink-100), var(--vl-pink-200));'}">
                            <span style="font-size: 4rem;">${score >= passingScore ? '🏆' : '📚'}</span>
                        </div>
                        <h3 class="mb-3">${score >= passingScore ? 'Chúc mừng bạn!' : 'Cố gắng hơn nhé!'}</h3>
                        <div class="xp-badge mx-auto mb-3" style="${score >= passingScore ? '' : 'background: var(--vl-pink-500); box-shadow: 0 4px 0 var(--vl-pink-700);'}">
                            <i class="bi bi-star-fill"></i>
                            ${score}% — ${correct}/${questions.length} câu đúng
                        </div>
                        <p class="text-muted mb-4">
                            ${score >= passingScore 
                                ? 'Bạn đã nắm vững kiến thức của bài học!' 
                                : 'Hãy ôn lại bài học và thử lại quiz nhé!'}
                        </p>
                        <div class="d-flex gap-2 justify-content-center">
                            <a href="/" class="btn btn-outline-secondary">
                                <i class="bi bi-house me-1"></i> Trang chủ
                            </a>
                            ${score < passingScore 
                                ? `<a href="javascript:location.reload()" class="btn btn-primary">
                                    <i class="bi bi-arrow-repeat me-1"></i> Thử lại
                                   </a>`
                                : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Create or update modal
        let modalEl = document.getElementById("quizResultsModal");
        if (!modalEl) {
            modalEl = document.createElement("div");
            modalEl.className = "modal fade";
            modalEl.id = "quizResultsModal";
            modalEl.tabIndex = -1;
            modalEl.innerHTML = `<div class="modal-dialog modal-dialog-centered">${resultsHtml.split('modal-dialog modal-dialog-centered">')[1].split("</div>")[0]}</div>`;
            document.body.appendChild(modalEl);
        } else {
            modalEl.querySelector(".modal-dialog").outerHTML = resultsHtml;
        }

        // Show modal
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }

    // ------------------------------------------------------------------
    // Escape HTML helper
    // ------------------------------------------------------------------
    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    // ------------------------------------------------------------------
    // Initialize
    // ------------------------------------------------------------------
    if (questions.length > 0) {
        renderQuestion();
    }

})();
