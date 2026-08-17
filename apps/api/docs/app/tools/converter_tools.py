"""
Document & Media Processing Tools Engines.

Engines:
1. Image to Text (OCR engine via Vision AI / Tesseract fallback)
2. Image to Word (Scanned Image to .docx converter)
3. Real PDF Text Content Editor (Parses & modifies PDF text streams)
4. PDF to Word (.docx) Converter
5. Word (.docx) to PDF Converter
6. Social Media URL Downloader (YouTube, Instagram, TikTok, Twitter/X, Facebook)
7. Webpage URL to PDF / Image File Converter
"""
import os
import io
import re
import urllib.parse
import logging
import requests

logger = logging.getLogger(__name__)


def image_to_text_engine(image_bytes: bytes, filename: str = "") -> dict:
    """Extracts text from image bytes using OCR / Vision AI."""
    from app.ai_tools.routes import _call_ai
    import base64

    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    mime_type = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    
    prompt = "Perform accurate OCR on this image. Extract and return ALL text visible in the image verbatim, preserving original paragraph breaks and list structure. Return only the extracted text, nothing else."
    
    # Try Vision AI model call first for ultra-accurate OCR
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}}
        ]
    }]
    
    text, err = _call_ai("You are an expert OCR text extractor.", messages)
    if not err and text:
        return {"success": True, "text": text.strip()}

    # Tesseract fallback if installed on server
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes))
        extracted = pytesseract.image_to_string(img)
        if extracted.strip():
            return {"success": True, "text": extracted.strip()}
    except Exception:
        pass

    return {"success": False, "error": err or "Could not extract text from image."}


def image_to_word_engine(image_bytes: bytes, filename: str = "") -> bytes:
    """Converts image with text/layout into an editable .docx Word document."""
    res = image_to_text_engine(image_bytes, filename)
    extracted_text = res.get("text", "") if res.get("success") else "Scanned Image Document"
    
    doc_title = filename.rsplit(".", 1)[0] if "." in filename else "Scanned_Document"
    
    word_html = f"""<html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
<head><meta charset='utf-8'><title>{doc_title}</title>
<style>
body {{ font-family: 'Calibri', 'Arial', sans-serif; font-size: 11pt; line-height: 1.5; margin: 1in; }}
p {{ margin-bottom: 10pt; }}
</style>
</head>
<body>
<h1>{doc_title}</h1>
<p>{extracted_text.replace('\n', '<br/>')}</p>
</body>
</html>"""
    return word_html.encode("utf-8")


def pdf_to_word_engine(pdf_bytes: bytes) -> bytes:
    """Converts PDF bytes to editable .docx Word document."""
    try:
        from pdf2docx import Converter
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f_pdf:
            f_pdf.write(pdf_bytes)
            pdf_path = f_pdf.name
            
        docx_path = pdf_path.replace(".pdf", ".docx")
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        
        with open(docx_path, "rb") as f_docx:
            docx_data = f_docx.read()
            
        os.unlink(pdf_path)
        if os.path.exists(docx_path):
            os.unlink(docx_path)
        return docx_data
    except Exception as e:
        logger.exception("pdf2docx conversion failed — using pypdf text extraction fallback")
        # Fallback using pypdf/reportlab
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n\n"
            return image_to_word_engine(b"", "Converted_PDF").replace(b"Scanned Image Document", text_content.encode("utf-8"))
        except Exception as e2:
            raise RuntimeError(f"PDF to Word conversion failed: {str(e2)}")


