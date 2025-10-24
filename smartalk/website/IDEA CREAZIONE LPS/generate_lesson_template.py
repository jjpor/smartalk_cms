import html
import re
import os
from slugify import slugify # Potresti dover installare 'python-slugify'

def clean_text_for_jinja(text):
    """Sostituisce caratteri tipografici con quelli standard."""
    text = text.replace('’', "'").replace('‘', "'")
    text = text.replace('”', '"').replace('“', '"')
    text = text.replace('—', '-')
    # Aggiungi altre sostituzioni se necessario
    return text

def generate_lesson_template(title, subtitle, sections_data):
    """
    Genera la stringa del template Jinja per una lezione.

    Args:
        title (str): Il titolo della lezione.
        subtitle (str): Il sottotitolo della lezione.
        sections_data (list): Una lista di dizionari, dove ogni dizionario
                              rappresenta una sezione e contiene:
                              {'id': '...', 'title': '...', 'content': '...html...'}
    Returns:
        str: La stringa completa del template Jinja.
    """

    # --- 1. Pulizia Input ---
    lesson_title = clean_text_for_jinja(title)
    lesson_subtitle = clean_text_for_jinja(subtitle)
    
    # --- 2. Definisci Variabili Jinja ---
    nav_links = [{'id': s['id'], 'title': s['title'].split('. ')[1] if '. ' in s['title'] else s['title']} 
                 for s in sections_data] # Estrae titolo pulito per nav
    
    # Intestazione del template
    template_parts = [
        f'{{# --- Lezione: {lesson_title} --- #}}\n',
        f'{{% set lesson_title = "{lesson_title}" %}}',
        f'{{% set lesson_subtitle = "{lesson_subtitle}" %}}',
        f'{{% set nav_links = {nav_links!r} %}}\n', # !r usa repr() per formattare la lista Python in sintassi Jinja
        '{# --- Dati per Esercizi (se necessari, aggiungere qui) --- #}\n',
        '{% extends "abstract_templates/lesson_base.html" %}',
        '{% from "abstract_templates/_macros.html" import info_card %}\n', # Aggiungere altre macro se servono
        '{% block lesson_content %}\n'
    ]

    # --- 3. Genera Blocchi info_card ---
    for i, section in enumerate(sections_data):
        section_id = clean_text_for_jinja(section['id'])
        section_title = clean_text_for_jinja(section['title'])
        # Pulisci il contenuto HTML da caratteri speciali potenzialmente problematici
        # e assicurati che l'HTML sia "safe" per Jinja
        section_content = clean_text_for_jinja(section['content']).strip()
        
        # Applica indentazione corretta al contenuto per leggibilità
        indented_content = "\n".join(["    " + line for line in section_content.splitlines()])

        template_parts.append(f"    {{% call info_card('{section_id}', '{section_title}', initial_state='show') %}}")
        template_parts.append(indented_content) # Contenuto HTML pulito e indentato
        template_parts.append(f"    {{% endcall %}}\n")

        # Aggiungi separatore <hr> tranne dopo l'ultima sezione
        if i < len(sections_data) - 1:
            template_parts.append('    <hr class="my-12 border-gray-200">\n')

    # --- 4. Chiusura Template ---
    template_parts.append('{% endblock lesson_content %}')

    return "\n".join(template_parts)

# --- Esempio di Utilizzo ---
if __name__ == '__main__':
    # Dati che potrebbero arrivare dalla dashboard
    lesson_data = {
        "title": "Employee Engagement & Retention",
        "subtitle": "Strategies for a motivated and loyal team.",
        "sections": [
            {
                "id": "warmup",
                "title": "1. Warm-Up Discussion",
                "content": """
<ul class="text-slate-600"> {# Classi lista rimosse come da CSS master #}
    <li>What does "employee engagement" mean to you?</li>
    <li>How does engagement look different from simply being satisfied with a job?</li>
    <li>What's one factor that has kept you motivated in a past role?</li>
</ul>
                """
            },
            {
                "id": "part1",
                "title": "2. Part 1 – Understanding the Importance",
                "content": """
<p class="mt-4 font-semibold text-slate-700">Objective: Understand why engagement and retention are critical for business success.</p>
<div class="mt-4">
    <h4 class="font-semibold text-slate-800">Speaking Prompts:</h4>
    <ul class="text-slate-600"> {# Classi lista rimosse #}
        <li>Reflect on a time when you felt highly engaged at work. What contributed to that?</li>
        <li>What are the risks for a company when turnover is high?</li>
        <li>How does retention connect to employee engagement?</li>
    </ul>
</div>
<div class="mt-4">
    <h4 class="font-semibold text-slate-800">Pair/Group Discussion:</h4>
    <ul class="text-slate-600"> {# Classi lista rimosse #}
        <li>How does employee wellbeing impact engagement?</li>
        <li>How does company culture affect whether people stay or leave?</li>
    </ul>
</div>
                """
            },
            # ... Aggiungere le altre sezioni qui ...
        ]
    }

    generated_template = generate_lesson_template(
        lesson_data["title"],
        lesson_data["subtitle"],
        lesson_data["sections"]
    )
    
    print(generated_template) 
    # Questa stringa 'generated_template' è quello che salveresti nel file .html

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