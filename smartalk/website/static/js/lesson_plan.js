/**
 * Smartalk Lesson Engine v1.0
 * Un file JavaScript unificato per gestire tutti i moduli interattivi delle lezioni.
 * Questo script gestisce:
 * 1. Accordion (Tendine a comparsa)
 * 2. Navigazione interna con Smooth Scroll
 * 3. Quiz: Fill in the Gaps (con data-answer)
 * 4. Quiz: Multiple Choice (con data-answer)
 * 5. Esercizio: Match the Items (con data-match-id)
 * 6. Esercizio: Random Item Generator (da una lista HTML)
 */

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. SETUP UI DI BASE (Tendine e Navigazione) ---
    setupCollapsibleCards();
    setupPageNavigation();

    // --- 2. SETUP ESERCIZI INTERATTIVI ---
    setupInteractiveExercises();

});

/**
 * 1a. Logica Accordion (Tendine a comparsa)
 * Cerca tutti i '.card-header' e li rende cliccabili
 * per mostrare/nascondere il '.card-content' successivo.
 * Gestisce anche la rotazione di un '.arrow-icon' (se presente).
 * (Unione della logica di content.js e lesson_base.html)
 */
function setupCollapsibleCards() {
    const cardHeaders = document.querySelectorAll('.card-header');
    cardHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('card-content')) {
                // Attiva/disattiva la classe 'show'
                content.classList.toggle('show');

                // Cerca un'icona e la ruota
                const arrowIcon = header.querySelector('.arrow-icon');
                if (arrowIcon) {
                    arrowIcon.style.transform = content.classList.contains('show') ? 'rotate(180deg)' : 'rotate(0deg)';
                }
            }
        });
    });
}

/**
 * 1b. Logica Navigazione Interna (Smooth Scroll)
 * Cerca tutti i '.section-nav-link' e attiva lo smooth scroll
 * verso l'ancora (es. href="#sezione-1").
 * (Da lesson_base.html)
 */
