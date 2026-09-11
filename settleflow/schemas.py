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

Verified & wired (2026-09-11, research in docs/RESEARCH-gateway-samples.md):
- Cashfree Settlement Recon report — BOTH sections of the one file, via
  load_cashfree_recon_report(): 14-col batches (which land in the bank) and
  63-col per-event lines.
- PayU — the two official settlement APIs are parsed in parsers.py
  (parse_payu_settlement_range / parse_payu_transaction_details) and exposed
  through API_PARSERS. PayU's CSV export is closed as BY-DESIGN un-wireable:
  the merchant picks its columns in a dashboard dialog.
- Juspay settlement file — load_juspay_settlement_csv() handles both the
  documented 25-column schema and the variant Juspay's own parser reads. Money
  unit RUPEES is vendor-code corroboration, NOT documented — see the loader.

Verified header but deliberately NOT wired — each for a stated reason, not a lack of
effort: Cashfree's PLAIN settlements report (a different file from the two-section
Settlement Recon report above, which IS wired) and IDFC statements (no real public
sample exists; four community parsers corroborate the PDF layout but every one of
them tests against hand-written mock text). See docs/SCHEMAS.md.
"""
from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from .models import ReconLine, Txn
from .parsers import (
    _money_or_zero,
    _recon_lines_from_rows,
    _txns_from_rows,
    load_bank_statement_csv,
    load_csv,
    load_recon_csv,
    parse_amount,
    parse_bank_text,
    parse_date,
    parse_drcr_statement,
    parse_payu_settlement_range,
    parse_payu_transaction_details,
    parse_razorpay_recon,
    parse_razorpay_settlements,
    split_cashfree_recon_report,
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
    """Column names for load_recon_csv, from a real recon CSV header.

    Set `direction_col` for a vendor that prints a CREDIT/DEBIT flag instead of a
    debit/credit pair; then `debit_col` and `credit_col` are unused and are
    passed as "" (they cannot be dropped: they are positional in this dataclass
    and every map shares the shape), and `direction_amount_col` names the column
    carrying the money MOVEMENT while `amount_col` stays the gross amount.
    """

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
    direction_col: str | None = None
    direction_amount_col: str | None = None


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
    # Section 1 of Cashfree's two-section Settlement Recon report — the
    # settlement BATCHES, i.e. what lands in the bank. Verbatim 14-column header
    # in docs/RESEARCH-gateway-samples.md §1a. `Net Settlement Amount` is what
    # Cashfree documents as total - charge - tax + adjustment, which is the
    # credit a bank line reconciles against.
    # Do NOT read the raw file through this map: section 2's 63-column event
    # rows would be read as more batches. Use load_cashfree_recon_report().
    "cashfree_settlement_csv": ColumnMap(
        utr_col="UTR No.", amount_col="Net Settlement Amount",
        date_col="Settlement Date", ref_col="Id",
    ),
    # PayU's settlement CSV export is user-configurable column-by-column in the
    # dashboard (docs.payu.in/docs/export-the-settlement-records), so no fixed
    # public header can ever exist. Closed as BY-DESIGN, not as un-found: use
    # parse_payu_settlement_range / parse_payu_transaction_details instead.
    "payu_settlement_csv": None,
    # PhonePe's settlement report is one row per TRANSACTION, so the rows must be
    # aggregated per bank credit before level-1 matching — see
    # load_phonepe_settlement_csv() below, which this map feeds. Column names below
    # are verbatim from two real publicly committed merchant exports (15-col and
    # 23-col variants; this is the 15-col set), captured 2026-09-11 in
    # docs/RESEARCH-gateway-samples.md. Parse by header name, never position: the
    # 23-col variant inserts columns mid-file.
    "phonepe_settlement_csv": ColumnMap(
        utr_col="BankReferenceNo",      # PhonePe's own column glossary: the settlement UTR
        amount_col="Amount",            # row-level amount; NOT the settled total (see below)
        date_col="SettlementDate",      # dd-MM-yyyy
        ref_col="MerchantReferenceId",
    ),
    # The documented 25-column schema is real (juspay.io/pe/docs/.../settlement-files)
    # and Juspay's own production parser reads the same file, but it cannot be
    # expressed as a ColumnMap: it has separate Credit and Debit columns instead
    # of one amount, and the documented variant carries NO bank-UTR column. It
    # gets a dedicated loader (load_juspay_settlement_csv) instead.
    # Two things are still UNVERIFIED on a real populated file: the money unit
    # (docs say only "Integer"; vendor code reads plain rupee decimals, so
    # RUPEES) and whether one Settlement Date really is one bank credit.
    "juspay_settlement_csv": None,
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
    # Section 2 (63 columns, not 48 — SCHEMAS.md undercounted) of the same
    # two-section Cashfree file as cashfree_settlement_csv above; read it through
    # load_cashfree_recon_report(), which splits the file first. There is no
    # debit/credit column pair and no separate batch-id column: the direction is
    # `Sale Type` (CREDIT/DEBIT), the money movement is `Event Settlement Amount`
    # (already net of the fee/tax columns beside it — and it is printed NEGATIVE
    # on a refund, which is why the loader takes the magnitude and lets the flag
    # set the side), and the batch is identified by its `UTR`, so both
    # settlement_id_col and utr_col point at `UTR`.
    "cashfree_recon_csv": ReconColumnMap(
        entity_id_col="Event Id",
        type_col="Event Type",
        debit_col="", credit_col="",
        direction_col="Sale Type", direction_amount_col="Event Settlement Amount",
        amount_col="Event Amount",
        date_col="Event Time",
        settlement_id_col="UTR",
        currency_col="Event Currency",
        fee_col="Transaction Service Charge",
        tax_col="Txn ST/GST",
        utr_col="UTR",
        order_id_col="Merchant Reference Id",
    ),
    "phonepe_recon_csv": None,    # tax columns + undocumented type values -> real file needed
    "juspay_recon_csv": None,     # no bank-UTR column in the schema -> see load_juspay_settlement_csv
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

def load_phonepe_settlement_csv(path) -> list[Txn]:
    """Load PhonePe's settlement report as one Txn per BANK CREDIT (not per row).

    PhonePe's file is one row per TRANSACTION. Rows that share a `BankReferenceNo`
    (which is the settlement UTR) were settled to the bank as a single credit, and
    what reaches the bank is the row amount net of fee and taxes. PhonePe's own docs
    state the relation:

        settled = Amount + Fee + IGST + CGST + SGST

    and the fee/tax cells are negative in real exports — verified against two
    publicly committed merchant files on 2026-09-11 (docs/RESEARCH-gateway-samples.md).

    This aggregates before handing anything to the matcher. Feeding the per-row
    amounts to `match()` instead would try to match each transaction against one
    bank credit: a wall of false "unmatched", and the (amount, date) fallback could
    pair the wrong rows outright.

    NOT VERIFIED: the aggregate has never been compared against a real bank credit
    for the same settlement. The formula is documented and the per-row fields are
    observed in real files, but the join between them is untested. Fix this the
    first time a real PhonePe settlement total is available — that is the one thing
    missing, and until then this map is the best-supported reading of the evidence.
    """
    raw = Path(path).read_text(encoding="utf-8-sig")

    nets: dict[str, Decimal] = {}
    dates: dict[str, object] = {}
    refs: dict[str, str | None] = {}
    order: list[str] = []

    for row in csv.DictReader(io.StringIO(raw)):
        utr = (row.get("BankReferenceNo") or "").strip()
        if not utr:
            continue        # not yet settled to a bank credit

        try:
            settled = parse_amount((row.get("Amount") or "").strip() or "0")
        except ValueError as exc:
            raise ValueError(
                f"PhonePe Amount could not be read for settlement {utr!r}: {row.get('Amount')!r}"
            ) from exc
        for col in ("Fee", "IGST", "CGST", "SGST"):
            cell = (row.get(col) or "").strip()
            if cell:
                settled += parse_amount(cell)

        if utr not in nets:
            date_cell = (row.get("SettlementDate") or "").strip()
            try:
                dates[utr] = parse_date(date_cell)
            except ValueError as exc:
                raise ValueError(
                    f"PhonePe SettlementDate could not be read ({date_cell!r}) for "
                    f"settlement {utr!r}; expected dd-MM-yyyy"
                ) from exc
            nets[utr] = Decimal(0)
            refs[utr] = (row.get("MerchantReferenceId") or "").strip() or None
            order.append(utr)
        nets[utr] += settled

    return [
        Txn(utr=utr, amount=nets[utr], txn_date=dates[utr], ref=refs[utr])  # type: ignore[arg-type]
        for utr in order
    ]


# Juspay's documented Settlement Status values. Only "Settled" means the funds
# have actually reached the merchant's bank account, so only those rows may be
# netted into a bank credit. An unrecognised value raises: a row dropped by a
# guessed filter is a reconciliation error nobody sees.
_JUSPAY_SETTLED = "Settled"
_JUSPAY_SETTLEMENT_STATUSES = frozenset(
    {"Sent for settlement", "Settled", "Pending", "Failed"}
)


def load_juspay_settlement_csv(path) -> list[Txn]:
    """Load a Juspay settlement file as one Txn per BANK CREDIT.

    Handles the two real shapes of this file, keyed off its header:

    * the DOCUMENTED 25-column schema (juspay.io/pe/docs/upi-merchant-stack-pe/
      docs/resources/settlement-files): per-transaction rows with separate
      `Credit` and `Debit` columns and NO bank-UTR column; and
    * the variant Juspay's OWN production parser reads (nammayatri/shared-kernel,
      YesBiz), which carries `UTR Number` plus `Partner Amount`.

    Rows are netted per bank credit: grouped by `UTR Number` where the file has
    one, otherwise by `Settlement Date` — the only settlement-level key the
    documented schema carries. The credit is sum(Credit) - sum(Debit).

    Handing the per-transaction rows straight to `match()` would repeat what
    PhonePe's loader exists to prevent: every row matched against one bank
    credit, a wall of false "unmatched".

    NOT VERIFIED — this loader runs entirely on documentation and vendor code,
    never on a real populated file, and three things ride on that:
      * the money unit: the docs say only "Integer", while Juspay's own parser
        reads plain rupee decimals (no /100). RUPEES is assumed.
      * one `Settlement Date` being one bank credit. The documented variant has
        no batch id and no UTR, so nothing better is available to key on.
      * the `Settlement Status` filter: correct per the docs, never seen in a
        real file.
    Treat a Juspay run as needing review until a real file and its matching bank
    credit agree.
    """
    raw = Path(path).read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    header = reader.fieldnames or []
    if "Settlement Date" not in header:
        raise ValueError(
            "not a Juspay settlement file: no 'Settlement Date' column in header "
            f"{header[:8]}"
        )

    has_utr = "UTR Number" in header
    sum_direction = "Credit" in header and "Debit" in header
    sum_partner = "Partner Amount" in header
    if not sum_direction and not sum_partner:
        raise ValueError(
            "Juspay settlement file has neither Credit/Debit nor Partner Amount "
            "columns — unknown variant; refusing to guess the amount column"
        )

    rows = list(reader)
    if "Settlement Status" in header:
        seen = {(r.get("Settlement Status") or "").strip() for r in rows}
        unexpected = {s for s in seen if s and s not in _JUSPAY_SETTLEMENT_STATUSES}
        if unexpected:
            raise ValueError(
                f"unrecognised Juspay Settlement Status {sorted(unexpected)}; "
                f"expected one of {sorted(_JUSPAY_SETTLEMENT_STATUSES)}"
            )

    nets: dict[str, Decimal] = {}
    dates: dict[str, object] = {}
    refs: dict[str, str | None] = {}
    utrs: dict[str, str | None] = {}
    order: list[str] = []

    for row in rows:
        status = (
            (row.get("Settlement Status") or "").strip()
            if "Settlement Status" in header else _JUSPAY_SETTLED
        )
        if status != _JUSPAY_SETTLED:
            continue        # dispatched / pending / failed: no funds at the bank yet
        key = (
            (row.get("UTR Number") or "").strip() if has_utr
            else (row.get("Settlement Date") or "").strip()
        )
        if not key:
            continue        # nothing to key a bank credit on
        if sum_direction:
            amount = _money_or_zero(row.get("Credit")) - _money_or_zero(row.get("Debit"))
        else:
            amount = _money_or_zero(row.get("Partner Amount"))

        if key not in nets:
            date_cell = (row.get("Settlement Date") or "").strip()
            try:
                dates[key] = parse_date(date_cell)
            except ValueError as exc:
                raise ValueError(
                    f"Juspay Settlement Date could not be read ({date_cell!r}) for "
                    f"{key!r}; expected dd/mm/yyyy"
                ) from exc
            nets[key] = Decimal("0")
            utrs[key] = key if has_utr else None
            refs[key] = (
                (row.get("Order ID") or row.get("UPI Request Id") or "").strip() or None
            )
            order.append(key)
        nets[key] += amount

    return [
        Txn(utr=utrs[k], amount=nets[k], txn_date=dates[k], ref=refs[k])  # type: ignore[arg-type]
        for k in order
    ]


def load_cashfree_recon_report(path) -> tuple[list[Txn], list[ReconLine]]:
    """Load Cashfree's Settlement Recon report — BOTH sections of the one file.

    Returns `(batches, lines)`: one Txn per settlement batch (what the bank
    credited, with `UTR No.` as the UTR) and one ReconLine per event inside those
    batches. The file really is two reports concatenated, so the split comes
    first and each section is then read through its own registered column map —
    there is no other way to read it, because the sections' headers disagree.

    Money in both sections is already in rupees.
    """
    raw = Path(path).read_text(encoding="utf-8-sig")
    batch_text, event_text = split_cashfree_recon_report(raw)

    bmap = SETTLEMENT_CSV_MAPS["cashfree_settlement_csv"]
    emap = RECON_CSV_MAPS["cashfree_recon_csv"]
    assert bmap is not None and emap is not None, "cashfree maps must stay filled"

    batches = _txns_from_rows(
        csv.DictReader(io.StringIO(batch_text)),
        bmap.utr_col, bmap.amount_col, bmap.date_col, bmap.ref_col,
    )
    lines = _recon_lines_from_rows(
        csv.DictReader(io.StringIO(event_text)),
        entity_id_col=emap.entity_id_col, type_col=emap.type_col,
        debit_col=emap.debit_col, credit_col=emap.credit_col,
        amount_col=emap.amount_col, date_col=emap.date_col,
        settlement_id_col=emap.settlement_id_col, currency_col=emap.currency_col,
        fee_col=emap.fee_col, tax_col=emap.tax_col, utr_col=emap.utr_col,
        order_id_col=emap.order_id_col, payment_id_col=emap.payment_id_col,
        direction_col=emap.direction_col,
        direction_amount_col=emap.direction_amount_col,
    )
    return batches, lines


# Files that are NOT one (utr, amount, date) row per bank credit, so no column
# map can describe them and the loader IS the wiring. Everything else is
# map-driven through load_csv. load_cashfree_recon_report is not here: it returns
# two row types, so it is called by name, not through a vendor key.
VENDOR_LOADERS = {
    "phonepe_settlement_csv": load_phonepe_settlement_csv,
    "juspay_settlement_csv": load_juspay_settlement_csv,
}


def load_settlement_csv(path, vendor: str) -> list[Txn]:
    """Load a vendor settlement CSV using its registered column map.

    Raises KeyError for an unknown vendor and ValueError for a registered
    vendor whose map is still awaiting a real sample — never guesses.
    """
    if vendor not in SETTLEMENT_CSV_MAPS:
        raise KeyError(f"unknown vendor {vendor!r}; register it in SETTLEMENT_CSV_MAPS")
    dedicated = VENDOR_LOADERS.get(vendor)
    if dedicated is not None:
        return dedicated(path)
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
        direction_col=cm.direction_col,
        direction_amount_col=cm.direction_amount_col,
    )


# Every verified API-JSON parser, so callers have one entry point for the
# vendors whose data is not a CSV. PayU's two endpoints are here because its
# settlement CSV export cannot have a fixed header at all (see parsers.py).
# Cashfree's recon is not an API parser: it is a two-section FILE, reached by
# name through load_cashfree_recon_report above.
API_PARSERS = {
    "razorpay_settlements_api": parse_razorpay_settlements,
    "razorpay_recon_api": parse_razorpay_recon,
    "payu_settlement_range_api": parse_payu_settlement_range,
    "payu_transaction_details_api": parse_payu_transaction_details,
}
