import base64
import json
from email.message import EmailMessage
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.templating import Jinja2Templates
from weasyprint import HTML

from smartalk.core.settings import settings

# ==========================
# CONFIGURAZIONE
# ==========================

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
REAL_TEMPLATES_FOLDER = "smartalk/email_and_automations/templates"

# Template Jinja2
templates = Jinja2Templates(directory=REAL_TEMPLATES_FOLDER)


# ==========================
# TEMPLATE UTILITY
# ==========================


def load_snippet_from_template(name: str) -> str:
    """
    Renderizza un template HTML “statico” (es. signature.html, logoBase64.html)
    senza variabili di contesto.
    """
    tmpl = templates.env.get_template(name)
    return tmpl.render()


# ==========================
# GMAIL API
# ==========================


def get_gmail_service():
    """
    Crea il client Gmail API.
    """
    try:
        creds = Credentials.from_authorized_user_info(json.loads(settings.GMAIL_TOKEN_JSON), SCOPES)
        service = build("gmail", "v1", credentials=creds)
        print("email service ready")
        return service
    except Exception:
        raise RuntimeError("Environment variable GMAIL_TOKEN_JSON missing")


def build_email_with_pdf(
    sender: str,
    to: str,
    subject: str,
    html_body: str,
    pdf_list: Optional[list] = None,
    cc: Optional[str] = None,
    name: Optional[str] = None,
) -> str:
    """
    Crea la MIME email con allegato PDF e la codifica in base64url
    per Gmail API (campo "raw").
    """
    msg = EmailMessage()
    msg["From"] = f"{name} <{sender}>" if name else f"Smartalk <{sender}>"
    msg["To"] = to
    if cc:
        msg["Cc"] = cc
    msg["Subject"] = subject

    # For only textual browser
    msg.set_content("This is an HTML email. Please use an HTML-compatible client.")

    # Real email
    msg.add_alternative(html_body, subtype="html")

    if pdf_list:
        for pdf_file in pdf_list:
            msg.add_attachment(
                pdf_file["pdf_bytes"],
                maintype="application",
                subtype="pdf",
                filename=pdf_file["pdf_filename"],
            )

    raw_bytes = msg.as_bytes()
    raw_b64 = base64.urlsafe_b64encode(raw_bytes).decode("utf-8")
    return raw_b64


def send_gmail_message_with_pdf(
    service,
    sender: str,
    to: str,
    subject: str,
    html_body: str,
    pdf_list: Optional[list] = None,
    cc: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Invia l'email tramite Gmail API.
    """
    raw_b64 = build_email_with_pdf(
        sender=sender, to=to, subject=subject, html_body=html_body, pdf_list=pdf_list, cc=cc, name=name
    )
    body = {"raw": raw_b64}
    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent


# ==========================
# PDF in memory
# ==========================


def generate_pdf_bytes_from_html(html_content: str) -> bytes:
    """
    Genera il PDF in memoria (bytes) a partire dall'HTML.
    """
    return HTML(string=html_content).write_pdf()
