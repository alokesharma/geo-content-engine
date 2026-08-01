#!/usr/bin/env python3
"""One-time re-auth to add the Sheets scope, if you want the optional add-on to write the
Doc link back into a source sheet. Keeps drive.file (delivery still works) and adds
spreadsheets. Opens a browser; sign in with the Google account that owns the sheet.

Config directory is read from GOOGLE_CREDENTIALS_PATH (defaults to
~/.config/geo-content-engine/). Place your own credentials.json there. Nothing is bundled.

Run:  python3 optional/google-docs-delivery/reauth_sheets.py
"""
import os, shutil, time
from google_auth_oauthlib.flow import InstalledAppFlow

CFG = os.environ.get(
    "GOOGLE_CREDENTIALS_PATH",
    os.path.expanduser("~/.config/geo-content-engine"),
)
CREDS = os.path.join(CFG, "credentials.json")
TOKEN = os.path.join(CFG, "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",       # keep: delivery upload-convert
    "https://www.googleapis.com/auth/spreadsheets",      # add: write col I on the source sheet
]

if os.path.exists(TOKEN):
    bak = TOKEN + ".bak-" + str(int(time.time()))
    shutil.copy(TOKEN, bak)
    print("backed up existing token ->", bak)

flow = InstalledAppFlow.from_client_secrets_file(CREDS, SCOPES)
creds = flow.run_local_server(port=0)   # opens browser; approve as the sheet owner
with open(TOKEN, "w") as f:
    f.write(creds.to_json())
print("OK: token.json now carries scopes:", creds.scopes)
