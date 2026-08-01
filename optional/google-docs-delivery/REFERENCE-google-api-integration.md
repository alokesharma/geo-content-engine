# Google Sheets Output from Claude Code — Integration Guide

How to create a native Google Sheet from any Python pipeline running in Claude Code / Cowork.

---

## One-Time Setup (User Does This Once)

### Google Cloud Console
1. Go to https://console.cloud.google.com → create or pick a project
2. Enable these APIs:
   - **Google Drive API**
   - **Google Sheets API**
3. Create OAuth client ID → type: **Desktop app** → download as `credentials.json`
4. Place `credentials.json` in `~/.config/geo-content-engine/credentials.json`

### Required pip packages
```bash
pip install google-api-python-client google-auth google-auth-oauthlib
```

---

## Authentication Pattern

```python
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CENTRAL_DIR = os.path.expanduser('~/.config/geo-content-engine')
HERE = os.path.dirname(os.path.abspath(__file__))

CREDS_FILE = (
    os.path.join(CENTRAL_DIR, 'credentials.json')
    if os.path.exists(os.path.join(CENTRAL_DIR, 'credentials.json'))
    else os.path.join(HERE, 'credentials.json')
)
TOKEN_FILE = (
    os.path.join(CENTRAL_DIR, 'token.json')
    if os.path.exists(os.path.join(CENTRAL_DIR, 'token.json'))
    else os.path.join(HERE, 'token.json')
)

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
]


def authenticate():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
        central_token = os.path.join(CENTRAL_DIR, 'token.json')
        if os.path.isdir(CENTRAL_DIR) and central_token != TOKEN_FILE:
            with open(central_token, 'w') as f:
                f.write(creds.to_json())
    return creds
```

First run opens a browser for OAuth consent. After that, `token.json` is cached and auto-refreshes silently.

---

## Creating a Google Sheet

```python
def create_google_sheet(creds, sheet_name, tabs_data):
    """
    Creates a Google Sheet with multiple tabs and writes data.

    Args:
        creds: Google OAuth credentials
        sheet_name: Name of the spreadsheet (appears in Drive)
        tabs_data: dict of {tab_name: [[header_row], [row1], [row2], ...]}

    Returns:
        sheet_id, sheet_url
    """
    drive = build('drive', 'v3', credentials=creds)
    sheets = build('sheets', 'v4', credentials=creds)

    # Create spreadsheet
    meta = drive.files().create(
        body={'name': sheet_name, 'mimeType': 'application/vnd.google-apps.spreadsheet'},
        fields='id'
    ).execute()
    sheet_id = meta['id']

    # Get default Sheet1 ID (to delete later)
    spreadsheet = sheets.spreadsheets().get(spreadsheetId=sheet_id).execute()
    default_sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']

    # Create tabs
    requests = []
    tab_ids = {}
    for i, tab_name in enumerate(tabs_data.keys()):
        sid = i + 1
        tab_ids[tab_name] = sid
        requests.append({
            'addSheet': {'properties': {'sheetId': sid, 'title': tab_name, 'index': i}}
        })
    requests.append({'deleteSheet': {'sheetId': default_sheet_id}})
    sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests': requests}).execute()

    # Write data
    value_ranges = []
    for tab_name, rows in tabs_data.items():
        value_ranges.append({'range': f"'{tab_name}'!A1", 'values': rows})
    sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={'valueInputOption': 'RAW', 'data': value_ranges}
    ).execute()

    # Format: bold headers, freeze row 1, auto-filter, auto-resize
    fmt_requests = []
    for tab_name, sid in tab_ids.items():
        rows = tabs_data[tab_name]
        num_cols = len(rows[0]) if rows else 1
        num_rows = len(rows)

        # Bold header with dark background + white text
        fmt_requests.append({
            'repeatCell': {
                'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': 1,
                          'startColumnIndex': 0, 'endColumnIndex': num_cols},
                'cell': {'userEnteredFormat': {
                    'backgroundColor': {'red': 0.16, 'green': 0.16, 'blue': 0.36},
                    'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                    'horizontalAlignment': 'CENTER',
                }},
                'fields': 'userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)',
            }
        })
        # Freeze header
        fmt_requests.append({
            'updateSheetProperties': {
                'properties': {'sheetId': sid, 'gridProperties': {'frozenRowCount': 1}},
                'fields': 'gridProperties.frozenRowCount',
            }
        })
        # Auto-filter
        fmt_requests.append({
            'setBasicFilter': {
                'filter': {'range': {'sheetId': sid, 'startRowIndex': 0, 'endRowIndex': num_rows,
                                     'startColumnIndex': 0, 'endColumnIndex': num_cols}}
            }
        })
        # Auto-resize columns
        fmt_requests.append({
            'autoResizeDimensions': {
                'dimensions': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 0, 'endIndex': num_cols}
            }
        })

    sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests': fmt_requests}).execute()

    url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit'
    return sheet_id, url
```

---

## Usage Example

```python
creds = authenticate()

tabs_data = {
    'Summary': [
        ['Metric', 'Value'],
        ['Total Keywords', 150],
        ['Total Prompts', 320],
    ],
    'Keywords': [
        ['#', 'Keyword', 'Volume', 'Position'],
        [1, 'car insurance', 90500, 3],
        [2, 'bike insurance', 40500, 5],
    ],
    'Prompts': [
        ['#', 'Prompt', 'Source'],
        [1, 'What is car insurance?', 'DIRECT'],
        [2, 'How to buy bike insurance online', 'Reddit'],
    ],
}

sheet_id, url = create_google_sheet(creds, 'My Pipeline Output', tabs_data)
print(f'Sheet: {url}')
```

---

## Optional: Tab Colors

```python
def hex_to_rgb(h):
    h = h.lstrip('#')
    return {'red': int(h[0:2], 16)/255.0, 'green': int(h[2:4], 16)/255.0, 'blue': int(h[4:6], 16)/255.0}

# When creating tabs, add tabColorStyle:
requests.append({
    'addSheet': {'properties': {
        'sheetId': sid,
        'title': tab_name,
        'index': i,
        'tabColorStyle': {'rgbColor': hex_to_rgb('4472C4')}
    }}
})
```

---

## Optional: Hide Columns

```python
# Hide column C (index 2) on a specific tab
fmt_requests.append({
    'updateDimensionProperties': {
        'range': {'sheetId': sid, 'dimension': 'COLUMNS', 'startIndex': 2, 'endIndex': 3},
        'properties': {'hiddenByUser': True},
        'fields': 'hiddenByUser',
    }
})
```

---

## Gotchas

1. **Token expiry:** If user changes Google password or revokes access, delete `token.json` and re-auth.
2. **Scope changes:** If you add new scopes later, delete `token.json` — old token won't have them.
3. **Tab names with special chars:** Always wrap in single quotes in range refs: `"'My Tab'!A1"`
4. **valueInputOption:** Use `RAW` for plain data. Use `USER_ENTERED` if cells contain formulas like `=SUM(A1:A10)`.
5. **batchUpdate limits:** Max ~500 requests per call. Split if needed.
