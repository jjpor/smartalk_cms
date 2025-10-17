document.addEventListener('DOMContentLoaded', () => {
    // --- General UI: Smooth scroll for main section navigation ---
    const mainNavLinks = document.querySelectorAll('.section-nav-link');
    mainNavLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = e.currentTarget.getAttribute('href');
            const targetSection = document.querySelector(targetId);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    // --- General UI: Accordion functionality for expandable cards ---
    const cardHeaders = document.querySelectorAll('.card-header');
    cardHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            if (content && content.classList.contains('card-content')) {
                content.classList.toggle('show');
            }
        });
    });

    // --- General UI: Active link highlighting on scroll ---
    const sections = document.querySelectorAll('main section');
    if (sections.length > 0 && mainNavLinks.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    mainNavLinks.forEach(link => {
                        const isActive = link.getAttribute('href') === `#${entry.target.id}`;
                        link.classList.toggle('active', isActive);
                    });
                }
            });
        }, { rootMargin: '-40% 0px -60% 0px', threshold: 0 });
        sections.forEach(section => observer.observe(section));
    }

    // --- FEATURE: Salary Negotiation AI Generator ---
    const salaryGenerateBtn = document.getElementById('generate-btn');
    if (salaryGenerateBtn) {
        const scenarioInput = document.getElementById('user-scenario');
        const responseContainer = document.getElementById('response-container');
        const responseContent = document.getElementById('response-content');
        const loadingSpinner = document.getElementById('loading-spinner');

        salaryGenerateBtn.addEventListener('click', async () => {
            const userScenario = scenarioInput.value.trim();
            if (!userScenario) {
                alert("Please describe your negotiation scenario.");
                return;
            }
            responseContainer.classList.remove('hidden');
            loadingSpinner.style.display = 'block';
            responseContent.innerHTML = '';
            salaryGenerateBtn.disabled = true;

            try {
                const prompt = `You are a salary negotiation expert. Analyze the user's scenario and provide a detailed, personalized strategy in markdown format with clear headings: 1. **Analysis**, 2. **Strengths to highlight**, 3. **Strategy suggestions**, 4. **Example phrase**, 5. **What to avoid**. Scenario: "${userScenario}"`;
                const payload = { contents: [{ role: "user", parts: [{ text: prompt }] }] };
                const apiKey = ""; // IMPORTANT: Add your Gemini API key here
                const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${apiKey}`;
                const response = await fetch(apiUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!response.ok) throw new Error(`Network error: ${response.statusText}`);
                const result = await response.json();
                const generatedText = result.candidates?.[0]?.content?.parts?.[0]?.text;
                if (generatedText) {
                    responseContent.innerHTML = marked.parse(generatedText);
                } else {
                    throw new Error("Could not generate a valid response.");
                }
            } catch (error) {
                responseContent.innerHTML = `<p class="text-red-500">❌ Error: ${error.message}</p>`;
            } finally {
                loadingSpinner.style.display = 'none';
                salaryGenerateBtn.disabled = false;
            }
        });
    }

    // --- FEATURE: Comparatives & Superlatives AI Generator ---
    const comparativesGenerateBtn = document.getElementById('generate-button');
    if (comparativesGenerateBtn) {
        const topicInput = document.getElementById('topic-input');
        const questionsOutput = document.getElementById('questions-output');
        const loadingSpinner = document.getElementById('loading-spinner');

        comparativesGenerateBtn.addEventListener('click', async () => {
            const topic = topicInput.value.trim();
            if (!topic) {
                questionsOutput.innerHTML = '<p class="text-red-500">Please enter a topic.</p>';
                return;
            }
            questionsOutput.innerHTML = '';
            loadingSpinner.classList.remove('hidden');
            comparativesGenerateBtn.disabled = true;

            try {
                const prompt = `Generate a list of 15 questions to practice comparatives and superlatives on the topic "${topic}". Include 5 questions with comparatives, 5 with superlatives, and 5 with "as...as". Do not include explanations, just the list.`;
                const payload = { contents: [{ parts: [{ text: prompt }] }] };
                const apiKey = ""; // IMPORTANT: Add your Gemini API key here
                const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${apiKey}`;
                const response = await fetch(apiUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
                const result = await response.json();
                const text = result.candidates?.[0]?.content?.parts?.[0]?.text;
                if (text) {
                    const questions = text.split('\n').filter(q => q.trim().length > 0);
                    const formattedQuestions = questions.map(q => `<li class="mt-1">${q.replace(/^\d+\.\s*/, '')}</li>`).join('');
                    questionsOutput.innerHTML = `<ul class="list-disc list-inside space-y-2">${formattedQuestions}</ul>`;
                } else {
                    throw new Error("Unable to generate questions.");
                }
            } catch (error) {
                questionsOutput.innerHTML = `<p class="text-red-500">Error: ${error.message}</p>`;
            } finally {
                loadingSpinner.classList.add('hidden');
                comparativesGenerateBtn.disabled = false;
            }
        });
    }
    
    // --- FEATURE: Leadership AI Scenario Generator ---
    const getAdviceBtn = document.getElementById('get-advice-btn');
    if (getAdviceBtn) {
        const scenarioInput = document.getElementById('scenario-input');
        const responseContainer = document.getElementById('response-container');
        const scenarioResponse = document.getElementById('scenario-response');
        const loadingSpinner = document.getElementById('loading-spinner');

        getAdviceBtn.addEventListener('click', async () => {
            const prompt = scenarioInput.value.trim();
            if (!prompt) {
                scenarioResponse.textContent = "Please enter a scenario.";
                responseContainer.classList.remove('hidden');
                return;
            }
            loadingSpinner.classList.remove('hidden');
            getAdviceBtn.disabled = true;
            responseContainer.classList.remove('hidden');
            scenarioResponse.textContent = "The AI is thinking...";

            try {
                const fullPrompt = `Act as an expert leadership coach. Provide practical, empathetic advice on handling this scenario: "${prompt}"`;
                const payload = { contents: [{ parts: [{ text: fullPrompt }] }] };
                const apiKey = ""; // IMPORTANT: Add your Gemini API key here
                const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${apiKey}`;
                const response = await fetch(apiUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
                const result = await response.json();
                const text = result.candidates?.[0]?.content?.parts?.[0]?.text;
                if (text) {
                    scenarioResponse.textContent = text;
                } else {
                    throw new Error("Invalid API response structure.");
                }
            } catch (error) {
                scenarioResponse.textContent = `Sorry, there was an error: ${error.message}`;
            } finally {
                loadingSpinner.classList.add('hidden');
                getAdviceBtn.disabled = false;
            }
        });
    }

    // --- FEATURE: Text-to-Speech ---
    async function textToSpeech(text) {
        // Stop any currently playing audio
        const existingPlayer = document.getElementById('audio-player');
        if (existingPlayer) {
            existingPlayer.pause();
            existingPlayer.currentTime = 0;
        }

        try {
            const payload = {
                input: { text: text },
                voice: { languageCode: 'en-US', name: 'en-US-Studio-O' }, // A pleasant, professional voice
                audioConfig: { audioEncoding: 'MP3' }
            };
            const apiKey = ""; // IMPORTANT: Add your Google Cloud Text-to-Speech API key here
            const apiUrl = `https://texttospeech.googleapis.com/v1/text:synthesize?key=${apiKey}`;
            
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
            
            const result = await response.json();
            const audioContent = result.audioContent;

            if (audioContent) {
                const audioSrc = `data:audio/mp3;base64,${audioContent}`;
                let player = document.getElementById('audio-player');
                if (!player) {
                    player = new Audio();
                    player.id = 'audio-player';
                    document.body.appendChild(player);
                }
                player.src = audioSrc;
                player.play();
            } else {
                throw new Error("No audio content in response.");
            }
        } catch (error) {
            console.error("Text-to-Speech Error:", error);
            alert("Sorry, the text-to-speech feature is currently unavailable.");
        }
    }
    // Make the function globally available for the onclick attribute
    window.textToSpeech = textToSpeech;
});
    // ===========================
    //  INTERACTIVE QUIZ LOGIC
    // ===========================
function sanitize(value) {
    return value.toLowerCase().trim().replace(/[^a-z0-9\s]/g, '');
}

function checkQuiz(quizId) {
    const form = document.getElementById(quizId);
    if (!form) return;
    let score = 0;
    let total = 0;

    const questions = form.querySelectorAll('.question-item');
    questions.forEach((item, index) => {
        const qNum = index + 1;
        const radios = item.querySelectorAll(`input[name="q${qNum}"]`);
        const feedbackEl = document.getElementById(`feedback${qNum}`);
        const correctAnswerIndex = parseInt(item.getAttribute('data-answer'));
        
        let selectedValue = null;
        radios.forEach(radio => {
            if (radio.checked) {
                selectedValue = parseInt(radio.value);
            }
        });
        
        total++;
        
        if (feedbackEl) {
            feedbackEl.textContent = '';
            feedbackEl.className = 'feedback mt-2';
            
            if (selectedValue === null) {
                feedbackEl.textContent = 'Please select an option.';
                feedbackEl.classList.add('incorrect');
            } else if (selectedValue === correctAnswerIndex) {
                feedbackEl.textContent = 'Correct!';
                feedbackEl.classList.add('correct');
                score++;
            } else {
                const options = item.querySelectorAll('.options label');
                const correctOptionText = options[correctAnswerIndex].textContent.trim();
                feedbackEl.textContent = `Incorrect. The correct choice is: ${correctOptionText}.`;
                feedbackEl.classList.add('incorrect');
            }
        }
    });

    const scoreEl = document.getElementById(`score-${quizId}`);
    if (scoreEl) {
        scoreEl.textContent = `Score: ${score} / ${total}`;
    }
}

function checkFillInQuiz(quizId) {
    const form = document.getElementById(quizId);
    if (!form) return;
    let score = 0;
    let total = 0;
    let allCorrect = true;

    const answersMap = {
        'quiz-two': {
            'q2-1': 'can', 'q2-2': 'need not', 'q2-3': 'might', 'q2-4': 'must not',
            'q2-5': 'should not', 'q2-6': 'cannot', 'q2-7': 'must', 'q2-8': 'ought to find',
            'q2-9': 'will', 'q2-10': 'need not',
        },
        'quiz-three': {
            'q3-1': 'could', 'q3-2': 'should', 'q3-3': 'could', 'q3-4': 'should',
            'q3-5': 'must', 'q3-6': 'should', 'q3-7': 'could',
        }
    };
    const answers = answersMap[quizId];
    if (!answers) return;
    
    form.querySelectorAll('input[type="text"]').forEach(input => {
        const correct = sanitize(answers[input.id] || '');
        const user = sanitize(input.value);
        
        input.style.borderColor = '#ccc';
        
        if (user === correct) {
            input.style.borderColor = '#10B981'; // Green
            score++;
        } else {
            input.style.borderColor = '#EF4444'; // Red
            allCorrect = false;
        }
        total++;
    });

    const scoreEl = document.getElementById(`score-${quizId}`);
    if (scoreEl) {
        scoreEl.textContent = `Score: ${score} / ${total}. Review the answers highlighted in red.`;
        scoreEl.classList.toggle('correct', allCorrect);
        scoreEl.classList.toggle('incorrect', !allCorrect);
    }
}
// ===================================
//  LYING & MANIPULATION QUIZ LOGIC
// ===================================
const vocabularyData = [
    { term: "A White Lie", definition: "A harmless or trivial lie told to avoid hurting someone's feelings or to be polite." },
    { term: "Fibbing", definition: "Telling a small, unimportant lie, often used when talking about children." },
    { term: "Leading Me On", definition: "Intentionally giving someone false hope or misleading them about your true intentions or feelings." },
    { term: "Lied To My Face", definition: "Telling a direct lie to a person when they are standing right in front of you." },
    { term: "It’s Written All Over Your Face", definition: "Meaning the truth is obvious from someone's facial expression, despite what they are saying." },
    { term: "That’s Total BS", definition: "A slang phrase meaning 'That's completely false' or 'That's nonsense.'" },
    { term: "’Fess Up", definition: "A short, informal phrase meaning to confess or admit the truth." },
    { term: "Come Clean", definition: "To finally tell the complete truth about something that you have been keeping a secret." },
    { term: "Be Straight With Me", definition: "An urgent request for someone to be honest and direct." }
];

const scenarioQuestions = [
    { text: "Politician hiding important financial details to win votes.", answer: 2 },
    { text: "Wife telling her husband he looks fat so he will start exercising.", answer: 1 },
    { text: "Teacher saying students aren’t good enough to make them study harder.", answer: 1 },
    { text: "Writer deliberately altering historical facts in a play to make a new leader look good.", answer: 0 },
    { text: "Employee telling the boss a project is finished when only 10% is complete.", answer: 0 },
    { text: "Colleague feigns a serious personal emergency to transfer their work to you.", answer: 2 },
];

const quizOptions = ["Lying (only)", "Manipulation (only)", "Both Lying and Manipulation", "Neither"];

function setupVocabulary() {
    const vocabList = document.getElementById('vocab-list');
    if (!vocabList) return;
    vocabularyData.forEach((item, index) => {
        const termHtml = `
            <div class="vocab-term flex justify-between items-start flex-col sm:flex-row">
                <span class="font-bold text-lg text-indigo-700">${item.term}</span>
                <button type="button" class="reveal-button mt-2 sm:mt-0" onclick="toggleDefinition(this, 'def-${index}')">Reveal Definition</button>
            </div>
            <div id="def-${index}" class="vocab-definition">${item.definition}</div>`;
        vocabList.insertAdjacentHTML('beforeend', termHtml);
    });
}

function setupScenarios() {
    const quizForm = document.getElementById('scenario-quiz');
    if (!quizForm) return;
    const container = quizForm.querySelector('.quiz-container');
    
    scenarioQuestions.forEach((q, index) => {
        const qNumber = index + 1;
        let optionsHtml = '';
        quizOptions.forEach((option, optionIndex) => {
            optionsHtml += `
                <label class="inline-flex items-center mr-6 mt-2">
                    <input type="radio" name="q${qNumber}" value="${optionIndex}" class="form-radio text-teal-600 h-4 w-4">
                    <span class="ml-2 text-sm">${option}</span>
                </label>`;
        });

        const questionHtml = `
            <div class="question-item" data-answer="${q.answer}">
                <p class="scenario-text">${qNumber}. ${q.text}</p>
                <div class="options space-x-2 md:space-x-4">${optionsHtml}</div>
                <p class="feedback text-sm" id="feedback-q${qNumber}"></p>
            </div>`;
        container.insertAdjacentHTML('beforeend', questionHtml);
    });
}

function toggleDefinition(button, defId) {
    const definition = document.getElementById(defId);
    if (definition.style.display === 'block') {
        definition.style.display = 'none';
        button.textContent = 'Reveal Definition';
        button.classList.remove('bg-red-500');
        button.classList.add('bg-blue-500');
    } else {
        definition.style.display = 'block';
        button.textContent = 'Hide Definition';
        button.classList.remove('bg-blue-500');
        button.classList.add('bg-red-500');
    }
}

function checkScenarios() {
    let score = 0;
    let total = scenarioQuestions.length;

    scenarioQuestions.forEach((q, index) => {
        const qNumber = index + 1;
        const radios = document.querySelectorAll(`input[name="q${qNumber}"]`);
        const feedbackEl = document.getElementById(`feedback-q${qNumber}`);
        const correctAnswerIndex = q.answer;
        
        let selectedValue = null;
        radios.forEach(radio => {
            if (radio.checked) {
                selectedValue = parseInt(radio.value);
            }
        });
        
        feedbackEl.textContent = '';
        feedbackEl.className = 'feedback text-sm mt-2';
        
        if (selectedValue === null) {
            feedbackEl.textContent = 'Please select an option.';
            feedbackEl.classList.add('incorrect');
        } else if (selectedValue === correctAnswerIndex) {
            feedbackEl.textContent = 'Correct! Great job distinguishing the intent.';
            feedbackEl.classList.add('correct');
            score++;
        } else {
            const correctOptionText = quizOptions[correctAnswerIndex];
            feedbackEl.textContent = `Incorrect. The correct answer is: ${correctOptionText}.`;
            feedbackEl.classList.add('incorrect');
        }
    });

    const scoreEl = document.getElementById('score-scenarios');
    scoreEl.textContent = `Final Score: ${score} / ${total}`;
    scoreEl.classList.remove('correct', 'incorrect');
    scoreEl.classList.add(score === total ? 'correct' : 'incorrect');
}

// Initial setup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('vocab-list')) {
        setupVocabulary();
    }
    if (document.getElementById('scenario-quiz')) {
        setupScenarios();
    }
});
// ===================================
//  METRIC/IMPERIAL CONVERTER LOGIC
// ===================================
const CONVERSION_FACTORS = {
    miles_to_km: 1.60934,
    feet_to_m: 0.3048,
    pounds_to_kg: 0.453592,
    gallons_to_L: 3.78541,
};

