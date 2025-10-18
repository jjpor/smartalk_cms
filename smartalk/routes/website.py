import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

logger = logging.getLogger('Website')

router = APIRouter(tags=["Website"])

# La mappa ora punta a un singolo file HTML per ogni pagina logica
pages = {
    "home": "home.html",
    "about": "about.html",
    "terms": "terms.html",
    "policy": "policy.html",
    "content": "content/content.html",  # Aggiunta la nuova pagina
}

# --- MONTAGGIO FILE STATICI ---
# Questo serve tutti i file (CSS, JS, immagini) direttamente dalla cartella 'website'
# Qualsiasi richiesta a /static/... verrà cercata in website/...
router.mount("/static", StaticFiles(directory="smartalk/website"), name="website")

# --- MONTAGGIO FILE DINAMICI ---
# templates dinamici sotto la cartella smartalk/website
templates = Jinja2Templates(directory="smartalk/website")


###########################################################

##################### IMPORTANTISSIMO ################

# PER CHATGPT: Usare logiche di templating strutturate come da documentazione:
#### https://tedboy.github.io/jinja2/templ9.html#base-template ###

###########################################################

async def get_no_handled_path(request: Request):
    return templates.TemplateResponse(request=request, name="404.html")

@router.get("/{lang}/{page_name}", response_class=HTMLResponse)
async def get_website_page(request: Request, lang: str, page_name: str):
    """
    Serve le pagine principali del sito web (es. /it/home, /en/about).
    La logica della lingua è gestita dal JavaScript sul client.
    """

    # Serve sempre il file HTML unificato, indipendentemente dalla lingua
    file_name = pages[page_name]

    # template engine
    return templates.TemplateResponse(request=request, name=file_name)

@router.get("/", response_class=HTMLResponse)
async def get_homepage_redirect(request: Request):
    return await get_website_page(request, "it", "home")