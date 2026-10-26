"""Bounded Tesseract adapter; the binary and language data are external capabilities."""

import shutil


def available():
    return bool(shutil.which("tesseract"))


def extract(image):
    if not available():
        return "", ["Tesseract executable is unavailable."]
    import pytesseract

    try:
        return pytesseract.image_to_string(image, timeout=15)[:16000], []
    except (RuntimeError, pytesseract.TesseractError):
        return "", ["Tesseract timed out or failed."]