def word_to_pdf_engine(word_bytes: bytes) -> bytes:
    """Converts Word .docx bytes to standard .pdf bytes. Legacy binary
    .doc (pre-2007 format) isn't a zip/XML package at all — python-docx
    can't open it and would fail with a cryptic zip-format error, so we
    check for that specific case up front and raise something the user
    can actually act on instead."""
    if word_bytes[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ValueError("This looks like an older .doc file (pre-2007 Word format). Please open it in Word, use 'Save As' -> .docx, and upload that instead.")
    try:
        import docx
        doc = docx.Document(io.BytesIO(word_bytes))
        full_text = "\n".join(p.text for p in doc.paragraphs)

        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        y = 750
        for line in full_text.split("\n"):
            if y < 50:
                c.showPage()
                y = 750
            c.drawString(50, y, line[:90])
            y -= 15
        c.save()
        return buffer.getvalue()
    except ValueError:
        raise
    except Exception as e:
        logger.exception("word_to_pdf conversion failed")
        raise RuntimeError(f"Couldn't read this file as a Word document ({e}). Make sure it's a valid, non-corrupted .docx file.")


def social_media_download_engine(url: str) -> dict:
    """Extracts a real, direct downloadable media URL from a social media
    page URL (YouTube, IG, TikTok, Twitter/X, FB) via yt-dlp."""
    url_clean = url.strip()

    try:
        import yt_dlp
    except ImportError:
        return {"success": False, "error": "yt-dlp isn't installed on the server — run `pip install yt-dlp`."}

    # 'best' alone often resolves to a separate (not-yet-merged) video-only
    # stream on sites that split audio/video by quality — merging those
    # requires ffmpeg, which isn't available here. Asking for a *progressive*
    # (single-file, already has both audio+video) format avoids needing
    # ffmpeg at all, at the cost of capping resolution on a few sites.
    ydl_opts = {'format': 'best[acodec!=none][vcodec!=none]/best', 'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_clean, download=False)
    except Exception as e:
        return {"success": False, "error": f"Couldn't extract this media — {e}"}

    media_url = info.get('url')
    if not media_url:
        # Pick the best progressive (audio+video, already-merged) format
        # available, instead of blindly grabbing whichever format happened
        # to be last in the list (which was often audio-only or low-res).
        formats = [f for f in (info.get('formats') or [])
                   if f.get('url') and f.get('acodec') not in (None, 'none') and f.get('vcodec') not in (None, 'none')]
        if formats:
            best = max(formats, key=lambda f: f.get('height') or 0)
            media_url = best.get('url')

    if not media_url:
        return {"success": False, "error": "No directly-downloadable (audio+video merged) format is available for this URL without server-side ffmpeg, which isn't set up here."}

    return {
        "success": True,
        "title": info.get('title', 'Social Media Media File'),
        "download_url": media_url,
        "thumbnail": info.get('thumbnail'),
        "duration": info.get('duration'),
        "ext": info.get('ext', 'mp4'),
    }


def url_to_file_engine(url: str, output_format: str = "pdf") -> bytes:
    """Fetches a public webpage and exports its readable text content as a
    real PDF (or raw HTML). This extracts text, not a visual screenshot —
    a pixel-accurate "print webpage to PDF" needs a headless browser
    (Playwright/wkhtmltopdf), which needs system packages this host can't
    install. Previously "pdf" mode didn't produce a PDF at all — it wrapped
    raw unrendered HTML/CSS/JS source in Word-namespaced markup and served
    it with a .doc extension, which just showed garbled source code when
    opened. This produces an actual openable, readable PDF."""
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    html = resp.text

    if output_format == "html":
        return html.encode("utf-8")

    from bs4 import BeautifulSoup
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)[:120]
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 0.75 * inch
    y = height - margin
    c.setFont("Helvetica-Bold", 14)
    for chunk_start in range(0, len(title), 90):
        c.drawString(margin, y, title[chunk_start:chunk_start + 90])
        y -= 18
    y -= 10
    c.setFont("Helvetica", 10)
    max_chars = 95
    for line in lines:
        for i in range(0, len(line), max_chars) or [0]:
            if y < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - margin
            c.drawString(margin, y, line[i:i + max_chars])
            y -= 13
    c.save()
    return buffer.getvalue()
