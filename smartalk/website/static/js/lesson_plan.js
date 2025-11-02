/**
 * ===================================================================
 * SMARTALK LESSON ENGINE v2.0
 * * This is the unified JavaScript file for the entire site.
 * It contains all generic modules for interactivity.
 * * Modules only activate if they find the corresponding HTML
 * elements on the page (e.g., '.card-header', '[data-quiz-button]').
 * ===================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize core UI modules (present on most pages)
    // This covers priority 1 (lesson-plans.html page)
    initBaseUI();

    // Initialize interactive modules (present only in lessons)
    // This covers priority 2 (generalization)
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
 * (Unified logic from both legacy files)
 */
function initAccordions() {
    const cardHeaders = document.querySelectorAll('.card-header');
    cardHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('card-content')) {
                content.classList.toggle('show');

                // Also handle the arrow rotation (logic from File 31)
                const arrow = header.querySelector('.arrow-icon');
                if (arrow) {
                    arrow.style.transform = content.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
                }
            } else {
                console.warn("No .card-content found after this header:", header);
            }
        });

        // Set initial state (logic from File 31)
        const content = header.nextElementSibling;
        if (content && content.classList.contains('card-content') && content.classList.contains('show')) {
            const arrow = header.querySelector('.arrow-icon');
            if (arrow) arrow.style.transform = 'rotate(180deg)';
        }
    });
}

/**
 * 2. MODULE: Page Navigation (Smooth Scroll & Active Highlight)
 * Handles smooth scrolling for '.section-nav-link' links
 * and highlights the active link based on scroll (logic from File 32).
 */
function initPageNavigation() {
    const navLinks = document.querySelectorAll('.section-nav-link');
    const sections = document.querySelectorAll('main section[id]');

    if (navLinks.length === 0) return; // Nothing to do

    // 2a. Click Handling (Smooth Scroll)
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.currentTarget.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                // Compute correct position considering fixed header (64px)
                // and sticky navigation (which sticks at 64px)
                const offset = 64;
                const bodyRect = document.body.getBoundingClientRect().top;
                const elementRect = targetSection.getBoundingClientRect().top;
                const elementPosition = elementRect - bodyRect;
                const offsetPosition = elementPosition - offset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                // Immediately update 'active' class on click
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
            rootMargin: '-80px 0px -40% 0px', // Triggers when the section is near the top of the screen
            threshold: 0
        });

        sections.forEach(section => observer.observe(section));
    }
}


// ===================================
// EXERCISE MODULES (QUIZ, MATCH, RANDOM)
// ===================================

function initInteractiveModules() {
    // Find all quiz buttons and initialize them
    const quizButtons = document.querySelectorAll('[data-quiz-button]');

    quizButtons.forEach(button => {
        // 1. Prova a prendere il tipo dal bottone (per i vecchi esercizi)
        let quizType = button.dataset.quizType;

        // 2. Se non è sul bottone, cerca sul container (per i nuovi esercizi)
        if (!quizType) {
            const container = button.closest('[data-exercise-container]');
            if (container) {
                quizType = container.dataset.quizType;
            }
        }

        // 3. Esegui l'init corretto in base al tipo trovato
        if (quizType === 'fill-in') {
            initFillInQuiz(button);
        } else if (quizType === 'multiple-choice') {
            initMultipleChoiceQuiz(button);
        } else if (quizType === 'dropdown-fill-in') {
            initDropdownFillInQuiz(button);
        } else if (quizType === 'classify') { // <-- Nuovo
            initClassificationExercise(button);
        } else if (quizType === 'sequence') { // <-- Nuovo
            initSequenceExercise(button);
        }
    });

    // Gli altri moduli (match e random) restano invariati
    const matchContainers = document.querySelectorAll('[data-match-container]');
    matchContainers.forEach(initMatchingExercise);

    const randomButtons = document.querySelectorAll('[data-random-button]');
    randomButtons.forEach(initRandomGenerator);
}

