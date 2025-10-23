// Global overlay loader controls
function showGlobalLoader() {
    const el = document.getElementById('globalLoader');
    if (el) el.classList.add('active');
}

function hideGlobalLoader() {
    const el = document.getElementById('globalLoader');
    if (el) el.classList.remove('active');
}

/**
 * Pulisce tutti i campi del modulo Debrief e nasconde i messaggi di stato.
 */
function resetDebriefForm() {
    // Pulisce i campi principali
    debriefGoals.value = "";
    debriefTopics.value = "";
    debriefGrammar.value = "";
    debriefVocabulary.value = "";
    debriefPronunciation.value = "";
    debriefOther.value = "";
    debriefHomework.value = "";

    if (lessonPlanContent) lessonPlanContent.value = '';

    // Pulisce i messaggi di stato
    if (debriefMsg) debriefMsg.textContent = "";

    // Nasconde la tabella bozze, se visibile
    const container = document.getElementById('debriefDraftsContainer');
    if (container) {
        container.innerHTML = "";
        container.classList.add('hidden');
    }

    // Ricarica la data odierna
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    debriefDateInput.value = `${yyyy}-${mm}-${dd}`;

    // Imposta la variabile globale di riga a null
    window.debriefLoadedRow = null;
}

async function handleGoogleLogin(response) {
    showGlobalLoader(); // 👈 overlay a schermo intero

    try {
        const credential = response.credential;
        const resp = await apiPost("loginWithGoogle", { credential });

        if (!resp.success) {
            showToast("Google login fallito: " + resp.error, 5000, "bg-red-600");
            location.reload();
            return;
        }

        document.getElementById('googleLoginContainer').classList.add('hidden');

        CURRENT_COACH_NAME = resp.name;
        CURRENT_COACH_ROLE = resp.role;
        // Persist session
        localStorage.setItem("coachSession", JSON.stringify({
            name: CURRENT_COACH_NAME,
            role: CURRENT_COACH_ROLE
        }));

        coachNameDisplay.textContent = CURRENT_COACH_NAME;
        callSectionCoachNameDisplay.textContent = CURRENT_COACH_NAME;

        switchSection(dashboardSection);

        hideGlobalLoader(); // 👈 chiudiamo subito, l’utente entra in dashboard

        // caricamenti secondari (non bloccano l’UI)
        await fetchMonthlyEarnings();
        await loadStudentIds();
    } catch (err) {
        showToast("Errore login Google: " + (err.message || err), 5000, "bg-red-600");
    } finally {
        hideGlobalLoader(); // 👈 safety net in caso di errori
    }
}

// DOM refs
const loginForm = document.getElementById('loginForm');
const loginBtn = document.getElementById('loginBtn');
const loginMessageBox = document.getElementById('loginMessageBox');

const loginSection = document.getElementById('loginSection');
const dashboardSection = document.getElementById('dashboardSection');
const callSection = document.getElementById('callSection');

const coachIdInput = document.getElementById('coachId');
const passwordInput = document.getElementById('password');
const coachNameDisplay = document.getElementById('coachNameDisplay');
const callSectionCoachNameDisplay = document.getElementById('callSectionCoachNameDisplay');

const earningsAmountDisplay = document.getElementById('earningsAmount');

const logCallBtn = document.getElementById('logCallBtn');
const viewStudentsBtn = document.getElementById('viewStudentsBtn');
const viewFolderBtn = document.getElementById('viewFolderBtn');
const viewCallLogBtn = document.getElementById('viewCallLogBtn');
const viewReportCardsBtn = document.getElementById('viewReportCardsBtn');
const viewCoachingDebriefBtn = document.getElementById('viewCoachingDebriefBtn');
const coachingDebriefSection = document.getElementById('coachingDebriefSection');
// Coaching Debrief DOM
const debriefStudentSelect = document.getElementById('debriefStudentSelect');
const debriefDateInput = document.getElementById('debriefDateInput');
const debriefGoals = document.getElementById('debrief_goals');
const debriefTopics = document.getElementById('debrief_topics');
const debriefGrammar = document.getElementById('debrief_grammar');
const debriefVocabulary = document.getElementById('debrief_vocabulary');
const debriefPronunciation = document.getElementById('debrief_pronunciation');
const debriefOther = document.getElementById('debrief_other');
const debriefHomework = document.getElementById('debrief_homework');
const debriefSaveDraftBtn = document.getElementById('debriefSaveDraftBtn');
const debriefSendBtn = document.getElementById('debriefSendBtn');
const debriefDeleteDraftBtn = document.getElementById('debriefDeleteDraftBtn');
const debriefMsg = document.getElementById('debriefMsg');
const lessonPlanContent = document.getElementById('lessonPlanContent');
const generatePlanBtn = document.getElementById('debriefGeneratePlanBtn');

const logoutBtn = document.getElementById('logoutBtn');

const studentIdSelect = document.getElementById('studentId');
const productIdSelect = document.getElementById('productIdSelect');
const groupStudentsContainer = document.getElementById('groupStudentsContainer');

const callDateInput = document.getElementById('callDate');
const hourlyRateInput = document.getElementById('hourlyRate');
const technicalDurationInput = document.getElementById('technicalDuration');
const callDurationSelect = document.getElementById('callDuration');
const unitsInput = document.getElementById('units');
const contractIdInput = document.getElementById('contractId');
const productIdInput = document.getElementById('productId');
const submitBtn = document.getElementById('submitBtn');
const callMessageBox = document.getElementById('callMessageBox');

const callTypeRadios = document.querySelectorAll('input[name="callType"]');
var remainingCallsDisplay = document.getElementById('remainingCalls');

const callHistorySection = document.getElementById('callHistorySection');
const callHistoryTableBody = document.getElementById('callHistoryTableBody');
const backFromCallHistoryBtn = document.getElementById('backFromCallHistoryBtn');
const historyMonthYear = document.getElementById('historyMonthYear');

const viewFlashcardsBtn = document.getElementById('viewFlashcardsBtn');
const flashcardsSection = document.getElementById('flashcardsSection');
const backToDashboardFromFlashcardsBtn = document.getElementById('backToDashboardFromFlashcardsBtn');
const flashcardsContainer = document.getElementById('flashcardsContainer');


// Stato
let CURRENT_COACH_NAME = null;
let CURRENT_COACH_ROLE = null;
let CURRENT_ALLOCATIONS_BY_STUDENT = {};
let LAST_SELECTED_STUDENT = null;
let LAST_DRAFTS = [];
let pendingFlashcardUpdates = [];

// Helpers UI
function showMessage(box, message, isSuccess = true) {
    box.textContent = message;
    box.className = 'mt-4 p-4 rounded-xl text-center block ' + (isSuccess ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700');
}

function hideMessage(box) {
    box.textContent = '';
    box.className = 'mt-4 p-4 rounded-xl text-center hidden';
}

function loaderHTML(message = "Loading...") {
    return `
    <div class="flex flex-col items-center justify-center py-4 text-gray-500">
      <div class="spinner-container mb-2">
        <div class="spinner-dot"></div>
        <div class="spinner-dot"></div>
        <div class="spinner-dot"></div>
      </div>
      <p>${message}</p>
    </div>
  `;
}

function showToast(msg, ms = 4000, color = "bg-green-600") {
    const t = document.getElementById("toast");
    if (!t) return;
    t.className = `fixed top-4 right-4 text-white px-4 py-2 rounded-lg shadow-lg z-[99999] ${color}`;
    t.textContent = msg;
    t.classList.remove("hidden");
    setTimeout(() => { t.classList.add("hidden"); }, ms);
}

function switchSection(showEl) {
    // nasconde tutte le sezioni app-section
    document.querySelectorAll('.app-section').forEach(el => el.classList.add('hidden'));
    // mostra la sezione richiesta
    if (showEl) showEl.classList.remove('hidden');
    // torna in cima
    window.scrollTo({ top: 0, behavior: 'auto' });
    // evidenzia voce attiva nell'header (versione sicura)
    const header = document.getElementById('mainHeader');
    if (!header) return; // se l'header non esiste, esci senza errori
    const nav = header.querySelector('nav');
    if (!nav) return;
    const buttons = nav.querySelectorAll('button');
    buttons.forEach(btn => btn.classList.remove('text-blue-600', 'font-semibold'));
    let matched = false;
    buttons.forEach(btn => {
        const onclk = btn.getAttribute('onclick') || '';
        if (showEl && showEl.id && onclk.indexOf(showEl.id) !== -1) {
            btn.classList.add('text-blue-600', 'font-semibold');
            matched = true;
        }
    });
    // nessun errore se non trova match
}

function formatLessonPlan(plainText) {
    if (!plainText) return '';
    let html = plainText;

    // 1. Grassetto (es. **Testo**)
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // 2. Corsivo (es. *Testo*)
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // 3. Liste (sostituisce righe che iniziano con - o * con <li> e avvolge in <ul>)
    // Sostituisci i marker di lista e poi avvolgi il blocco.
    html = html.replace(/^\s*([-\*]\s*.+)$/gm, '<li>$1</li>');
    html = html.replace(/<ul>\s*<li>/g, '<ul><li>').replace(/<\/li>\s*<\/ul>/g, '</li></ul>');
    html = html.replace(/(<li>.*<\/li>(\s*<li>.*<\/li>)*)/gs, '<ul>$1</ul>'); // Cerca blocchi <li>

    // 4. Paragrafi (converte doppi a capo in chiusura/apertura paragrafo)
    html = html.replace(/\n\n/g, '</p><p>');

    // 5. Inizializza e pulisce
    html = `<p>${html}</p>`;
    html = html.replace(/<p><\/p>/g, ''); // Rimuove paragrafi vuoti

    return html;
}
// ====================================================================
// GESTIONE DEL TOKEN (Client-Side)
// ====================================================================

const TOKEN_STORAGE_KEY = "smartalk_auth_token";
const TOKEN_REFRESH_HEADER = "X-New-Auth-Token";

function getAuthToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function setAuthToken(token) {
    if (token) {
        localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
        localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
}

/**
 * Controlla la risposta API e aggiorna il token se presente nell'header custom.
 */
function checkAndRefreshAuthToken(res) {
    const newToken = res.headers.get(TOKEN_REFRESH_HEADER);
    if (newToken) {
        setAuthToken(newToken);
        console.log("JWT token refreshed successfully.");
    }
}

// ====================================================================
// API HELPERS AGGIORNATI (apiGet / apiPost)
// ====================================================================

/**
 * Esegue una richiesta GET autenticata al router coach.
 */
async function apiGet(action, params = {}) {
    const token = getAuthToken();
    if (!token) {
        throw new Error("Missing token for authenticated request. Please log in.");
    }

    // Prefisso: /api/coach/
    const url = new URL("/api/coach/" + action, window.location.origin);
    url.searchParams.set("_ts", Date.now());
    Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });

    const headers = {
        "Authorization": `Bearer ${token}`,
    };

    const res = await fetch(url.toString(), { headers });

    if (res.status === 401 || res.status === 403) {
        setAuthToken(null);
        throw new Error(`Authentication failed: ${res.status}. Session expired.`);
    }
    if (!res.ok) {
        const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(`GET /${action} failed: ${res.status} - ${errorBody.detail}`);
    }

    checkAndRefreshAuthToken(res);

    return res.json();
}

/**
 * Esegue una richiesta POST autenticata (o di login).
 */
async function apiPost(action, body = {}) {
    const token = getAuthToken();
    const isLogin = action === 'login';
    const urlPath = isLogin ? "/api/auth/login" : "/api/coach/" + action;

    const headers = {
        "Content-Type": "application/json",
    };

    if (!isLogin) {
        if (!token) {
            throw new Error("Missing token for authenticated request. Please log in.");
        }
        headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(urlPath, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({ ...body })
    });

    if (res.status === 401 || res.status === 403) {
        setAuthToken(null);
        throw new Error(`Authentication failed: ${res.status}. Session expired.`);
    }
    if (!res.ok) {
        const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(`POST /${action} failed: ${res.status} - ${errorBody.detail}`);
    }

    checkAndRefreshAuthToken(res);

    if (isLogin) {
        const jsonResponse = await res.json();
        if (jsonResponse.success && jsonResponse.token) {
            setAuthToken(jsonResponse.token);
        }
        return jsonResponse;
    }

    return res.json();
}

