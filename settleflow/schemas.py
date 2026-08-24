"""Vendor/bank column-map registry (Phase 3).

D-7 rule: a vendor or bank format is COLUMN-MAP DATA, never vendor-specific
code, and never guessed. Every map below is filled from a VERIFIED source — an
official sample file, an official docs page, or a parser that reads that exact
vendor's real export — captured in `docs/SCHEMAS.md` with the verbatim header
row and source URL. Any map still `None` is awaiting a real sample and raises a
clear error rather than guessing.

Verified & wired (2026-08-16):
- Razorpay settlement CSV  (official sample file on razorpay.com/docs)
- Razorpay recon CSV       (official sample file on razorpay.com/docs)
- HDFC / SBI / ICICI / Axis / Kotak bank-statement CSVs (real fixtures + parsers)

Verified schema but NOT wired (needs a dedicated parser or a real file to
resolve a money-unit / type-semantics ambiguity): Cashfree recon (two-section
file), PhonePe settlement report (tax columns, undocumented type values),
Juspay settlement file (money unit unstated). See docs/SCHEMAS.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import ReconLine, Txn
from .parsers import (
    load_bank_statement_csv,
    load_csv,
    load_recon_csv,
    parse_bank_text,
    parse_drcr_statement,
    parse_razorpay_recon,
    parse_razorpay_settlements,
)
from .pdf import parse_sbi_statement


@dataclass(frozen=True)
class ColumnMap:
    """Column names for load_csv, as they appear in a real file's header."""

    utr_col: str
    amount_col: str
    date_col: str
    ref_col: str | None = None


@dataclass(frozen=True)
class BankColumnMap:
    """Column names for load_bank_statement_csv (two-column debit/credit)."""

    date_col: str
    debit_col: str
    credit_col: str
    ref_col: str | None = None       # bank's own ref number -> Txn.utr
    narration_col: str | None = None  # description -> Txn.ref


@dataclass(frozen=True)
class ReconColumnMap:
    """Column names for load_recon_csv, from a real recon CSV header."""

    entity_id_col: str
    type_col: str
    debit_col: str
    credit_col: str
    amount_col: str
    date_col: str
    settlement_id_col: str
    currency_col: str | None = None
    fee_col: str | None = None
    tax_col: str | None = None
    utr_col: str | None = None
    order_id_col: str | None = None
    payment_id_col: str | None = None


# ---------------------------------------------------------------------------
# Settlement batch CSVs (one row = one settlement batch -> match vs bank credit)
# ---------------------------------------------------------------------------
SETTLEMENT_CSV_MAPS: dict[str, ColumnMap | None] = {
    # Official sample file: sample-settlements-report.xlsx (razorpay.com/docs).
    # NOTE: the sample shows decimal RUPEES (1.91); the API is paise. The CSV
    # parser follows the sample (rupees), the API parser follows the API docs.
    "razorpay_settlement_csv": ColumnMap(
        utr_col="utr", amount_col="amount", date_col="created_at", ref_col="id",
    ),
    "cashfree_settlement_csv": None,   # plain settlement report header not public
    "payu_settlement_csv": None,       # columns are user-selectable; no fixed header
    "phonepe_settlement_csv": None,    # verified fields but needs dedicated parser
    "juspay_settlement_csv": None,     # verified schema but money unit unstated
}


# ---------------------------------------------------------------------------
# Recon (line-item) CSVs (one row = one payment/refund/transfer/adjustment)
# ---------------------------------------------------------------------------
RECON_CSV_MAPS: dict[str, ReconColumnMap | None] = {
    # Official sample file: sample-settlements-recon-report.xlsx (27 cols).
    "razorpay_recon_csv": ReconColumnMap(
        entity_id_col="entity_id",
        type_col="transaction_entity",     # payment | refund | transfer | adjustment
        debit_col="debit",
        credit_col="credit",
        amount_col="amount",
        date_col="entity_created_at",
        settlement_id_col="settlement_id",
        currency_col="currency",
        fee_col="fee (exclusive tax)",
        tax_col="tax",
        utr_col="settlement_utr",
        order_id_col="order_id",
        payment_id_col=None,               # entity_id IS the payment id for payments
    ),
    "cashfree_recon_csv": None,   # two-section file (14 + 48 cols) -> dedicated parser
    "phonepe_recon_csv": None,    # tax columns + undocumented type values -> real file needed
    "juspay_recon_csv": None,     # money unit unstated -> real file needed
}