/**
 * 3. MODULE: Fill-in-the-Gaps Quiz
 * @param {HTMLElement} quizButton - The button that triggered the init.
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
 * @param {HTMLElement} quizButton - The button that triggered the init.
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
                    feedbackEl.textContent = `Wrong. The correct answer was "${correctAnswer}".`;
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
 * @param {HTMLElement} quizButton - The button that triggered the init.
 */
function initDropdownFillInQuiz(quizButton) {
    const container = quizButton.closest('[data-exercise-container]');
    if (!container) return;

    const items = container.querySelectorAll('.dropdown-fill-item'); // Seleziona i <p>
    const summaryEl = container.querySelector('.quiz-summary');

    quizButton.addEventListener('click', () => {
        let correctCount = 0;

        // Reset feedback prima di controllare
        items.forEach(item => {
            const selectElement = item.querySelector('select[data-dropdown-input]');
            const feedbackEl = item.querySelector('.quiz-feedback');
            if (selectElement) selectElement.classList.remove('correct', 'incorrect');
            if (feedbackEl) {
                feedbackEl.textContent = '';
                feedbackEl.className = 'quiz-feedback ml-2'; // Reset classi
            }
        });

        items.forEach(item => {
            const selectElement = item.querySelector('select[data-dropdown-input]');
            const correctAnswer = item.dataset.answer.trim();
            const userAnswer = selectElement.value.trim(); // Non serve toLowerCase se i valori delle option corrispondono esattamente
            const feedbackEl = item.querySelector('.quiz-feedback');

            if (!userAnswer) { // Nessuna selezione
                selectElement.classList.add('incorrect');
                if (feedbackEl) {
                    feedbackEl.textContent = `❌ Select an option. (Correct: ${correctAnswer})`;
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
 * @param {HTMLElement} container - The [data-match-container] element.
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

    function checkMatch() {
        if (!selectedA || !selectedB) return; // Wait for both selections

        if (selectedA.dataset.matchId === selectedB.dataset.matchId) {
            // Correct
            selectedA.classList.add('matched');
            selectedB.classList.add('matched');
            selectedA.classList.remove('selected');
            selectedB.classList.remove('selected');
            selectedA = null;
            selectedB = null;
            matchesMade++;
            if (feedbackEl) feedbackEl.textContent = "Correct!";

            if (matchesMade === totalMatches) {
                if (feedbackEl) feedbackEl.textContent = "Great job, you're done!";
            }
        } else {
            // Wrong
            selectedA.classList.add('error');
            selectedB.classList.add('error');
            if (feedbackEl) feedbackEl.textContent = "Wrong, try again.";
        }

        setTimeout(resetSelections, 500); // Reset after a short delay
    }
}

/**
 * 7. MODULE: Random Generator
 * @param {HTMLElement} randomButton - The [data-random-button] element.
 */
function initRandomGenerator(randomButton) {
    const sourceListSelector = randomButton.dataset.sourceList;
    const sourceList = document.querySelector(sourceListSelector);
    const container = randomButton.closest('[data-random-container]');
    const displayArea = container.querySelector('.random-display');

    if (!sourceList || !displayArea) {
        console.error("Random Generator: missing 'sourceList' or 'displayArea'.");
        return;
    }

    const items = Array.from(sourceList.children);
    let lastIndex = -1; // Avoid immediate repeats

    randomButton.addEventListener('click', () => {
        if (items.length === 0) {
            displayArea.innerHTML = 'No items to display.';
            return;
        }

        let randomIndex = Math.floor(Math.random() * items.length);
        // Simple logic to avoid immediate repetition when there is more than 1 item
        if (items.length > 1 && randomIndex === lastIndex) {
            randomIndex = (randomIndex + 1) % items.length;
        }
        lastIndex = randomIndex;

        displayArea.innerHTML = items[randomIndex].innerHTML;
    });
    /**
     * ===================================================================
     * NUOVI ESERCIZI (CLASSIFICAZIONE E SEQUENZA)
     * ===================================================================
     */

    /**
     * 8. MODULE: Classification (Drag & Drop)
     * @param {HTMLElement} quizButton - The button that triggered the init.
     */
    function initClassificationExercise(quizButton) {
        const container = quizButton.closest('[data-exercise-container]');
        if (!container) return;

        const pool = container.querySelector('[data-classify-pool]');
        const dropzones = container.querySelectorAll('.classify-dropzone');
        const items = container.querySelectorAll('.classify-item');
        const summaryEl = container.querySelector('.quiz-summary');

        let draggedItem = null;

        // Aggiungi listeners per il drag
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

        // Aggiungi listeners per il drop
        dropzones.forEach(zone => {
            zone.addEventListener('dragover', e => {
                e.preventDefault(); // Necessario per permettere il drop
                zone.classList.add('drag-over');
            });
            zone.addEventListener('dragleave', () => {
                zone.classList.remove('drag-over');
            });
            zone.addEventListener('drop', e => {
                e.preventDefault();
                zone.classList.remove('drag-over');
                if (draggedItem) {
                    // Rimuovi il placeholder se è il primo item
                    const placeholder = zone.querySelector('.dropzone-placeholder');
                    if (placeholder) placeholder.style.display = 'none';

                    zone.appendChild(draggedItem);
                }
            });
        });

        // Rendi il pool una dropzone valida per rimettere gli elementi
        pool.addEventListener('dragover', e => {
            e.preventDefault();
            pool.classList.add('drag-over');
        });
        pool.addEventListener('dragleave', () => {
            pool.classList.remove('drag-over');
        });
        pool.addEventListener('drop', e => {
            e.preventDefault();
            pool.classList.remove('drag-over');
            if (draggedItem) {
                pool.appendChild(draggedItem);
            }
        });


        // Logica del bottone "Check"
        quizButton.addEventListener('click', () => {
            let correctCount = 0;
            let totalChecked = 0;

            // Resetta feedback precedente
            items.forEach(item => item.classList.remove('correct', 'incorrect'));

            dropzones.forEach(zone => {
                const correctCategory = zone.dataset.categoryName;
                const itemsInZone = zone.querySelectorAll('.classify-item');

                itemsInZone.forEach(item => {
                    totalChecked++;
                    const itemCategory = item.dataset.correctCategory;
                    if (itemCategory === correctCategory) {
                        item.classList.add('correct');
                        correctCount++;
                    } else {
                        item.classList.add('incorrect');
                    }
                });
            });

            // Controlla gli item rimasti nel pool (sono tutti sbagliati)
            const itemsInPool = pool.querySelectorAll('.classify-item');
            itemsInPool.forEach(item => item.classList.add('incorrect'));

            if (summaryEl) {
                summaryEl.textContent = `Score: ${correctCount} / ${items.length}`;
                if (itemsInPool.length > 0) {
                    summaryEl.textContent += ` (${itemsInPool.length} items not classified)`;
                }
            }
        });
    }

    /**
     * 9. MODULE: Sequence (Ordering)
     * @param {HTMLElement} quizButton - The button that triggered the init.
     */
    function initSequenceExercise(quizButton) {
        const container = quizButton.closest('[data-exercise-container]');
        if (!container) return;

        const list = container.querySelector('[data-sequence-list]');
        const summaryEl = container.querySelector('.quiz-summary');

        let draggedItem = null;

        list.addEventListener('dragstart', e => {
            const target = e.target.closest('.sequence-item');
            if (target) {
                draggedItem = target;
                setTimeout(() => draggedItem.classList.add('dragging'), 0);
            }
        });

        list.addEventListener('dragend', () => {
            if (draggedItem) {
                draggedItem.classList.remove('dragging');
                draggedItem = null;
            }
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

        // Funzione helper per trovare l'elemento dopo cui inserire
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

        // Logica del bottone "Check"
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
}
