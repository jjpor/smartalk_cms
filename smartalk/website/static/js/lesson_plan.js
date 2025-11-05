/**
 * ===================================================================
 * SMARTALK LESSON ENGINE v2.4 (COMPLETE & ROBUST)
 * * This is the unified JavaScript file for the entire site.
 * * It contains all generic modules for interactivity.
 * * INCLUDES: Standard Quizzes, Matching, Random Generator,
 * AND NEW: Classification (Drag & Drop), Sequence (Ordering)
 * ===================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize core UI modules (present on most pages)
    initBaseUI();

    // Initialize interactive modules (present only in lessons)
    initInteractiveModules();
});

// ===================================
// BASE UI MODULE (NAVIGATION & ACCORDION)
// ===================================

function initBaseUI() {
    initAccordions();
    initPageNavigation();
}

/**
 * 1. MODULE: Accordion
 * Finds all '.card-header' elements and makes them clickable
 * to show/hide the following '.card-content'.
 */
function initAccordions() {
    const cardHeaders = document.querySelectorAll('.card-header');
    cardHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('card-content')) {
                content.classList.toggle('show');
                
                // Handle arrow rotation
                const arrow = header.querySelector('.arrow-icon');
                if (arrow) {
                    arrow.style.transform = content.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
                }
            }
        });
        
        // Set initial state for already open cards
        const content = header.nextElementSibling;
        if (content && content.classList.contains('card-content') && content.classList.contains('show')) {
            const arrow = header.querySelector('.arrow-icon');
            if (arrow) arrow.style.transform = 'rotate(180deg)';
        }
    });
}

/**
 * 2. MODULE: Page Navigation (Smooth Scroll & Active Highlight)
 * Handles smooth scrolling for '.section-nav-link' links.
 */
function initPageNavigation() {
    const navLinks = document.querySelectorAll('.section-nav-link');
    const sections = document.querySelectorAll('main section[id]');

    if (navLinks.length === 0) return;

    // 2a. Click Handling (Smooth Scroll)
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.currentTarget.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                const offset = 64; // Header height
                const bodyRect = document.body.getBoundingClientRect().top;
                const elementRect = targetSection.getBoundingClientRect().top;
                const elementPosition = elementRect - bodyRect;
                const offsetPosition = elementPosition - offset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                // Immediately update 'active' class
                navLinks.forEach(l => l.classList.remove('active'));
                e.currentTarget.classList.add('active');
            }
        });
    });

    // 2b. Scroll Handling (Active Highlight)
    if (sections.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    navLinks.forEach(link => {
                        const isActive = link.getAttribute('href') === `#${entry.target.id}`;
                        link.classList.toggle('active', isActive);
                    });
                }
            });
        }, {
            rootMargin: '-80px 0px -40% 0px',
            threshold: 0
        });

        sections.forEach(section => observer.observe(section));
    }
}


// ===================================
// EXERCISE MODULES INITIALIZER
// ===================================

function initInteractiveModules() {
    // Find all quiz buttons and initialize them based on their type
    const quizButtons = document.querySelectorAll('[data-quiz-button]');
    quizButtons.forEach(button => {
        // ROBUST TYPE DETECTION:
        // 1. Try to get type from the button itself (old style macros)
        let quizType = button.dataset.quizType;
        
        // 2. If not found, try to get type from the container (new style macros)
        if (!quizType) {
            const container = button.closest('[data-exercise-container]');
            if (container) {
                quizType = container.dataset.quizType;
            }
        }

        // 3. Initialize the correct module
        if (quizType === 'fill-in') {
            initFillInQuiz(button);
        } else if (quizType === 'multiple-choice') {
            initMultipleChoiceQuiz(button);
        } else if (quizType === 'dropdown-fill-in') {
            initDropdownFillInQuiz(button);
        } else if (quizType === 'classify') {
            initClassificationExercise(button);
        } else if (quizType === 'sequence') {
            initSequenceExercise(button);
        }
    });

    // Initialize other standalone modules
    document.querySelectorAll('[data-match-container]').forEach(initMatchingExercise);
    document.querySelectorAll('[data-random-button]').forEach(initRandomGenerator);
}


/**
 * 3. MODULE: Fill-in-the-Gaps Quiz
 */
function initFillInQuiz(quizButton) {
    const container = quizButton.closest('[data-exercise-container]');
    if (!container) return;

    const inputs = container.querySelectorAll('.quiz-input-text');
    const summaryEl = container.querySelector('.quiz-summary');

    quizButton.addEventListener('click', () => {
        let correctCount = 0;
        inputs.forEach(input => {
            const answer = input.dataset.answer.trim();
            const feedbackEl = input.nextElementSibling && input.nextElementSibling.matches('.quiz-feedback')
                ? input.nextElementSibling
                : null;

            if (input.value.trim().toLowerCase() === answer.toLowerCase()) {
                input.classList.remove('incorrect');
                input.classList.add('correct');
                if (feedbackEl) feedbackEl.textContent = '✓';
                correctCount++;
            } else {
                input.classList.remove('correct');
                input.classList.add('incorrect');
                if (feedbackEl) feedbackEl.textContent = `✗ (Answer: ${answer})`;
            }
        });

        if (summaryEl) {
            summaryEl.textContent = `Score: ${correctCount} / ${inputs.length}`;
        }
    });
}