function formatResult(value, unit) {
    // Check if value is a whole number
    if (value % 1 === 0) {
        return `${value} ${unit}`;
    }
    return `${value.toFixed(2)} ${unit}`;
}

function convertImperialToMetric() {
    const unit = document.getElementById('imperialUnit').value;
    const valueEl = document.getElementById('imperialValue');
    const resultEl = document.getElementById('imperialResult');
    const inputValue = parseFloat(valueEl.value);

    if (!resultEl) return;
    resultEl.classList.add('hidden');
    resultEl.textContent = '';

    if (isNaN(inputValue) || inputValue < 0) {
        resultEl.textContent = 'Please enter a valid positive number.';
        resultEl.classList.remove('hidden');
        return;
    }

    let resultValue, resultUnit;
    switch (unit) {
        case 'miles':
            resultValue = inputValue * CONVERSION_FACTORS.miles_to_km;
            resultUnit = 'km';
            break;
        case 'feet':
            resultValue = inputValue * CONVERSION_FACTORS.feet_to_m;
            resultUnit = 'm';
            break;
        case 'pounds':
            resultValue = inputValue * CONVERSION_FACTORS.pounds_to_kg;
            resultUnit = 'kg';
            break;
        case 'gallons':
            resultValue = inputValue * CONVERSION_FACTORS.gallons_to_L;
            resultUnit = 'L';
            break;
    }

    resultEl.textContent = `${formatResult(inputValue, unit)} is equal to ${formatResult(resultValue, resultUnit)}.`;
    resultEl.classList.remove('hidden');
}

