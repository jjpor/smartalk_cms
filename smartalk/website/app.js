// ====================================================================
// Logica di scroll ripristinata
// ====================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Gestione dello scroll per il link "Contatti" nell'header.
    // L'ID del link è 'nav-contact' in _header.html, e l'ancora è #contact.
    const contactLinkContainer = document.getElementById('nav-contact');

    if (contactLinkContainer) {
        contactLinkContainer.querySelector('a').addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            // Intercetta solo i click sul link Contatti che puntano all'ancora #contact
            if (href && href.endsWith('#contact')) {
                e.preventDefault();
                const contactSection = document.getElementById('contact');
                if (contactSection) {
                    // Esegue lo scroll fluido alla sezione con ID="contact"
                    contactSection.scrollIntoView({ behavior: 'smooth' });
                }
            }
        });
    }

    console.log("Custom JS logic loaded. Contact scroll handler active.");
});