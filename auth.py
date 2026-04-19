"""
OAuth 2.0 authentication for Google Business Profile API.

Before running:
  1. Download client_secret.json from Google Cloud Console
     (APIs & Services > Credentials > your OAuth 2.0 Client ID)
  2. Place client_secret.json in this directory
  3. Run: python auth.py
"""

import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/business.manage"]
CLIENT_SECRET_FILE = "client_secret.json"
TOKEN_FILE = "token.json"


def get_credentials() -> Credentials:
    """Return valid credentials, running the OAuth flow if needed."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"'{CLIENT_SECRET_FILE}' not found.\n"
                    "Download it from Google Cloud Console:\n"
                    "  APIs & Services > Credentials > your OAuth 2.0 Client ID > Download JSON\n"
                    f"Then place it in this directory as '{CLIENT_SECRET_FILE}'."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"Credentials saved to {TOKEN_FILE}")

    return creds


if __name__ == "__main__":
    creds = get_credentials()
    print("Authentication successful.")
    token_data = json.loads(creds.to_json())
    print(f"  Token expires: {token_data.get('expiry', 'N/A')}")
    print(f"  Scopes granted: {creds.scopes}")