function convertMetricToImperial() {
    const unit = document.getElementById('metricUnit').value;
    const valueEl = document.getElementById('metricValue');
    const resultEl = document.getElementById('metricResult');
    const inputValue = parseFloat(valueEl.value);

    if (!resultEl) return;
    resultEl.classList.add('hidden');
    resultEl.textContent = '';

    if (isNaN(inputValue) || inputValue < 0) {
        resultEl.textContent = 'Please enter a valid positive number.';
        resultEl.classList.remove('hidden');
        return;
    }

    let resultValue, resultUnit;
    switch (unit) {
        case 'kilometers':
            resultValue = inputValue / CONVERSION_FACTORS.miles_to_km;
            resultUnit = 'miles';
            break;
        case 'meters':
            resultValue = inputValue / CONVERSION_FACTORS.feet_to_m;
            resultUnit = 'feet';
            break;
        case 'kilograms':
            resultValue = inputValue / CONVERSION_FACTORS.pounds_to_kg;
            resultUnit = 'pounds';
            break;
        case 'liters':
            resultValue = inputValue / CONVERSION_FACTORS.gallons_to_L;
            resultUnit = 'gallons';
            break;
    }

    resultEl.textContent = `${formatResult(inputValue, unit)} is equal to ${formatResult(resultValue, resultUnit)}.`;
    resultEl.classList.remove('hidden');
}