# ---------------------------------------------------------------------------
# Bank-statement CSVs (two-column debit/credit, verified against real fixtures)
# ---------------------------------------------------------------------------
BANK_STATEMENT_MAPS: dict[str, BankColumnMap | None] = {
    "hdfc": BankColumnMap(
        date_col="Date", debit_col="Withdrawal Amt.", credit_col="Deposit Amt.",
        ref_col="Chq./Ref.No.", narration_col="Narration",
    ),
    "sbi": BankColumnMap(
        date_col="Txn Date", debit_col="Debit", credit_col="Credit",
        ref_col="Ref No./Cheque No.", narration_col="Description",
    ),
    "icici": BankColumnMap(
        date_col="Transaction Date", debit_col="Withdrawal Amount(INR)",
        credit_col="Deposit Amount(INR)", ref_col="Cheque Number",
        narration_col="Transaction Remarks",
    ),
    "axis": BankColumnMap(
        date_col="Tran Date", debit_col="DR", credit_col="CR",
        ref_col="CHQNO", narration_col="PARTICULARS",
    ),
    # Kotak has two documented layouts; this is the netbanking CSV (variant A).
    # Variant B (bankii: "Transaction date"/"Debit amount"/"Credit amount"/"Dr/Cr")
    # is documented in docs/SCHEMAS.md; auto-detect when a real sample arrives.
    "kotak": BankColumnMap(
        date_col="Transaction Date", debit_col="Withdrawal Amt.",
        credit_col="Deposit Amt.", ref_col="Chq./Ref.No.", narration_col="Description",
    ),
    # Kotak "bankii" variant B — separate Debit amount / Credit amount columns
    # plus a Dr/Cr flag. Transcribed from the real parser jasimmk/bankii
    # in_kotak.py (Serial|Transaction date|Value date|Description|Chq / Ref No.|
    # Debit amount|Credit amount|Balance|Dr/Cr; %d-%m-%Y), verified 2026-08-24
    # (ATL-90). The Dr/Cr flag is redundant here: only one amount column is
    # populated per row, load_bank_statement_csv already signs credit=+, debit=-.
    # Auto-detected in load_bank_statement by the "Debit amount"/"Credit amount"
    # headers. Parse-from-real-file test is pending a real bankii fixture (D-7).
    "kotak_bankii": BankColumnMap(
        date_col="Transaction date", debit_col="Debit amount",
        credit_col="Credit amount", ref_col="Chq / Ref No.", narration_col="Description",
    ),
    "idfc": None,
}


