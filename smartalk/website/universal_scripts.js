// FUNZIONE UNIVERSALE PER EVIDENZIARE IL LINK ATTIVO
    function setActiveNav(pageId) {
        // Rimuove la classe 'attiva' (rosso) e ripristina 'hover' (blu) da tutti i link
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('text-red-600');
            link.classList.add('hover:text-blue-600');
        });
        
        // Aggiunge la classe 'attiva' al link corrispondente all'ID della pagina
        const activeLink = document.querySelector(`#nav-${pageId} .nav-link`);
        if (activeLink) {
            activeLink.classList.add('text-red-600');
            activeLink.classList.remove('hover:text-blue-600');
        }
    }

    // Nota: Il link Contatti ora reindirizza alla homepage (home#contact).
    // Se volessi lo scroll LISCIO sulla homepage, aggiungi:
    // if (document.getElementById('contact')) { /* Solo se l'elemento 'contact' esiste sulla pagina */
    //     document.getElementById('nav-contatti').querySelector('a').addEventListener('click', function(e) {
    //         e.preventDefault();
    //         document.getElementById('contact').scrollIntoView({ behavior: 'smooth' });
    //     });
    // }