function resetImperial() {
    const valueEl = document.getElementById('imperialValue');
    const resultEl = document.getElementById('imperialResult');
    if (valueEl) valueEl.value = '';
    if (resultEl) resultEl.classList.add('hidden');
}

function resetMetric() {
    const valueEl = document.getElementById('metricValue');
    const resultEl = document.getElementById('metricResult');
    if (valueEl) valueEl.value = '';
    if (resultEl) resultEl.classList.add('hidden');
}
// ===================================
//  FEEDBACK LESSON SCRIPT & QUIZ LOGIC
// ===================================
const receivingQuizData = [
    {
        scenario: "Scenario 1: During your annual review, your manager criticizes your project management skills, saying 'You were disorganized this year.'",
        options: [
            "A. Immediately list five reasons why the projects were difficult to manage.",
            "B. Say, 'Thank you. Can you give me an example of a specific project where my organization fell short?'",
            "C. Nod silently and change the subject to next year's goals.",
        ],
        answer: 1,
        explanation: "Correct. The feedback is vague. You must seek clarity and specific examples before taking action."
    },
    {
        scenario: "Scenario 2: A coworker tells you, 'You sometimes dominate team meetings and cut people off.'",
        options: [
            "A. Defensively reply, 'I only interrupt when someone is off-topic.'",
            "B. Say, 'I appreciate you bringing this up. I'll try to be more mindful.'",
            "C. Say, 'Thank you for the feedback. Can you point out the last time I did that?'",
        ],
        answer: 2,
        explanation: "Correct. This combines gratitude with seeking specific clarity, which is key to finding value."
    },
    {
        scenario: "Scenario 3: A client expresses dissatisfaction with your deliverables, stating they are 'too abstract.'",
        options: [
            "A. Apologize profusely and promise to rewrite the entire deliverable immediately.",
            "B. Say, 'I understand your frustration. What specific type of actionable steps would make this more valuable for you?'",
            "C. Explain that the work is 'abstract' because the client didn't provide enough data.",
        ],
        answer: 1,
        explanation: "Correct. You empathize and immediately ask for specifics to guide your revision."
    }
];

