from io import BytesIO
from uuid import uuid4
from pathlib import Path
import pytest
from pypdf import PdfWriter
from openpyxl import Workbook
from fastapi import HTTPException
from app.modules.imports.service import parse
from app.modules.certificates.service import inspect_document
from app.core.files import contained


def test_xlsx_formula_rejected():
    book = Workbook()
    sheet = book.active
    sheet.append(["Name"])
    sheet.append(["=1+1"])
    buffer = BytesIO()
    book.save(buffer)
    with pytest.raises(HTTPException) as caught:
        parse(buffer.getvalue(), "formula.xlsx")
    assert caught.value.detail["code"] == "XLSX_FORMULA_NOT_SUPPORTED"


def test_xlsx_width_bounded_before_materializing_rows():
    book = Workbook()
    book.active.append([str(i) for i in range(101)])
    buffer = BytesIO()
    book.save(buffer)
    with pytest.raises(HTTPException) as caught:
        parse(buffer.getvalue(), "wide.xlsx")
    assert caught.value.detail["code"] == "INVALID_HEADERS"


def test_encrypted_and_oversize_pdf_rejected():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt(str(uuid4()))
    buffer = BytesIO()
    writer.write(buffer)
    with pytest.raises(HTTPException) as caught:
        inspect_document(buffer.getvalue())
    assert caught.value.status_code == 422
    with pytest.raises(HTTPException) as caught:
        inspect_document(b"%PDF-" + b"x" * (10 * 1024 * 1024))
    assert caught.value.status_code == 413


def test_storage_traversal_rejected():
    with pytest.raises(HTTPException) as caught:
        contained(Path.cwd() / "storage", "../../outside")
    assert caught.value.status_code == 404


def test_html_disguised_as_pdf_rejected():
    with pytest.raises(HTTPException) as caught:
        inspect_document(b"<html><script>alert(1)</script></html>")
    assert caught.value.status_code == 415
