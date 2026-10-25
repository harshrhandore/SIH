import csv
import hashlib
import json
from datetime import date, timedelta
from io import BytesIO
from uuid import UUID, uuid5

import pypdfium2
from app.core.algorithms import name_match, synthetic_id
from app.settings import ROOT
from openpyxl import Workbook
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

NAMESPACE = UUID("6f1c9a52-3d7e-4b18-9c4a-5e2d8b7a1f63")


def uid(kind, key):
    return uuid5(NAMESPACE, f"{kind}:{key}")


def reference(counter):
    if counter == 1:
        return dict(full_name="Riya Sharma", dob=date(2004, 6, 15), parent_name="Synthetic Sharma Parent")
    return dict(
        full_name=f"Aarav Reference{counter:03d}", dob=date(1960, 1, 1) + timedelta(days=counter), parent_name=None
    )


def pdf_bytes(name="Riya Sharma", title="Data Science Foundations", credential="SYNDS-0018", tampered=False):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(595, 842), invariant=1)
    c.setStrokeColorRGB(0.06, 0.36, 0.33)
    c.rect(40, 40, 515, 762)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(65, 735, "SYNTHETIC CERTIFICATE")
    c.setFont("Helvetica", 14)
    for index, text in enumerate(
        [
            f"Name: {name}",
            f"Certificate: {title}",
            "Issued by: Shiksham Demo Academy",
            "Date: 2026-06-20",
            f"Credential: {credential}",
        ]
    ):
        c.drawString(65, 640 - index * 42, text)
    c.setFont("Helvetica", 10)
    c.drawString(65, 110, "SYNTHETIC DEMO CERTIFICATE - NO REAL CREDENTIAL VALUE.")
    c.save()
    writer = PdfWriter(clone_from=PdfReader(BytesIO(buffer.getvalue())))
    writer.add_metadata(
        {
            "/CreationDate": "D:20260620000000Z",
            "/ModDate": "D:20260627000000Z" if tampered else "D:20260620000000Z",
            "/Creator": "LibreOffice" if tampered else "Shiksham Synthetic Generator",
            "/Producer": "LibreOffice" if tampered else "Shiksham Synthetic Generator",
        }
    )
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def generate():
    target = ROOT / "fixtures"
    (target / "certificates").mkdir(parents=True, exist_ok=True)
    for filename, data in [
        ("showcase-genuine.pdf", pdf_bytes()),
        ("showcase-tampered.pdf", pdf_bytes(name="Kunal Mehta", tampered=True)),
        ("showcase-python.pdf", pdf_bytes(title="Python Fundamentals", credential="SDA-00000018")),
    ]:
        (target / "certificates" / filename).write_bytes(data)
    doc = pypdfium2.PdfDocument(str(target / "certificates/showcase-genuine.pdf"))
    doc[0].render(scale=150 / 72).to_pil().save(target / "certificates/showcase-genuine.png")
    doc.close()
    headers = [
        "APAAR ID",
        "Enrollment No",
        "Student Name",
        "DOB",
        "Parent Name",
        "Program",
        "Admission Year",
        "Year",
        "Semester",
        "SGPA",
        "Credits",
        "Email",
        "Gender",
    ]
    rows = []
    expected = {}
    for n in range(1, 1001):
        row = {
            "APAAR ID": synthetic_id(100000 + n),
            "Enrollment No": f"DEMO-A-{n:04d}",
            "Student Name": f"Synthetic Learner {n:04d}",
            "DOB": (date(1980, 1, 1) + timedelta(days=n)).strftime("%d/%m/%Y"),
            "Parent Name": "",
            "Program": "BTECH:CSE",
            "Admission Year": "2022",
            "Year": "4",
            "Semester": "1",
            "SGPA": "8.0",
            "Credits": "22",
            "Email": f"demo.{n}@example.test",
            "Gender": "UNDISCLOSED",
        }
        codes = []
        ref = None
        if n <= 30:
            row["APAAR ID"] = ""
            codes = ["MISSING_APAAR"]
        elif n <= 50:
            row["APAAR ID"] = "BAD-" + row["APAAR ID"][4:]
            codes = ["INVALID_APAAR"]
        elif n <= 70:
            ref = n - 49
            row["APAAR ID"] = synthetic_id(ref)
            codes = ["DUPLICATE_APAAR"]
        elif n <= 90:
            ref = n - 49
            base = reference(ref)
            row.update(
                {
                    "Enrollment No": f"SYN-A-{ref:06d}",
                    "Student Name": base["full_name"].replace("Aarav", "Aariv"),
                    "DOB": base["dob"].strftime("%d/%m/%Y"),
                }
            )
            assert 70 <= name_match(row["Student Name"], base["full_name"])[0] < 95
            codes = ["NAME_INCONSISTENCY", "ENROLLMENT_CONFLICT"]
        elif n <= 100:
            row["SGPA"] = "12.5"
            codes = ["IMPOSSIBLE_ACADEMIC"]
        elif n <= 110:
            ref = n - 49
            base = reference(ref)
            row.update(
                {"Student Name": base["full_name"].replace("Aarav", "Aaravv"), "DOB": base["dob"].strftime("%d/%m/%Y")}
            )
            codes = ["POSSIBLE_DUPLICATE"]
        elif n <= 120:
            row["Student Name"] = ""
            codes = ["MISSING_MANDATORY"]
        if codes:
            expected[str(n)] = dict(
                primary=codes[0], secondary=codes[1:], candidate_reference_id=str(uid("student", ref)) if ref else None
            )
        rows.append(row)
    with (target / "demo-import-1000.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    book = Workbook()
    sheet = book.active
    sheet.append(headers)
    for row in rows:
        sheet.append([row[h] for h in headers])
    book.save(target / "demo-import-1000.xlsx")
    expected_document = dict(
        schema_version=1,
        seed=2026263,
        clock="2026-10-25",
        fixtureSHA=hashlib.sha256((target / "demo-import-1000.csv").read_bytes()).hexdigest(),
        rows=expected,
        totals=dict(clean=880, flagged=110, incomplete=10, primary=120, secondary=20, candidates=50, cases=120),
    )
    (target / "expected_findings.json").write_text(json.dumps(expected_document, indent=2))
    manifest = dict(
        seed=2026263,
        clock="2026-10-25",
        showcase_student_id=str(uid("student", 1)),
        showcase_apaar_id=synthetic_id(1),
        institution_a_id=str(uid("institution", 0)),
        correction_row=32,
        correct_to=synthetic_id(100032),
        correction_enrollment="DEMO-A-0032",
        expected_import=expected_document["totals"],
        fixture_import="demo-import-1000.csv",
        showcase_readiness=74,
        showcase_trust=91,
    )
    manifest["hashes"] = {
        str(p.relative_to(target)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(target.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