function generateScript() {
    const open = document.getElementById('inputPositive').value.trim();
    const specific = document.getElementById('inputSpecific').value.trim();
    const action = document.getElementById('inputAction').value.trim();
    const close = document.getElementById('inputClose').value.trim();
    const output = document.getElementById('scriptOutput');
    
    if (!output) return;
    output.textContent = '';

    if (!open || !specific || !action || !close) {
        output.textContent = "Please fill in all four parts to build your 'feedback sandwich'.";
        output.style.display = 'block';
        return;
    }

    const script = `--- Feedback Sandwich Script ---\n\n[Positive Opening]\n"${open}"\n\n[Specific Observation & Impact]\n"${specific}"\n\n[Suggestion / Request for Change]\n"${action}"\n\n[Positive Closing]\n"${close}"`;
    output.textContent = script;
    output.style.display = 'block';
}

function setupReceivingQuiz() {
    const quizContainer = document.querySelector('#receiving-quiz .quiz-container');
    if (!quizContainer) return;
    
    receivingQuizData.forEach((q, index) => {
        const qNumber = index + 1;
        let optionsHtml = '';
        q.options.forEach((option, optionIndex) => {
            optionsHtml += `
                <label class="block items-center mt-2 cursor-pointer hover:bg-rose-100 p-2 rounded-md">
                    <input type="radio" name="r_q${qNumber}" value="${optionIndex}" class="form-radio text-rose-600 h-4 w-4">
                    <span class="ml-2 text-sm">${option}</span>
                </label>`;
        });

        const questionHtml = `
            <div class="feedback-quiz-item" data-answer="${q.answer}" data-explanation="${q.explanation}">
                <p class="font-semibold mb-2">${q.scenario}</p>
                <div class="options space-y-1">${optionsHtml}</div>
                <p class="feedback text-sm" id="feedback-r_q${qNumber}"></p>
            </div>`;
        quizContainer.insertAdjacentHTML('beforeend', questionHtml);
    });
}

function checkReceivingQuiz() {
    let score = 0;
    const total = receivingQuizData.length;

    receivingQuizData.forEach((q, index) => {
        const qNumber = index + 1;
        const radios = document.querySelectorAll(`input[name="r_q${qNumber}"]`);
        const feedbackEl = document.getElementById(`feedback-r_q${qNumber}`);
        const questionItem = feedbackEl.closest('.feedback-quiz-item');
        const correctAnswerIndex = parseInt(questionItem.dataset.answer);
        const explanation = questionItem.dataset.explanation;
        
        let selectedValue = null;
        radios.forEach(radio => {
            if (radio.checked) selectedValue = parseInt(radio.value);
        });
        
        feedbackEl.textContent = '';
        feedbackEl.className = 'feedback text-sm mt-2';
        
        if (selectedValue === null) {
            feedbackEl.textContent = 'Please select an option.';
            feedbackEl.classList.add('incorrect');
        } else if (selectedValue === correctAnswerIndex) {
            feedbackEl.textContent = `${explanation}`;
            feedbackEl.classList.add('correct');
            score++;
        } else {
            feedbackEl.textContent = `Incorrect. ${explanation}`;
            feedbackEl.classList.add('incorrect');
        }
    });

    const scoreEl = document.getElementById('score-receiving');
    if(scoreEl) {
        scoreEl.textContent = `Final Score: ${score} / ${total}`;
        scoreEl.className = 'font-bold mt-4 text-lg ' + (score === total ? 'correct' : 'incorrect');
    }
}

// Initial setup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('receiving-quiz')) {
        setupReceivingQuiz();
    }
});

// ===================================
//  GOOD NEWS/BAD NEWS VOCABULARY QUIZ
// ===================================
const vocabularyQuizData = [
    { question: "a) I’m [_______] I have some bad news. I was fired.", answer: "sorry" },
    { question: "b) I [_______] to say that the project has been cancelled.", answer: "regret" },
    { question: "c) I [_______] to inform you that your application has been unsuccessful.", answer: "regret" },
    { question: "d) We appreciate the opportunity to read your article, but [_______] it will not be published.", answer: "unfortunately" },
    { question: "e) There is no easy [_______] to say this, but we will be closing our London division.", answer: "way" },
    { question: "f) You [_______] what? I got the job!", answer: "know" },
    { question: "g) Guess [_______] ? We got engaged!", answer: "what" },
    { question: "h) We’re [_______] to tell you that you have been nominated for Employee of the Year.", answer: "pleased" },
    { question: "i) I have some great news [_______] you. You’ve been promoted to senior manager.", answer: "for" },
    { question: "j) Good [_______]! I passed my final exam and got an A.", answer: "news" }
];

function setupVocabularyQuiz() {
    const quizContainer = document.getElementById('quiz-container');
    if (!quizContainer) return;

    vocabularyQuizData.forEach((item, index) => {
        const qId = `vocab-q${index}`;
        const parts = item.question.split('[_______]');
        const questionHtml = `
            <div class="flex flex-wrap items-center">
                <span class="text-sm">${parts[0].trim()}</span>
                <input type="text" id="${qId}" data-answer="${item.answer}" class="input-fill-blank text-base" placeholder="...">
                <span class="text-sm">${parts[1].trim()}</span>
                <span id="feedback-${qId}" class="feedback ml-4 text-xs"></span>
            </div>`;
        quizContainer.insertAdjacentHTML('beforeend', questionHtml);
    });
}

