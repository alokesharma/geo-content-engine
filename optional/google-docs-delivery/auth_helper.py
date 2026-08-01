#!/usr/bin/env python3
"""
auth_helper.py - OAuth credentials for the optional Google Docs delivery add-on.

Config directory is read from the GOOGLE_CREDENTIALS_PATH env var (the directory that
holds your own credentials.json). If unset, it defaults to ~/.config/geo-content-engine/.
Place your own OAuth credentials.json there. The Drive scope is enough for the
upload-convert delivery path. If you change scopes, delete token.json once and re-auth
so the new token carries them. Nothing here is hardcoded and no credentials are bundled.
"""
import os

CONFIG_DIR = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH",
    os.path.expanduser("~/.config/geo-content-engine"),
)
TOKEN = os.path.join(CONFIG_DIR, "token.json")
CREDS = os.path.join(CONFIG_DIR, "credentials.json")
DEFAULT_SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def get_credentials(scopes=None):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    scopes = scopes or DEFAULT_SCOPES
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS, scopes)
            creds = flow.run_local_server(port=0)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(TOKEN, "w") as f:
            f.write(creds.to_json())
    return creds