document.addEventListener('DOMContentLoaded', () => {
    console.log("Smartalk API Helpers with strict JWT management initialized.");
});

// --- Load Students Dropdown
async function loadStudentsDropdown() {
    const select = document.getElementById('studentSelect');
    const container = document.getElementById('studentDetailsContainer');

    // UI di attesa
    select.innerHTML = '<option value="" disabled selected>Loading students...</option>';
    container.innerHTML = '<p class="text-gray-500 text-center">Select a student from the dropdown to view their details.</p>';

    showGlobalLoader(); // 👈 overlay on

    try {
        const resp = await apiGet('getStudents');
        let arr = (resp && resp.success && Array.isArray(resp.students)) ? resp.students : [];

        // 👉 Ordina alfabeticamente ignorando maiuscole/minuscole
        arr.sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' }));

        // Ripopola il select
        select.innerHTML = '<option value="" disabled selected>Select a student</option>';
        arr.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            select.appendChild(opt);
        });
    } catch (err) {
        select.innerHTML = '<option value="" disabled selected>Error loading students</option>';
    } finally {
        hideGlobalLoader(); // 👈 overlay off SEMPRE
    }
}


// --- Fetch & Render Student Details
async function fetchAndRenderStudentDetails(studentId) {
    const container = document.getElementById('studentDetailsContainer');
    container.innerHTML = '<p class="text-gray-500 text-center">Loading student details...</p>';
    try {
        const resp = await apiGet('getStudentInfo', { studentId });
        if (!resp.success || !resp.studentInfo) throw new Error(resp.error || "Student not found");
        const info = resp.studentInfo;
        const calls = info.calls || [];
        delete info.calls;

        // --- Fetch contracts per tabellina ---
        let contracts = [];
        try {
            const respContracts = await apiGet('getStudentContracts', { studentId });
            if (respContracts.success) contracts = respContracts.contracts || [];
        } catch (e) {
            console.warn("Contracts load error:", e);
        }


        // --- Link fields da trasformare in bottoni (con alias reali dallo sheet)
        const linkFieldDefs = {
            "Quizlet Link": { label: "Quizlet", aliases: ["Quizlet"] },
            "Drive Folder Link": { label: "Drive Folder", aliases: ["Drive"] },
            "Homework File": { label: "Homework", aliases: ["Homework"] },
            "Lesson Plan File": { label: "Lesson Plan", aliases: ["Lesson Plan"] }
        };

        // helper per rendere cliccabile anche link senza http/https
        function normalizeUrl(u) {
            if (!u) return "";
            const s = String(u).trim();
            if (!s) return "";
            if (/^https?:\/\//i.test(s)) return s;
            return "https://" + s;
        }

        let buttonsHtml = "";
        for (const [primaryKey, def] of Object.entries(linkFieldDefs)) {
            // prova le chiavi in ordine: primaria + alias
            const candidates = [primaryKey, ...(def.aliases || [])];
            let value = "";
            for (const k of candidates) {
                const v = (info[k] || "").toString().trim();
                if (v && v !== "N/A") { value = v; break; }
            }
            // elimina SEMPRE tutte le chiavi (così non compaiono nella tabella)
            candidates.forEach(k => delete info[k]);

            if (value) {
                const url = normalizeUrl(value);
                buttonsHtml += `
          <a href="${url}" target="_blank" rel="noopener noreferrer"
             class="inline-flex items-center justify-center px-5 py-2 rounded-xl bg-blue-600 text-white shadow
                    hover:bg-blue-700 active:scale-[.99] transition text-sm font-medium">
            ${def.label}
          </a>`;
            } else {
                buttonsHtml += `
          <span class="inline-flex items-center justify-center px-5 py-2 rounded-xl bg-gray-200 text-gray-500 shadow-inner
                       cursor-not-allowed text-sm font-medium">
            ${def.label}
          </span>`;
            }
        }

        // --- Tabella dettagli
        let detailsHtml = `<h3 class="text-xl font-semibold text-gray-800 mb-4">Student Details</h3>
    <div class="overflow-x-auto mb-6"><table class="w-full text-sm"><tbody>`;

        for (const [key, value] of Object.entries(info)) {
            // Nascondi campo "Onboarded (dashboard)"
            if (key === 'Onboarded (dashboard)') {
                continue;
            }

            // Secondary Email → mailto
            if ((key === 'Email' || key === 'Secondary Email') && value && value !== 'N/A') {
                detailsHtml += `
          <tr>
            <td class="py-3 px-6 font-medium text-gray-700 whitespace-nowrap">${key}</td>
            <td class="py-3 px-6">
              <a href="mailto:${value}" class="text-blue-600 underline hover:text-blue-800">${value}</a>
            </td>
          </tr>`;
                continue;
            }

            // Phone → WhatsApp
            if (key === 'Phone' && value && value !== 'N/A') {
                const clean = value.replace(/\D/g, '');
                detailsHtml += `
          <tr>
            <td class="py-3 px-6 font-medium text-gray-700 whitespace-nowrap">${key}</td>
            <td class="py-3 px-6">
              <a href="https://wa.me/${clean}" target="_blank" class="text-blue-600 underline hover:text-blue-800">${value}</a>
            </td>
          </tr>`;
                continue;
            }

            // Status → badge
            if (key === 'Status') {
                const color = value === 'Active' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800';
                detailsHtml += `
          <tr>
            <td class="py-3 px-6 font-medium text-gray-700 whitespace-nowrap">${key}</td>
            <td class="py-3 px-6"><span class="px-3 py-1 rounded-full text-xs font-semibold ${color}">${value}</span></td>
          </tr>`;
                continue;
            }

            // Report Card Cadency Months → "No report card" se vuoto/N.A.
            if (key === 'Report Card Cadency Months') {
                const hasCadency = value && value !== 'N/A';
                const display = hasCadency ? value : 'No report card';
                const badgeClass = hasCadency
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-200 text-gray-600";

                detailsHtml += `
          <tr>
            <td class="py-3 px-6 font-medium text-gray-700 whitespace-nowrap">${key}</td>
            <td class="py-3 px-6">
              <span class="px-3 py-1 rounded-full text-xs font-semibold ${badgeClass}">
                ${display}
              </span>
            </td>
          </tr>`;
                continue;
            }

            // Default
            detailsHtml += `
        <tr>
          <td class="py-3 px-6 font-medium text-gray-700 whitespace-nowrap">${key}</td>
          <td class="py-3 px-6 text-gray-800">${value || 'N/A'}</td>
        </tr>`;
        }
        detailsHtml += `</tbody></table></div>`;

        // --- Se ci sono bottoni, aggiungili sotto la tabella (centrati e responsive)
        if (buttonsHtml) {
            detailsHtml += `
        <div class="mt-6 flex flex-wrap items-center justify-center gap-3">
          ${buttonsHtml}
        </div>`;
        }


        // --- Active & Expired Contracts ---
        if (contracts && contracts.length) {
            detailsHtml += `
          <h3 class="text-xl font-semibold text-gray-800 mb-4 mt-2">Contracts</h3>
          <div class="flex justify-center">
            <table class="text-sm border border-gray-200 rounded-xl mb-6">
              <thead class="bg-gray-100">
                <tr>
                  <th class="py-2 px-4 text-left">Product</th>
                  <th class="py-2 px-4 text-center">Duration</th>
                  <th class="py-2 px-4 text-center">Used</th>
                  <th class="py-2 px-4 text-center">Left</th>
                  <th class="py-2 px-4 text-center">Expiration</th>
                  <th class="py-2 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
            ${contracts.map(c => {
                return `
                <tr class="${(c.left_calls === 0 || c.status === 'inactive') ? 'text-gray-400' : ''}">
                    <td class="py-2 px-4">${c.product.product_name}</td>
                    <td class="py-2 px-4 text-center">${c.product.duration}</td>
                    <td class="py-2 px-4 text-center">${c.used_calls}</td>
                    <td class="py-2 px-4 text-center">${c.left_calls}</td>
                    <td class="py-2 px-4 text-center">${c.max_end_date}</td>
                    <td class="py-2 px-4 text-center">${c.status}</td>
                </tr>`;
            }).join('')}
              </tbody>
            </table>
          </div>
        `;
        } else {
            detailsHtml += `<p class="text-gray-500 italic text-center mb-4">No contracts found.</p>`;
        }



        // --- Call History (nuovo formato)
        detailsHtml += `<h3 class="text-xl font-semibold text-gray-800 mb-4 mt-6">Call History</h3>
    <div class="overflow-x-auto"><table class="w-full text-sm border border-gray-200 rounded-xl">
      <thead class="bg-gray-100">
        <tr>
          <th class="py-3 px-6 text-left">Date</th>
          <th class="py-3 px-6 text-left">Product</th>
          <th class="py-3 px-6 text-left">Coach ID</th>
          <th class="py-3 px-6 text-left">Duration (min)</th>
          <th class="py-3 px-6 text-left">Attendance</th>
          <th class="py-3 px-6 text-left">Notes</th>
        </tr>
      </thead>
      <tbody>`;

        if (calls.length > 0) {
            calls.forEach(c => {
                detailsHtml += `
        <tr class="border-b hover:bg-gray-50">
          <td class="py-3 px-6">${c.date || 'N/A'}</td>
          <td class="py-3 px-6">${c.productName || c.productId || '-'}</td>
          <td class="py-3 px-6">${c.coachId || '-'}</td>
          <td class="py-3 px-6">${c.duration || '-'}</td>
          <td class="py-3 px-6">${c.attendance || '-'}</td>
          <td class="py-3 px-6">${c.notes || ''}</td>
        </tr>`;
            });
        } else {
            detailsHtml += `<tr><td colspan="6" class="py-3 px-6 text-center text-gray-500">No calls found.</td></tr>`;
        }


        detailsHtml += `</tbody></table></div>`;

        container.innerHTML = detailsHtml;
    } catch (err) {
        container.innerHTML = `<p class="text-red-500 text-center">Error: ${err.message}</p>`;
    }
}


// Validazione form
function updateFormState() {
    const selectedStudent = studentIdSelect.value;
    const selectedProduct = productIdSelect.value;
    const selectedDuration = callDurationSelect.value;
    const isInd = document.querySelector('input[name="callType"]:checked').value === 'IND';
    const isGroup = document.querySelector('input[name="callType"]:checked').value === 'GROUP';
    const hourlyRate = parseFloat(hourlyRateInput.value);

    let isValid = false;
    if (isInd) {
        isValid = selectedStudent && selectedProduct && selectedDuration && !isNaN(hourlyRate) && hourlyRate > 0;
    } else if (isGroup) {
        const selects = groupStudentsDynamic.querySelectorAll('select');
        const chosen = Array.from(selects).map(s => s.value).filter(Boolean);
        const unique = new Set(chosen);

        isValid = selectedProduct
            && chosen.length === selects.length       // tutti compilati
            && unique.size === chosen.length          // no duplicati
            && selectedDuration
            && !isNaN(hourlyRate) && hourlyRate > 0;
    }
    submitBtn.disabled = !isValid;
}

// Login
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessage(loginMessageBox);

    showGlobalLoader(); // 👈 solo overlay, niente spinner nel bottone

    try {
        const coachId = coachIdInput.value.trim();
        const password = passwordInput.value.trim();
        const resp = await apiPost('login', { coachId, password });
        if (!resp.success) throw new Error(resp.error || 'Login failed');

        CURRENT_COACH_NAME = resp.name;
        CURRENT_COACH_ROLE = resp.role;
        // Persist session
        localStorage.setItem("coachSession", JSON.stringify({
            name: CURRENT_COACH_NAME,
            role: CURRENT_COACH_ROLE
        }));


        coachNameDisplay.textContent = CURRENT_COACH_NAME;
        callSectionCoachNameDisplay.textContent = CURRENT_COACH_NAME;

        switchSection(dashboardSection);
        hideGlobalLoader();
        await fetchMonthlyEarnings();
        await loadStudentIds();

        document.getElementById('googleLoginContainer').classList.add('hidden');

    } catch (err) {
        showMessage(loginMessageBox, err.message || String(err), false);
    } finally {
    }
});

