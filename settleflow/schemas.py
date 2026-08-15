"""Vendor/bank column-map registry (Phase 3).

D-7 rule: a vendor or bank format is COLUMN-MAP DATA, never vendor-specific
code, and never guessed. Each mapping is a ColumnMap filled from a REAL sample
file or verified docs. Shipping a mapping without that evidence is the exact
Nova-zoning failure mode — so this registry ships only what is verified and
holds empty slots for every format awaiting a real sample.

Verified (2026-08-16):
- RAZORPAY_SETTLEMENTS_API  -> parse_razorpay_settlements (docs + real sample)
- RAZORPAY_RECON_API        -> parse_razorpay_recon (docs, 24 documented params)

Awaiting a real sample file (slots exist, data does not — do NOT fill these
from memory or from JS-rendered docs):
- Razorpay settlement CSV, Cashfree (PG + vendor + recon CSV),
  PayU, PhonePe, Juspay settlement formats
- Bank statements: HDFC, SBI, ICICI, Axis, Kotak, IDFC, Yes
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import ReconLine, Settlement, Txn
from .parsers import load_csv, load_recon_csv


@dataclass(frozen=True)
class ColumnMap:
    """Column names for load_csv, as they appear in a real file's header."""

    utr_col: str
    amount_col: str
    date_col: str
    ref_col: str | None = None


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


# Registry: key -> verified mapping or None (= slot, awaiting real sample).
SETTLEMENT_CSV_MAPS: dict[str, ColumnMap | None] = {
    "razorpay_settlement_csv": None,   # dashboard export header unverified
    "cashfree_settlement_csv": None,
    "payu_settlement_csv": None,
    "phonepe_settlement_csv": None,
    "juspay_settlement_csv": None,
}

BANK_STATEMENT_MAPS: dict[str, ColumnMap | None] = {
    "hdfc": None,
    "sbi": None,
    "icici": None,
    "axis": None,
    "kotak": None,
    "idfc": None,
}

RECON_CSV_MAPS: dict[str, ReconColumnMap | None] = {
    "razorpay_recon_csv": None,   # API JSON is verified; CSV export is not
    "cashfree_recon_csv": None,
}


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
            "(D-7: never guess a schema)"
        )
    return load_csv(path, cm.utr_col, cm.amount_col, cm.date_col, cm.ref_col)


def load_bank_statement(path, bank: str) -> list[Txn]:
    """Load a bank statement CSV using its registered column map."""
    if bank not in BANK_STATEMENT_MAPS:
        raise KeyError(f"unknown bank {bank!r}; register it in BANK_STATEMENT_MAPS")
    cm = BANK_STATEMENT_MAPS[bank]
    if cm is None:
        raise ValueError(
            f"{bank}: column map not filled — supply a real statement's header "
            "(D-7: never guess a schema)"
        )
    return load_csv(path, cm.utr_col, cm.amount_col, cm.date_col, cm.ref_col)


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
