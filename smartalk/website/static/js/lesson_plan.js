/**
 * ===================================================================
 * SMARTALK LESSON ENGINE v2.0
 * * Questo è il file JavaScript unificato per l'intero sito.
 * Contiene tutti i moduli generici per l'interattività.
 * * I moduli si attivano solo se trovano gli elementi HTML 
 * corrispondenti sulla pagina (es. '.card-header', '[data-quiz-button]').
 * ===================================================================
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // Inizializza i moduli UI di base (presenti in quasi tutte le pagine)
    // Questo copre la priorità 1 (pagina lesson-plans.html)
    initBaseUI();

    // Inizializza i moduli interattivi (presenti solo nelle lezioni)
    // Questo copre la priorità 2 (generalizzazione)
    initInteractiveModules();

});

// ===================================
// MODULO UI DI BASE (NAVIGAZIONE E ACCORDION)
// ===================================

function initBaseUI() {
    initAccordions();
    initPageNavigation();
}

/**
 * 1. MODULO: Accordion (Tendine)
 * Cerca tutti i '.card-header' e li rende cliccabili
 * per mostrare/nascondere il '.card-content' successivo.
 * (Logica unificata da entrambi i vecchi file)
 */
function initAccordions() {
    const cardHeaders = document.querySelectorAll('.card-header');
    cardHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('card-content')) {
                content.classList.toggle('show');
                
                // Gestisce anche la rotazione dell'icona (logica da File 31)
                const arrow = header.querySelector('.arrow-icon');
                if (arrow) {
                    arrow.style.transform = content.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
                }
            } else {
                console.warn("Nessun .card-content trovato dopo questo header:", header);
            }
        });
        
        // Imposta lo stato iniziale (logica da File 31)
        const content = header.nextElementSibling;
        if (content && content.classList.contains('card-content') && content.classList.contains('show')) {
            const arrow = header.querySelector('.arrow-icon');
            if (arrow) arrow.style.transform = 'rotate(180deg)';
        }
    });
}

/**
 * 2. MODULO: Navigazione Pagina (Smooth Scroll & Active Highlight)
 * Gestisce lo smooth scroll per i link '.section-nav-link'
 * E evidenzia il link attivo in base allo scroll (logica da File 32).
 */
function initPageNavigation() {
    const navLinks = document.querySelectorAll('.section-nav-link');
    const sections = document.querySelectorAll('main section[id]');

    if (navLinks.length === 0) return; // Niente da fare

    // 2a. Gestione Click (Smooth Scroll)
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.currentTarget.getAttribute('href');
            const targetSection = document.querySelector(targetId);

            if (targetSection) {
                // Calcola la posizione corretta tenendo conto dell'header fisso (64px)
                // e della navigazione sticky (che si attacca a 64px)
                const offset = 64; 
                const bodyRect = document.body.getBoundingClientRect().top;
                const elementRect = targetSection.getBoundingClientRect().top;
                const elementPosition = elementRect - bodyRect;
                const offsetPosition = elementPosition - offset;

                window.scrollTo({
                    top: offsetPosition,
                    behavior: 'smooth'
                });

                // Aggiorna subito la classe 'active' al click
                navLinks.forEach(l => l.classList.remove('active'));
                e.currentTarget.classList.add('active');
            }
        });
    });

    // 2b. Gestione Scroll (Active Highlight)
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
            rootMargin: '-80px 0px -40% 0px', // Si attiva quando la sezione è nella parte alta dello schermo
            threshold: 0
        });

        sections.forEach(section => observer.observe(section));
    }
}


// ===================================
// MODULI ESERCIZI (QUIZ, MATCH, RANDOM)
// ===================================

function initInteractiveModules() {
    // Cerca tutti i bottoni quiz e li inizializza
    const quizButtons = document.querySelectorAll('[data-quiz-button]');
    quizButtons.forEach(button => {
        const quizType = button.dataset.quizType;
        if (quizType === 'fill-in') {
            initFillInQuiz(button);
        } else if (quizType === 'multiple-choice') {
            initMultipleChoiceQuiz(button);
        }
    });

    // Cerca tutti i container 'match' e li inizializza
    const matchContainers = document.querySelectorAll('[data-match-container]');
    matchContainers.forEach(initMatchingExercise);

    // Cerca tutti i bottoni 'random' e li inizializza
    const randomButtons = document.querySelectorAll('[data-random-button]');
    randomButtons.forEach(initRandomGenerator);
}


