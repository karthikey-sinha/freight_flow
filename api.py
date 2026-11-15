"""REST API so no-code tools (n8n / Make / Zapier / Power Automate) can call the Python brain.

    uvicorn api:app --reload --port 8000
    open http://localhost:8000/docs   (auto-generated Swagger UI)

Endpoints
    POST /process-email          triage + draft (n8n sends email JSON here)
    POST /extract-document       upload a PDF, get structured fields back
    GET  /drafts                 pending drafts (human review queue)
    POST /drafts/{id}/approve    approve (optionally with edited body) -> n8n then sends it
    POST /drafts/{id}/reject
    GET  /dashboard              live HTML dashboard
"""
import base64
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from freightflow import db
from freightflow.dashboard import build
from freightflow.documents import extract
from freightflow.pipeline import process_email

app = FastAPI(title="FreightFlow API", version="1.0")


class Attachment(BaseModel):
    filename: str
    content_base64: str


class EmailIn(BaseModel):
    id: str
    sender: str
    subject: str
    body: str
    received_at: Optional[str] = None
    attachments: List[Attachment] = []


class ReviewIn(BaseModel):
    reviewer: str = "reviewer"
    body: Optional[str] = None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/process-email")
def process(email: EmailIn):
    with tempfile.TemporaryDirectory() as tmp:
        names = []
        for a in email.attachments:
            safe = Path(a.filename).name
            (Path(tmp) / safe).write_bytes(base64.b64decode(a.content_base64))
            names.append(safe)
        payload = {"id": email.id, "from": email.sender, "subject": email.subject, "body": email.body,
                   "received_at": email.received_at, "attachments": names}
        return process_email(payload, tmp)


@app.post("/extract-document")
async def extract_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / Path(file.filename).name
        path.write_bytes(await file.read())
        return extract(path)


@app.get("/drafts")
def drafts():
    con = db.connect()
    try:
        return db.pending_drafts(con)
    finally:
        con.close()


def _get_draft(con, draft_id):
    row = con.execute("SELECT d.*, e.sender, e.subject FROM drafts d JOIN emails e ON e.id=d.email_id WHERE d.id=?",
                      (draft_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Draft not found")
    return dict(row)


@app.post("/drafts/{draft_id}/approve")
def approve(draft_id: int, review: ReviewIn):
    con = db.connect()
    try:
        _get_draft(con, draft_id)
        db.review_draft(con, draft_id, "approved", review.reviewer, review.body)
        d = _get_draft(con, draft_id)
        # n8n uses these fields to send the reply via Gmail
        return {"status": "approved", "to": d["sender"], "subject": "Re: " + d["subject"], "body": d["body"]}
    finally:
        con.close()


@app.post("/drafts/{draft_id}/reject")
def reject(draft_id: int, review: ReviewIn):
    con = db.connect()
    try:
        _get_draft(con, draft_id)
        db.review_draft(con, draft_id, "rejected", review.reviewer)
        return {"status": "rejected"}
    finally:
        con.close()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    return build().read_text(encoding="utf-8")