# Flattened-text banks whose debit/credit columns collapse in extracted text;
# the sign is recovered from the running balance (see parse_bank_text). PNB
# prints narration AFTER the balance, DBS BEFORE the amount.
TEXT_BANK_PARSERS = {
    "pnb": lambda raw: parse_bank_text(raw, narration_after=True),
    "dbs": lambda raw: parse_bank_text(raw, narration_after=False),
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_settlement_csv(path, vendor: str) -> list[Txn]:
    """Load a vendor settlement CSV using its registered column map.

    Raises KeyError for an unknown vendor and ValueError for a registered
    vendor whose map is still awaiting a real sample — never guesses.
    """
    if vendor not in SETTLEMENT_CSV_MAPS:
        raise KeyError(f"unknown vendor {vendor!r}; register it in SETTLEMENT_CSV_MAPS")
    cm = SETTLEMENT_CSV_MAPS[vendor]
    if cm is None:
        raise ValueError(
            f"{vendor}: column map not filled — supply a real sample file's header "
            "(D-7: never guess a schema; see docs/SCHEMAS.md)"
        )
    return load_csv(path, cm.utr_col, cm.amount_col, cm.date_col, cm.ref_col)


def load_bank_statement(path, bank: str) -> list[Txn]:
    """Load a bank statement using its registered parser.

    Two auto-detected text formats are routed by content, not column map:
    - a Dr/Cr combined-amount statement (Kotak netbanking), and
    - a flattened-text collapsed-column statement (PNB/DBS, where the running
      balance recovers the debit/credit sign).
    Everything else goes through the two-column map below.
    """
    raw = Path(path).read_text(encoding="utf-8-sig")
    if "(Dr)" in raw and "(Cr)" in raw:
        return parse_drcr_statement(raw)
    upper = raw.upper()
    # SBI statement TEXT (YONO / credit card) — content-routed, not a column map
    if ("TRANSACTION REFERENCE" in upper or "CREDIT CARD STATEMENT" in upper
            or "AMOUNT (RS.)" in upper):
        return parse_sbi_statement(raw)
    if bank in TEXT_BANK_PARSERS:
        return TEXT_BANK_PARSERS[bank](raw)
    # Kotak "bankii" variant B (ATL-90): separate "Debit amount"/"Credit amount"
    # columns + Dr/Cr flag. Detected by header content (bankii-specific column
    # names), not the bank key, so "kotak" auto-routes here and "kotak_bankii"
    # works too. Schema transcribed from the real parser jasimmk/bankii.
    if "Debit amount" in raw and "Credit amount" in raw:
        cm = BANK_STATEMENT_MAPS["kotak_bankii"]
        return load_bank_statement_csv(
            path,
            date_col=cm.date_col, debit_col=cm.debit_col, credit_col=cm.credit_col,
            ref_col=cm.ref_col, narration_col=cm.narration_col,
        )
    if bank not in BANK_STATEMENT_MAPS:
        raise KeyError(f"unknown bank {bank!r}; register it in BANK_STATEMENT_MAPS")
    cm = BANK_STATEMENT_MAPS[bank]
    if cm is None:
        raise ValueError(
            f"{bank}: column map not filled — supply a real statement's header "
            "(D-7: never guess a schema; see docs/SCHEMAS.md)"
        )
    return load_bank_statement_csv(
        path,
        date_col=cm.date_col, debit_col=cm.debit_col, credit_col=cm.credit_col,
        ref_col=cm.ref_col, narration_col=cm.narration_col,
    )


def load_vendor_recon_csv(path, vendor: str) -> list[ReconLine]:
    """Load a vendor recon CSV using its registered recon column map."""
    if vendor not in RECON_CSV_MAPS:
        raise KeyError(f"unknown vendor {vendor!r}; register it in RECON_CSV_MAPS")
    cm = RECON_CSV_MAPS[vendor]
    if cm is None:
        raise ValueError(
            f"{vendor}: recon column map not filled — supply a real sample (D-7)"
        )
    return load_recon_csv(
        path,
        entity_id_col=cm.entity_id_col, type_col=cm.type_col,
        debit_col=cm.debit_col, credit_col=cm.credit_col,
        amount_col=cm.amount_col, date_col=cm.date_col,
        settlement_id_col=cm.settlement_id_col, currency_col=cm.currency_col,
        fee_col=cm.fee_col, tax_col=cm.tax_col, utr_col=cm.utr_col,
        order_id_col=cm.order_id_col, payment_id_col=cm.payment_id_col,
    )


# The Razorpay API-JSON parsers are the only verified API surfaces; expose them
# through the registry too so callers have one entry point.
API_PARSERS = {
    "razorpay_settlements_api": parse_razorpay_settlements,
    "razorpay_recon_api": parse_razorpay_recon,
}