/**
 * 3. MODULO: Quiz Fill-in-the-Gaps
 * @param {HTMLElement} quizButton - Il bottone che ha triggerato l'init.
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
            const feedbackEl = input.nextElementSibling.matches('.quiz-feedback') ? input.nextElementSibling : null;

            if (input.value.trim().toLowerCase() === answer.toLowerCase()) {
                input.classList.remove('incorrect');
                input.classList.add('correct');
                if (feedbackEl) feedbackEl.textContent = '✓';
                correctCount++;
            } else {
                input.classList.remove('correct');
                input.classList.add('incorrect');
                if (feedbackEl) feedbackEl.textContent = `✗ (Risposta: ${answer})`;
            }
        });

        if (summaryEl) {
            summaryEl.textContent = `Punteggio: ${correctCount} / ${inputs.length}`;
        }
    });
}

/**
 * 4. MODULO: Quiz Multiple Choice
 * @param {HTMLElement} quizButton - Il bottone che ha triggerato l'init.
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
                    feedbackEl.textContent = 'Corretto!';
                    feedbackEl.className = 'quiz-feedback correct';
                    correctCount++;
                } else {
                    feedbackEl.textContent = `Sbagliato. La risposta corretta era "${correctAnswer}".`;
                    feedbackEl.className = 'quiz-feedback incorrect';
                }
            } else {
                feedbackEl.textContent = 'Per favore, seleziona una risposta.';
                feedbackEl.className = 'quiz-feedback incorrect';
            }
        });

        if (summaryEl) {
            summaryEl.textContent = `Punteggio: ${correctCount} / ${questions.length}`;
        }
    });
}

/**
 * 5. MODULO: Esercizio Matching
 * @param {HTMLElement} container - Il container [data-match-container].
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
        if (!selectedA || !selectedB) return; // Aspetta entrambe le selezioni

        if (selectedA.dataset.matchId === selectedB.dataset.matchId) {
            // Corretto
            selectedA.classList.add('matched');
            selectedB.classList.add('matched');
            selectedA.classList.remove('selected');
            selectedB.classList.remove('selected');
            selectedA = null;
            selectedB = null;
            matchesMade++;
            if (feedbackEl) feedbackEl.textContent = "Corretto!";
            
            if (matchesMade === totalMatches) {
                if (feedbackEl) feedbackEl.textContent = "Complimenti, hai finito!";
            }
        } else {
            // Sbagliato
            selectedA.classList.add('error');
            selectedB.classList.add('error');
            if (feedbackEl) feedbackEl.textContent = "Sbagliato, riprova.";
        }
        
        setTimeout(resetSelections, 500); // Resetta dopo un breve ritardo
    }
}

/**
 * 6. MODULO: Generatore Random
 * @param {HTMLElement} randomButton - Il bottone [data-random-button].
 */
function initRandomGenerator(randomButton) {
    const sourceListSelector = randomButton.dataset.sourceList;
    const sourceList = document.querySelector(sourceListSelector);
    const container = randomButton.closest('[data-random-container]');
    const displayArea = container.querySelector('.random-display');

    if (!sourceList || !displayArea) {
        console.error("Generatore Random: mancano 'sourceList' o 'displayArea'.");
        return;
    }

    const items = Array.from(sourceList.children);
    let lastIndex = -1; // Per evitare ripetizioni

    randomButton.addEventListener('click', () => {
        if (items.length === 0) {
            displayArea.innerHTML = 'Nessun elemento da mostrare.';
            return;
        }

        let randomIndex = Math.floor(Math.random() * items.length);
        // Semplice logica per evitare la ripetizione immediata se ci sono più di 1 elemento
        if (items.length > 1 && randomIndex === lastIndex) {
            randomIndex = (randomIndex + 1) % items.length;
        }
        lastIndex = randomIndex;
        
        displayArea.innerHTML = items[randomIndex].innerHTML;
    });
}