/**
 * 4. MODULE: Multiple Choice Quiz
 */
function initMultipleChoiceQuiz(quizButton) {
    const container = quizButton.closest('[data-exercise-container]');
    if (!container) return;
    
    const questions = container.querySelectorAll('.quiz-question-item');
    const summaryEl = container.querySelector('.quiz-summary');

    quizButton.addEventListener('click', () => {
        let correctCount = 0;
        questions.forEach(question => {
            const correctAnswer = question.dataset.answer;
            const selectedInput = question.querySelector('input:checked');
            const feedbackEl = question.querySelector('.quiz-feedback');

            if (selectedInput) {
                if (selectedInput.value === correctAnswer) {
                    feedbackEl.textContent = 'Correct!';
                    feedbackEl.className = 'quiz-feedback correct';
                    correctCount++;
                } else {
                    feedbackEl.textContent = `Wrong.`;
                    feedbackEl.className = 'quiz-feedback incorrect';
                }
            } else {
                feedbackEl.textContent = 'Please select an answer.';
                feedbackEl.className = 'quiz-feedback incorrect';
            }
        });

        if (summaryEl) {
            summaryEl.textContent = `Score: ${correctCount} / ${questions.length}`;
        }
    });
}

/**
 * 5. MODULE: Dropdown Fill-in Quiz
 */
function initDropdownFillInQuiz(quizButton) {
    const container = quizButton.closest('[data-exercise-container]');
    if (!container) return;

    const items = container.querySelectorAll('.dropdown-fill-item');
    const summaryEl = container.querySelector('.quiz-summary');

    quizButton.addEventListener('click', () => {
        let correctCount = 0;

        items.forEach(item => {
            const selectElement = item.querySelector('select[data-dropdown-input]');
            const correctAnswer = item.dataset.answer.trim();
            const userAnswer = selectElement.value.trim();
            const feedbackEl = item.querySelector('.quiz-feedback');

            // Reset classes
            selectElement.classList.remove('correct', 'incorrect');
            if (feedbackEl) {
                 feedbackEl.textContent = '';
                 feedbackEl.className = 'quiz-feedback ml-2';
            }

            if (!userAnswer) {
                selectElement.classList.add('incorrect');
                if (feedbackEl) {
                     feedbackEl.textContent = `❌ Select an option.`;
                     feedbackEl.classList.add('incorrect');
                }
            } else if (userAnswer === correctAnswer) {
                selectElement.classList.add('correct');
                if (feedbackEl) feedbackEl.textContent = '✅';
                correctCount++;
            } else {
                selectElement.classList.add('incorrect');
                if (feedbackEl) {
                    feedbackEl.textContent = `❌ (Correct: ${correctAnswer})`;
                    feedbackEl.classList.add('incorrect');
                }
            }
        });

        if (summaryEl) {
            summaryEl.textContent = `Score: ${correctCount} / ${items.length}`;
        }
    });
}

/**
 * 6. MODULE: Matching Exercise
 */
