import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # refresh del token, se già esiste
            creds.refresh(Request())
        else:
            # primo giro: usa credentials.json per fare il login
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)  # apre il browser

        # salva token.json (access + refresh token)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    print("token.json creato/aggiornato")


if __name__ == "__main__":
    main()
    # viene generato token.json: prendere il contenuto e metterlo nella variabile GMAIL_TOKEN_JSON di .env
