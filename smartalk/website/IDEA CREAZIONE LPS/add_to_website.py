from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os # Importa os

router = APIRouter()

# Configura Jinja2 per cercare i template nella cartella giusta
# Assicurati che il percorso 'templates' sia corretto rispetto alla posizione del tuo script FastAPI
templates = Jinja2Templates(directory="smartalk/website/templates") 

# Percorso base per i template delle lezioni
LESSON_TEMPLATE_DIR = "lesson_plans" 

@router.get("/auth/lesson-plans/{lesson_slug}", response_class=HTMLResponse)
async def get_lesson_page(request: Request, lesson_slug: str):
    """
    Mostra la pagina HTML di una specifica lezione.
    """
    template_name = f"{LESSON_TEMPLATE_DIR}/{lesson_slug}.html"
    
    # Verifica se il file template esiste prima di provare a renderizzarlo
    template_path = os.path.join(templates.env.loader.searchpath[0], template_name)
    if not os.path.exists(template_path):
         raise HTTPException(status_code=404, detail="Lesson plan not found")

    # Passa la request a Jinja (necessario per url_for, ecc.)
    # Puoi aggiungere altri dati al context se servono al template base
    context = {"request": request} 
    
    return templates.TemplateResponse(template_name, context)