function checkVocabularyQuiz() {
    let correctCount = 0;
    const totalCount = vocabularyQuizData.length;

    vocabularyQuizData.forEach((item, index) => {
        const qId = `vocab-q${index}`;
        const inputEl = document.getElementById(qId);
        const feedbackEl = document.getElementById(`feedback-${qId}`);
        
        const userAnswer = inputEl.value.trim().toLowerCase();
        const correctAnswer = item.answer.toLowerCase();

        feedbackEl.textContent = '';
        feedbackEl.className = 'feedback ml-4 text-xs';

        if (userAnswer === correctAnswer) {
            feedbackEl.textContent = 'Correct!';
            feedbackEl.classList.add('correct');
            correctCount++;
        } else {
            feedbackEl.textContent = `Incorrect. It should be: ${item.answer}`;
            feedbackEl.classList.add('incorrect');
        }
    });

    const overallFeedback = document.getElementById('vocabulary-feedback');
    if (overallFeedback) {
        overallFeedback.textContent = `You scored ${correctCount} out of ${totalCount}.`;
        overallFeedback.className = 'feedback ' + (correctCount === totalCount ? 'correct' : 'incorrect');
    }
}

// Initial setup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('quiz-container')) {
        setupVocabularyQuiz();
    }
});
// ===================================
//  READING LARGE NUMBERS QUIZ LOGIC
// ===================================
const matchData = [
    { word: "Three hundred thousand", digit: "300,000" },
    { word: "Two million five hundred thousand", digit: "2,500,000" },
    { word: "Four million three hundred thousand", digit: "4,300,000" },
    { word: "Nine hundred fifty thousand", digit: "950,000" },
    { word: "Five hundred thousand", digit: "500,000" },
];
const writingData = [
    { digit: "650,000", answer: "six hundred fifty thousand" },
    { digit: "1,200,000", answer: "one million two hundred thousand" },
    { digit: "3,450,000", answer: "three million four hundred fifty thousand" },
    { digit: "123,456", answer: "one hundred twenty-three thousand four hundred fifty-six" },
    { digit: "6,000,001", answer: "six million one" },
];

let selectedWord = null;
let selectedDigit = null;
let matchedPairs = 0;

function normalizeAnswer(text) {
    return text.toLowerCase().replace(/ and /g, ' ').replace(/,|-/g, '').replace(/\s+/g, ' ').trim();
}

function setupMatchQuiz() {
    const wordContainer = document.getElementById('word-container');
    const digitContainer = document.getElementById('digit-container');
    if (!wordContainer || !digitContainer) return;

    const digits = matchData.map(item => ({ id: item.digit, text: item.digit }));
    const words = matchData.map(item => ({ id: item.digit, text: item.word }));
    
    digits.sort(() => Math.random() - 0.5); // Shuffle digits

    wordContainer.innerHTML = '';
    digitContainer.innerHTML = '';

    words.forEach(item => {
        wordContainer.innerHTML += `<div class="match-word" data-id="${item.id}" onclick="selectWord(this)">${item.text}</div>`;
    });
    digits.forEach(item => {
        digitContainer.innerHTML += `<div class="match-digit" data-id="${item.id}" onclick="selectDigit(this)">${item.text}</div>`;
    });
    
    const feedbackEl = document.getElementById('match-feedback');
    if (feedbackEl) feedbackEl.textContent = '';
}

function clearSelections() {
    if (selectedWord) selectedWord.classList.remove('selected');
    if (selectedDigit) selectedDigit.classList.remove('selected');
    selectedWord = null;
    selectedDigit = null;
}

function selectWord(el) {
    if (el.classList.contains('matched')) return;
    clearSelections();
    selectedWord = el;
    selectedWord.classList.add('selected');
}

function selectDigit(el) {
    const feedbackEl = document.getElementById('match-feedback');
    if (el.classList.contains('matched')) return;
    if (!selectedWord) {
        if(feedbackEl) {
            feedbackEl.textContent = 'Please select a word first!';
            feedbackEl.className = 'feedback incorrect';
        }
        return;
    }
    
    selectedDigit = el;
    selectedDigit.classList.add('selected');
    checkMatch();
}

function checkMatch() {
    const feedbackEl = document.getElementById('match-feedback');
    if (!feedbackEl) return;

    if (selectedWord.dataset.id === selectedDigit.dataset.id) {
        selectedWord.classList.add('matched');
        selectedDigit.classList.add('matched');
        feedbackEl.textContent = 'Correct! Pair matched.';
        feedbackEl.className = 'feedback correct';
        matchedPairs++;
        if (matchedPairs === matchData.length) {
            feedbackEl.textContent = 'Great job! You matched all the numbers!';
        }
    } else {
        feedbackEl.textContent = 'That pair is incorrect. Try again.';
        feedbackEl.className = 'feedback incorrect';
    }
    setTimeout(clearSelections, 500);
}

function resetMatchQuiz() {
    matchedPairs = 0;
    setupMatchQuiz();
}

function setupWritingQuiz() {
    const quizContainer = document.getElementById('writing-quiz-container');
    if (!quizContainer) return;
    quizContainer.innerHTML = '';

    writingData.forEach((item, index) => {
        const qId = `w_q${index}`;
        quizContainer.innerHTML += `
            <div class="writing-item">
                <p class="font-semibold text-base mb-1">${index + 1}. ${item.digit}</p>
                <input type="text" id="${qId}" class="writing-input" placeholder="Type the number in words...">
                <p id="feedback-${qId}" class="feedback text-sm mt-1"></p>
            </div>`;
    });
    
    const feedbackEl = document.getElementById('writing-feedback');
    if(feedbackEl) feedbackEl.textContent = '';
}

