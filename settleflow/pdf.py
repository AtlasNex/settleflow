"""PDF bank-statement extraction (SBI first). Separate trust boundary per D-20.

The library core stays stdlib-only (CONSTRAINTS.md #6 / D-17), so PDF support
is an OPTIONAL extra: `pip install settleflow[pdf]` pulls `pymupdf`, imported
lazily so `import settleflow` never requires it.

Scope (v1): TEXT-based SBI statements in the modern **YONO / e-statement**
layout, whose transaction table is

    Date | Transaction Reference | Ref.No./Chq.No. | Credit | Debit | Balance

Rows may wrap onto several lines in the extracted text (a long narration
overflows its column), so the parser reconstructs each transaction from the
trailing money columns (ref / credit / debit / balance), never from a guessed
column width. Verified against real SBI statements (anonymised Apache-2.0
fixtures in tests/fixtures/sbi/, see NOTICE.md).

Explicitly NOT handled (raise rather than half-parse, D-7):
- The legacy netbanking statement layout ("Txn Date | Value Date | Description
  | Ref No./Cheque No. | Debit | Credit | Balance"), whose day/month/year
  split across wrapped lines in the text layer — use the CSV export instead.
- Scanned (image-only) PDFs — needs OCR, a separate layer.
- Password-locked PDFs — detected and reported; decrypt externally first.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

from .models import Txn
from .parsers import parse_date

_MONEY = re.compile(r"^\d[\d,]*\.\d{2}$")
_YONO_DATE = re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}$")
_YONO_HEADER = ("Transaction Reference", "Balance")
_NETBANKING_HEADER = ("Txn Date", "Description")


class PdfEncryptedError(ValueError):
    """The PDF needs a user password before its text can be read."""


class PdfScannedError(ValueError):
    """The PDF has no text layer (scanned image); OCR is a separate layer."""


class PdfLayoutError(ValueError):
    """The PDF's statement layout is recognised but not yet supported."""


def _is_money(tok: str) -> bool:
    return bool(_MONEY.match(tok))


def _is_dash(tok: str) -> bool:
    return tok == "-"


def _is_yono_date(tok: str) -> bool:
    return bool(_YONO_DATE.match(tok))


def _tail(toks: list[str]):
    """Return (refno, credit, debit, balance) if `toks` ends in a YONO money row.

    The trailing four columns of a YONO transaction row are always
    `Ref.No./Chq.No. Credit Debit Balance`, with exactly one of credit/debit
    a money amount (the other a "-") and balance always money. Returns None
    when the line does not end that way (header/footer/narration-only lines).
    """
    if len(toks) < 4:
        return None
    refno, credit, debit, balance = toks[-4], toks[-3], toks[-2], toks[-1]
    if not _is_money(balance):
        return None
    if not ((_is_money(credit) and _is_dash(debit))
            or (_is_dash(credit) and _is_money(debit))):
        return None
    if not (_is_dash(refno) or (refno.replace(",", "").isalnum() and not _is_money(refno))):
        return None
    return refno, credit, debit, balance


def parse_sbi_statement(text: str) -> list[Txn]:
    """Parse the text layer of a modern SBI (YONO) statement into Txn rows.

    Credit -> positive amount, debit -> negative. The bank's Ref.No./Chq.No.
    becomes Txn.utr (None when "-"), the narration becomes Txn.ref. Rows are
    reconstructed from the money-column tail, so a narration that wraps onto
    its own line is still attached to the right transaction. Raises
    PdfLayoutError if the text looks like the legacy netbanking layout (not
    yet supported) rather than silently mis-parsing it.
    """
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln]

    saw_yono_header = False
    for ln in lines:
        if all(k in ln for k in _YONO_HEADER):
            saw_yono_header = True
            break
        if all(k in ln for k in _NETBANKING_HEADER) and "Balance" in ln:
            raise PdfLayoutError(
                "legacy netbanking statement layout is not yet supported by the "
                "PDF parser — use SBI's CSV/Excel export (load_bank_statement, "
                "'sbi') instead"
            )
    if not saw_yono_header:
        raise PdfLayoutError(
            "no SBI statement transaction table found (looked for a header row "
            "with 'Transaction Reference' and 'Balance')"
        )

    txns: list[Txn] = []
    cur_date = None
    cur_narration: list[str] = []

    def _emit(refno, credit, debit):
        nonlocal cur_date, cur_narration
        if cur_date is None:
            # money row with no preceding date line: cannot attribute it
            cur_narration = []
            return None
        narration = " ".join(cur_narration) or None
        if _is_money(credit):
            amount = Decimal(credit.replace(",", ""))
        else:
            amount = -Decimal(debit.replace(",", ""))
        utr = None if _is_dash(refno) else refno
        txns.append(Txn(utr=utr, amount=amount, txn_date=cur_date, ref=narration))
        cur_date = None
        cur_narration = []
        return txns[-1]

    for ln in lines:
        toks = ln.split()
        if not toks:
            continue
        if all(t == "null" for t in toks):
            continue
        if all(k in ln for k in _YONO_HEADER) or all(k in ln for k in _NETBANKING_HEADER):
            continue  # header row (may repeat across pages / tables)
        if any(m in ln for m in ("TRANSACTION OVERVIEW", "Opening Balance",
                                 "Closing Balance", "Contents of this")):
            cur_date = None
            cur_narration = []
            continue

        tail = _tail(toks)
        if tail:
            refno, credit, debit, _balance = tail
            lead = toks[:-4]
            if lead and _is_yono_date(lead[0]):
                cur_date = parse_date(lead[0])
                cur_narration = lead[1:]
            _emit(refno, credit, debit)
            continue

        # No money tail: a date-only line starts a transaction; anything else
        # is a continuation of the current narration.
        if _is_yono_date(toks[0]):
            cur_date = parse_date(toks[0])
            cur_narration = toks[1:]
        else:
            cur_narration.extend(toks)

    return txns


def extract_pdf_text(path: str | Path) -> str:
    """Return the full text layer of a PDF, or raise a clear, specific error.

    Raises PdfEncryptedError for a password-locked PDF and PdfScannedError for
    an image-only PDF with no text layer. `pymupdf` is imported lazily so the
    stdlib-only core never needs it unless this function is called.
    """
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover - env-specific
        raise ImportError(
            "PDF support requires pymupdf: pip install 'settleflow[pdf]'"
        ) from exc

    doc = pymupdf.open(str(path))
    try:
        if doc.needs_pass:
            raise PdfEncryptedError(
                f"{Path(path).name} is password-protected; decrypt it (or export "
                "an unlocked copy) before parsing"
            )
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()

    if not text.strip():
        raise PdfScannedError(
            f"{Path(path).name} has no text layer (scanned image). OCR is a "
            "separate, not-yet-built layer — see docs/FEATURE.md"
        )
    return text


def parse_sbi_pdf(path: str | Path) -> list[Txn]:
    """Extract the text of an SBI statement PDF and parse its transactions."""
    return parse_sbi_statement(extract_pdf_text(path))
