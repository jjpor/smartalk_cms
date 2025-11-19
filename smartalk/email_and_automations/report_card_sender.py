from datetime import datetime
from typing import Any, Dict, Iterable, List

import pandas as pd

from smartalk.email_and_automations.utils.email import (
    generate_pdf_bytes_from_html,
    get_gmail_service,
    load_snippet_from_template,
    send_gmail_message_with_pdf,
    templates,
)

"""
report_cards_sender.py

Pipeline produzione:
- input: completed_report_cards: List[Dict[str, Any]]
  (schede già completate e approvate, pronte per l'invio)
- usa student_names_by_id e client_names_by_id (dict semplici id -> nome completo)
- raggruppa per client_id
- genera PDF per ogni client via Jinja2 + WeasyPrint (in memoria)
- invia via Gmail API
"""

# ==========================
# DATAFRAME E GROUPING
# ==========================


def prepare_report_cards_dataframe(
    completed_report_cards: Iterable[Dict[str, Any]],
    student_names_by_id: Dict[str, str],
) -> pd.DataFrame:
    """
    Converte completed_report_cards (list[dict]) in DataFrame
    e aggiunge il nome completo dello studente.

    Assunzione: i dict hanno le chiavi in snake_case come:
      - student_id
      - coach_id
      - attendance
      - report
      - report_card_email_recipients
      - start_month
      - end_month
      - client_id
    """
    rows = list(completed_report_cards)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # nome completo studente, es. "Mario Rossi"
    def _student_full_name(sid: str) -> str:
        return student_names_by_id.get(sid, "")

    df["student_full_name"] = df["student_id"].map(_student_full_name)
    return df


# ==========================
# JINJA2 → HTML → PDF
# ==========================


def render_pdf_html_for_client(
    company_name: str,
    period_str: str,
    client_df: pd.DataFrame,
    logo_html: str,
) -> str:
    """
    Usa il template HTML reportCardPdf.html per un singolo client_id.

    Assunzione: reportCardPdf.html è stato adattato a Jinja2 e accetta il contesto:

      companyName: str
      periodStr: str
      logoHtml: str (HTML <img ...> con base64)
      items: lista di dict:
        - fullName
        - coach
        - attendance
        - report
    """
    pdf_template = templates.env.get_template("reportCardPdf.html")

    # ordina per nome studente
    client_df = client_df.sort_values("student_full_name", na_position="last")

    items: List[Dict[str, Any]] = []
    for _, row in client_df.iterrows():
        full_name = row.get("student_full_name", "") or ""
        items.append(
            {
                "fullName": full_name,
                "coach": row.get("coach_id", "") or "",
                "attendance": row.get("attendance", "") or "",
                "report": row.get("report", "") or "",
            }
        )

    html = pdf_template.render(
        companyName=company_name,
        periodStr=period_str,
        logoHtml=logo_html,
        items=items,
    )
    return html


# ==========================
# BUNDLE PER OGNI CLIENT_ID
# ==========================


