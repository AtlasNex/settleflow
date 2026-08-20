"""CSV/API loaders. Field names are explicit so any vendor/bank plugs in."""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import ReconLine, Settlement, Txn

_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d",      # ISO / machine
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",  # Indian numeric (4-digit year)
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y",  # month-name (SBI "1 Jul 2026", ICICI "01-Jul-2024")
)

# Two-digit-year Indian dates ("01/07/26", "1-7-26"). Handled explicitly so that
# strptime's greedy %Y (which would read "26" as the year 26 AD) never fires.
_TWO_DIGIT_YEAR = re.compile(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2})$")

# Trailing time component ("2022-06-07T13:33:57", "29/06/2022 07:34:39").
_TIME_SUFFIX = re.compile(r"^(.+?)[T ]\d{1,2}:\d{2}")


def parse_date(value: str) -> date:
    s = value.strip()
    m = _TIME_SUFFIX.match(s)
    if m:
        s = m.group(1)
    m = _TWO_DIGIT_YEAR.match(s)
    if m:
        d, mo, y = m.groups()
        return date(2000 + int(y), int(mo), int(d))
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unparseable date: {value!r}")


def parse_amount(value: str) -> Decimal:
    s = (
        value.strip()
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs", "")
        .replace("rs", "")
        .replace(" ", "")
    )
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"unparseable amount: {value!r}") from exc


