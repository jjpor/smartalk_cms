// Logica per evidenziare il link di navigazione attivo
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = '{{ page_name }}';
    const activeLink = document.getElementById(`nav-${currentPage}`);
    if (activeLink) {
        const link = activeLink.querySelector('a');
        if (link) {
            link.classList.add('text-red-600');
            link.classList.remove('hover:text-blue-600');
        }
    }
});