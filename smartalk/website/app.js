// ====================================================================
// CONFIGURAZIONE GLOBALE DELLE PAGINE
// ====================================================================
const PAGE_CONFIG = {
    'home': {
        navId: 'home',
        it: { title: 'Smartalk | English Coaching per Professionisti' },
        en: { title: 'Smartalk | English Coaching for Professionals' }
    },
    'about': {
        navId: 'chisiamo',
        it: { title: 'Chi Siamo | Smartalk' },
        en: { title: 'About Us | Smartalk' }
    },
    'terms': {
        navId: null, // Nessun link attivo nella navbar
        it: { title: 'Termini e Condizioni | Smartalk' },
        en: { title: 'Terms and Conditions | Smartalk' }
    },
    'policy': {
        navId: null, // Nessun link attivo nella navbar
        it: { title: 'Policy | Smartalk' },
        en: { title: 'Policy | Smartalk' }
    }
};

// ====================================================================
// FUNZIONE PER EVIDENZIARE IL LINK ATTIVO NELLA NAVBAR
// ====================================================================
function setActiveNav(pageId) {
    if (!pageId) return;

    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('text-red-600');
        link.classList.add('hover:text-blue-600');
    });

    const activeLinkIt = document.querySelector(`header[data-lang="it"] #nav-${pageId} .nav-link`);
    if (activeLinkIt) {
        activeLinkIt.classList.add('text-red-600');
        activeLinkIt.classList.remove('hover:text-blue-600');
    }
    const activeLinkEn = document.querySelector(`header[data-lang="en"] #nav-${pageId} .nav-link`);
    if (activeLinkEn) {
        activeLinkEn.classList.add('text-red-600');
        activeLinkEn.classList.remove('hover:text-blue-600');
    }
}

// ====================================================================
// FUNZIONE PER GESTIRE IL CAMBIO LINGUA
// ====================================================================
function setupLanguageSwitcher() {
    const path = window.location.pathname;
    const pathParts = path.split('/').filter(p => p); // Rimuove parti vuote
    const currentPage = pathParts.length > 1 ? pathParts[1] : 'home';

    const switcherToEn = document.getElementById('lang-switcher-en');
    const switcherToIt = document.getElementById('lang-switcher-it');

    if (switcherToEn) {
        switcherToEn.href = `/en/${currentPage}`;
    }
    if (switcherToIt) {
        switcherToIt.href = `/it/${currentPage}`;
    }
}


// ====================================================================
// FUNZIONE PRINCIPALE DI CARICAMENTO PAGINA
// ====================================================================
function handlePageLoad() {
    const path = window.location.pathname;
    const lang = (path.split('/')[1] || 'it').toLowerCase();
    const pageName = (path.split('/')[2] || 'home').toLowerCase();

    const isEnglish = (lang === 'en');

    // --- 1. Gestione Visibilità dei Contenuti ---
    document.querySelectorAll('[data-lang="it"]').forEach(el => el.style.display = isEnglish ? 'none' : 'block');
    document.querySelectorAll('[data-lang="en"]').forEach(el => el.style.display = isEnglish ? 'block' : 'none');

    // --- 2. Configurazione Specifica della Pagina ---
    const config = PAGE_CONFIG[pageName];
    if (config) {
        document.title = isEnglish ? config.en.title : config.it.title;
        setActiveNav(config.navId);
    }

    // --- 3. Imposta la lingua del documento e lo switcher ---
    document.documentElement.lang = lang;
    setupLanguageSwitcher();
}

// Esegui la funzione principale quando il DOM è pronto
document.addEventListener('DOMContentLoaded', handlePageLoad);