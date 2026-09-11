"""CSV/API loaders. Field names are explicit so any vendor/bank plugs in."""
from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import ReconLine, Settlement, Txn

_DATE_FORMATS = (
    "%Y-%m-%d", "%Y/%m/%d",      # ISO / machine
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",  # Indian numeric (4-digit year)
    "%d %b %Y", "%d %B %Y", "%d-%b-%Y",  # month-name (SBI "1 Jul 2026", ICICI "01-Jul-2024")
    "%d-%b-%y",  # two-digit-year month-name (e.g. "01-Jul-25")
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


#: A money cell after its currency prefix and thousands separators are removed.
#: ASCII digits, optional sign, optional decimals — nothing else. Deliberately
#: strict, because Decimal() accepts far more than a bank export emits and the
#: tolerant version of this function produced silently wrong ledgers: stripping
#: "Rs" before its dot turned 'Rs.100' into '.100' (a 1000x understatement with no
#: error), and 'NaN'/'Infinity' came through as non-finite values that later raise
#: InvalidOperation inside every export's quantize(). Non-ASCII digits ('١٢٣') and
#: Python's underscore literals ('1_000') are refused rather than reinterpreted: a
#: file containing them is not a statement we understand, and an unknown format
#: must raise (CONSTRAINTS #2), not be guessed at.
#: NOTE: named _MONEY_CELL_RE, not _MONEY_RE — a later module-level _MONEY_RE
#: already exists below for _is_money()'s flattened-bank-statement scan, and
#: reusing the name silently shadowed this one.
_MONEY_CELL_RE = re.compile(r"^[+-]?[0-9]+(?:\.[0-9]+)?$")

#: Currency prefix, with or without a dot, case-insensitive: 'Rs.', 'Rs', 'INR', '₹'.
_CURRENCY_PREFIX = re.compile(r"^(?:INR|Rs\.?|₹)\s*", re.IGNORECASE)

#: Digit bounds. Every export calls Decimal.quantize() to 2 places, which raises
#: once the value needs more digits than the decimal context's precision (28), so
#: an absurd amount would surface as a 500 rather than a refusal. ₹99,99,99,99,999
#: is already far beyond any single settlement line, and real money has at most
#: paise (2) — 6 is generous for a source that writes fractions oddly.
_MAX_INT_DIGITS = 13
_MAX_FRAC_DIGITS = 6


def _validate_money(amount: Decimal, source: object) -> Decimal:
    """Reject money that is not finite, or not a plausible rupee amount.

    The one place non-finite and out-of-range values are stopped, so every entry
    point (CSV cells, JSON amounts, paise) is covered by the same rule. Without
    it a hostile or merely odd input reaches the export layer and becomes a 500.
    Each refusal names the actual problem, because "out of range" on a lossy float
    sends the caller looking in the wrong place.
    """
    if not amount.is_finite():
        raise ValueError(f"non-finite amount: {source!r}")
    tup = amount.as_tuple()
    int_digits = len(tup.digits) + tup.exponent
    frac_digits = max(0, -tup.exponent)
    if int_digits > _MAX_INT_DIGITS:
        raise ValueError(f"amount out of range for a rupee amount: {source!r}")
    if frac_digits > _MAX_FRAC_DIGITS:
        # Reached by passing a float: Decimal(191.9) carries the binary expansion
        # (1.919000000000000056843418861), which is not a price anyone quoted. Pass
        # a string or a Decimal instead of guessing what the float meant.
        raise ValueError(
            f"amount has more than {_MAX_FRAC_DIGITS} decimal places ({source!r}); "
            "pass an exact value (str or Decimal), not a float"
        )
    return amount


def parse_amount(value: str) -> Decimal:
    """Parse a money cell into Decimal RUPEES, or raise. Never guesses."""
    s = (value or "").strip()
    parenthesised = s.startswith("(") and s.endswith(")")   # accounting negative
    if parenthesised:
        s = s[1:-1]
    s = _CURRENCY_PREFIX.sub("", s).replace(",", "").replace(" ", "")
    if not _MONEY_CELL_RE.match(s):
        raise ValueError(f"unparseable amount: {value!r}")
    try:
        amount = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError(f"unparseable amount: {value!r}") from exc
    return _validate_money(-amount if parenthesised else amount, value)


def _txns_from_rows(
    rows,
    utr_col: str,
    amount_col: str,
    date_col: str,
    ref_col: str | None = None,
) -> list[Txn]:
    """Build Txn rows from dict rows (a DictReader, or a slice of one).

    Separate from load_csv so a single file carrying SEVERAL sections with
    different headers (Cashfree's recon report) can reuse one field mapping
    per section instead of duplicating the loop.
    """
    txns: list[Txn] = []
    for row in rows:
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

    Refuses a JSON payload by name. Handed `{"items": [...]}`, a CSV reader takes
    the whole line as ONE header field and finds no data rows, so the caller gets
    an empty result rather than an error — and an empty reconciliation looks
    exactly like a clean one. That silent zero is the worst failure this library
    can produce, so the payload is detected instead of reported as success.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        if fh.read(64).lstrip()[:1] in ("{", "["):
            raise ValueError(
                f"{path} looks like JSON, not CSV. This loader reads comma-separated "
                "files; use a JSON parser (e.g. parse_razorpay_settlements) for a JSON "
                "payload, or export the data as CSV."
            )
        fh.seek(0)
        return _txns_from_rows(
            csv.DictReader(fh), utr_col, amount_col, date_col, ref_col
        )


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
    """Razorpay money: smallest currency unit (paise) -> Decimal RUPEES.

    Validated as well as at the CSV boundary, because a JSON amount can arrive as
    `1e400` (legal JSON, parses to float('inf')) or as a bare `Infinity` literal.
    A non-finite Decimal survives all the way into the export layer's quantize(),
    where it raises InvalidOperation mid-request — so bad input surfaces as a 500
    instead of the 400 the caller can act on.
    """
    try:
        rupees = Decimal(value) / Decimal("100")
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"unparseable amount: {value!r}") from exc
    return _validate_money(rupees, value)


