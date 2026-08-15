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
