#!/usr/bin/env python3
"""
upload_to_gdoc.py - the delivery path that actually works.

Instead of building the Doc via the Docs API batchUpdate (which drifted and rejected `pageless`),
we render a clean .docx locally (build_doc.render_to_docx) then upload it to Drive with mimeType
conversion to a NATIVE Google Doc. Drive's converter preserves the heading/table/bold/list
styling python-docx applied, so the format is locked by the .docx, not by fragile API calls.
"""
import os


def upload_docx_as_gdoc(docx_path, doc_title):
    """Upload a .docx to Drive, converting to a native Google Doc. Returns the Doc URL."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from auth_helper import get_credentials
    creds = get_credentials(["https://www.googleapis.com/auth/drive.file"])
    drive = build("drive", "v3", credentials=creds)
    media = MediaFileUpload(
        docx_path,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        resumable=False)
    f = drive.files().create(
        body={"name": doc_title, "mimeType": "application/vnd.google-apps.document"},  # convert
        media_body=media,
        fields="id").execute()
    return "https://docs.google.com/document/d/%s/edit" % f["id"]


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        print(upload_docx_as_gdoc(sys.argv[1], sys.argv[2]))
    else:
        print("usage: upload_to_gdoc.py <file.docx> <doc title>")
