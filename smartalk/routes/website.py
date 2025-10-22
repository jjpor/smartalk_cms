import logging
import random

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("Website")

router = APIRouter(tags=["Website"])

##################### IMPORTANTISSIMO #####################

# PER CHATGPT: Usare logiche di templating strutturate come da documentazione:
#### https://tedboy.github.io/jinja2/templ9.html#base-template ###

###########################################################

# --- MONTAGGIO FILE DINAMICI ---
# templates dinamici sotto la cartella smartalk/website/templates
templates = Jinja2Templates(directory="smartalk/website/templates")
# reload automatico e cache disabilitata
templates.env.auto_reload = True
templates.env.cache = {}
# |shuffle diventa un filtro disponibile per tutti i template
templates.env.filters["shuffle"] = lambda seq: random.sample(seq, len(seq))
# aggiungi la funzione random (utile per servire sempre nuove risorse ai browser e impedire la cache)
templates.env.globals["random"] = random.random

# funzione per gestire pagine non trovate e eccezioni
async def get_no_handled_path(request: Request, lang: str = "en"):
    # La 404 non ha una lingua definita, usiamo un fallback
    logger.info('get_no_handled_path')
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        context={"lang": lang, "page_name": "404"},
    )

###########################################################

#################### SERVIZI ESPOSTI ######################

###########################################################

##############################
########### SITE #############
##############################
@router.get("/site/{lang}/{page_name}", response_class=HTMLResponse)
async def get_website_page(request: Request, lang: str, page_name: str):
    """
    Serve le pagine principali del sito web (es. /it/home, /en/about).
    La logica della lingua è gestita dal template.
    """
    logger.info('get_website_page')
    try:
        assert "/" not in lang, "indirizzo non valido"
        assert "/" not in page_name, "indirizzo non valido"
        # template engine
        return templates.TemplateResponse(
            request=request,
            name=f"site/{page_name}.html",
            # Passa lo stato al template per la logica di lingua e link
            context={"lang": lang, "page_name": page_name},
        )
    except Exception as e:
        logger.error(e)
        return await get_no_handled_path(request, lang)

@router.get("/site/{lang}", response_class=HTMLResponse)
async def get_homepage_with_lang(request: Request, lang: str):
    logger.info('get_homepage_with_lang')
    return await get_website_page(request, lang, "home")


@router.get("/site", response_class=HTMLResponse)
async def get_homepage(request: Request):
    logger.info('get_homepage')
    return await get_homepage_with_lang(request, "it")

@router.get("/", response_class=HTMLResponse)
async def get_default(request: Request):
    logger.info('get_default')
    return await get_homepage(request)

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Serve la pagina di login della dashboard.
    """
    logger.info('get_dashboard')
    try:
        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            # Passa lo stato al template per la logica di lingua e link
            context={"lang": "en", "page_name": "dashboard"},
        )
    except Exception as e:
        logger.error(e)
        return await get_no_handled_path(request)

##############################
######## LANDING PAGES #######
##############################
@router.get("/auth/{section_landing_page}", response_class=HTMLResponse)
async def get_section_landing_page(request: Request, section_landing_page: str):
    """
    Serve la pagina di presentazione di una sezione  (es. /auth/lesson_plans, /auth/homework).
    """
    logger.info('get_section_landing_page')
    try:

        # TODO: capire se deve essere presente un utente loggato di un certo tipo: ad esempio 
        ############# section = lesson_plans    ->      user_type = coach
        ############# section = homework        ->      user_type = student
        
        assert "/" not in section_landing_page, "indirizzo non valido"
        return templates.TemplateResponse(
            request=request,
            name=f"landing_pages/{section_landing_page}.html",
            context={"lang": "en", "page_name": {section_landing_page}},
        )
    except Exception as e:
        logger.error(e)
        return await get_no_handled_path(request)

##############################
######## SECTION PAGE ########
##############################
@router.get("/auth/{section}/{item}", response_class=HTMLResponse)
async def get_section_page(request: Request, section: str, item: str):
    """
    Serve le pagine delle sezioni (es. /auth/lesson_plans/150-questions, /auth/homework/esempio).
    """
    logger.info('get_section_page')
    try:

        # TODO: capire se deve essere presente un utente loggato di un certo tipo: ad esempio 
        ############# section = lesson_plans    ->      user_type = coach
        ############# section = homework        ->      user_type = student
        
        assert "/" not in section, "indirizzo non valido"
        assert "/" not in item, "indirizzo non valido"
        return templates.TemplateResponse(
            request=request,
            name=f"/{section}/{item}.html",
            context={"lang": "en", "page_name": {section} - {item}},
        )
    except Exception as e:
        logger.error(e)
        return await get_no_handled_path(request)
