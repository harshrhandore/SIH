"""PDF text extraction followed by bounded optional local OCR."""

from io import BytesIO
from pypdf import PdfReader
from PIL import Image
from app.core.errors import fail
from app.integrations import ocr_tesseract


def extract_text(data, mime):
    warnings: list[str] = []
    metadata = {}
    text = ""
    image = None
    if mime == "application/pdf":
        reader = PdfReader(BytesIO(data))
        metadata = {str(k): str(v) for k, v in (reader.metadata or {}).items()}
        text = "\n".join(p.extract_text() or "" for p in reader.pages)
        if len("".join(text.split())) >= 50 and all(
            label in text for label in ["Name:", "Issued by:", "Date:", "Credential:"]
        ):
            return text[:16000], "PDF_TEXT", metadata, warnings
        import pypdfium2

        doc = pypdfium2.PdfDocument(data)
        page = doc[0]
        if page.get_width() * page.get_height() * (150 / 72) ** 2 > 40_000_000:
            fail("UNSUPPORTED_DOCUMENT")
        image = page.render(scale=150 / 72).to_pil()
    else:
        image = Image.open(BytesIO(data))
    if ocr_tesseract.available():
        text, engine_warnings = ocr_tesseract.extract(image)
        warnings.extend(engine_warnings)
        if text.strip():
            return text, "TESSERACT", metadata, warnings
    warnings.append("No available OCR engine produced readable text.")
    return "", "UNAVAILABLE", metadata, warnings
