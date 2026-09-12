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
    non-PDF file, `PdfEncryptedError` for a password-locked file,
    `PdfResourceLimitError` for a document over a documented bound, and
    `OcrError` if no text could be recovered. Returns the text per page, in page
    order.

    Work bounds (vuln-0012): page count, DECODED content-stream size, and
    accumulated characters are bounded like the text layer; the raster is
    bounded by pixel count (a page's MediaBox is chosen by the file's author,
    so it is never trusted as a size), one page image exists at a time, and
    Tesseract gets a timeout that arrives as this layer's own error type.
    Residual for untrusted files: a bound on a single page's parse cost cannot
    be expressed inside the process — run this layer under an external memory
    and CPU limit (container MemoryLimit, systemd MemoryMax, or a child
    process with resource.setrlimit).
    """
    from .pdf import (
        OCR_MAX_PIXELS, OCR_TIMEOUT_SECONDS,
        PDF_MAX_PAGE_STREAM_BYTES, PDF_MAX_PAGES, PDF_MAX_TEXT_CHARS,
        PdfEncryptedError, PdfResourceLimitError,
    )

    import pymupdf

    tess = _tesseract_binary()
    doc = pymupdf.open(str(path))
    pages: list[str] = []
    try:
        if not doc.is_pdf:
            raise ValueError(
                f"{Path(path).name} is not a PDF file — refusing to OCR non-PDF input"
            )
        if doc.needs_pass:
            raise PdfEncryptedError(
                f"{Path(path).name} is password-protected; decrypt it first"
            )
        if doc.page_count > PDF_MAX_PAGES:
            raise PdfResourceLimitError(
                f"{Path(path).name}: {doc.page_count} pages exceeds the "
                f"{PDF_MAX_PAGES}-page limit for this layer"
            )
        total_chars = 0
        for i, page in enumerate(doc):
            stream = len(page.read_contents())
            if stream > PDF_MAX_PAGE_STREAM_BYTES:
                raise PdfResourceLimitError(
                    f"{Path(path).name}: page {i + 1} has {stream:,} decoded "
                    f"content-stream bytes, over the {PDF_MAX_PAGE_STREAM_BYTES:,} "
                    "limit for this layer"
                )
            # The MediaBox is author-chosen: compute the pixels this page would
            # rasterise to at the requested DPI and refuse BEFORE allocating.
            w_pt, h_pt = page.rect.width, page.rect.height
            pixels = (max(w_pt, 0) * dpi / 72.0) * (max(h_pt, 0) * dpi / 72.0)
            if pixels > OCR_MAX_PIXELS:
                raise PdfResourceLimitError(
                    f"{Path(path).name}: page {i + 1} would rasterise to "
                    f"{pixels:,.0f} pixels at {dpi} DPI, over the "
                    f"{OCR_MAX_PIXELS:,} limit for this layer"
                )
            # One page's PNG exists at a time (removing what .ocr_pdf_text did
            # before: a whole document's rasters accumulated in one directory).
            with tempfile.TemporaryDirectory() as td:
                png = Path(td) / f"p{i}.png"
                page.get_pixmap(dpi=dpi).save(str(png))
                try:
                    res = subprocess.run(
                        [tess, str(png), "stdout", "--psm", str(psm), "-l", "eng"],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", timeout=OCR_TIMEOUT_SECONDS,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise PdfResourceLimitError(
                        f"{Path(path).name}: page {i + 1} OCR exceeded "
                        f"{OCR_TIMEOUT_SECONDS}s (a huge or degenerate page); "
                        "refusing the document"
                    ) from exc
            if res.returncode == 0 and res.stdout.strip():
                total_chars += len(res.stdout)
                if total_chars > PDF_MAX_TEXT_CHARS:
                    raise PdfResourceLimitError(
                        f"{Path(path).name}: OCR text exceeds "
                        f"{PDF_MAX_TEXT_CHARS:,} characters"
                    )
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
