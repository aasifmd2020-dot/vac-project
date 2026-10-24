from pathlib import Path
from io import BytesIO
from pypdf import PdfReader
from docx import Document
from PIL import Image
from fastapi import UploadFile, HTTPException
import pytesseract
from .config import settings

ALLOWED = {".pdf", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".bmp"}

async def extract_upload(upload: UploadFile) -> str:
    filename = upload.filename or "upload.txt"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(415, "Unsupported file type. Use PDF, DOCX, TXT, or an image.")
    raw = await upload.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Upload exceeds {settings.max_upload_mb} MB limit.")
    try:
        if ext == ".txt":
            return raw.decode("utf-8-sig", errors="replace")[:50000]
        if ext == ".pdf":
            reader = PdfReader(BytesIO(raw))
            return "\n".join((p.extract_text() or "") for p in reader.pages)[:50000]
        if ext == ".docx":
            doc = Document(BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)[:50000]
        try:
            return pytesseract.image_to_string(Image.open(BytesIO(raw)))[:30000]
        except Exception as exc:
            raise HTTPException(422, "Image OCR failed. Install Tesseract OCR and verify pytesseract is installed.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(422, "Could not read the uploaded document.") from exc