# Razorpay timestamps are Unix epoch seconds in UTC. Indian bank statements are
# IST, so convert to IST (+05:30) to align the (amount, date) fallback date with
# the statement's calendar date — a UTC date was one day off for transactions
# within ~05:30 of midnight UTC (D-26).
_IST = timezone(timedelta(hours=5, minutes=30))


def _epoch_date(value) -> date:
    """Convert a Unix epoch (UTC) to an IST calendar date."""
    return datetime.fromtimestamp(int(value), tz=_IST).date()


#: The two fields a settlement row cannot be built without. The documented schema
#: has more (entity, fees, tax, utr) but all of those have sane defaults or are
#: optional; these two are what the row IS.
RAZORPAY_SETTLEMENT_REQUIRED = ("id", "amount", "created_at")


def parse_razorpay_settlements(data: dict) -> list[Settlement]:
    """Parse a Razorpay 'Fetch All Settlements' response into Settlement rows.

    Field names follow the documented API schema (id, entity, amount, fees,
    tax, utr, created_at). amount/fees/tax are integers in paise and are
    converted to Decimal rupees. Non-settlement entities are skipped.

    Validates its envelope and raises ValueError, exactly as the recon parser
    does — the two used to disagree. This parser read `data.get(...)` and
    `item.get(...)` unguarded, so a payload that was merely the wrong shape (a
    top-level list, or `items` as an object) raised AttributeError/KeyError, which
    the hosted layer correctly refused to treat as user error and turned into a
    500. A wrong-shaped file is the caller's, not a server fault (D-15).
    """
    if not isinstance(data, dict):
        raise ValueError(
            "razorpay settlements response must be a JSON object with an 'items' list "
            f"(got {type(data).__name__})"
        )
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError(
            "razorpay settlements response has no 'items' list "
            f"(got {type(items).__name__})"
        )
    out: list[Settlement] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(
                f"settlement entry must be an object (got {type(item).__name__})"
            )
        if item.get("entity") != "settlement":
            continue
        missing = [k for k in RAZORPAY_SETTLEMENT_REQUIRED if k not in item]
        if missing:
            raise ValueError(f"settlement entry missing required keys: {missing}")
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


