// --- CONFIGURAZIONE DELLE TRADUZIONI ---
const Translations = {
    // Configurazione per la pagina Policy
    policy: {
        it: {
            title: 'Accordo Mutuo per il Completamento del Corso',
            subtitle: 'Etica per la buona riuscita del percorso di apprendimento',
            ack: 'Ho letto e compreso l\'Informativa di Cancellazione e Scadenza.',
        },
        en: {
            title: 'Mutual Agreement for the Completion of the Course',
            subtitle: 'Ethics for the successful completion of the learning path',
            ack: 'I have read and understood the Cancellation & Expiration Policy.',
        }
    },
    // Configurazione per la pagina Terms and Conditions
    terms: {
        it: {
            title: 'Termini e Condizioni',
            subtitle: '', // Sottotitolo non presente in questa pagina
            ack: 'Ho letto e compreso i Termini e Condizioni.',
        },
        en: {
            title: 'Terms and Conditions',
            subtitle: '', // Sottotitolo non presente in questa pagina
            ack: 'I have read and understood the Terms and Conditions.',
        }
    }
};

// --- LOGICA DI NASCONDIMENTO (HIDING) E TRADUZIONE ---
function setLegalLanguage() {
    const path = window.location.pathname;
    const isEnglishPage = path.includes('/en-');
    
    // Determina se siamo sulla pagina Policy o Terms
    const pageKey = path.includes('/terms') ? 'terms' : 'policy'; 
    const currentTranslations = Translations[pageKey];

    // Selettori dinamici per i blocchi di contenuto
    const itContentBlockIds = pageKey === 'policy' ? ['it-content-1', 'it-content-2'] : ['it-content-terms'];
    const enContentBlockIds = pageKey === 'policy' ? ['en-content-1', 'en-content-2'] : ['en-content-terms'];

    // Nascondi il contenuto non desiderato
    const contentToHideIds = isEnglishPage ? itContentBlockIds : enContentBlockIds;
    const contentToShowIds = isEnglishPage ? enContentBlockIds : itContentBlockIds;

    contentToHideIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    
    // Opzionale: Se vuoi mostrare solo una colonna e centrarla
    // contentToShowIds.forEach(id => {
    //     const el = document.getElementById(id);
    //     if (el) el.style.gridColumn = '1 / -1'; // Se si usa grid-cols-2, lo centra
    // });
    
    // Aggiorna titoli e testo del modulo
    const lang = isEnglishPage ? 'en' : 'it';

    if(document.getElementById('main-title')) document.getElementById('main-title').textContent = currentTranslations[lang].title;
    if(document.getElementById('main-subtitle')) document.getElementById('main-subtitle').textContent = currentTranslations[lang].subtitle;
    if(document.getElementById('confirmation-text')) document.getElementById('confirmation-text').textContent = currentTranslations[lang].ack;
    
    // Testi generici del modulo
    if(document.getElementById('email-label')) document.getElementById('email-label').textContent = lang === 'en' ? 'Your Email:' : 'La tua Email:';
    if(document.getElementById('confirm-button-text')) document.getElementById('confirm-button-text').textContent = lang === 'en' ? 'Confirm' : 'Conferma';
}

// Chiama la funzione quando il contenuto è caricato
document.addEventListener('DOMContentLoaded', setLegalLanguage);


// --- SCRIPT DI CONFERMA (UNCHANGED, MA ADATTATO PER LA LOCALIZZAZIONE MESSAGGI) ---
const checkbox = document.getElementById("ack");
const button = document.getElementById("confirmBtn");

if (checkbox && button) {
    checkbox.addEventListener("change", () => {
        button.disabled = !checkbox.checked;
        button.style.cursor = checkbox.checked ? "pointer" : "not-allowed";
        // Al cambio, pulisce il messaggio precedente
        document.getElementById("confirmation-message").innerHTML = '';
    });
}

function showMessage(type) {
    const messageBox = document.getElementById("confirmation-message");
    const isEnglishPage = window.location.pathname.includes('/en-');
    
    if (!messageBox) return;

    if (type === 'success') {
        messageBox.innerHTML = `<strong class="text-green-600">✅ Thank you for accepting the policy.</strong><br><em class="text-green-600">Grazie per aver accettato l'informativa.</em>`;
    } else if (type === 'error') {
        const errorMessage = isEnglishPage ? "❌ Please enter your email." : "❌ Per favore, inserisci la tua email.";
        messageBox.innerHTML = `<strong class="text-red-600">${errorMessage}</strong>`;
    } else if (type === 'info') {
        const infoMessage = isEnglishPage ? "Submitting..." : "Invio in corso...";
        messageBox.innerHTML = `<span class="text-blue-600">${infoMessage}</span>`;
    }
}

// La funzione di invio è globale e deve essere definita qui per onclick
window.submitConfirmation = function() {
    const emailInput = document.getElementById("userEmail");
    if (!emailInput || !emailInput.value) {
        showMessage("error");
        return;
    }

    showMessage("info");
    button.disabled = true;

    const data = new URLSearchParams();
    data.append("email", emailInput.value);
    
    // Identifica se è Policy o Terms per la traccia nel Google Sheet
    const isTerms = window.location.pathname.includes('/terms');
    data.append("name", isTerms ? "Terms Acceptance" : "Policy Acceptance"); 

    fetch("https://script.google.com/macros/s/AKfycby2NiEUTCFtaauYOnCcLYPkxP8Z4snv_1ZEGOYVbzs_GuTjiUC1KkzPDAw_RW6-l76_tg/exec", {
        method: "POST",
        body: data
    })
    .then(res => res.text())
    .then(response => {
        showMessage("success");
        if(button) button.style.display = "none";
        if(checkbox) checkbox.disabled = true;
        if(emailInput) emailInput.disabled = true;
    })
    .catch(err => {
        const isEnglishPage = window.location.pathname.includes('/en-');
        const errorMessage = isEnglishPage ? "Something went wrong: " + err : "Qualcosa è andato storto: " + err;
        document.getElementById("confirmation-message").innerHTML = `<strong class="text-red-600">❌ ${errorMessage}</strong>`;
        if(button) button.disabled = false;
    });
}