function setupPageNavigation() {
    const navLinks = document.querySelectorAll('.section-nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.currentTarget.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

/**
 * 2. Inizializzatore per tutti gli esercizi
 * Cerca i vari tipi di esercizi nella pagina e collega i bottoni
 * alle funzioni corrette.
 */
function setupInteractiveExercises() {

    // Collega tutti i bottoni "Verifica" dei quiz
    const quizButtons = document.querySelectorAll('[data-quiz-button]');
    quizButtons.forEach(button => {
        button.addEventListener('click', () => {
            const exerciseContainer = button.closest('[data-exercise-container]');
            const quizType = button.dataset.quizType; // "fill-in" o "multiple-choice"

            if (quizType === 'fill-in') {
                checkFillInGaps(exerciseContainer);
            } else if (quizType === 'multiple-choice') {
                checkMultipleChoiceQuiz(exerciseContainer);
            }
        });
    });

    // Inizializza tutti i giochi "Match"
    const matchGames = document.querySelectorAll('[data-match-container]');
    matchGames.forEach(game => initializeMatchingGame(game));

    // Inizializza tutti i generatori "Random"
    const randomButtons = document.querySelectorAll('[data-random-button]');
    randomButtons.forEach(button => initializeRandomGenerator(button));
}


// --- FUNZIONI DEGLI ESERCIZI ---

/**
 * Helper per normalizzare le risposte
 */
function normalizeAnswer(str) {
    return str.toLowerCase().trim().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, ' ');
}

/**
 * 3. TIPO ESERCIZIO: Fill in the Gaps
 * Controlla tutti gli input in un blocco.
 * HTML richiesto:
 * <div data-exercise-container>
 * <input type="text" data-answer="risposta corretta">
 * <span class="feedback"></span>
 * ...
 * <button data-quiz-button data-quiz-type="fill-in">Verifica</button>
 * <div class="quiz-summary"></div>
 * </div>
 */
function checkFillInGaps(exerciseContainer) {
    const inputs = exerciseContainer.querySelectorAll('input[data-answer]');
    let score = 0;

    inputs.forEach(input => {
        const correctAnswer = normalizeAnswer(input.dataset.answer);
        const userAnswer = normalizeAnswer(input.value);
        const feedbackEl = input.nextElementSibling; // Cerca un '.feedback'

        input.classList.remove('correct', 'incorrect');
        if (feedbackEl) feedbackEl.textContent = '';

        if (userAnswer === correctAnswer) {
            input.classList.add('correct');
            if (feedbackEl) feedbackEl.textContent = '✔️';
            score++;
        } else {
            input.classList.add('incorrect');
            if (feedbackEl) feedbackEl.textContent = `❌ (Corretta: ${input.dataset.answer})`;
        }
    });

    const summaryEl = exerciseContainer.querySelector('.quiz-summary');
    if (summaryEl) {
        summaryEl.textContent = `Punteggio: ${score} / ${inputs.length}`;
    }
}

/**
 * 4. TIPO ESERCIZIO: Multiple Choice
 * Controlla tutti i gruppi di radio button.
 * HTML richiesto:
 * <div data-exercise-container>
 * <div class="question-item" data-answer="valore_corretto">
 * <input type="radio" name="q1" value="valore_1">
 * <input type="radio" name="q1" value="valore_corretto">
 * <span class="feedback"></span>
 * </div>
 * ...
 * <button data-quiz-button data-quiz-type="multiple-choice">Verifica</button>
 * <div class="quiz-summary"></div>
 * </div>
 */
function checkMultipleChoiceQuiz(exerciseContainer) {
    const questions = exerciseContainer.querySelectorAll('.question-item[data-answer]');
    let score = 0;

    questions.forEach(q => {
        const correctAnswer = q.dataset.answer;
        const feedbackEl = q.querySelector('.feedback');
        const selectedRadio = q.querySelector('input[type="radio"]:checked');

        if (feedbackEl) feedbackEl.textContent = '';

        if (selectedRadio) {
            if (selectedRadio.value === correctAnswer) {
                if (feedbackEl) feedbackEl.textContent = '✔️ Corretto!';
                feedbackEl.classList.add('correct');
                feedbackEl.classList.remove('incorrect');
                score++;
            } else {
                if (feedbackEl) feedbackEl.textContent = `❌ Errato.`;
                feedbackEl.classList.add('incorrect');
                feedbackEl.classList.remove('correct');
            }
        } else {
            if (feedbackEl) feedbackEl.textContent = '⚠️ Seleziona una risposta.';
            feedbackEl.classList.add('incorrect');
            feedbackEl.classList.remove('correct');
        }
    });

    const summaryEl = exerciseContainer.querySelector('.quiz-summary');
    if (summaryEl) {
        summaryEl.textContent = `Punteggio: ${score} / ${questions.length}`;
    }
}

/**
 * 5. TIPO ESERCIZIO: Match the Items
 * Permette di abbinare due elementi (es. parola e definizione).
 * HTML richiesto:
 * <div data-match-container>
 * <div class="match-feedback"></div>
 * <div class="match-group-a">
 * <div class="match-item" data-match-id="1">Parola A</div>
 * <div class="match-item" data-match-id="2">Parola B</div>
 * </div>
 * <div class="match-group-b">
 * <div class="match-item" data-match-id="2">Definizione B</div>
 * <div class="match-item" data-match-id="1">Definizione A</div>
 * </div>
 * </div>
 */
function initializeMatchingGame(matchContainer) {
    let selectedA = null;
    let selectedB = null;
    const feedbackEl = matchContainer.querySelector('.match-feedback');
    const groupA = matchContainer.querySelector('.match-group-a');
    const groupB = matchContainer.querySelector('.match-group-b');
    const totalMatches = groupA.querySelectorAll('.match-item').length;
    let correctMatches = 0;

    const clearSelections = () => {
        if (selectedA) selectedA.classList.remove('selected');
        if (selectedB) selectedB.classList.remove('selected');
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
            if (feedbackEl) feedbackEl.textContent = 'Corretto!';
            correctMatches++;
        } else {
            if (feedbackEl) feedbackEl.textContent = 'Errato, riprova.';
            selectedA.classList.add('error');
            selectedB.classList.add('error');
            setTimeout(() => {
                selectedA.classList.remove('error');
                selectedB.classList.remove('error');
                clearSelections();
            }, 800);
        }

        if (correctMatches === totalMatches) {
            if (feedbackEl) feedbackEl.textContent = 'Ottimo! Esercizio completato!';
        }

        // Pulisci per il prossimo tentativo (se non è stato un errore)
        if (selectedA && !selectedA.classList.contains('error')) {
            clearSelections();
        }
    };

    groupA.querySelectorAll('.match-item').forEach(item => {
        item.addEventListener('click', () => {
            if (item.classList.contains('matched')) return;
            if (selectedA) selectedA.classList.remove('selected');
            item.classList.add('selected');
            selectedA = item;
            checkMatch();
        });
    });

    groupB.querySelectorAll('.match-item').forEach(item => {
        item.addEventListener('click', () => {
            if (item.classList.contains('matched')) return;
            if (selectedB) selectedB.classList.remove('selected');
            item.classList.add('selected');
            selectedB = item;
            checkMatch();
        });
    });
}

/**
 * 6. TIPO ESERCIZIO: Random Item Generator
 * Mostra un elemento a caso da una lista nascosta.
 * HTML richiesto:
 * <div data-random-container>
 * <div id="display-area" class="random-display">...</div>
 * <button data-random-button data-source-list="#lista-domande">Genera Domanda</button>
 *
 * <ul id="lista-domande" style="display: none;">
 * <li>Domanda 1</li>
 * <li>Domanda 2</li>
 * </ul>
 * </div>
 */
function initializeRandomGenerator(randomButton) {
    const sourceListSelector = randomButton.dataset.sourceList;
    const sourceList = document.querySelector(sourceListSelector);

    // Trova l'area di display (deve essere dentro lo stesso container)
    const container = randomButton.closest('[data-random-container]');
    const displayArea = container.querySelector('.random-display');

    if (!sourceList || !displayArea) {
        console.error("Generatore Random: mancano 'sourceList' o 'displayArea'.");
        return;
    }

    const items = Array.from(sourceList.children); // <li> o <div>

    randomButton.addEventListener('click', () => {
        if (items.length === 0) {
            displayArea.textContent = 'Nessun elemento da mostrare.';
            return;
        }
        const randomIndex = Math.floor(Math.random() * items.length);
        // Usiamo innerHTML per copiare anche eventuali stili/strutture
        displayArea.innerHTML = items[randomIndex].innerHTML;
    });
}

// ===================================
//  ALTRI MODULI (es. AI, TTS, ecc.)
// ===================================
//
// Qui potremmo aggiungere le funzioni AI (come 'generateSalaryScript')
// o il Text-to-Speech, ma le lasciamo fuori per ora
// per concentrarci sui TIPI DI ESERCIZIO come richiesto.
//
// ===================================