function initMatchingExercise(container) {
    let selectedA = null;
    let selectedB = null;
    const groupA = container.querySelector('.match-group-a');
    const groupB = container.querySelector('.match-group-b');
    const feedbackEl = container.querySelector('.match-feedback');
    const totalMatches = groupA.children.length;
    let matchesMade = 0;

    const resetSelections = () => {
        selectedA?.classList.remove('selected', 'error');
        selectedB?.classList.remove('selected', 'error');
        selectedA = null;
        selectedB = null;
    };

    const checkMatch = () => {
        if (!selectedA || !selectedB) return;

        if (selectedA.dataset.matchId === selectedB.dataset.matchId) {
            selectedA.classList.add('matched');
            selectedB.classList.add('matched');
            selectedA.classList.remove('selected');
            selectedB.classList.remove('selected');
            selectedA = null;
            selectedB = null;
            matchesMade++;
            if (feedbackEl) feedbackEl.textContent = matchesMade === totalMatches ? "Great job, all matched!" : "Correct match!";
        } else {
            selectedA.classList.add('error');
            selectedB.classList.add('error');
            if (feedbackEl) feedbackEl.textContent = "Wrong, try again.";
        }
        setTimeout(resetSelections, 500);
    };

    groupA.addEventListener('click', e => {
        const item = e.target.closest('.match-item');
        if (!item || item.classList.contains('matched')) return;
        groupA.querySelectorAll('.match-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
        selectedA = item;
        checkMatch();
    });

    groupB.addEventListener('click', e => {
        const item = e.target.closest('.match-item');
        if (!item || item.classList.contains('matched')) return;
        groupB.querySelectorAll('.match-item').forEach(i => i.classList.remove('selected'));
        item.classList.add('selected');
        selectedB = item;
        checkMatch();
    });
}

/**
 * 7. MODULE: Random Generator
 */
function initRandomGenerator(randomButton) {
    const sourceListSelector = randomButton.dataset.sourceList;
    const sourceList = document.querySelector(sourceListSelector);
    const container = randomButton.closest('[data-random-container]');
    const displayArea = container.querySelector('.random-display');

    if (!sourceList || !displayArea) return;

    const items = Array.from(sourceList.children);
    let lastIndex = -1;

    randomButton.addEventListener('click', () => {
        if (items.length === 0) {
            displayArea.innerHTML = 'No items.';
            return;
        }
        let randomIndex = Math.floor(Math.random() * items.length);
        if (items.length > 1 && randomIndex === lastIndex) {
            randomIndex = (randomIndex + 1) % items.length;
        }
        lastIndex = randomIndex;
        displayArea.innerHTML = items[randomIndex].innerHTML;
    });
}


// ===================================
// NEW MODULES (ADDED v2.4)
// ===================================

/**
 * 8. MODULE: Classification (Drag & Drop)
 */
function initClassificationExercise(quizButton) {
    const container = quizButton.closest('[data-exercise-container]');
    if (!container) return;

    const pool = container.querySelector('[data-classify-pool]');
    const dropzones = container.querySelectorAll('.classify-dropzone');
    const items = container.querySelectorAll('.classify-item');
    const summaryEl = container.querySelector('.quiz-summary');

    let draggedItem = null;

    // Drag Events for Items
    items.forEach(item => {
        item.addEventListener('dragstart', () => {
            draggedItem = item;
            setTimeout(() => item.classList.add('dragging'), 0);
        });
        item.addEventListener('dragend', () => {
            draggedItem.classList.remove('dragging');
            draggedItem = null;
        });
    });

    // Drop Events for Zones (including pool to return items)
    [...dropzones, pool].forEach(zone => {
        zone.addEventListener('dragover', e => {
            e.preventDefault();
            zone.classList.add('drag-over');
        });
        zone.addEventListener('dragleave', () => {
            zone.classList.remove('drag-over');
        });
        zone.addEventListener('drop', e => {
            e.preventDefault();
            zone.classList.remove('drag-over');
            if (draggedItem) {
                // If dropping into a category zone, hide its placeholder
                if (zone.classList.contains('classify-dropzone')) {
                    const placeholder = zone.querySelector('.dropzone-placeholder');
                    if (placeholder) placeholder.style.display = 'none';
                }
                zone.appendChild(draggedItem);
            }
        });
    });

    // Check Logic
    quizButton.addEventListener('click', () => {
        let correctCount = 0;
        
        // Reset previous feedback
        items.forEach(item => item.classList.remove('correct', 'incorrect'));

        // Check items in category zones
        dropzones.forEach(zone => {
            const correctCategory = zone.dataset.categoryName;
            zone.querySelectorAll('.classify-item').forEach(item => {
                if (item.dataset.correctCategory === correctCategory) {
                    item.classList.add('correct');
                    correctCount++;
                } else {
                    item.classList.add('incorrect');
                }
            });
        });
        
        // Items still in pool are incorrect
        pool.querySelectorAll('.classify-item').forEach(item => item.classList.add('incorrect'));

        if (summaryEl) {
            summaryEl.textContent = `Score: ${correctCount} / ${items.length}`;
        }
    });
}

/**
 * 9. MODULE: Sequence (Ordering)
 */
function initSequenceExercise(quizButton) {
    const container = quizButton.closest('[data-exercise-container]');
    if (!container) return;

    const list = container.querySelector('[data-sequence-list]');
    const summaryEl = container.querySelector('.quiz-summary');
    let draggedItem = null;

    list.addEventListener('dragstart', e => {
        draggedItem = e.target.closest('.sequence-item');
        if (draggedItem) setTimeout(() => draggedItem.classList.add('dragging'), 0);
    });

    list.addEventListener('dragend', () => {
        if (draggedItem) draggedItem.classList.remove('dragging');
        draggedItem = null;
    });

    list.addEventListener('dragover', e => {
        e.preventDefault();
        const afterElement = getDragAfterElement(list, e.clientY);
        if (draggedItem) {
            if (afterElement == null) {
                list.appendChild(draggedItem);
            } else {
                list.insertBefore(draggedItem, afterElement);
            }
        }
    });

    // Helper to find insertion point
    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.sequence-item:not(.dragging)')];
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    // Check Logic
    quizButton.addEventListener('click', () => {
        const items = list.querySelectorAll('.sequence-item');
        let correctCount = 0;
        
        items.forEach((item, index) => {
            const correctOrder = parseInt(item.dataset.correctOrder, 10);
            const currentOrder = index + 1;
            const feedbackEl = item.querySelector('.quiz-feedback');
            
            if (correctOrder === currentOrder) {
                item.classList.remove('incorrect');
                item.classList.add('correct');
                if (feedbackEl) feedbackEl.textContent = '✅';
                correctCount++;
            } else {
                item.classList.remove('correct');
                item.classList.add('incorrect');
                if (feedbackEl) feedbackEl.textContent = '❌';
            }
        });

        if (summaryEl) {
            summaryEl.textContent = `Score: ${correctCount} / ${items.length}`;
        }
    });
}