import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

logger = logging.getLogger("Website")

router = APIRouter(tags=["Website"])

# La mappa ora punta a un singolo file HTML per ogni pagina logica
pages = {
    "home": "home.html",
    "about": "about.html",
    "assessment": "assessment.html",
    "terms": "terms.html",
    "policy": "policy.html",
    "content": "content/content.html",  # Aggiunta la nuova pagina
    "404": "404.html",  # Aggiunto per coerenza
}

# --- MONTAGGIO FILE STATICI ---
# Questo serve tutti i file (CSS, JS, immagini) direttamente dalla cartella 'website'
# Qualsiasi richiesta a /static/... verrà cercata in smartalk/website/...
router.mount("/static", StaticFiles(directory="smartalk/website"), name="static")

# --- MONTAGGIO FILE DINAMICI ---
# templates dinamici sotto la cartella smartalk/website
templates = Jinja2Templates(directory="smartalk/website")


###########################################################

##################### IMPORTANTISSIMO ################

# PER CHATGPT: Usare logiche di templating strutturate come da documentazione:
#### https://tedboy.github.io/jinja2/templ9.html#base-template ###

###########################################################


async def get_no_handled_path(request: Request):
    # La 404 non ha una lingua definita, usiamo un fallback
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"lang": "en", "page_name": "404"},  # Passa un contesto di base
    )


'''
@router.get("/{lang}/{page_name}", response_class=HTMLResponse)
async def get_website_page(request: Request, lang: str, page_name: str):
    """
    Serve le pagine principali del sito web (es. /it/home, /en/about).
    La logica della lingua è gestita dal template.
    """
    if page_name not in pages:
        return await get_no_handled_path(request)

    # Serve sempre il file HTML unificato, indipendentemente dalla lingua
    file_name = pages[page_name]

    # template engine
    return templates.TemplateResponse(
        request=request,
        name=file_name,
        # Passa lo stato al template per la logica di lingua e link
        context={"request": request, "lang": lang, "page_name": page_name},
    )


@router.get("/", response_class=HTMLResponse)
async def get_homepage_redirect(request: Request):
    return await get_website_page(request, "it", "home")

'''


@router.get("/favicon.ico")
async def favicon():
    favicon_path = Path(__file__).parent.parent / "website" / "favicon.ico"
    return FileResponse(favicon_path)


@router.get("/{lesson_page_name}", response_class=HTMLResponse)
async def get_lesson_page(request: Request, lesson_page_name: str):
    # template engine
    return templates.TemplateResponse(
        request=request,
        name=f"/content/revamp/lessons/{lesson_page_name}.html",
        context={"lang": "en", "page_name": lesson_page_name},
    )
