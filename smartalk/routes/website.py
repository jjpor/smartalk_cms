import os

from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse

# Definiamo il percorso della cartella 'website' in modo robusto
# Questo sale di due livelli da /routes/website.py per arrivare alla root del progetto
WEBSITE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "website")

router = APIRouter(tags=["Website"])

# Mappa per gestire le pagine e le loro traduzioni
pages = {
    "home": {"it": "homepage.html", "en": "homepage_en.html"},
    "about": {"it": "chi_siamo.html", "en": "aboutus.html"},
    "terms": {"it": "terms.html", "en": "terms_en.html"},
    "policy": {"it": "policy.html", "en": "policy_en.html"},
}

@router.get("/{lang}/{page_name}", response_class=FileResponse)
async def get_website_page(lang: str, page_name: str):
    """
    Serve le pagine principali del sito web (es. /it/home, /en/about).
    """
    if page_name not in pages or lang not in pages[page_name]:
        raise HTTPException(status_code=404, detail="Page not found")

    file_name = pages[page_name][lang]
    file_path = os.path.join(WEBSITE_DIR, file_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path)

@router.get("/", response_class=FileResponse, include_in_schema=False)
async def get_homepage_redirect():
    """
    Redirect dalla root '/' alla homepage in italiano per comodità.
    """
    file_path = os.path.join(WEBSITE_DIR, "homepage.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Homepage not found")
    return FileResponse(file_path)