// === LOAD DRAFTS (complete version) ===
const btn = document.getElementById('debriefLoadDraftsBtn');
const container = document.getElementById('debriefDraftsContainer');

if (btn && !btn.dataset.bound) {
    btn.dataset.bound = "1"; // evita duplicati

    btn.addEventListener('click', async () => {
        const studentId = debriefStudentSelect.value || null;
        container.innerHTML = "";
        container.classList.remove('hidden');
        showGlobalLoader();

        try {
            const resp = await apiGet('getDebriefDrafts', { studentId });
            if (!resp.success || !resp.drafts?.length) {
                container.innerHTML = '<p class="text-gray-500 mt-4 border-t pt-3">No drafts found.</p>';
                return;
            }

            // costruiamo la tabella dinamicamente
            let html = `
        <div class="border-t mt-6 pt-4">
          <h3 class="text-lg font-semibold mb-2">💾 Saved Drafts</h3>
          <div class="max-h-80 overflow-y-auto rounded-xl border border-gray-200">
            <table class="min-w-full text-sm w-full table-fixed">
              <thead class="bg-gray-100 sticky top-0">
                <tr>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Date</th>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Student</th>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Goals</th>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Topics</th>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Grammar</th>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Vocabulary</th>
                  <th class="px-3 py-2 border" style="width: 9.09%;">Pronunciation</th>
                  
                  <th class="px-3 py-2 border" style="width: 18.18%;">Homework</th>
                  
                  <th class="px-3 py-2 border" style="width: 9.09%;">Other</th>
                  <th class="px-3 py-2 border text-center" style="width: 9.10%;">Load</th>
                </tr>
              </thead>
              <tbody>`;

            resp.drafts.forEach(d => {
                const safe = v => (v || "").replace(/\n/g, " ").slice(0, 80);
                html += `
          <tr class="border-b hover:bg-gray-50">
            <td class="px-3 py-2" style="width: 9.09%;">${(d.dateISO || '-').slice(0, 10)}</td>
            <td class="px-3 py-2" style="width: 9.09%;">${d.studentId || '-'}</td>
            <td class="px-3 py-2" style="width: 9.09%;">${safe(d.goals)}</td>
            <td class="px-3 py-2" style="width: 9.09%;">${safe(d.topics)}</td>
            <td class="px-3 py-2" style="width: 9.09%;">${safe(d.grammar)}</td>
            <td class="px-3 py-2" style="width: 9.09%;">${safe(d.vocabulary)}</td>
            <td class="px-3 py-2" style="width: 9.09%;">${safe(d.pronunciation)}</td>
            
            <td class="px-3 py-2" style="width: 18.18%;">${safe(d.homework)}</td>
            
            <td class="px-3 py-2" style="width: 9.09%;">${safe(d.other)}</td>
            <td class="px-3 py-2 text-center" style="width: 9.10%;">
              <button class="loadDraftBtn px-2 py-1 bg-green-600 text-white rounded text-xs"
                      data-row="${d.rowNumber}">Load</button>
            </td>
          </tr>`;
            });

            html += `</tbody></table></div></div>`;
            container.innerHTML = html;


            // La tua funzione fillDebriefFields aggiornata
            function fillDebriefFields(draft) {
                const map = {
                    goals: 'debrief_goals',
                    topics: 'debrief_topics',
                    grammar: 'debrief_grammar',
                    vocabulary: 'debrief_vocabulary',
                    pronunciation: 'debrief_pronunciation',
                    homework: 'debrief_homework',
                    other: 'debrief_other'
                };

                // 1. Carica i campi della mappa (textarea)
                for (const key in map) {
                    const el = document.getElementById(map[key]);
                    if (el && draft[key] !== undefined) el.value = draft[key] || '';
                }

                // 2. ✅ CRITICO: Carica Data e Studente (che non sono nella mappa)

                // Assumi che le variabili DOM globali siano accessibili (o usa document.getElementById qui)
                const dateInput = document.getElementById('debriefDateInput');
                const studentSelect = document.getElementById('debriefStudentSelect');

                if (dateInput && draft.date) {
                    dateInput.value = draft.date;
                }

                // Assumiamo che la chiave restituita dal GS sia ora 'studentId' (corretto al punto 1)
                if (studentSelect && draft.studentId) {
                    studentSelect.value = draft.studentId;
                }
            }

            // listener per ogni bottone "Load"
            container.querySelectorAll('.loadDraftBtn').forEach(loadBtn => {
                loadBtn.addEventListener('click', async e => {
                    const rowNumber = e.target.dataset.row;
                    showGlobalLoader();
                    try {
                        const single = await apiGet('getDebriefByRow', { rowNumber });
                        if (single.success && single.draft) {
                            fillDebriefFields(single.draft);

                            // 💡 CORREZIONE CRITICA: SALVA IL NUMERO DI RIGA
                            window.debriefLoadedRow = rowNumber;

                            showToast("Draft loaded ✅", 3000, "bg-green-600");
                        } else {
                            showToast("Failed to load draft", 3000, "bg-red-600");
                        }
                    } catch (err) {
                        showToast(`Error: ${err.message}`, 3000, "bg-red-600");
                    } finally {
                        hideGlobalLoader();
                    }
                });
            });

        } catch (err) {
            container.innerHTML = `<p class="text-red-500 text-sm mt-4">Error: ${err.message}</p>`;
        } finally {
            hideGlobalLoader();
        }
    });
}



viewCoachingDebriefBtn.addEventListener('click', async () => {

    switchSection(coachingDebriefSection);

    // Precompila la data odierna
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    debriefDateInput.value = `${yyyy}-${mm}-${dd}`;

    // Carica lista studenti nel dropdown
    showGlobalLoader();  // 👈 mostra overlay

    try {
        const resp = await apiGet('getStudents');
        let arr = (resp && resp.success && Array.isArray(resp.students)) ? resp.students : [];
        arr.sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' }));

        debriefStudentSelect.innerHTML = '<option value="" disabled selected>Select a student</option>';
        arr.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            debriefStudentSelect.appendChild(opt);
        });
    } catch (err) {
        debriefStudentSelect.innerHTML = '<option value="" disabled selected>Error loading students</option>';
    } finally {
        hideGlobalLoader();  // 👈 chiudi overlay SEMPRE
    }
});


// --- Save Draft Debrief ---
debriefSaveDraftBtn.addEventListener('click', async () => {
    debriefMsg.textContent = "💾 Saving draft...";
    showGlobalLoader(); // 👈 AGGIUNTO

    try {
        const payload = {
            action: "saveDebrief",
            studentId: debriefStudentSelect.value,
            date: debriefDateInput.value,
            goals: debriefGoals.value,
            topics: debriefTopics.value,
            grammar: debriefGrammar.value,
            vocabulary: debriefVocabulary.value,
            pronunciation: debriefPronunciation.value,
            other: debriefOther.value,
            homework: debriefHomework.value,
            draft: true
        };
        const resp = await apiPost('saveDebrief', payload);

        if (!resp.success) throw new Error(resp.error || "Unknown error");
        debriefMsg.textContent = "✅ Draft saved!";
    } catch (err) {
        console.error("Save draft error:", err);
        debriefMsg.textContent = "❌ " + (err.message || "Error saving draft");
    } finally {
        hideGlobalLoader(); // 👈 AGGIUNTO
    }
});

// --- Send Debrief ---
debriefSendBtn.addEventListener('click', async () => {
    debriefMsg.textContent = "📤 Sending...";
    showGlobalLoader(); // 👈 AGGIUNTO

    try {
        const resp = await apiPost("sendDebrief", {
            studentId: debriefStudentSelect.value,
            rowNumber: window.debriefLoadedRow || null
        });

        if (!resp.success) throw new Error(resp.error || "Send failed");
        debriefMsg.textContent = "✅ Sent to student!";
    } catch (err) {
        console.error("Send debrief error:", err);
        debriefMsg.textContent = "❌ " + (err.message || "Error sending debrief");
    } finally {
        hideGlobalLoader(); // 👈 AGGIUNTO
    }
});

// --- Delete Draft Handler ---
if (debriefDeleteDraftBtn) {
    debriefDeleteDraftBtn.addEventListener('click', async () => {
        const rowToDelete = window.debriefLoadedRow || null;

        if (!rowToDelete) {
            debriefMsg.textContent = "❌ No draft is currently loaded to delete.";
            showToast("No draft loaded.", 3000, "bg-red-600");
            return;
        }

        if (!confirm(`Are you sure you want to permanently delete the draft from row ${rowToDelete}?`)) {
            return;
        }

        debriefMsg.textContent = "🗑️ Deleting draft...";
        showGlobalLoader(); // 👈 AGGIUNTO

        try {
            const resp = await apiPost('deleteDebriefDraft', { rowNumber: rowToDelete });

            if (!resp.success) throw new Error(resp.error || "Deletion failed");

            debriefMsg.textContent = "✅ Draft successfully deleted!";
            showToast("Draft deleted!", 3000, "bg-green-600");

            resetDebriefForm();
            window.debriefLoadedRow = null;

        } catch (err) {
            console.error("Delete draft error:", err);
            debriefMsg.textContent = "❌ " + (err.message || "Error deleting draft");
            showToast("Error deleting draft.", 3000, "bg-red-600");
        } finally {
            hideGlobalLoader(); // 👈 AGGIUNTO
        }
    });
}



// =============== AI Preview Handler ===================
async function handleAIPreview(fieldType) {
    const studentSelect = document.getElementById("debriefStudentSelect");
    const studentName = studentSelect?.options[studentSelect.selectedIndex]?.text || "Student";

    const textArea = document.getElementById(`debrief_${fieldType}`);
    const previewBox = document.getElementById(`aiPreview_${fieldType}`);
    const currentText = textArea.value.trim();

    // mostra loader
    previewBox.innerHTML = loaderHTML("Generating preview...");
    previewBox.classList.remove("hidden");

    try {
        const resp = await apiPost("generateDebriefText", {
            fieldType,
            currentText,
            studentName
        });

        if (!resp.success) throw new Error(resp.error || "AI generation failed");

        const suggestion = (resp.suggestion || "").trim();
        if (!suggestion) throw new Error("Empty AI response");

        // crea box anteprima
        previewBox.innerHTML = `
            <div class="bg-gray-100 p-3 rounded-lg shadow-sm text-sm text-gray-800">
              <div class="font-semibold mb-1">AI suggestion for ${capitalize(fieldType)}:</div>
              <div class="whitespace-pre-line mb-3">${escapeHTML(suggestion)}</div>
              <div class="flex gap-2">
                <button class="px-2 py-1 bg-blue-600 text-white text-xs rounded"
                        onclick="applyAISuggestion('${fieldType}', \`${escapeBackticks(suggestion)}\`)">
                  ✅ Apply suggestion
                </button>
                <button class="px-2 py-1 bg-gray-300 text-xs rounded"
                        onclick="discardAISuggestion('${fieldType}')">
                  ❌ Discard
                </button>
              </div>
              <p class="text-[11px] text-gray-500 mt-1">No changes will be made until you confirm.</p>
            </div>
          `;
    } catch (err) {
        previewBox.innerHTML = `<p class="text-red-600 text-sm">Error: ${escapeHTML(err.message)}</p>`;
    }
}

