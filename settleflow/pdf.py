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
from datetime import date
from decimal import Decimal
from pathlib import Path

from .models import Txn
from .parsers import _money, parse_date

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


def parse_sbi_credit_card(text: str) -> list[Txn]:
    """Parse an SBI credit-card statement's text into Txn rows.

    Layout: ``Date | Description | Amount (Rs.)``. Purchases/fees are plain
    (debit -> negative); payments and refunds carry a trailing ``Cr`` marker
    (credit -> positive).
    """
    row = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?[\d,]+\.\d{2})\s*(?:CR\.?)?\s*$",
        re.IGNORECASE,
    )
    txns: list[Txn] = []
    for ln in text.replace("\r", "\n").split("\n"):
        ln = ln.strip()
        m = row.match(ln)
        if not m:
            continue
        amount = _money(m.group(3))
        is_credit = amount < 0 or re.search(r"\bCR\.?$", ln, re.IGNORECASE) is not None
        magnitude = -amount if amount < 0 else amount
        txns.append(Txn(
            utr=None,
            amount=magnitude if is_credit else -magnitude,
            txn_date=parse_date(m.group(1)),
            ref=m.group(2).strip() or None,
        ))
    return txns


# Legacy SBI netbanking layout:
#   Txn Date | Value Date | Description | Ref No./Cheque No. | Debit | Credit | Balance
# Dates are "dd MMM" and the transaction year is printed on a following
# "yyyy yyyy" line (a PDF text-extraction artifact). One of debit/credit is
# populated per row (the other collapses), so the sign is recovered from
# description heuristics ("BY UPI" = credit, "TO UPI" = debit, etc.).
_NET_ROW = re.compile(r"^(\d{1,2}\s+[A-Za-z]{3})(?:\s+\d{1,2}\s+[A-Za-z]{3})?\s*(.*)$")
_NET_YEAR_LINE = re.compile(r"^(\d{4})\s+(\d{4})\s*(.*)$")
_NET_AMOUNT = re.compile(r"[\d,]+\.\d{2}")
_NET_UTR = re.compile(r"\b(?:NEFT\*?[A-Z0-9*]+|[A-Za-z0-9]{12,})\b")


def _is_credit(desc: str) -> bool:
    d = desc.upper()
    if d.startswith("TO") or d.startswith("DEBIT"):
        return False
    if re.search(r"TRANSFER[- ]?INB", d):
        return True
    if any(kw in d for kw in ("CREDIT", "DEPOSIT", "SALARY", "INTEREST",
                              "REFUND", "INWARD", "ACHC")):
        return True
    if d.endswith("CR"):
        return True
    if re.search(r"^BY\s+(TRANSFER|CLEARING|CASH|CHEQUE|NEFT|RTGS|IMPS|UPI)", d):
        return True
    return False


def parse_sbi_netbanking(text: str) -> list[Txn]:
    """Parse a legacy SBI netbanking statement's text into Txn rows."""
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln]

    header_i = None
    for i, ln in enumerate(lines):
        if re.search(r"Txn\s+Date", ln, re.IGNORECASE) and "Balance" in ln:
            header_i = i
            break
    if header_i is None:
        raise PdfLayoutError("no SBI netbanking transaction table found")

    txns: list[Txn] = []
    i = header_i + 1
    while i < len(lines):
        ln = lines[i]
        m = _NET_ROW.match(ln)
        if not m:
            i += 1
            continue
        date_str = m.group(1)
        rest = m.group(2)

        year = None
        tail = ""
        if i + 1 < len(lines):
            ym = _NET_YEAR_LINE.match(lines[i + 1])
            if ym:
                year = int(ym.group(1))
                tail = ym.group(3).strip()
                i += 1  # consume the year line

        amts = list(_NET_AMOUNT.finditer(rest))
        if len(amts) < 2:
            i += 1
            continue
        balance = _money(amts[-1].group(0))
        amount = _money(amts[-2].group(0))

        desc = rest[:amts[-2].start()].strip()
        if tail:
            desc = f"{desc} {tail}".strip()
        desc = re.sub(r"\s+", " ", desc)

        if year is None:
            ym2 = re.search(r"from\s+\d{1,2}\s+\w{3}\s+(\d{4})", text, re.IGNORECASE)
            year = int(ym2.group(1)) if ym2 else date.today().year

        ref = None
        um = _NET_UTR.search(desc)
        if um:
            ref = um.group(0)

        txns.append(Txn(
            utr=ref,
            amount=(Decimal(1) if _is_credit(desc) else Decimal(-1)) * amount,
            txn_date=parse_date(f"{date_str} {year}"),
            ref=desc or None,
        ))
        i += 1
    return txns


def parse_sbi_statement(text: str) -> list[Txn]:
    """Parse any SBI statement text (YONO, netbanking, credit card) into Txn rows.

    Credit -> positive amount, debit -> negative. The narration becomes
    Txn.ref; a reference number, when present, becomes Txn.utr. Raises
    PdfLayoutError on an unrecognised layout.
    """
    upper = text.upper()
    if "CREDIT CARD STATEMENT" in upper or "AMOUNT (RS.)" in upper:
        return parse_sbi_credit_card(text)
    if "TXN DATE" in upper and "VALUE" in upper and "BALANCE" in upper:
        return parse_sbi_netbanking(text)

    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln]

    saw_yono_header = False
    for ln in lines:
        if all(k in ln for k in _YONO_HEADER):
            saw_yono_header = True
            break
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
            amount = _money(credit)
        else:
            amount = -_money(debit)
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
        if not doc.is_pdf:
            raise ValueError(
                f"{Path(path).name} is not a PDF file — refusing to parse non-PDF "
                "input as a statement (D-7 trust boundary; pymupdf leniently opens "
                "plain text as a 1-page doc)"
            )
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


def parse_sbi_pdf(path: str | Path, *, ocr: bool = False) -> list[Txn]:
    """Extract the text of an SBI statement PDF and parse its transactions.

    By default reads the native text layer. For a SCANNED (image-only) PDF,
    `extract_pdf_text` raises `PdfScannedError`; set `ocr=True` to fall back to
    OCR (settleflow.ocr, best-effort: it recovers a text layer, not perfect
    columns). Requires `pip install 'settleflow[ocr]'`.
    """
    try:
        return parse_sbi_statement(extract_pdf_text(path))
    except PdfScannedError:
        if not ocr:
            raise
        from .ocr import parse_sbi_scanned_pdf  # lazy: avoid module-load cycle

        return parse_sbi_scanned_pdf(path)