# ---------------------------------------------------------------------------
# PayU — the two official settlement APIs. Verified 2026-09-11 from
# docs.payu.in/reference/settlement-detail-range-api.md and
# .../settlement_transaction_details_api.md (recorded in
# docs/RESEARCH-gateway-samples.md §4a/§4b).
#
# PayU's settlement CSV export can NEVER have a fixed public header: their own
# docs say the merchant picks the columns in a dashboard dialog. That is why the
# search for a sample file kept coming back empty, and it is not a search
# failure — the format is un-wireable BY DESIGN. These two APIs are the real
# integration surface.
#
# Money arrives as rupee STRINGS on /range ("1479.82") and as JSON NUMBERS on
# /transactionDetails (8.0, -8.0). Both go through Decimal; the file loader uses
# parse_float=Decimal so the literal is preserved exactly and no float ever
# touches an amount.
# ---------------------------------------------------------------------------

PAYU_RANGE_KEYS = frozenset({
    "settlementId", "settlementCompletedDate", "settlementAmount", "merchantId",
    "utrNumber", "transactionAmount", "adjustmentAmount", "refundAmount",
    "chargebackAmount", "refundReversalAmount", "chargebackReversalAmount",
    "serviceFee", "serviceTax", "additionalServiceFee", "additionalServiceTax",
    "numberOfTransactions", "transaction", "additionalTdrFee", "additionalTdrTax",
    "totalServiceTax", "totalProcessingFee", "transactionCurrency",
    "settlementCurrency",
})
PAYU_RANGE_REQUIRED = (
    "settlementId", "settlementCompletedDate", "settlementAmount", "utrNumber",
)

PAYU_TXN_DETAIL_KEYS = frozenset({
    "merchantId", "merchantTransactionId", "payuId", "transactionType",
    "settlementStatus", "settlementUTR", "settlementDate", "settlementId",
    "settlementAmount",
})
PAYU_TXN_DETAIL_REQUIRED = (
    "merchantTransactionId", "payuId", "transactionType", "settlementAmount",
)


def _rupees(value) -> Decimal:
    """Money from a JSON payload: a rupee string, or a JSON number.

    Never float arithmetic: a JSON number is routed through its decimal string
    form, and the file loaders ask json for Decimal directly. Validated like every
    other money entry point, so a non-finite or absurd value is refused here rather
    than crashing an export later.
    """
    if isinstance(value, str):
        amount = parse_amount(value)
    elif value is None or isinstance(value, bool):
        raise ValueError(f"unparseable amount: {value!r}")
    else:
        try:
            amount = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError(f"unparseable amount: {value!r}") from exc
    return _validate_money(amount, value)


def _rupees_or_zero(value) -> Decimal:
    """Optional money from a JSON payload; missing/blank -> Decimal(0)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return Decimal("0")
    return _rupees(value)


def _assert_payu_success(data: dict, *, endpoint: str) -> None:
    """Fail closed on PayU's own envelope (status 0 = success, 1 = failure)."""
    if not isinstance(data, dict):
        raise ValueError(f"{endpoint} response must be a JSON object")
    if data.get("status") != 0:
        raise ValueError(
            f"{endpoint} returned status={data.get('status')!r}: "
            f"{data.get('message') or data.get('result') or 'no message'}"
        )