def load_csv(
    path: str | Path,
    utr_col: str,
    amount_col: str,
    date_col: str,
    ref_col: str | None = None,
) -> list[Txn]:
    """Read a CSV into Txn rows.

    Column names are passed explicitly, so this works for any settlement-file
    or bank-statement layout without vendor-specific code. The mapping for a
    given vendor is a small dict, filled from a real sample file, not guessed.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        txns: list[Txn] = []
        for row in reader:
            utr = (row.get(utr_col) or "").strip() or None
            txns.append(
                Txn(
                    utr=utr,
                    amount=parse_amount(row[amount_col]),
                    txn_date=parse_date(row[date_col]),
                    ref=(row.get(ref_col) or "").strip() or None if ref_col else None,
                )
            )
    return txns


def _money_or_zero(value: str | None) -> Decimal:
    """Parse an optional money cell; empty/blank -> Decimal(0)."""
    s = (value or "").strip()
    if not s:
        return Decimal("0")
    return parse_amount(s)


def load_bank_statement_csv(
    path: str | Path,
    *,
    date_col: str,
    debit_col: str,
    credit_col: str,
    ref_col: str | None = None,
    narration_col: str | None = None,
) -> list[Txn]:
    """Read an Indian bank-statement CSV into Txn rows.

    Indian statements (HDFC/SBI/ICICI/Axis/Kotak) use TWO columns — a debit
    ("Withdrawal") and a credit ("Deposit") — not one signed amount. Exactly one
    is populated per row. This loader folds them into the single Txn.amount:
    credits are positive, debits are negative. The bank's own reference number
    (Chq./Ref.No. / Ref No. / CHQNO) becomes Txn.utr; the narration becomes
    Txn.ref so a human can read what each line was.

    Real bank CSVs carry preamble rows above the header (HDFC ~2-3, Axis ~20),
    so the header row is detected by scanning for the row containing date_col +
    debit_col + credit_col rather than assuming row 0.
    """
    required = {date_col, debit_col, credit_col}
    raw = Path(path).read_text(encoding="utf-8-sig")

    # Auto-detect the delimiter. SBI's native "CSV" export is actually a
    # tab-separated ".xls"; HDFC/ICICI/Axis/Kotak are comma CSVs. Sniffing
    # covers both without per-bank code.
    try:
        dialect = csv.Sniffer().sniff(raw[:4096], delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel  # fall back to comma

    rows = list(csv.reader(raw.splitlines(), dialect))

    header_i = None
    for i, row in enumerate(rows):
        if required.issubset({c.strip() for c in row}):
            header_i = i
            break
    if header_i is None:
        raise ValueError(
            f"no header row found containing {sorted(required)} — is this a "
            f"statement CSV for this bank?"
        )

    header = [c.strip() for c in rows[header_i]]
    idx = {name: header.index(name) for name in (date_col, debit_col, credit_col)}

    def _cell(row, name):
        if name is None:
            return None
        if name not in header:
            return None
        return (row[header.index(name)] or "").strip() or None

    txns: list[Txn] = []
    for row in rows[header_i + 1:]:
        debit = _money_or_zero(row[idx[debit_col]] if idx[debit_col] < len(row) else None)
        credit = _money_or_zero(row[idx[credit_col]] if idx[credit_col] < len(row) else None)
        if debit == 0 and credit == 0:
            continue  # skip balance-only / blank / OPENING BALANCE rows
        amount = credit if credit != 0 else -debit
        txns.append(
            Txn(
                utr=_cell(row, ref_col),
                amount=amount,
                txn_date=parse_date(row[idx[date_col]]),
                ref=_cell(row, narration_col),
            )
        )
    return txns


_MONEY_RE = re.compile(r"^\d[\d,]*\.\d{2}$")


def _is_money(tok: str) -> bool:
    """True for a money token like '347.00' or '9,653.00' (Indian grouping)."""
    return bool(_MONEY_RE.match(tok))


# Kotak's netbanking statement (and some other banks) use a SINGLE combined
# amount column with an explicit Dr/Cr marker rather than separate Debit/Credit
# columns: "347.00 Dr" = debit, "35,000.00 Cr" = credit. The marker makes the
# sign unambiguous in flattened text (unlike separate Debit/Credit columns,
# whose empty cells collapse ambiguously).
_DRCR_DATE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2,4}$")  # 01-Jul-2025


def parse_drcr_statement(text: str) -> list[Txn]:
    """Parse a Dr/Cr-marker statement's text into Txn rows.

    Each transaction ends with a trailing "amount Dr|Cr balance" trio; the
    narration may wrap onto its own line, so it is accumulated until that trio
    appears. Debit (Dr) -> negative amount, credit (Cr) -> positive. The
    narration becomes Txn.ref; there is no separate reference column in this
    format, so Txn.utr stays None.
    """
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln]

    txns: list[Txn] = []
    cur_date = None
    cur_narration: list[str] = []

    for ln in lines:
        # footer/aggregate rows must not be mistaken for transactions (the
        # "Sub Total" line also carries Dr/Cr markers)
        if any(m in ln for m in ("Opening Balance", "Closing Balance", "Sub Total")):
            cur_date = None
            cur_narration = []
            continue
        toks = ln.split()
        if not toks:
            continue
        # trailing money trio: amount Dr|Cr balance
        if (len(toks) >= 3 and toks[-2] in ("Dr", "Cr")
                and _is_money(toks[-1]) and _is_money(toks[-3])):
            amount = Decimal(toks[-3].replace(",", ""))
            signed = -amount if toks[-2] == "Dr" else amount
            lead = toks[:-3]
            if lead:
                if _DRCR_DATE.match(lead[0]):
                    cur_date = parse_date(lead[0])
                    cur_narration = lead[1:]
                else:
                    # narration wrapped onto the money row's first line
                    cur_narration.extend(lead)
            if cur_date is not None:
                txns.append(Txn(utr=None, amount=signed, txn_date=cur_date,
                                ref=" ".join(cur_narration) or None))
            cur_date = None
            cur_narration = []
            continue
        # a date at the start of a line opens a new transaction; anything else
        # is a continuation of the current narration
        if _DRCR_DATE.match(toks[0]):
            cur_date = parse_date(toks[0])
            cur_narration = toks[1:]
        else:
            cur_narration.extend(toks)

    return txns


def load_bank_statement_drcr(path: str | Path) -> list[Txn]:
    """Load a Dr/Cr-marker bank statement (text/CSV) into Txn rows."""
    return parse_drcr_statement(Path(path).read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------------------
# Generic flattened-text bank statement parser (collapsed debit/credit columns).
#
# PNB, DBS and others print separate Withdrawal/Deposit columns whose blank
# cells collapse out of the extracted text, so a row only shows the transaction
# amount followed by the running balance. The debit/credit sign is recovered by
# running-balance arithmetic against the opening balance (prev + amount ==
# balance -> credit; prev - amount == balance -> debit), falling back to a
# Dr/Cr marker and then description heuristics. This is the same proven
# technique as raptar231/indian-bank-statement-parser (Apache-2.0).
# ---------------------------------------------------------------------------

_BANK_AMOUNT = re.compile(r"[\d,]+\.\d{2}")
_OPENING_BAL = re.compile(r"Opening\s+Balance[.:\s]*(?:INR\s*)?([\d,]+\.\d{2})", re.IGNORECASE)
_MARKER = re.compile(r"([\d,]+\.\d{2})\s*(Dr|Cr)\b", re.IGNORECASE)
_SKIP_LINE = re.compile(
    r"^(?:Opening|Closing)\s+Balance|Sub\s*[- ]?Total|Total\b|"
    r"Statement\s+(?:Period|For)|A/C|Account\s+(?:Number|No|Type)|"
    r"Branch|IFSC|Page\b|Date\s+Transaction|Transaction\s+Date|"
    r"Cheque\s+Number|Withdrawal|Deposit|Transaction\s+Details",
    re.IGNORECASE,
)
_CREDIT_HINT = re.compile(r"\bCr\b|REFUND|SALARY|DEPOSIT|INWARD|NEFT|RTGS|INTEREST", re.IGNORECASE)
_REF_PATTERNS = [
    re.compile(r"UPI/(?:DR|CR)/(\d+)", re.IGNORECASE),
    re.compile(r"\bUTR\s*(?:NO\.?)?[:]?\s*([A-Z0-9]+)", re.IGNORECASE),
    re.compile(r"([A-Z]?\d{12,})"),
]


def _extract_ref(narration: str | None) -> str | None:
    """Pull a UPI reference / UTR / 12+ digit run out of a narration."""
    if not narration:
        return None
    for pat in _REF_PATTERNS:
        m = pat.search(narration)
        if m:
            return m.group(1)
    return None


def _is_date_token(tok: str) -> bool:
    try:
        parse_date(tok)
        return True
    except ValueError:
        return False


def _block_narration(block: list[str], amounts: list[tuple], narration_after: bool) -> str:
    """Reassemble the narration from a transaction block.

    `amounts` is a list of (text, line_idx, start, end) for every money token.
    PNB prints the narration AFTER the balance; DBS prints it BEFORE the amount.
    """
    parts: list[str] = []
    if narration_after:
        bal_line, _, bal_end = amounts[-1][1], amounts[-1][2], amounts[-1][3]
        for i, ln in enumerate(block):
            if i == bal_line:
                tail = ln[bal_end:].strip()
                if tail:
                    parts.append(tail)
            elif ln.strip():
                parts.append(ln.strip())
    else:
        first_line = amounts[0][1]
        for i, ln in enumerate(block):
            if i == 0:
                date_len = len(block[0].split()[0])
                if first_line == 0:
                    seg = ln[date_len:amounts[0][2]]
                else:
                    seg = ln[date_len:]
            else:
                line_amts = [a for a in amounts if a[1] == i]
                seg = ln[:line_amts[0][2]] if line_amts else ln
            seg = seg.strip()
            if seg:
                parts.append(seg)
    nar = re.sub(r"^[\s\-:;]+|[\s\-:;]+$", "", " ".join(parts))
    return re.sub(r"\s+", " ", nar).strip()


def _parse_bank_block(block, prev_balance, narration_after):
    """Parse one transaction block -> (Txn, balance) or None."""
    try:
        txn_date = parse_date(block[0].split()[0])
    except ValueError:
        return None

    amounts = []
    for i, ln in enumerate(block):
        for mm in _BANK_AMOUNT.finditer(ln):
            amounts.append((mm.group(0), i, mm.start(), mm.end()))
    if len(amounts) < 2:
        return None

    balance = Decimal(amounts[-1][0].replace(",", ""))
    amount = Decimal(amounts[-2][0].replace(",", ""))

    narration = _block_narration(block, amounts, narration_after)

    marker = _MARKER.search(" ".join(block))
    if marker:
        sign = 1 if marker.group(2).upper() == "CR" else -1
    elif prev_balance is not None:
        if prev_balance + amount == balance:
            sign = 1
        elif prev_balance - amount == balance:
            sign = -1
        else:
            sign = 1 if _CREDIT_HINT.search(narration) else -1
    else:
        sign = 1 if _CREDIT_HINT.search(narration) else -1

    return (
        Txn(utr=_extract_ref(narration), amount=Decimal(sign) * amount,
            txn_date=txn_date, ref=narration or None),
        balance,
    )


def parse_bank_text(text: str, *, narration_after: bool = False) -> list[Txn]:
    """Parse a flattened-text bank statement with collapsed debit/credit columns.

    `narration_after=True` for PNB (narration after the balance), False for DBS
    (narration before the amount). Debit -> negative amount, credit -> positive.
    """
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]
    lines = [ln for ln in lines if ln]

    m = _OPENING_BAL.search(text)
    prev_balance = Decimal(m.group(1).replace(",", "")) if m else None

    blocks: list[list[str]] = []
    current: list[str] | None = None
    for ln in lines:
        if _SKIP_LINE.match(ln):
            continue
        toks = ln.split()
        if toks and _is_date_token(toks[0]):
            current = [ln]
            blocks.append(current)
        elif current is not None:
            current.append(ln)

    txns: list[Txn] = []
    for block in blocks:
        parsed = _parse_bank_block(block, prev_balance, narration_after)
        if parsed is None:
            continue
        txn, balance = parsed
        txns.append(txn)
        prev_balance = balance
    return txns


def load_bank_statement_text(path: str | Path, *, narration_after: bool = False) -> list[Txn]:
    """Load a flattened-text bank statement (PNB/DBS) into Txn rows."""
    return parse_bank_text(Path(path).read_text(encoding="utf-8-sig"),
                           narration_after=narration_after)


def _paise(value) -> Decimal:
    """Razorpay returns money in the smallest currency unit (paise). Convert to rupees."""
    return Decimal(value) / Decimal("100")


def _epoch_date(value) -> date:
    return datetime.fromtimestamp(int(value), tz=timezone.utc).date()


def parse_razorpay_settlements(data: dict) -> list[Settlement]:
    """Parse a Razorpay 'Fetch All Settlements' response into Settlement rows.

    Field names follow the documented API schema (id, entity, amount, fees,
    tax, utr, created_at). amount/fees/tax are integers in paise and are
    converted to Decimal rupees. Non-settlement entities are skipped.
    """
    out: list[Settlement] = []
    for item in data.get("items", []):
        if item.get("entity") != "settlement":
            continue
        out.append(
            Settlement(
                settlement_id=item["id"],
                amount=_paise(item.get("amount", 0)),
                created_at=_epoch_date(item["created_at"]),
                utr=item.get("utr"),
                fees=_paise(item.get("fees", 0)),
                tax=_paise(item.get("tax", 0)),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Settlement recon report (per-transaction line items) — verified schema.
#
# GET /v1/settlements/recon/combined — the 24 documented response parameters
# (verified against the docs page 2026-08-16 via Wayback snapshot of
# razorpay.com/docs/api/settlements/fetch-recon). Money fields arrive as
# integers in PAISE; created_at/settled_at are epoch seconds. `credit_type`
# appears in the docs example but is not among the 24 documented params.
# ---------------------------------------------------------------------------

RAZORPAY_RECON_KEYS = frozenset({
    "entity_id", "type", "debit", "credit", "amount", "currency", "fee",
    "tax", "on_hold", "settled", "created_at", "settled_at", "settlement_id",
    "description", "notes", "payment_id", "settlement_utr", "order_id",
    "order_receipt", "method", "card_network", "card_issuer", "card_type",
    "dispute_id",
})
RAZORPAY_RECON_REQUIRED = ("entity_id", "type", "settlement_id", "created_at")


def parse_razorpay_recon(data: dict) -> list[ReconLine]:
    """Parse a Razorpay 'Fetch Settlement Recon Details' response.

    Schema = the 24 documented response parameters. Money is in paise
    (converted to rupees); created_at/settled_at are epoch seconds.
    Raises ValueError on an unknown top-level shape or an item missing
    required keys — never guesses (D-7).
    """
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("razorpay recon response must be a dict with an 'items' list")
    out: list[ReconLine] = []
    for item in items:
        missing = [k for k in RAZORPAY_RECON_REQUIRED if k not in item]
        if missing:
            raise ValueError(f"recon line missing required keys: {missing}")
        unknown = set(item) - RAZORPAY_RECON_KEYS - {"credit_type", "posted_at"}
        if unknown:
            raise ValueError(f"unknown recon fields {sorted(unknown)} — schema changed?")
        settled_at = item.get("settled_at")
        out.append(
            ReconLine(
                entity_id=item["entity_id"],
                type=item["type"],
                debit=_paise(item.get("debit", 0)),
                credit=_paise(item.get("credit", 0)),
                amount=_paise(item.get("amount", 0)),
                currency=item.get("currency", "INR"),
                fee=_paise(item.get("fee", 0)),
                tax=_paise(item.get("tax", 0)),
                on_hold=bool(item.get("on_hold", False)),
                settled=bool(item.get("settled", False)),
                created_at=_epoch_date(item["created_at"]),
                settled_at=_epoch_date(settled_at) if settled_at else None,
                settlement_id=item["settlement_id"],
                credit_type=item.get("credit_type"),
                description=item.get("description"),
                notes=item.get("notes"),
                payment_id=item.get("payment_id"),
                settlement_utr=item.get("settlement_utr"),
                order_id=item.get("order_id"),
                order_receipt=item.get("order_receipt"),
                method=item.get("method"),
                card_network=item.get("card_network"),
                card_issuer=item.get("card_issuer"),
                card_type=item.get("card_type"),
                dispute_id=item.get("dispute_id"),
            )
        )
    return out


def load_razorpay_recon_json(path: str | Path) -> list[ReconLine]:
    """Load a saved recon API response JSON file from disk."""
    with open(path, encoding="utf-8") as fh:
        return parse_razorpay_recon(json.load(fh))


def load_recon_csv(
    path: str | Path,
    *,
    entity_id_col: str,
    type_col: str,
    debit_col: str,
    credit_col: str,
    amount_col: str,
    date_col: str,
    settlement_id_col: str,
    currency_col: str | None = None,
    fee_col: str | None = None,
    tax_col: str | None = None,
    utr_col: str | None = None,
    order_id_col: str | None = None,
    payment_id_col: str | None = None,
) -> list[ReconLine]:
    """Load a dashboard-exported recon CSV into ReconLine rows.

    Column names are EXPLICIT arguments (D-7): every vendor's CSV header
    differs, so the mapping is supplied from a real sample file, never
    guessed. Money columns must already be in rupees.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        out: list[ReconLine] = []
        for row in reader:
            fee = _money_or_zero(row.get(fee_col)) if fee_col else Decimal("0")
            tax = _money_or_zero(row.get(tax_col)) if tax_col else Decimal("0")
            out.append(
                ReconLine(
                    entity_id=(row.get(entity_id_col) or "").strip(),
                    type=(row.get(type_col) or "").strip().lower(),
                    debit=_money_or_zero(row.get(debit_col)),
                    credit=_money_or_zero(row.get(credit_col)),
                    amount=_money_or_zero(row.get(amount_col)),
                    currency=(row.get(currency_col) or "INR").strip() if currency_col else "INR",
                    fee=fee,
                    tax=tax,
                    on_hold=False,
                    settled=True,
                    created_at=parse_date(row[date_col]),
                    settled_at=None,
                    settlement_id=(row.get(settlement_id_col) or "").strip(),
                    settlement_utr=(row.get(utr_col) or "").strip() or None if utr_col else None,
                    order_id=(row.get(order_id_col) or "").strip() or None if order_id_col else None,
                    payment_id=(row.get(payment_id_col) or "").strip() or None if payment_id_col else None,
                )
            )
        return out
