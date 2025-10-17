import os
from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse, RedirectResponse

# Definiamo il percorso della cartella 'website' in modo robusto
WEBSITE_DIR = os.path.join(os.path.dirname(__file__), "..", "website")

router = APIRouter(tags=["Website"])

# La mappa ora punta a un singolo file HTML per ogni pagina logica
pages = {
    "home": "home.html",
    "about": "about.html",
    "terms": "terms.html",
    "policy": "policy.html",
    "content": "content/content.html",  # Aggiunta la nuova pagina
}

@router.get("/{lang}/{page_name}", response_class=FileResponse)
async def get_website_page(lang: str, page_name: str):
    """
    Serve le pagine principali del sito web (es. /it/home, /en/about).
    La logica della lingua è gestita dal JavaScript sul client.
    """
    if page_name not in pages or lang not in ['it', 'en']:
        raise HTTPException(status_code=404, detail="Page not found")

    # Serve sempre il file HTML unificato, indipendentemente dalla lingua
    file_name = pages[page_name]
    file_path = os.path.join(WEBSITE_DIR, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File '{file_name}' not found")

    return FileResponse(file_path)

@router.get("/", response_class=RedirectResponse, include_in_schema=False)
async def get_homepage_redirect():
    """
    Redirect dalla root '/' alla homepage in italiano per comodità.
    L'URL /it/home caricherà comunque il file unificato home.html.
    """
    return RedirectResponse(url="/it/home")