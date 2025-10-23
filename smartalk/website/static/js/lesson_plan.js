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
        const quizType = button.dataset.quizType;
        if (quizType === 'fill-in') {
            initFillInQuiz(button);
        } else if (quizType === 'multiple-choice') {
            initMultipleChoiceQuiz(button);
        }
    });

    // Find all 'match' containers and initialize them
    const matchContainers = document.querySelectorAll('[data-match-container]');
    matchContainers.forEach(initMatchingExercise);

    // Find all 'random' buttons and initialize them
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
 * 5. MODULE: Matching Exercise
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
 * 6. MODULE: Random Generator
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
}