def load_payu_json(path: str | Path) -> dict:
    """Load a saved PayU API response; money literals stay exact (Decimal)."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh, parse_float=Decimal)


def parse_payu_settlement_range(data: dict) -> list[Settlement]:
    """Parse a PayU GET /settlement/range response into Settlement rows.

    One row per UTR. `settlementAmount` is the net credited to the merchant's
    bank account for that UTR — exactly what a bank statement line has to
    reconcile against — and `utrNumber` is the bank reference, so these rows
    level-1 match in `match()` without falling back to amount+date.

    Field set = the 23 documented UTR-level parameters; an unknown field raises
    (D-7: a changed schema must not be read as if it were the old one). The
    nested `transaction` array is the same batch at transaction grain and is
    already available per-transaction from /transactionDetails, so it is not
    consumed here.

    Pagination is the caller's job: PayU returns `result.data` (one page) plus
    `totalCount`. This returns the page it was given.
    """
    _assert_payu_success(data, endpoint="payu /settlement/range")
    result = data.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("data"), list):
        raise ValueError("payu /settlement/range response has no result.data list")

    out: list[Settlement] = []
    for item in result["data"]:
        missing = [k for k in PAYU_RANGE_REQUIRED if k not in item]
        if missing:
            raise ValueError(f"payu settlement row missing required keys: {missing}")
        unknown = set(item) - PAYU_RANGE_KEYS
        if unknown:
            raise ValueError(
                f"unknown payu settlement fields {sorted(unknown)}: schema changed?"
            )
        fees = _rupees_or_zero(item.get("serviceFee")) + _rupees_or_zero(
            item.get("additionalServiceFee")
        )
        tax = _rupees_or_zero(item.get("serviceTax")) + _rupees_or_zero(
            item.get("additionalServiceTax")
        )
        out.append(
            Settlement(
                settlement_id=str(item["settlementId"]),
                amount=_rupees(item["settlementAmount"]),
                created_at=parse_date(item["settlementCompletedDate"]),
                utr=str(item["utrNumber"]),
                fees=fees,
                tax=tax,
            )
        )
    return out


def parse_payu_transaction_details(data: dict) -> list[ReconLine]:
    """Parse a PayU GET /settlement/transactionDetails response.

    One ReconLine per transaction state (capture / refund / chargeback /
    chargebackreversal / adjustment / cancel) of the requested merchant
    transaction id.

    `settlementAmount` is SIGNED in this response — a refund or a chargeback is
    negative — so the magnitude goes in `amount` and the direction in
    debit/credit. That keeps `ReconLine.net` equal to the signed amount PayU
    reported, which is the field the batch netting reads.

    `settlementStatus` is mapped to the two booleans the model carries:
    `Settled` -> settled, `On Hold` -> on_hold. `settlementUTR` is optional
    because an unsettled transaction may not have one yet.
    """
    _assert_payu_success(data, endpoint="payu /settlement/transactionDetails")
    result = data.get("result")
    if not isinstance(result, list):
        raise ValueError(
            "payu /settlement/transactionDetails response has no result list"
        )

    out: list[ReconLine] = []
    for item in result:
        missing = [k for k in PAYU_TXN_DETAIL_REQUIRED if k not in item]
        if missing:
            raise ValueError(f"payu transaction row missing required keys: {missing}")
        unknown = set(item) - PAYU_TXN_DETAIL_KEYS
        if unknown:
            raise ValueError(
                f"unknown payu transaction fields {sorted(unknown)}: schema changed?"
            )
        signed = _rupees(item["settlementAmount"])
        magnitude = abs(signed)
        status = str(item.get("settlementStatus") or "")
        utr = str(item["settlementUTR"]).strip() if item.get("settlementUTR") else None
        out.append(
            ReconLine(
                entity_id=str(item["payuId"]),
                type=str(item["transactionType"]),
                debit=magnitude if signed < 0 else Decimal("0"),
                credit=magnitude if signed > 0 else Decimal("0"),
                amount=magnitude,
                currency="INR",     # this endpoint carries no currency field
                fee=Decimal("0"),
                tax=Decimal("0"),
                on_hold=status == "On Hold",
                settled=status == "Settled",
                created_at=parse_date(item["settlementDate"]),
                settled_at=None,
                settlement_id=str(item.get("settlementId") or ""),
                settlement_utr=utr,
                order_id=str(item["merchantTransactionId"]),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Cashfree — Settlement Recon report. ONE file, TWO reports: a 14-column
# settlement-batch section, then the marker line, then a 63-column per-event
# section. Verified 2026-09-11 against a real (header-only) export; both header
# rows and the source URL are in docs/RESEARCH-gateway-samples.md §1a. The
# column maps live in schemas.py with every other vendor map — this is only the
# split, so there is exactly one place that knows a column name.
# ---------------------------------------------------------------------------

CASHFREE_RECON_MARKER = "** Settlement Reconciliation Details **"


def split_cashfree_recon_report(raw: str) -> tuple[str, str]:
    """Split a Cashfree recon export into (batch section, event section).

    The two sections have DIFFERENT column maps, so a file without the marker
    raises rather than being read as whichever section it resembles — reading
    63-column event rows through the 14-column batch map would produce
    confident nonsense, and reading batches as events would understate every
    line (D-7: never guess a schema).
    """
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == CASHFREE_RECON_MARKER:
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:])
    raise ValueError(
        "not a Cashfree Settlement Recon report: marker line "
        f"{CASHFREE_RECON_MARKER!r} not found"
    )


def _recon_lines_from_rows(
    rows,
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
    direction_col: str | None = None,
    direction_amount_col: str | None = None,
) -> list[ReconLine]:
    """Build ReconLine rows from dict rows (a DictReader, or a slice of one).

    `direction_col` covers vendors that print a CREDIT/DEBIT flag instead of
    separate debit/credit columns — Cashfree's recon report has `Sale Type`
    (CREDIT/DEBIT). With it set, `debit_col`/`credit_col` are unused and
    `direction_amount_col` names the column carrying the money MOVEMENT (net of
    fee — Cashfree's `Event Settlement Amount`), while `amount_col` stays the
    gross amount a ReconLine.amount is documented to hold. The movement is read
    as a magnitude and the flag decides the side, so a vendor printing an
    already-negative refund and a vendor printing it positive both land the same
    way. An unrecognised flag raises rather than guessing a sign, because a
    guessed sign silently reverses a reconciliation.
    """
    out: list[ReconLine] = []
    for row in rows:
        fee = _money_or_zero(row.get(fee_col)) if fee_col else Decimal("0")
        tax = _money_or_zero(row.get(tax_col)) if tax_col else Decimal("0")
        if direction_col:
            flag = (row.get(direction_col) or "").strip().upper()
            movement = abs(
                _money_or_zero(row.get(direction_amount_col or amount_col))
            )
            if flag == "CREDIT":
                debit, credit = Decimal("0"), movement
            elif flag == "DEBIT":
                debit, credit = movement, Decimal("0")
            else:
                raise ValueError(
                    f"unrecognised {direction_col} {row.get(direction_col)!r} on "
                    f"{row.get(entity_id_col)!r}: expected CREDIT or DEBIT"
                )
        else:
            debit = _money_or_zero(row.get(debit_col))
            credit = _money_or_zero(row.get(credit_col))
        out.append(
            ReconLine(
                entity_id=(row.get(entity_id_col) or "").strip(),
                type=(row.get(type_col) or "").strip().lower(),
                debit=debit,
                credit=credit,
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
    direction_col: str | None = None,
    direction_amount_col: str | None = None,
) -> list[ReconLine]:
    """Load a dashboard-exported recon CSV into ReconLine rows.

    Column names are EXPLICIT arguments (D-7): every vendor's CSV header
    differs, so the mapping is supplied from a real sample file, never
    guessed. Money columns must already be in rupees.
    """
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return _recon_lines_from_rows(
            csv.DictReader(fh),
            entity_id_col=entity_id_col, type_col=type_col,
            debit_col=debit_col, credit_col=credit_col,
            amount_col=amount_col, date_col=date_col,
            settlement_id_col=settlement_id_col, currency_col=currency_col,
            fee_col=fee_col, tax_col=tax_col, utr_col=utr_col,
            order_id_col=order_id_col, payment_id_col=payment_id_col,
            direction_col=direction_col, direction_amount_col=direction_amount_col,
        )
