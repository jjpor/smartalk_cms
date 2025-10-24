OK, hai la funzione Python `generate_lesson_template` che produce la stringa Jinja. Ecco cosa manca per vederla funzionare sul tuo sito FastAPI:

-----

## 1\. Salvare il File Template

La funzione Python genera solo una **stringa**. Questa stringa deve essere **salvata fisicamente** come un file `.html` nella cartella corretta dove FastAPI cerca i template delle lezioni.

  * **Dove:** `smartalk/website/templates/lesson_plans/`
  * **Nome File:** Dovresti usare uno "slug" dal titolo (es., `employee-engagement-retention.html`).

**Azione:** Modifica la funzione Python (o il codice che la chiama) per includere la logica di salvataggio:

```python
import os
from slugify import slugify # Potresti dover installare 'python-slugify'

# ... (funzione generate_lesson_template come prima) ...

# --- Esempio di Utilizzo AGGIORNATO ---
if __name__ == '__main__':
    # ... (lesson_data come prima) ...

    generated_template = generate_lesson_template(
        lesson_data["title"],
        lesson_data["subtitle"],
        lesson_data["sections"]
    )

    # --- Logica di Salvataggio ---
    TEMPLATE_DIR = os.path.join('smartalk', 'website', 'templates', 'lesson_plans')
    if not os.path.exists(TEMPLATE_DIR):
        os.makedirs(TEMPLATE_DIR) # Crea la cartella se non esiste

    lesson_slug = slugify(lesson_data["title"]) # Es: "employee-engagement-retention"
    file_path = os.path.join(TEMPLATE_DIR, f"{lesson_slug}.html")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(generated_template)
        print(f"Template salvato con successo in: {file_path}")
    except IOError as e:
        print(f"Errore durante il salvataggio del file: {e}")

```

-----

## 2\. Creare la Route FastAPI per Visualizzare la Lezione

Ora che il file `nome-lezione.html` esiste nella cartella `templates/lesson_plans/`, devi creare un endpoint (una route) in FastAPI che lo *mostri* all'utente.

Questo endpoint prenderà lo "slug" della lezione dall'URL (es. `/auth/lesson-plans/employee-engagement-retention`) e dirà a Jinja di renderizzare il file corrispondente.

**Azione:** Nel tuo file router per le lezioni (`smartalk/website/routers/lesson_plans.py` o simile), aggiungi o modifica una route come questa:

```python
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

```

**Punti Chiave:**

  * `Jinja2Templates(directory="smartalk/website/templates")`: Dice a FastAPI dove si trova la cartella base dei template.
  * `@router.get("/auth/lesson-plans/{lesson_slug}")`: Definisce l'URL. Prende lo `lesson_slug` dall'URL.
  * `template_name = f"{LESSON_TEMPLATE_DIR}/{lesson_slug}.html"`: Costruisce il percorso *relativo* al template da caricare (es. `lesson_plans/employee-engagement-retention.html`).
  * `os.path.exists`: Controlla che il file esista per evitare errori 500 se l'URL non corrisponde a un file.
  * `templates.TemplateResponse(template_name, context)`: Dice a Jinja di renderizzare quel file.

-----

## 3\. (Opzionale ma Raccomandato) Endpoint per la Creazione

Per completare il ciclo, avresti bisogno di un altro endpoint FastAPI (es. un `POST` a `/admin/create-lesson`) che:

1.  Riceva i dati della lezione dalla dashboard (magari come JSON).
2.  Chiami la funzione `generate_lesson_template` per creare la stringa Jinja.
3.  Salvi la stringa nel file `.html` corretto (come nello Step 1).
4.  Idealmente, salvi anche i metadati della lezione (titolo, slug, autore, ecc.) in un **database**, in modo da poter generare dinamicamente l'indice delle lezioni disponibili.

-----

**In sintesi:** Una volta che la funzione Python **salva** il file `.html` nella cartella `templates/lesson_plans`, la route `get_lesson_page` in FastAPI sarà in grado di **trovarlo e mostrarlo** quando visiti l'URL corrispondente.