// accetta il suggerimento
function applyAISuggestion(fieldType, suggestion) {
    const textArea = document.getElementById(`debrief_${fieldType}`);
    textArea.value = suggestion.trim();
    discardAISuggestion(fieldType);
    showToast(`Applied AI suggestion for ${capitalize(fieldType)}`, "success");
}

// annulla il suggerimento
function discardAISuggestion(fieldType) {
    const previewBox = document.getElementById(`aiPreview_${fieldType}`);
    previewBox.classList.add("hidden");
    previewBox.innerHTML = "";
}

// helper utils
function capitalize(s) {
    return s.charAt(0).toUpperCase() + s.slice(1);
}
function escapeHTML(str) {
    return str.replace(/[&<>'"]/g, c => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[c]));
}
function escapeBackticks(str) {
    return str.replace(/`/g, "\\`");
}


// My payment folder
viewFolderBtn.addEventListener('click', async () => {
    try {
        const resp = await apiGet('getPaymentFolderUrl');
        if (resp.success && resp.url) {
            window.open(resp.url, "_blank");
        } else {
            showToast("No folder found", 4000, "bg-red-600");
        }
    } catch (err) {
        showToast("Error: " + err.message, 5000, "bg-red-600");
    } finally {
        hideGlobalLoader(); // 👈 loader off
    }
});

//Student Info
// Student dropdown change
document.getElementById('studentSelect').addEventListener('change', e => {
    const sid = e.target.value;
    if (sid) fetchAndRenderStudentDetails(sid);
});

// Aprire sezione Students dal dashboard
document.getElementById('viewStudentsBtn').addEventListener('click', () => {
    switchSection(document.getElementById('studentsSection'));
    loadStudentsDropdown();
});

// Torna al dashboard
document.getElementById('backToDashboardFromStudentsBtn').addEventListener('click', () => {
    switchSection(document.getElementById('dashboardSection'));
});


// Call History
let fullHistory = []; // memorizza tutte le calls
viewCallLogBtn.addEventListener('click', async () => {
    switchSection(callHistorySection);
    callHistoryTableBody.innerHTML = `<tr><td colspan="4">${loaderHTML("Loading call history...")}</td></tr>`;
    try {
        const resp = await apiGet('getCallHistory');
        if (resp.success && resp.history.length) {
            fullHistory = resp.history; // salva tutto
            renderHistoryTable();       // disegna tabella (gestisce già i loop)
        } else {
            callHistoryTableBody.innerHTML = '<tr><td colspan="4" class="text-center p-4">No calls logged</td></tr>';
        }

    } catch (err) {
        callHistoryTableBody.innerHTML = `<tr><td colspan="4" class="text-center p-4 text-red-500">Error: ${err.message}</td></tr>`;
    }
});
backFromCallHistoryBtn.addEventListener('click', () => switchSection(dashboardSection));
// cambio mese
historyMonthYear.addEventListener('change', renderHistoryTable);

function renderHistoryTable() {
    const selected = document.getElementById('historyMonthYear').value; // es. "2025-09"
    callHistoryTableBody.innerHTML = '';

    const filtered = fullHistory.filter(h => {
        if (!selected) return true;
        if (!h.dateISO) return false;
        let ym = "";
        if (h.dateISO instanceof Date) {
            ym = h.dateISO.toISOString().slice(0, 7);
        } else {
            const d = new Date(h.dateISO);
            ym = isNaN(d) ? String(h.dateISO).slice(0, 7) : d.toISOString().slice(0, 7);
        }
        return ym === selected;
    });



    if (!filtered.length) {
        callHistoryTableBody.innerHTML = '<tr><td colspan="4" class="text-center p-4">No calls found</td></tr>';
        return;
    }

    filtered.forEach(h => {
        const row = document.createElement('tr');
        row.innerHTML = `
        <td class="border px-4 py-2">${h.date || h.dateISO || 'N/A'}</td>
        <td class="border px-4 py-2">${h.studentId || ''}</td>
        <td class="border px-4 py-2">${h.productName || h.productId || ''}</td>
        <td class="border px-4 py-2 text-right">${(Number(h.earnings) || 0).toFixed(2)}</td>
      `;

        callHistoryTableBody.appendChild(row);
    });
}

// Logout
logoutBtn.addEventListener('click', () => {
    CURRENT_COACH_NAME = null;
    CURRENT_COACH_ROLE = null;
    CURRENT_ALLOCATIONS_BY_STUDENT = {};
    coachIdInput.value = "";
    passwordInput.value = "";

    // Clear persisted session
    localStorage.removeItem("coachSession");
    setAuthToken(null)

    // 👇 Riporta visibile il bottone Google
    document.getElementById('googleLoginContainer')?.classList.remove('hidden');

    switchSection(loginSection);
    hideMessage(loginMessageBox);
});

async function saveLessonPlanContent(content) {
    // LAST_SELECTED_STUDENT è una variabile globale che assumo esista
    if (!LAST_SELECTED_STUDENT) {
        showToast("Errore: Dati coach o studente mancanti.", 5000, "bg-red-600");
        return { success: false, error: "Missing data" };
    }

    try {
        const payload = {
            action: 'saveLessonPlanContent',
            studentId: LAST_SELECTED_STUDENT,
            content: content
        };

        // Chiamata all'API POST
        // Usiamo 'saveLessonPlanContent' come primo argomento per l'azione, e payload come dati
        const resp = await apiPost(payload.action, payload);

        if (resp.success) {
            showToast("Lesson Plan salvato con successo.", 3000, "bg-green-600");
        } else {
            showToast("Errore nel salvataggio del Lesson Plan: " + (resp.error || "Errore sconosciuto"), 5000, "bg-red-600");
        }
        return resp;

    } catch (err) {
        showToast("Errore di rete nel salvataggio del Lesson Plan: " + err.message, 5000, "bg-red-600");
        return { success: false, error: err.message };
    }
}

async function loadLessonPlan(studentId) {
    if (!lessonPlanContent) return; // lessonPlanContent è la textarea

    // 1. Reset e UI
    lessonPlanContent.value = 'Caricamento Lesson Plan...';
    const aiPreviewDiv = document.getElementById('aiPreview_lessonplan_content');
    if (aiPreviewDiv) aiPreviewDiv.innerHTML = `<p class="text-gray-500">Caricamento...</p>`;

    // Potresti voler disabilitare il pulsante AI qui se non è ancora pronto
    if (generatePlanBtn) generatePlanBtn.disabled = true;

    if (!studentId) {
        lessonPlanContent.value = '';
        if (aiPreviewDiv) aiPreviewDiv.innerHTML = `<p class="text-gray-500">Seleziona uno studente.</p>`;
        return;
    }

    try {
        // ✅ CHIAMATA ALLA NUOVA API GET: getLessonPlanContent
        const response = await apiGet('getLessonPlanContent', { studentId: studentId });

        if (response.success && response.content !== undefined) {
            const content = response.content || '';

            // Incolla il testo puro nel campo
            lessonPlanContent.value = content;

            // Popola il div di anteprima con il testo formattato (se formatLessonPlan esiste)
            if (aiPreviewDiv) {
                // Assumo che tu abbia una funzione formatLessonPlan per convertire Markdown/testo in HTML
                if (typeof formatLessonPlan === 'function') {
                    aiPreviewDiv.innerHTML = formatLessonPlan(content);
                } else {
                    aiPreviewDiv.innerHTML = content.replace(/\n/g, '<br>'); // Fallback semplice
                }
            }

        } else {
            // Errore o contenuto vuoto
            const errorMessage = response.error || 'Nessun Lesson Plan trovato.';
            lessonPlanContent.value = ''; // Lasciamo vuota, non un messaggio di errore

            if (aiPreviewDiv) {
                aiPreviewDiv.innerHTML = `<p class="text-gray-500">${errorMessage}</p>`;
            }
        }

        // Abilita il pulsante AI solo se tutto è andato a buon fine (o se lo studente è selezionato)
        if (generatePlanBtn) generatePlanBtn.disabled = false;

    } catch (error) {
        console.error("Errore critico nel caricamento del lesson plan:", error);
        lessonPlanContent.value = 'Errore durante la richiesta.';
        if (aiPreviewDiv) aiPreviewDiv.innerHTML = `<p class="text-red-500">Errore nel caricamento.</p>`;
    }
}

async function handleGeneratePlan() {
    // 1. Check essenziali
    if (!lessonPlanContent || !generatePlanBtn || generatePlanBtn.disabled) return;
    if (!debriefGoals || !debriefTopics) return;

    // Assumo CURRENT_STUDENT_INFO sia disponibile globalmente
    const studentInfo = CURRENT_STUDENT_INFO || {};
    const studentName = studentInfo.name || 'lo studente';

    const goals = debriefGoals.value.trim();
    const topics = debriefTopics.value.trim();

    if (!goals && !topics) {
        showToast("Per generare il piano, compila almeno Goals o Topics.", 4000, "bg-yellow-600");
        return;
    }

    // 2. Costruisci il Prompt (puoi affinarlo, ho aggiunto il Markdown)
    const systemPrompt = `Sei un coach linguistico. Genera un Lesson Plan conciso e strutturato per la prossima lezione. Usa il formato Markdown per le intestazioni (## Sezione). Includi sezioni per 'Warm-up', 'Attività Principali', 'Grammatica/Vocabolario', e 'Wrap-up'.`;

    let userQuery = `Crea un Lesson Plan per ${studentName}. Obiettivi della lezione: ${goals}. Argomenti specifici da trattare: ${topics}.`;
    if (studentInfo.level) {
        userQuery += ` Livello dello studente: ${studentInfo.level}.`;
    }

    // 3. Esecuzione del processo di generazione e salvataggio
    generatePlanBtn.disabled = true;
    generatePlanBtn.innerHTML = `<svg class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Genero...`;

    showGlobalLoader();
    let generatedContent = null;

    try {
        // --- CHIAMATA AI (MOLTO SIMILE ALLA TUA VECCHIA LOGICA) ---
        const apiKey = "" // Qui devi inserire la tua chiave, se non è gestita altrove.
        const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${apiKey}`;

        const payload = {
            contents: [{ parts: [{ text: userQuery }] }],
            systemInstruction: { parts: [{ text: systemPrompt }] },
            // Rimuovi tools: [{ "google_search": {} }] se non serve in questo prompt
        };

        const response = await fetchWithRetry(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        const text = result?.candidates?.[0]?.content?.parts?.[0]?.text;

        if (!text) throw new Error("AI ha generato una risposta vuota.");
        generatedContent = text;

        // 4. Incolla il contenuto nella TEXTAREA
        lessonPlanContent.value = generatedContent;

        // Popola l'anteprima (Assumendo che formatLessonPlan funzioni)
        const aiPreviewDiv = document.getElementById('aiPreview_lessonplan_content');
        if (aiPreviewDiv && typeof formatLessonPlan === 'function') {
            aiPreviewDiv.innerHTML = formatLessonPlan(generatedContent);
        }

        // 5. CHIAMATA DI SALVATAGGIO ALLA NUOVA API POST!
        const saveResp = await saveLessonPlanContent(generatedContent); // Chiama la funzione #1

        if (!saveResp.success) {
            throw new Error(saveResp.error || "Errore sconosciuto nel salvataggio su Sheet.");
        }

        showToast("Lesson Plan generato e salvato con successo!", 4000, "bg-green-600");

    } catch (err) {
        console.error("Errore Generazione Lesson Plan:", err);
        showToast("Errore di Generazione/Salvataggio: " + err.message, 6000, "bg-red-600");
    } finally {
        generatePlanBtn.disabled = false;
        generatePlanBtn.innerHTML = `<span class="text-xl">✨</span> Genera Piano`;
        hideGlobalLoader();
    }
}

// Earnings
async function fetchMonthlyEarnings() {
    try {
        const resp = await apiGet('getMonthlyEarnings');
        const value = (resp && resp.success) ? resp.earnings : 0;
        earningsAmountDisplay.textContent = Number(value).toFixed(2);
    } catch (err) {
        earningsAmountDisplay.textContent = '--';
    }
}

// --- IND: load students & contracts ---
async function loadStudentIds() {
    studentIdSelect.innerHTML = '<option value="" disabled selected>Loading Student IDs...</option>';
    productIdSelect.innerHTML = '<option value="" disabled selected>Select a Student ID first</option>';
    productIdSelect.disabled = true;
    remainingCallsDisplay.classList.add('hidden');

    try {
        const resp = await apiGet('getStudents');
        const arr = (resp && resp.success && Array.isArray(resp.students)) ? resp.students : [];

        studentIdSelect.innerHTML = '';
        const def = document.createElement('option');
        def.value = '';
        def.disabled = true;
        def.selected = true;
        def.textContent = 'Select a student';
        studentIdSelect.appendChild(def);

        // ordina alfabeticamente ignorando maiuscole/minuscole
        arr.sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' }));

        arr.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            studentIdSelect.appendChild(opt);
        });

        studentIdSelect.disabled = false;
    } catch (err) {
        studentIdSelect.innerHTML = '<option value="" disabled selected>Error loading</option>';
    }
}

async function loadStudentContracts(studentId) {
    productIdSelect.disabled = true;
    productIdSelect.innerHTML = '<option value="" disabled selected>Loading products...</option>';
    hourlyRateInput.value = '';
    technicalDurationInput.value = '';
    contractIdInput.value = '';
    productIdInput.value = '';
    remainingCallsDisplay.classList.add('hidden');
    updateFormState();

    showGlobalLoader(); // 👈 overlay on

    try {
        const resp = await apiGet('getStudentContracts', { studentId });
        const contracts = (resp && resp.success && Array.isArray(resp.contracts)) ? resp.contracts : [];
        CURRENT_ALLOCATIONS_BY_STUDENT[studentId] = contracts;

        productIdSelect.innerHTML = '';
        const def = document.createElement('option');
        def.value = '';
        def.disabled = true;
        def.selected = true;
        def.textContent = 'Select a product/allocation';
        productIdSelect.appendChild(def);

        contracts.forEach(c => {
            const prodName = (c.product && c.product.productName) ? c.product.productName : c.productId;
            const opt = document.createElement('option');
            opt.value = c.productId;
            opt.textContent = prodName;
            opt.dataset.contractId = c.contractId;
            opt.dataset.product = JSON.stringify(c.product || {});
            opt.dataset.remainingCalls = c.leftCalls;
            productIdSelect.appendChild(opt);
        });

        productIdSelect.disabled = false;
    } catch (err) {
        productIdSelect.innerHTML = '<option value="" disabled selected>Error loading</option>';
    } finally {
        hideGlobalLoader(); // 👈 overlay off SEMPRE
    }
}

studentIdSelect.addEventListener('change', () => {
    const studentId = studentIdSelect.value;
    LAST_SELECTED_STUDENT = studentId || null;

    if (studentId) {
        // carica i contratti per questo studente
        loadStudentContracts(studentId);
    } else {
        // reset UI se nessuno studente selezionato
        productIdSelect.innerHTML = '<option value="" disabled selected>Select a Student ID first</option>';
        productIdSelect.disabled = true;
        hourlyRateInput.value = '';
        technicalDurationInput.value = '';
        contractIdInput.value = '';
        productIdInput.value = '';
        remainingCallsDisplay.classList.add('hidden');
    }

    updateFormState();
});



// --- GROUP: load products & students ---
async function loadGroupProducts() {
    productIdSelect.disabled = true;
    productIdSelect.innerHTML = '<option value="" disabled selected>Loading group products...</option>';
    try {
        const resp = await apiGet('getGroupProducts');
        const prods = (resp && resp.success && Array.isArray(resp.products)) ? resp.products : [];

        productIdSelect.innerHTML = '';
        const def = document.createElement('option');
        def.value = '';
        def.disabled = true;
        def.selected = true;
        def.textContent = 'Select a group product';
        productIdSelect.appendChild(def);

        prods.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.productId;
            opt.textContent = `${p.productName || p.productId} (${p.productId})`;
            opt.dataset.product = JSON.stringify(p); // contiene duration + rates
            productIdSelect.appendChild(opt);
        });

        productIdSelect.disabled = false;
    } catch (err) {
        productIdSelect.innerHTML = '<option value="" disabled selected>Error loading group products</option>';
    }
}

productIdSelect.addEventListener('change', async () => {
    const callType = document.querySelector('input[name="callType"]:checked').value;
    const selectedProductId = productIdSelect.value;
    productIdInput.value = selectedProductId || '';
    hourlyRateInput.value = '';
    technicalDurationInput.value = '';
    contractIdInput.value = '';
    remainingCallsDisplay.classList.add('hidden');
    hideMessage(callMessageBox);
    updateFormState();

    // prendo l'opzione selezionata
    const opt = productIdSelect.options[productIdSelect.selectedIndex];
    if (!opt || !opt.dataset.product) {
        callDurationSelect.disabled = true;
        return;
    }

    let prod = {};
    try {
        prod = JSON.parse(opt.dataset.product);
    } catch (e) {
        console.error('Error parsing product data', e);
        callDurationSelect.disabled = true;
        return;
    }

    // rate per ruolo
    const rateKey = CURRENT_COACH_ROLE;
    let displayRate = 0;
    if (rateKey && prod.rates && Object.prototype.hasOwnProperty.call(prod.rates, rateKey)) {
        displayRate = Number(prod.rates[rateKey] || 0);
    } else {
        showMessage(callMessageBox, `Errore: ruolo '${rateKey}' mancante nel prodotto.`, false);
    }

    // durata nativa
    const nativeDuration = prod.duration || '';
    technicalDurationInput.value = nativeDuration;
    // memorizza i dati base per ricalcolo override
    hourlyRateInput.dataset.baseRate = String(displayRate || 0);
    hourlyRateInput.dataset.attendees = String(prod.participants || 1);


    // set default override = durata nativa
    if (nativeDuration) {
        let found = false;
        for (let i = 0; i < callDurationSelect.options.length; i++) {
            if (callDurationSelect.options[i].value == nativeDuration) {
                callDurationSelect.value = nativeDuration;
                found = true;
                break;
            }
        }
        if (!found) {
            const newOption = document.createElement('option');
            newOption.value = nativeDuration;
            newOption.textContent = nativeDuration;
            callDurationSelect.appendChild(newOption);
            callDurationSelect.value = nativeDuration;
        }
    }

    // --- IND ---
    if (callType === "IND") {
        const contractId = opt.dataset.contractId || '';
        contractIdInput.value = contractId;
        productIdInput.value = selectedProductId;

        if (opt.dataset.unlimited === "true") {
            remainingCallsDisplay.classList.add('hidden');
        } else {
            const remaining = opt.dataset.remainingCalls;
            if (remaining !== undefined && remaining !== null && remaining !== "" && remaining !== "null" && remaining !== "undefined") {
                remainingCallsDisplay.textContent = `Remaining: ${remaining} calls`;
                remainingCallsDisplay.classList.remove('hidden');
            } else {
                remainingCallsDisplay.classList.add('hidden');
            }
        }
    }

    // --- GROUP ---
    else {
        try {
            console.log("🧩 getGroupStudents called with:", selectedProductId);
            const resp = await apiGet('getGroupStudents', { productId: selectedProductId });
            const studs = (resp && resp.success && Array.isArray(resp.students)) ? resp.students : [];

            const n = prod.participants || 2;
            groupStudentsDynamic.innerHTML = '';

            for (let i = 0; i < n; i++) {
                const sel = document.createElement('select');
                sel.className = 'form-input';
                sel.required = true;

                const def = document.createElement('option');
                def.value = '';
                def.disabled = true;
                def.selected = true;
                def.textContent = `Select student ${i + 1}`;
                sel.appendChild(def);

                studs.forEach(sid => {
                    const o = document.createElement('option');
                    o.value = sid;
                    o.textContent = sid;
                    sel.appendChild(o);
                });

                groupStudentsDynamic.appendChild(sel);
                sel.addEventListener('change', updateFormState);
            }
        } catch (err) {
            console.error("Error loading group students", err);
        }
    }

    // abilita/disabilita override + recompute
    if (displayRate > 0) {
        hourlyRateInput.value = displayRate;
        callDurationSelect.disabled = false;
    } else {
        hourlyRateInput.value = '';
        callDurationSelect.disabled = true;
    }

    recomputeUnitsAndRate();
    updateFormState();

});

// Override duration -> recompute units + coach rate
function recomputeUnitsAndRate() {
    const override = parseFloat(callDurationSelect.value || '0');
    const native = parseFloat(technicalDurationInput.value || '0');
    const units = (!native || !override) ? 0 : (override / native);

    // aggiorna campo hidden Units
    unitsInput.value = units ? units.toFixed(2) : '';

    // dati base
    const baseRateTotal = parseFloat(hourlyRateInput.dataset.baseRate || '0');
    const attendees = parseInt(hourlyRateInput.dataset.attendees || '1', 10) || 1;
    const callType = document.querySelector('input[name="callType"]:checked').value;

    // calcoli
    const perStudentBase = attendees > 0 ? (baseRateTotal / attendees) : baseRateTotal;
    const ratePerStudent = perStudentBase * units;
    const rateTotal = ratePerStudent * attendees;

    // mostra
    if (callType === "IND") {
        hourlyRateInput.value = ratePerStudent > 0 ? ratePerStudent.toFixed(2) : '';
    } else {
        hourlyRateInput.value = rateTotal > 0 ? rateTotal.toFixed(2) : '';
    }

    updateFormState();
}
callDurationSelect.addEventListener('change', recomputeUnitsAndRate);


// --- Toggle IND / GROUP ---
callTypeRadios.forEach(radio => {
    radio.addEventListener('change', async () => {
        showGlobalLoader();

        try {
            // ** 1. RESET DEI CAMPI TECNICI (SEMPRE)**
            // Li resettiamo all'inizio per pulire i valori vecchi indipendentemente dal tipo
            hourlyRateInput.value = '';
            technicalDurationInput.value = '';
            contractIdInput.value = '';
            productIdInput.value = '';
            callDurationSelect.value = '';
            unitsInput.value = '';

            // ** 2. LOGICA PRINCIPALE **
            if (radio.value === "GROUP" && radio.checked) {
                // nascondi/mostra sezioni
                studentIdContainer.classList.add('hidden');
                groupStudentsContainer.classList.remove('hidden');
                remainingCallsDisplay.classList.add('hidden');

                // Resetta la selezione dei prodotti PRIMA del caricamento
                productIdSelect.innerHTML = '<option value="" disabled selected>Loading...</option>';
                productIdSelect.disabled = true;

                // Carica la lista dei prodotti (asincrono)
                await loadGroupProducts();

                // Aggiorna lo stato del form DOPO il caricamento, per popolare i dati tecnici
                updateFormState(); // <-- CHIAMATA CORRETTA

            } else if (radio.value === "IND" && radio.checked) {
                // nascondi/mostra sezioni
                studentIdContainer.classList.remove('hidden');
                groupStudentsContainer.classList.add('hidden');

                // In INDIVIDUAL, il reset dei prodotti deve mostrare "Select a Student ID first"
                productIdSelect.innerHTML = '<option value="" disabled selected>Select a Student ID first</option>';
                productIdSelect.disabled = true; // <-- Aggiungo per coerenza

                // Carica lista studenti IND
                showGlobalLoader("Loading students...");
                await loadStudentIds();
                hideGlobalLoader();


                // updateFormState NON va chiamato qui. Sarà chiamato dall'evento di cambio studente.
            }

        } catch (err) {
            console.error("Error toggling call type:", err);
            showToast("Error loading data: " + (err.message || err), 4000, "bg-red-600");
        } finally {
            hideGlobalLoader();
        }
    });
});

// Apri form: reset senza azzerare subito le select
logCallBtn.addEventListener('click', async () => {
    switchSection(callSection);

    document.getElementById('callForm').reset();
    document.querySelector('input[name="callType"][value="IND"]').checked = true;

    // carica lista studenti
    await loadStudentIds();

    groupStudentsContainer.classList.add('hidden');
    callDateInput.value = new Date().toISOString().slice(0, 10);
    remainingCallsDisplay.classList.add('hidden');
    updateFormState();
});


// Back
document.getElementById('backToDashboardBtn').addEventListener('click', () => {
    switchSection(dashboardSection);
});

// --- Report Cards
const reportCardsSection = document.getElementById('reportCardsSection');
const reportCardsContainer = document.getElementById('reportCardsContainer');
const reportCardNoShowsContainer = document.getElementById('reportCardNoShowsContainer');
const reportCardFormSection = document.getElementById('reportCardFormSection');
const reportCardForm = document.getElementById('reportCardForm');
const backToReportCardsBtn = document.getElementById('backToReportCardsBtn');
const reportCardMessageBox = document.getElementById('reportCardMessageBox');
// storico report cards
const reportCardHistoryContainer = document.getElementById('reportCardHistoryContainer');
const reportCardHistoryTableBody = document.getElementById('reportCardHistoryTableBody');
const historyFilterMonth = document.getElementById('historyFilterMonth');


document.getElementById('viewReportCardsBtn').addEventListener('click', async () => {
    switchSection(reportCardsSection);
    await loadReportCardsPending();
    await loadReportCardHistory();
});


document.getElementById('backToDashboardFromReportsBtn').addEventListener('click', () => {
    switchSection(dashboardSection);
});

backToReportCardsBtn.addEventListener('click', () => {
    reportCardForm.reset();
    const callsTable = document.getElementById('reportCardCallsTable');
    if (callsTable) callsTable.classList.add('hidden');
    switchSection(reportCardsSection);
});

document.getElementById('backToDashboardFromDebriefBtn').addEventListener('click', () => {
    switchSection(dashboardSection);
});

async function loadReportCardsPending() {
    reportCardsContainer.innerHTML = loaderHTML("Loading pending report cards...");
    reportCardNoShowsContainer.innerHTML = "";
    reportCardNoShowsContainer.classList.add("hidden");

    try {
        // 🔹 Chiediamo sia tasks che drafts
        const [respTasks, respDrafts] = await Promise.all([
            apiGet("getReportCardTasks"),
            apiGet("getReportCardDrafts")
        ]);

        if (!respTasks.success) throw new Error(respTasks.error || "Unable to load tasks.");
        if (!respDrafts.success) throw new Error(respDrafts.error || "Unable to load drafts.");

        const tasks = respTasks.tasks || [];
        const drafts = respDrafts.drafts || [];

        LAST_DRAFTS = drafts; // ci serve per prefillare il form

        // 🔹 Merge: ogni task diventa "Write" o "Draft"
        const pending = tasks.map(t => {
            const match = drafts.find(d => d.studentId === t.studentId && d.contractId === t.contractId);
            return {
                ...t,
                alreadyDrafted: !!match,
                draftReport: match ? match.report : "",
                attendance: match ? match.attendance : ""
            };
        });

        if (!pending.length) {
            reportCardsContainer.innerHTML = '<p class="text-gray-500 text-center">No pending reports 🎉</p>';
        } else {
            let html = '<h3 class="text-xl font-semibold text-gray-800 mb-4">Pending Reports</h3><div class="grid gap-4">';
            pending.forEach(p => {
                const btnClass = p.alreadyDrafted
                    ? "bg-indigo-600 hover:bg-indigo-700"
                    : "bg-blue-600 hover:bg-blue-700";
                const btnLabel = p.alreadyDrafted ? "Edit Draft" : "Write Report";

                html += `
          <div class="p-4 bg-white rounded-xl shadow border border-gray-200">
            <h3 class="text-lg font-semibold text-gray-800">${p.name} ${p.surname} (${p.studentId})</h3>
            <p class="text-gray-600"><strong>Cadency:</strong> ${p.cadencyMonths} month(s)</p>
            <p class="text-gray-600"><strong>Calls:</strong> ${p.calls}</p>
            <button 
              class="writeReportBtn mt-3 text-white px-4 py-2 rounded-lg ${btnClass}"
              data-student="${p.studentId}" 
              data-contract="${p.contractId}"
              data-student-name="${p.name} ${p.surname}">
              ${btnLabel}
            </button>
          </div>`;
            });
            html += '</div>';
            reportCardsContainer.innerHTML = html;
        }

        // 🔹 Render dei No-shows
        if (CURRENT_COACH_ROLE === "Head Coach" && respTasks.noShows?.length) {
            const grouped = { current: [], previous: [] };
            respTasks.noShows.forEach(ns => {
                (ns.period === "previous" ? grouped.previous : grouped.current).push(ns);
            });

            let html = "";
            if (grouped.current.length) {
                html += `
          <details open class="mt-4 bg-red-50 rounded-xl border border-red-200">
            <summary class="cursor-pointer px-4 py-2 font-semibold text-red-600">
              No-show Students (Current Month)
            </summary>
            <div class="p-4">${renderNoShowList(grouped.current)}</div>
          </details>`;
            }
            if (grouped.previous.length) {
                html += `
          <details class="mt-6 bg-red-50 rounded-xl border border-red-200">
            <summary class="cursor-pointer px-4 py-2 font-semibold text-red-600">
              No-show Students (Previous Months)
            </summary>
            <div class="p-4">${renderNoShowList(grouped.previous)}</div>
          </details>`;
            }
            reportCardNoShowsContainer.innerHTML = html;
            reportCardNoShowsContainer.classList.remove("hidden");
        }

    } catch (err) {
        reportCardsContainer.innerHTML = `<p class="text-red-500 text-center">Error: ${err.message}</p>`;
    }
}


// funzione helper per disegnare lista no-shows
function renderNoShowList(list) {
    let html = '<div class="grid gap-4">';
    list.forEach(ns => {
        const isSubmitted = ns.alreadySubmitted;
        const disabledAttr = isSubmitted ? "disabled" : "";
        const btnClass = isSubmitted
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-indigo-600 hover:bg-indigo-700";
        const btnLabel = isSubmitted ? "Submitted" : "Submit";

        html += `
      <div class="p-4 bg-white rounded-xl shadow border border-gray-200 flex justify-between items-center">
        <div>
          <p class="font-semibold">${ns.name} ${ns.surname} (${ns.studentId}) — Contract ${ns.contractId}</p>
          <p class="text-gray-600">Cadency: ${ns.cadencyMonths} month(s)</p>
        </div>
        <button 
          class="submitNoShowBtn text-white px-3 py-1 rounded ${btnClass}"
          data-student="${ns.studentId}"
          data-contract="${ns.contractId}"
          ${disabledAttr}>
          ${btnLabel}
        </button>
      </div>`;
    });
    html += '</div>';
    return html;
}

// submit single no-show
document.addEventListener('click', async (e) => {
    if (e.target.classList.contains('submitNoShowBtn')) {
        const studentId = e.target.dataset.student;
        const contractId = e.target.dataset.contract;
        try {
            const resp = await apiPost('submitNoShow', { studentId, contractId });
            if (!resp.success) throw new Error(resp.error || "Failed to submit no-show");

            // disabilita il bottone subito
            e.target.disabled = true;
            e.target.classList.add("bg-gray-400", "cursor-not-allowed");
            e.target.classList.remove("bg-indigo-600", "hover:bg-indigo-700");
            e.target.textContent = "Submitted";

            if (resp.status === "inserted") {
                showToast(`No-show submitted for ${studentId}`, 4000, "bg-green-600");
            } else if (resp.status === "updated") {
                showToast(`No-show for ${studentId} was already submitted (updated).`, 4000, "bg-green-600");
            }
        } catch (err) {
            showToast("Error: " + err.message, 5000, "bg-red-600");
        }
    }
});


// submit all no-shows
document.addEventListener('click', async (e) => {
    if (e.target.id === 'submitAllNoShowsBtn') {
        const buttons = document.querySelectorAll('.submitNoShowBtn');
        for (const btn of buttons) {
            if (btn.disabled) continue; // già submitted
            const studentId = btn.dataset.student;
            const contractId = btn.dataset.contract;
            try {
                const resp = await apiPost('submitNoShow', { studentId, contractId });
                if (resp.success) {
                    btn.disabled = true;
                    btn.classList.add("bg-gray-400", "cursor-not-allowed");
                    btn.classList.remove("bg-indigo-600", "hover:bg-indigo-700");
                    btn.textContent = "Submitted";
                }
            } catch (err) {
                console.error("Error submitting no-show", err);
            }
        }
        showToast("All no-shows submitted!", 4000, "bg-green-600");
    }
});


// click write/edit (prefill sempre se esiste una bozza)
document.addEventListener('click', (e) => {
    if (!e.target.classList.contains('writeReportBtn')) return;

    const studentId = e.target.dataset.student;
    const contractId = e.target.dataset.contract;

    // reset base
    reportCardForm.reset();
    document.getElementById('rcStudentId').value = studentId;
    document.getElementById('rcContractId').value = contractId;
    document.getElementById('rcStudentName').value = e.target.dataset.studentName || '';

    // prefill se esiste in LAST_DRAFTS (indipendentemente dal bottone)
    const existing = (LAST_DRAFTS || []).find(d => d.studentId === studentId && d.contractId === contractId);
    if (existing) {
        document.getElementById('rcAttendance').value = existing.attendance || '';
        document.getElementById('rcReport').value = existing.report || '';
    }

    // nascondi eventuale tabella visibile da prima
    document.getElementById('reportCardCallsTable').classList.add('hidden');
    switchSection(document.getElementById('reportCardFormSection'));
    loadStudentCallsForMonth(studentId);
});

// submit report card (single handler, with spinner)
reportCardForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    hideMessage(reportCardMessageBox);

    const submitBtn = reportCardForm.querySelector('button[type="submit"]');
    const orig = submitBtn.innerHTML;
    submitBtn.innerHTML = `
    <div class="spinner-container">
      <div class="spinner-dot"></div>
      <div class="spinner-dot"></div>
      <div class="spinner-dot"></div>
    </div>`;
    submitBtn.disabled = true;

    const payload = {
        studentId: document.getElementById('rcStudentId').value,
        contractId: document.getElementById('rcContractId').value,
        attendance: document.getElementById('rcAttendance').value,
        report: document.getElementById('rcReport').value
    };

    try {
        const resp = await apiPost('submitReportCard', payload);
        if (!resp.success) throw new Error(resp.error || 'Error saving report.');

        showMessage(reportCardMessageBox, 'Report card saved as draft!', true);

        setTimeout(async () => {
            reportCardForm.reset();
            document.getElementById('reportCardCallsTable').classList.add('hidden');
            switchSection(reportCardsSection);
            await loadReportCardsPending();
            await loadReportCardHistory();
        }, 800);

    } catch (err) {
        showMessage(reportCardMessageBox, err.message, false);
    } finally {
        submitBtn.innerHTML = orig;
        submitBtn.disabled = false;
    }
});

// Submit call
document.getElementById('callForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    hideMessage(callMessageBox);

    const orig = submitBtn.innerHTML;
    submitBtn.innerHTML = '<div class="spinner-container"><div class="spinner-dot"></div><div class="spinner-dot"></div><div class="spinner-dot"></div></div>';
    submitBtn.disabled = true;

    try {
        const callType = document.querySelector('input[name="callType"]:checked').value;

        const payload = {
            callDate: callDateInput.value,
            callDuration: parseFloat(callDurationSelect.value), // minuti (override)
            units: parseFloat(unitsInput.value),                // Units Used (per debug/compat)
            hourlyRate: parseFloat(hourlyRateInput.value) || 0, // Coach Rate (per debug/compat)
            coachName: CURRENT_COACH_NAME,
            productId: productIdInput.value || productIdSelect.value || '',
            notes: document.getElementById('notes').value || "",  // 👈 virgola sopra
            attendance: document.getElementById('attendance').value || "YES" // 👈 sempre presente
        };


        if (callType === "IND") {
            payload.studentId = studentIdSelect.value;
            payload.contractId = contractIdInput.value;
        } else if (callType === "GROUP") {
            // raccoglie tutti gli ID selezionati dal gruppo
            const selects = groupStudentsDynamic.querySelectorAll('select');
            const chosenIds = Array.from(selects).map(s => s.value).filter(Boolean);

            // se nessuno selezionato → errore
            if (!chosenIds.length) throw new Error("Please select all group students before logging.");

            payload.studentIds = chosenIds;
            payload.contractId = null;
            payload.isGroup = true; // 👈 utile lato backend (non obbligatorio ma chiaro)
        }

        const resp = await apiPost('logCall', payload);
        if (!resp.success) throw new Error(resp.error || 'Error logging call.');

        showMessage(callMessageBox, 'Call logged successfully!', true);
        hideGlobalLoader();
        document.getElementById('callForm').reset();

        // reinserisci la data di oggi anche dopo il reset
        callDateInput.value = new Date().toISOString().slice(0, 10);

        contractIdInput.value = '';
        productIdInput.value = '';
        hourlyRateInput.value = '';
        technicalDurationInput.value = '';
        remainingCallsDisplay.classList.add('hidden');
    } catch (err) {
        showMessage(callMessageBox, err.message || String(err), false);
    } finally {
        updateFormState();
        fetchMonthlyEarnings();
        submitBtn.innerHTML = orig;
        submitBtn.disabled = false;
    }
});

async function loadReportCardHistory() {
    reportCardHistoryTableBody.innerHTML = `
    <tr><td colspan="5" class="text-center p-4">Loading...</td></tr>`;

    try {
        const resp = await apiGet('getReportCardHistory');
        if (!resp.success) throw new Error(resp.error || 'Unable to load history.');

        const rows = resp.history || [];   // 👈 non più drafts

        // filtro per mese scelto (formato "2025-09")
        const filterValue = historyFilterMonth.value;
        const filtered = rows.filter(r => {
            if (!filterValue) return true;
            if (!r.dateISO) return false;

            try {
                let ym = "";
                if (r.dateISO instanceof Date) {
                    ym = r.dateISO.toISOString().slice(0, 7);
                } else {
                    const dParsed = new Date(r.dateISO);
                    if (!isNaN(dParsed)) ym = dParsed.toISOString().slice(0, 7);
                }
                return ym === filterValue;
            } catch {
                return false;
            }
        });

        if (!filtered.length) {
            reportCardHistoryTableBody.innerHTML = `
        <tr><td colspan="5" class="text-center p-4">No report cards found</td></tr>`;

            // 👉 gestione Send All anche se tabella vuota
            const sendAllBtn = document.getElementById('sendAllReportCardsBtn');
            if (sendAllBtn) {
                if (CURRENT_COACH_ROLE === "Head Coach") {
                    sendAllBtn.classList.remove("hidden");
                } else {
                    sendAllBtn.classList.add("hidden");
                }
            }

            return;
        }

        reportCardHistoryTableBody.innerHTML = '';
        filtered.forEach(r => {
            // format date
            let formattedDate = '';
            try {
                if (r.dateISO instanceof Date) {
                    formattedDate = r.dateISO.toISOString().slice(0, 10);
                } else {
                    const d = new Date(r.dateISO);
                    formattedDate = isNaN(d) ? String(r.dateISO).slice(0, 10) : d.toISOString().slice(0, 10);
                }
            } catch {
                formattedDate = String(r.dateISO).slice(0, 10);
            }

            const sentIcon = r.sent ? '✅' : '❌';
            const reportExcerpt = (r.report || '').length > 150
                ? r.report.substring(0, 150) + '…'
                : (r.report || '');

            const row = document.createElement('tr');
            row.innerHTML = `
        <td class="border px-4 py-2">${formattedDate}</td>
        <td class="border px-4 py-2">${r.name || ''} ${r.surname || ''}</td>
        <td class="border px-4 py-2">${r.attendance || ''}</td>
        <td class="border px-4 py-2">${reportExcerpt}</td>
        <td class="border px-4 py-2 text-center">${sentIcon}</td>
      `;
            reportCardHistoryTableBody.appendChild(row);
        });

        // 👉 gestione Send All dopo aver popolato la tabella
        const sendAllBtn = document.getElementById('sendAllReportCardsBtn');
        if (sendAllBtn) {
            if (CURRENT_COACH_ROLE === "Head Coach") {
                sendAllBtn.classList.remove("hidden");
            } else {
                sendAllBtn.classList.add("hidden");
            }
        }

    } catch (err) {
        reportCardHistoryTableBody.innerHTML = `
      <tr><td colspan="5" class="text-center p-4 text-red-500">
        Error: ${err.message}
      </td></tr>`;
    }
}

// ricarica su cambio filtro
historyFilterMonth.addEventListener('change', loadReportCardHistory);

async function loadStudentCallsForMonth(studentId) {
    const table = document.getElementById('reportCardCallsTable');
    const tbody = document.getElementById('reportCardCallsTableBody');
    table.classList.remove('hidden');
    tbody.innerHTML = `<tr><td colspan="2">${loaderHTML("Loading calls...")}</td></tr>`;

    try {
        const resp = await apiGet('getStudentCallsForMonth', { studentId });
        if (!resp.success) throw new Error(resp.error || 'Unable to load calls');

        const calls = resp.calls || [];
        if (!calls.length) {
            tbody.innerHTML = '<tr><td colspan="2" class="text-center p-4">No calls this month</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        calls.forEach(c => {
            const row = document.createElement('tr');
            row.innerHTML = `
        <td class="border px-4 py-2">${c.date}</td>
        <td class="border px-4 py-2">${c.attendance}</td>
      `;
            tbody.appendChild(row);
        });
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="2" class="text-red-500 text-center p-4">Error: ${err.message}</td></tr>`;
    }
}

// --- Send All: modal di conferma + overlay loader ---
const sendAllBtn = document.getElementById('sendAllReportCardsBtn');
const confirmModal = document.getElementById('sendAllConfirmModal');
const confirmSendAllBtn = document.getElementById('confirmSendAllBtn');
const cancelSendAllBtn = document.getElementById('cancelSendAllBtn');

function openSendAllModal() { confirmModal?.classList.remove('hidden'); }
function closeSendAllModal() { confirmModal?.classList.add('hidden'); }

// Apri modal (solo Head Coach)
sendAllBtn?.addEventListener('click', () => {
    if (CURRENT_COACH_ROLE !== "Head Coach") {
        alert("Only Head Coach can send report cards.");
        return;
    }
    openSendAllModal();
});

// Chiudi modal
cancelSendAllBtn?.addEventListener('click', closeSendAllModal);
// Chiudi anche cliccando il backdrop
confirmModal?.addEventListener('click', (e) => {
    if (e.target === confirmModal) closeSendAllModal();
});

// Conferma → invia
confirmSendAllBtn?.addEventListener('click', async () => {
    closeSendAllModal();

    showGlobalLoader();
    try {
        const now = new Date();
        const resp = await apiPost('sendAllReportCards', {
            year: now.getFullYear(),
            month: now.getMonth()
        });
        if (!resp.success) throw new Error(resp.error || "Failed to send report cards");

        console.log("SendAll:", resp.message || "Report cards sent!");
        showToast(resp.message || "Report cards sent!", 4000, "bg-green-600");

        await loadReportCardHistory(); // refresh tabella
    } catch (err) {
        showToast("Error: " + (err.message || err), 5000, "bg-red-600");
    } finally {
        hideGlobalLoader();
    }
});



// ---- AI helper for Report Card ----
(function setupAIHelper() {
    const suggestBtn = document.getElementById('aiSuggestBtn');
    const refineBtn = document.getElementById('aiRefineBtn');
    const msg = document.getElementById('aiHelperMsg');
    const textarea = document.getElementById('rcReport');

    if (!suggestBtn || !refineBtn || !textarea) return;

    function setBusy(el, busyText) {
        el.dataset._orig = el.textContent;
        el.disabled = true;
        el.textContent = busyText;
        if (msg) msg.textContent = '';
    }
    function unsetBusy(el) {
        el.disabled = false;
        el.textContent = el.dataset._orig || el.textContent;
    }

    async function callAI(actionPayload) {
        // chiama il backend Apps Script tramite il tuo apiPost esistente
        const resp = await apiPost('generateReportCardText', actionPayload);
        if (!resp || !resp.success) throw new Error(resp?.error || 'Generation failed');
        return resp.suggestion || '';
    }

    suggestBtn.addEventListener('click', async () => {
        setBusy(suggestBtn, 'Generating...');
        try {
            const studentId = document.getElementById('rcStudentId').value;
            const studentName = document.getElementById('rcStudentName').value || 'Student';
            const attendance = document.getElementById('rcAttendance').value || '';

            const suggestion = await callAI({
                mode: 'suggest',
                studentId, studentName, attendance
            });

            textarea.value = suggestion || textarea.value;
            if (msg) msg.textContent = '✅ Suggestion inserted.';
        } catch (err) {
            if (msg) msg.textContent = '❌ ' + (err?.message || 'Error generating text');
        } finally {
            unsetBusy(suggestBtn);
        }
    });

    // Lesson Plan
    if (generatePlanBtn) {
        generatePlanBtn.addEventListener('click', handleGeneratePlan);
    }

    refineBtn.addEventListener('click', async () => {
        setBusy(refineBtn, 'Refining...');
        try {
            const studentId = document.getElementById('rcStudentId').value;
            const studentName = document.getElementById('rcStudentName').value || 'Student';
            const currentText = textarea.value;

            if (!currentText || !currentText.trim()) {
                if (msg) msg.textContent = 'ℹ️ Nothing to refine. Write something first or use “Suggest text”.';
                unsetBusy(refineBtn);
                return;
            }

            const refined = await callAI({
                mode: 'refine',
                studentId, studentName,
                currentText
            });

            if (refined) textarea.value = refined;
            if (msg) msg.textContent = '✅ Text refined.';
        } catch (err) {
            if (msg) msg.textContent = '❌ ' + (err?.message || 'Error refining text');
        } finally {
            unsetBusy(refineBtn);
        }
    });
})();
(function restoreSession() {
    try {
        const raw = localStorage.getItem("coachSession");
        if (!raw) return;
        const saved = JSON.parse(raw);
        if (!saved) return;

        CURRENT_COACH_NAME = saved.name || saved.id;
        CURRENT_COACH_ROLE = saved.role || "";

        if (coachNameDisplay) coachNameDisplay.textContent = CURRENT_COACH_NAME;
        if (callSectionCoachNameDisplay) callSectionCoachNameDisplay.textContent = CURRENT_COACH_NAME;
        document.getElementById('googleLoginContainer')?.classList.add('hidden');

        switchSection(dashboardSection);
        fetchMonthlyEarnings();
        loadStudentIds();
    } catch (e) {
        console.warn("Restore session failed:", e);
        localStorage.removeItem("coachSession");
    }
})();

viewFlashcardsBtn.addEventListener('click', async () => {
    switchSection(flashcardsSection);
    await loadFlashcards();
});

backToDashboardFromFlashcardsBtn.addEventListener('click', () => {
    switchSection(dashboardSection);
});

document.getElementById('viewTeachingMaterialsBtn').addEventListener('click', () => {
    switchSection(document.getElementById('teachingMaterialsSection'));
});

async function loadFlashcards() {
    const select = document.getElementById('flashcardsStudentSelect');
    const container = document.getElementById('flashcardsContainer');

    // 🧹 CORREZIONE: Pulizia preventiva dei listener globali e del dropdown 
    // per evitare sessioni "fantasma" in caso di ri-apertura.
    document.onkeydown = null;
    if (select) select.onchange = null;

    container.innerHTML = loaderHTML("Loading students...");

    try {
        // Carica lista studenti
        const resp = await apiGet('getStudents');
        if (!resp.success) throw new Error(resp.error || "Unable to load students.");
        const students = resp.students || [];

        // Popola dropdown
        select.innerHTML = '<option value="" disabled selected>Select a student</option>';
        students.sort((a, b) => a.localeCompare(b, 'en', { sensitivity: 'base' }));
        students.forEach(id => {
            const opt = document.createElement('option');
            opt.value = id;
            opt.textContent = id;
            select.appendChild(opt);
        });

        container.innerHTML = '<p class="text-gray-500">Select a student to load flashcards.</p>';

        // ===========================
        // 📚 CAMBIO STUDENTE
        // ===========================
        select.onchange = async () => {
            // Pulizia immediata se una sessione è già attiva (es. l'utente cambia studente a metà)
            document.onkeydown = null;

            const studentId = select.value;
            container.innerHTML = loaderHTML("Loading flashcards...");

            try {
                const respCards = await apiGet('getFlashcards', { studentId });
                if (!respCards.success) throw new Error(respCards.error || "Unable to load flashcards.");
                const cards = respCards.cards || [];

                if (!cards.length) {
                    container.innerHTML = '<p class="text-gray-500">No flashcards found.</p>';
                    return;
                }

                // 🔢 Calcolo punteggi ponderati
                cards.forEach(c => {
                    const attempts = Number(c.attempts) || 0;
                    const correct = Number(c.correct) || 0;
                    const base = attempts - correct;
                    const penalty = (c.status === "unknown" ? 2 : 0);
                    c.score = base + penalty;
                    if (c.score < 1) c.score = 1;
                });

                // 🎯 Smart Deck ponderato
                function buildSmartDeck(cards) {
                    const total = cards.reduce((sum, c) => sum + (c.score || 1), 0);
                    let cumulative = 0;
                    const smartDeck = cards.map(c => {
                        const w = (c.score || 1) / total;
                        const seg = { from: cumulative, to: cumulative + w };
                        cumulative += w;
                        return { range: seg, card: c };
                    });
                    // Normalizza l'ultimo "to" a 1.0 per sicurezza floating point
                    if (smartDeck.length > 0) smartDeck[smartDeck.length - 1].range.to = 1.0;
                    return smartDeck;
                }

                function pickCardFromSmartDeck(deck) {
                    const x = Math.random();
                    let low = 0, high = deck.length - 1;
                    let mid = Math.floor((low + high) / 2);

                    // Ricerca binaria
                    while (low < high) {
                        const seg = deck[mid].range;
                        if (x < seg.from) {
                            high = mid - 1;
                        } else if (x >= seg.to) {
                            low = mid + 1;
                        } else {
                            break; // Trovato il segmento
                        }
                        mid = Math.floor((low + high) / 2);
                    }
                    return deck[mid].card;
                }

                // ===========================
                // 🧠 Sessione Flashcards - Stato dinamico
                // ===========================
                const smartDeck = buildSmartDeck(cards);
                let sessionTotalSteps = 20; // CORREZIONE: Variabile dinamica
                let stepIndex = 0;
                let pendingFlashcardUpdates = [];
                const cardsByEn = new Map(cards.map(c => [String(c.en || "").toLowerCase(), c]));

                // 🧹 Cleanup centralizzato (rimuove solo listener tastiera, gli altri sono usa-e-getta)
                function cleanupSession() {
                    document.onkeydown = null;
                }

                function renderCard(index, total, card) {
                    const it = card.it || "";
                    const en = card.en || "";
                    const progress = (index / total) * 100;

                    container.innerHTML = `
            <div class="w-full bg-gray-200 rounded-full h-3 mb-4">
              <div class="bg-blue-600 h-3 rounded-full transition-all duration-500" style="width:${progress}%"></div>
            </div>
            <p class="text-sm text-gray-500 mb-4">Card ${index + 1} of ${total}</p>

            <div class="relative w-72 h-48 perspective mx-auto">
              <div id="flashcard" class="absolute w-full h-full transition-transform duration-500 transform-style-preserve-3d cursor-pointer">
                <div class="absolute w-full h-full flex items-center justify-center text-2xl font-bold bg-blue-900 text-white rounded-xl shadow backface-hidden">${it}</div>
                <div class="absolute w-full h-full flex items-center justify-center text-2xl font-bold bg-blue-600 text-white rounded-xl shadow backface-hidden rotate-y-180">${en}</div>
              </div>
            </div>

            <div class="flex gap-8 mt-6 justify-center items-center">
              <button id="btnUnknown" class="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg text-lg font-semibold">⬅️ Still learning</button>
              <button id="btnKnown" class="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-lg font-semibold">I know it ➡️</button>
            </div>
          `;

                    requestAnimationFrame(() => {
                        const cardEl = document.getElementById('flashcard');
                        const btnKnown = document.getElementById('btnKnown');
                        const btnUnknown = document.getElementById('btnUnknown');
                        if (!cardEl || !btnKnown || !btnUnknown) return;

                        cardEl.addEventListener('click', () => cardEl.classList.toggle("rotate-y-180"));

                        function handleAnswer(status) {
                            pendingFlashcardUpdates.push({ en, status, timestamp: new Date().toISOString() });
                            stepIndex++;
                            // CORREZIONE: Controllo rispetto al totale dinamico
                            if (stepIndex < sessionTotalSteps) renderNextCard();
                            else showSummaryAndFlush();
                        }

                        btnKnown.addEventListener('click', () => handleAnswer("known"));
                        btnUnknown.addEventListener('click', () => handleAnswer("unknown"));

                        document.onkeydown = (e) => {
                            if (e.key === "ArrowRight") handleAnswer("known");
                            if (e.key === "ArrowLeft") handleAnswer("unknown");
                            if (["ArrowUp", "ArrowDown", " ", "Enter"].includes(e.key))
                                cardEl.classList.toggle("rotate-y-180");
                        };

                        let touchStartX = 0;
                        cardEl.addEventListener("touchstart", e => touchStartX = e.changedTouches[0].screenX);
                        cardEl.addEventListener("touchend", e => {
                            const diff = e.changedTouches[0].screenX - touchStartX;
                            if (Math.abs(diff) > 50)
                                handleAnswer(diff > 0 ? "known" : "unknown");
                            else
                                cardEl.classList.toggle("rotate-y-180");
                        });
                    });
                }

                function renderNextCard() {
                    const next = pickCardFromSmartDeck(smartDeck);
                    // Usa il totale dinamico per il progress bar
                    renderCard(stepIndex, sessionTotalSteps, next);
                }

                async function showSummaryAndFlush() {
                    cleanupSession();

                    const known = pendingFlashcardUpdates.filter(c => c.status === "known").length;
                    const unknown = pendingFlashcardUpdates.filter(c => c.status === "unknown").length;
                    const percent = Math.round((known / Math.max(1, known + unknown)) * 100);

                    container.innerHTML = `
            <p class="text-xl font-bold text-gray-800 mb-4">🎉 You’ve completed the session!</p>
            <p class="text-lg text-green-600">✅ Known: ${known}</p>
            <p class="text-lg text-red-600">❌ Still learning: ${unknown}</p>
            <p class="text-lg text-blue-600 mb-6">📊 Success rate: ${percent}%</p>
            ${unknown > 0 ? `<button id="retryRedBtn" class="px-4 py-2 bg-red-600 text-white rounded-lg shadow hover:bg-red-700">🔄 Retry only the red ones</button>` : ""}
          `;

                    try {
                        if (pendingFlashcardUpdates.length)
                            await apiPost('updateFlashcardStatus', { studentId, cards: pendingFlashcardUpdates });
                    } catch (err) {
                        console.error("❌ Error saving updates:", err);
                    }

                    if (unknown > 0) {
                        document.getElementById('retryRedBtn').addEventListener('click', () => {
                            const redCards = pendingFlashcardUpdates
                                .filter(c => c.status === "unknown")
                                .map(u => cardsByEn.get(String(u.en || "").toLowerCase()))
                                .filter(Boolean);

                            if (!redCards.length) return;
                            redCards.forEach(rc => rc.score = Math.max(rc.score || 1, 1));

                            // Reset della sessione
                            pendingFlashcardUpdates = [];
                            stepIndex = 0;

                            // CORREZIONE: Imposta il nuovo totale per il retry (10)
                            sessionTotalSteps = 10;

                            const redDeck = buildSmartDeck(redCards);

                            // Sovrascrive la funzione per usare il deck e il totale corretti
                            function renderNextRed() {
                                const next = pickCardFromSmartDeck(redDeck);
                                renderCard(stepIndex, sessionTotalSteps, next);
                            }

                            // Assegna la nuova logica per il prossimo round
                            renderNextCard = renderNextRed;
                            renderNextCard();
                        });
                    }
                }

                // 🚀 Avvia la prima carta (inizialmente sessionTotalSteps è 20)
                renderNextCard();

            } catch (err) {
                container.innerHTML = `<p class="text-red-500 text-center">Error loading flashcards: ${err.message}</p>`;
            }
        };
    } catch (err) {
        container.innerHTML = `<p class="text-red-500 text-center">Error loading students: ${err.message}</p>`;
    }
}

// --- NUOVA LOGICA PER IL CARICAMENTO DEL LESSON PLAN (TESTO) ---

document.addEventListener('DOMContentLoaded', () => {
    // Le variabili sono definite all'esterno, quindi non le ridefiniamo qui.
    // Usiamo direttamente: debriefStudentSelect, lessonPlanContent, etc.

    // Aggiungiamo un controllo di sicurezza per la nuova variabile
    if (!debriefStudentSelect) {
        console.warn("Elemento 'debriefStudentSelect' non trovato.");
        return;
    }

    // Qui era il vecchio listener. Lo sovrascriviamo con la nuova logica.
    debriefStudentSelect.addEventListener('change', async (event) => {
        const studentId = event.target.value;

        // 1. Pulizia e check
        if (!studentId) {
            if (lessonPlanContent) lessonPlanContent.value = 'Seleziona uno studente.';
            return;
        }

        // 2. Stato di caricamento
        if (lessonPlanContent) lessonPlanContent.value = 'Caricamento Lesson Plan...';

        try {
            // ✅ CHIAMATA ALLA NUOVA API GET
            // Chiama 'getLessonPlanContent' che legge il testo dal Google Sheet
            const response = await apiGet('getLessonPlanContent', { studentId: studentId });

            if (response.success && response.content !== undefined) {
                // Incolla il testo puro nel campo
                lessonPlanContent.value = response.content;

                // Popola il div di anteprima con il testo formattato
                const aiPreviewDiv = document.getElementById('aiPreview_lessonplan_content');
                if (aiPreviewDiv) {
                    aiPreviewDiv.innerHTML = formatLessonPlan(response.content);
                }

            } else {
                // Errore o contenuto vuoto
                const errorMessage = response.error || 'Nessun Lesson Plan trovato.';
                lessonPlanContent.value = errorMessage;

                const aiPreviewDiv = document.getElementById('aiPreview_lessonplan_content');
                if (aiPreviewDiv) {
                    aiPreviewDiv.innerHTML = `<p class="text-gray-500">${errorMessage}</p>`;
                }
            }
        } catch (error) {
            console.error("Errore critico nel caricamento del lesson plan:", error);
            lessonPlanContent.value = 'Errore tecnico durante la richiesta del Lesson Plan.';
        }
    });
});