function checkWritingQuiz() {
    let correctCount = 0;
    const totalCount = writingData.length;

    writingData.forEach((item, index) => {
        const qId = `w_q${index}`;
        const inputEl = document.getElementById(qId);
        const feedbackEl = document.getElementById(`feedback-${qId}`);
        
        const userAnswer = normalizeAnswer(inputEl.value);
        const correctAnswer = normalizeAnswer(item.answer);
        
        if (userAnswer === correctAnswer) {
            feedbackEl.textContent = 'Correct!';
            feedbackEl.className = 'feedback text-sm mt-1 correct';
            correctCount++;
        } else {
            feedbackEl.textContent = `Incorrect. Correct answer: ${item.answer}`;
            feedbackEl.className = 'feedback text-sm mt-1 incorrect';
        }
    });

    const overallFeedback = document.getElementById('writing-feedback');
    if(overallFeedback) {
        overallFeedback.textContent = `You scored ${correctCount} out of ${totalCount}.`;
        overallFeedback.className = 'feedback text-base ' + (correctCount === totalCount ? 'correct' : 'incorrect');
    }
}

// Initial setup when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('word-container')) {
        setupMatchQuiz();
    }
    if (document.getElementById('writing-quiz-container')) {
        setupWritingQuiz();
    }
});

// ===================================
//  PRESENT PERFECT QUIZZES & UI LOGIC
// ===================================

// --- Data for the quizzes ---
const presentPerfectQuizData = [
    { id: 1, sentence: "She _____ (live) in Paris since 2010.", answer: "has lived", hint: "live" },
    { id: 2, sentence: "I _____ (see) that movie three times already.", answer: "have seen", hint: "see" },
    { id: 3, sentence: "They _____ (not finish) their homework yet.", answer: "have not finished", hint: "not finish" },
];
const adverbQuizData = [
    { id: 1, sentence: "We haven't received the package _____.", correct: "Yet", options: ["Just", "Already", "Yet"] },
    { id: 2, sentence: "The train has _____ left the station. We're too late!", correct: "Just", options: ["Just", "Never", "Yet"] },
    { id: 3, sentence: "I have _____ finished my project. That was fast!", correct: "Already", options: ["Ever", "Already", "Never"] },
];
const transformationQuizData = [
    { id: 1, past: "I went to Brazil last month.", presentPerfect: "I have been to Brazil.", hint: "Use 'be to' (Go)" },
    { id: 2, past: "He quit smoking last week.", presentPerfect: "He has quit smoking.", hint: "(Quit) Focus on the result" },
];

// --- Quiz Setup Functions ---

function setupFillInQuiz() {
    const container = document.getElementById('fill-in-quiz-container');
    if (!container) return;
    container.innerHTML = ''; // Clear previous content
    presentPerfectQuizData.forEach((item, index) => {
        const parts = item.sentence.split("_____");
        container.innerHTML += `
            <div class="fill-in-item">
                <p class="text-slate-800 flex items-center flex-wrap">
                    <span class="font-semibold mr-1">${index + 1}.</span>${parts[0]}
                    <input type="text" id="fill_q${item.id}" class="fill-in-input max-w-[180px]" placeholder="e.g., has lived">
                    ${parts[1] || ''}<span class="verb-hint">(${item.hint})</span>
                </p>
                <p id="feedback-fill_q${item.id}" class="feedback text-sm mt-1 ml-5"></p>
            </div>`;
    });
}

// ... (similar setup functions for adverb and transformation quizzes)

// --- Quiz Checking Functions ---

function checkFillInQuiz() {
    let score = 0;
    presentPerfectQuizData.forEach(item => {
        const inputEl = document.getElementById(`fill_q${item.id}`);
        const feedbackEl = document.getElementById(`feedback-fill_q${item.id}`);
        if (normalizeAnswer(inputEl.value) === normalizeAnswer(item.answer)) {
            feedbackEl.textContent = 'Correct!';
            feedbackEl.className = 'feedback text-sm mt-1 ml-5 correct';
            score++;
        } else {
            feedbackEl.textContent = `Incorrect. Correct: ${item.answer}`;
            feedbackEl.className = 'feedback text-sm mt-1 ml-5 incorrect';
        }
    });
    const overallFeedback = document.getElementById('quiz-feedback');
    if(overallFeedback) overallFeedback.textContent = `You scored ${score} / ${presentPerfectQuizData.length}.`;
}

// ... (similar check functions for adverb and transformation quizzes)

// --- UI Interaction ---

function toggleDiscussion(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = (el.style.display === 'block') ? 'none' : 'block';
}

// --- DOM Ready Initializer ---
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('fill-in-quiz-container')) setupFillInQuiz();
    // ... (Add other quiz setup calls here)
});

// ===================================
//  150 QUESTIONS INTERACTIVE TOOLS
// ===================================
const ALL_QUESTIONS = [
    { id: 1, text: "Who is your hero?", category: "Personal & Values" },
    { id: 2, text: "If you could live anywhere, where would it be?", category: "Hypothetical & Fantasy" },
    { id: 3, text: "What is your biggest fear?", category: "Personal & Values" },
    { id: 7, text: "What motivates you to work hard?", category: "Career & Work" },
    { id: 8, text: "What is your favorite thing about your career?", category: "Career & Work" },
    { id: 10, text: "What is your proudest accomplishment?", category: "Past & Memories" },
    { id: 12, text: "What is your favorite book to read?", category: "Favorites & Preferences" },
    { id: 40, text: "Where do you see yourself in five years?", category: "Career & Work" },
    { id: 41, text: "How many pairs of shoes do you own?", category: "Quick Check-in" },
    { id: 42, text: "If you were a superhero, what powers would you have?", category: "Hypothetical & Fantasy" },
    // (The rest of the 150 questions would be here)
];

