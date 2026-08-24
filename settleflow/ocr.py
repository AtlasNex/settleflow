"""Optional OCR layer for SCANNED (image-only) bank-statement PDFs.

The core is stdlib-only (CONSTRAINTS.md #6); OCR is an OPTIONAL extra that uses
the already-installed **Tesseract** engine (invoked via its CLI, no Python OCR
package, no network). `pymupdf` rasterises each page; Tesseract recovers a text
layer; the existing `parse_sbi_statement` dispatcher parses it. Both are imported
lazily, so `import settleflow` never requires them.

Scope (D-27): a scanned SBI statement has no text layer, so `extract_pdf_text`
raises `PdfScannedError`. This layer rasterises + OCRs the page and feeds the
recovered text into the same native layout dispatch.

Honest ceiling: OCR recovers a text LAYER, not perfect columns. On a clean scan
Tesseract (--psm 6) preserves the statement's columns and header, so the native
parser works; on a noisy/skewed scan the text may merge and the parser raises a
clear `PdfLayoutError` rather than guessing. Accuracy depends on the scan.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import Txn
from .pdf import parse_sbi_statement


class OcrUnavailableError(ValueError):
    """Tesseract is not installed / not locatable on this machine."""


class OcrError(ValueError):
    """OCR ran but recovered no usable text layer."""


def _tesseract_binary() -> str:
    """Return the tesseract executable path, or raise OcrUnavailableError."""
    cands = [
        shutil.which("tesseract"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for c in cands:
        if c and Path(c).exists():
            return c
    raise OcrUnavailableError(
        "Tesseract not found. Install Tesseract (tesseract-ocr) and ensure it is "
        "on PATH — e.g. pip install 'settleflow[ocr]' after installing Tesseract."
    )


def ocr_pdf_text(path: str | Path, *, dpi: int = 300, psm: int = 6) -> str:
    """Rasterise each page and OCR it with Tesseract into a text layer.

    Raises `OcrUnavailableError` if Tesseract isn't installed, `ValueError` for a
    non-PDF file, `PdfEncryptedError` for a password-locked file, and `OcrError`
    if no text could be recovered. Returns the text per page, in page order.
    """
    from .pdf import PdfEncryptedError

    import pymupdf

    tess = _tesseract_binary()
    doc = pymupdf.open(str(path))
    try:
        if not doc.is_pdf:
            raise ValueError(
                f"{Path(path).name} is not a PDF file — refusing to OCR non-PDF input"
            )
        if doc.needs_pass:
            raise PdfEncryptedError(
                f"{Path(path).name} is password-protected; decrypt it first"
            )

        pages: list[str] = []
        with tempfile.TemporaryDirectory() as td:
            for i, page in enumerate(doc):
                png = Path(td) / f"p{i}.png"
                page.get_pixmap(dpi=dpi).save(str(png))
                res = subprocess.run(
                    [tess, str(png), "stdout", "--psm", str(psm), "-l", "eng"],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                )
                if res.returncode == 0 and res.stdout.strip():
                    pages.append(res.stdout)
    finally:
        doc.close()

    out = "\n".join(pages)
    if not out.strip():
        raise OcrError(
            f"{Path(path).name}: OCR found no text — is this actually a statement scan?"
        )
    return out


def parse_sbi_scanned_pdf(path: str | Path, *, dpi: int = 300, psm: int = 6) -> list[Txn]:
    """OCR a scanned SBI statement PDF and parse it (best-effort).

    Tesseract recovers the text layer, which is fed into the native
    `parse_sbi_statement` dispatcher (YONO / netbanking / credit-card). On a
    clean scan the columns are preserved; on a noisy scan the parser raises
    `PdfLayoutError` rather than guessing columns.
    """
    return parse_sbi_statement(ocr_pdf_text(path, dpi=dpi, psm=psm))