def generate_grouped_report_card_bundles(
    completed_report_cards: Iterable[Dict[str, Any]],
    student_names_by_id: Dict[str, str],
    client_names_by_id: Dict[str, str],
    logo_html: str,
) -> List[Dict[str, Any]]:
    """
    Raggruppa i report card per client_id e costruisce una lista di "bundle":

    bundle = {
        "client_id": str,
        "company_name": str,
        "to_email": str,
        "cc_email": str,
        "pdf_list": list, # [{"pdf_bytes": bytes, "filename": str}]
        "report_cards": DataFrame di quel client,
    }
    """
    df = prepare_report_cards_dataframe(completed_report_cards, student_names_by_id)
    if df.empty:
        return []

    bundles: List[Dict[str, Any]] = []

    # Periodo: usa minimo start_month e massimo end_month del gruppo
    def build_period_str(group: pd.DataFrame) -> str:
        try:
            start_min = group["start_month"].min()
            end_max = group["end_month"].max()
            if start_min == end_max:
                return start_min
            return f"{start_min} – {end_max}"
        except Exception:
            return ""

    current_month = datetime.now().strftime("%Y-%m")
    grouped = df.groupby("client_id", dropna=True)

    for client_id, client_df in grouped:
        client_id_str = str(client_id).upper()
        company_name = client_names_by_id.get(client_id_str, client_id_str)

        # recipient: prende il primo non vuoto
        recipients_series = client_df["report_card_email_recipients"].dropna()
        recipient_str = recipients_series.iloc[0] if not recipients_series.empty else None
        if not recipient_str:
            continue

        emails = [e.strip() for e in recipient_str.split(",") if e.strip()]
        to_email = emails[0] if emails else ""
        cc_email = emails[1] if len(emails) > 1 else ""

        if not to_email:
            continue

        period_str = build_period_str(client_df)

        html_content = render_pdf_html_for_client(
            company_name=company_name,
            period_str=period_str,
            client_df=client_df,
            logo_html=logo_html,
        )
        pdf_bytes = generate_pdf_bytes_from_html(html_content)

        filename = f"{company_name}_Report_Card_{current_month}.pdf".replace(" ", "_")

        bundles.append(
            {
                "client_id": client_id_str,
                "company_name": company_name,
                "to_email": to_email,
                "cc_email": cc_email,
                "pdf_list": [
                    {
                        "pdf_bytes": pdf_bytes,
                        "filename": filename,
                    }
                ],
                "report_cards": client_df,
            }
        )

    return bundles


# ==========================
# INVIO EMAIL
# ==========================


def send_grouped_report_cards_emails_gmail(
    bundles: List[Dict[str, Any]],
    signature_html: str,
    sender: str,
) -> None:
    """
    Invia tutte le email per i bundle generati.
    Usa Gmail API e allega il PDF in memoria.
    """
    if not bundles:
        return

    service = get_gmail_service()

    for b in bundles:
        company_name = b["company_name"]
        to_email = b["to_email"]
        cc_email = b.get("cc_email")
        pdf_list = b.get("pdf_list")
        subject = f"Report Cards for {company_name}"
        html_body = (
            f"Dear {company_name},<br><br>"
            f"Please find attached the report cards for {company_name}.<br><br>"
            f"{signature_html}"
        )

        # se vuoi loggare, fallo qui
        send_gmail_message_with_pdf(
            service=service,
            sender=sender,
            to=to_email,
            subject=subject,
            html_body=html_body,
            pdf_list=pdf_list,
            cc=cc_email,
        )


# ==========================
# ENTRYPOINT AD ALTO LIVELLO
# ==========================


def run_send_report_cards(
    completed_report_cards: List[Dict[str, Any]],
    student_names_by_id: Dict[str, str],
    client_names_by_id: Dict[str, str],
    sender: str,
) -> None:
    """
    Funzione principale da chiamare dal tuo job/cron:

    - completed_report_cards: list[dict] già filtrate come "pronte per invio"
      (equivalente di Final check spuntato e non ancora Sent)
    - student_names_by_id: dict student_id -> "Nome Cognome"
      (puoi popolarlo usando get_client_name per user_type == "student")
    - client_names_by_id: dict client_id -> nome cliente/azienda
      (company o student singolo, sempre tramite get_client_name)
    - sender: indirizzo Gmail/Workspace da cui inviare, es. "jj@smartalk.online"
    """
    if not completed_report_cards:
        return

    logo_html = load_snippet_from_template("logoBase64.html")
    signature_html = load_snippet_from_template("signature.html")

    bundles = generate_grouped_report_card_bundles(
        completed_report_cards=completed_report_cards,
        student_names_by_id=student_names_by_id,
        client_names_by_id=client_names_by_id,
        logo_html=logo_html,
    )

    send_grouped_report_cards_emails_gmail(
        bundles=bundles,
        signature_html=signature_html,
        sender=sender,
    )