function populateFullList() {
    const listEl = document.getElementById('question-list-full');
    if (listEl) {
        listEl.innerHTML = ALL_QUESTIONS.map(q => `<li><span class="font-semibold">${q.id}.</span> ${q.text}</li>`).join('');
    }
}

function pickRandomQuestion() {
    const displayEl = document.getElementById('random-question-display');
    if (displayEl && ALL_QUESTIONS.length > 0) {
        const randomIndex = Math.floor(Math.random() * ALL_QUESTIONS.length);
        const question = ALL_QUESTIONS[randomIndex];
        displayEl.innerHTML = `<span class="text-slate-500 text-sm">Question #${question.id}:</span> ${question.text}`;
    }
}

function filterQuestions() {
    const selectEl = document.getElementById('category-select');
    const displayEl = document.getElementById('filtered-questions-display');
    if (!selectEl || !displayEl) return;

    const selectedCategory = selectEl.value;
    let filtered = (selectedCategory === 'All')
        ? ALL_QUESTIONS
        : ALL_QUESTIONS.filter(q => q.category === selectedCategory);

    if (filtered.length === 0) {
        displayEl.innerHTML = `<p class="text-center text-slate-500 pt-4">No questions found for this category.</p>`;
    } else {
        displayEl.innerHTML = filtered.map(q => `<div class="p-2 border-b border-gray-100 last:border-b-0 text-sm"><span class="font-semibold">${q.id}.</span> ${q.text}</div>`).join('');
    }
}

// Initial setup for this specific page
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('question-list-full')) {
        populateFullList();
    }
    if (document.getElementById('category-select')) {
        filterQuestions(); // Initial call to show "All" or placeholder
    }
});
// ===================================
//  MASTERING MOTIVATION INTERACTIVE LOGIC
// ===================================

const motivationQuizData = [
    { id: 1, scenario: "Studying for an exam only because your parents promised you money.", correct: "Extrinsic", options: ["Intrinsic", "Extrinsic"] },
    { id: 2, scenario: "Learning to play the guitar purely for the joy of making music.", correct: "Intrinsic", options: ["Intrinsic", "Extrinsic"] },
    { id: 3, scenario: "Volunteering at an animal shelter because you love animals.", correct: "Intrinsic", options: ["Intrinsic", "Extrinsic"] },
    { id: 4, scenario: "Writing a report perfectly to win a 'Best Employee' award.", correct: "Extrinsic", options: ["Intrinsic", "Extrinsic"] },
];

const motivationalQuotes = [
    "The best way to predict the future is to create it.",
    "The journey of a thousand miles begins with a single step.",
    "Success is not final, failure is not fatal: it is the courage to continue that counts.",
    "Believe you can and you’re halfway there.",
    "The only way to do great work is to love what you do.",
];

const motivationSelections = {};

function setupMotivationQuiz() {
    const quizContainer = document.getElementById('motivation-quiz-container');
    if (!quizContainer) return;
    quizContainer.innerHTML = ''; // Clear previous content

    motivationQuizData.forEach((item, index) => {
        const qId = `motivation_q${item.id}`;
        const buttonsHtml = item.options.map(opt => `<button class="select-button" data-value="${opt}" data-id="${qId}" onclick="selectMotivationType('${qId}', '${opt}')">${opt}</button>`).join('');
        const itemHtml = `
            <div class="motivation-item space-y-2 p-2 border-b border-sky-100 last:border-b-0">
                <p class="text-slate-800 font-medium"><span class="font-bold mr-1">${index + 1}.</span> ${item.scenario}</p>
                <div id="${qId}-select-container" class="inline-block pt-1">${buttonsHtml}</div>
                <p id="feedback-${qId}" class="feedback text-sm ml-5 pt-1"></p>
            </div>`;
        quizContainer.insertAdjacentHTML('beforeend', itemHtml);
    });
}

function selectMotivationType(qId, value) {
    motivationSelections[qId] = value;
    const container = document.getElementById(`${qId}-select-container`);
    container.querySelectorAll('.select-button').forEach(btn => {
        btn.classList.remove('selected');
        if (btn.getAttribute('data-value') === value) {
            btn.classList.add('selected');
        }
    });
    document.getElementById(`feedback-${qId}`).textContent = '';
}

function checkMotivationQuiz() {
    let correctCount = 0;
    motivationQuizData.forEach(item => {
        const qId = `motivation_q${item.id}`;
        const feedbackEl = document.getElementById(`feedback-${qId}`);
        const userAnswer = motivationSelections[qId];
        
        if (!userAnswer) {
            feedbackEl.textContent = 'Please select an answer.';
            feedbackEl.className = 'feedback text-sm ml-5 pt-1 incorrect';
        } else if (userAnswer === item.correct) {
            feedbackEl.textContent = 'Correct!';
            feedbackEl.className = 'feedback text-sm ml-5 pt-1 correct';
            correctCount++;
        } else {
            feedbackEl.textContent = `Incorrect. It's: ${item.correct} motivation.`;
            feedbackEl.className = 'feedback text-sm ml-5 pt-1 incorrect';
        }
    });

    const overallFeedback = document.getElementById('quiz-feedback');
    if(overallFeedback) overallFeedback.textContent = `You scored ${correctCount} out of ${motivationQuizData.length}.`;
}

function generateQuote() {
    const quoteDisplay = document.getElementById('quote-display');
    if(quoteDisplay && motivationalQuotes.length > 0) {
        const randomIndex = Math.floor(Math.random() * motivationalQuotes.length);
        quoteDisplay.textContent = `"${motivationalQuotes[randomIndex]}"`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('motivation-quiz-container')) {
        setupMotivationQuiz();
    }
});