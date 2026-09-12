"""Export matched/unmatched results into accountant-friendly formats.

Tally, Zoho Books, and GST workpapers all ingest CSV, so the export surface is
CSV (stdlib csv + Decimal, no third-party deps). These exports are the paid
layer of the open-core model: the OSS core matches; the SaaS wraps these
exports in a hosted UI.

Formats:
- export_tally_csv      -> one row per matched/unmatched settlement credit,
                           shaped for import into Tally as a bank receipt.
- export_gst_worksheet  -> gross/fee/tax netting per settlement batch for
                           GSTR-1 outward-supply and input-tax worksheets.
- export_tds_1035       -> e-commerce TDS (Income-tax Act 2025 s.393(1)
                           Sl.8(v), payment code 1035, ex-194O) deduction
                           worksheet for marketplace sellers.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO

from .matching import group_batches
from .models import BatchRecon, ReconLine, ReconResult


def _write(rows: list[list], header: list[str]) -> str:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


def format_money(value: Decimal) -> str:
    """Format a rupee amount as a consistent 2-decimal string.

    One function for both the exports and the results page, because they disagreed:
    the same amount printed as '100' in the page's summary table and '100.00' in the
    CSV that page links to. Quantize to paise so every money cell is 'x.xx'.
    """
    return str(Decimal(value).quantize(Decimal("0.01")))


#: Kept as the internal name used throughout this module.
_money = format_money


#: A cell a spreadsheet would EVALUATE rather than display. Excel, Google Sheets
#: and LibreOffice treat a leading = + - @ (or tab/CR) as the start of a formula
#: even when the field is CSV-quoted — a leading hyphen is a unary-minus formula,
#: exactly like '=' — so a narration like "=HYPERLINK(""http://evil/x"",""click"")"
#: or a reference like -2+2+cmd|' /C calc'!A0 becomes a live formula the moment
#: the accountant opens the workpaper. Prefixing a single quote is the standard
#: defusal: the cell still READS the same and stops being executable. Only
#: free-text cells pass through here — money goes via format_money() — so a
#: genuine negative amount is never turned into text (vuln-0005).
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: str | None) -> str:
    """Free text for a CSV cell, defused if it would be read as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def export_tally_csv(result: ReconResult) -> str:
    """Bank-receipt rows for Tally import.

    One row per settlement-side transaction: matched rows carry the bank ref;
    settlement_only rows are flagged 'PENDING_BANK' so the accountant knows
    the money has not landed (or the statement is missing the line).
    """
    rows = []
    for m in result.matched:
        rows.append([
            m.settlement.txn_date.isoformat(),
            _cell(m.settlement.ref or m.settlement.utr),
            _money(m.settlement.amount),
            _cell(m.bank.utr),
            "MATCHED",
        ])
    for t in result.settlement_only:
        rows.append([
            t.txn_date.isoformat(),
            _cell(t.ref or t.utr),
            _money(t.amount),
            "",
            "PENDING_BANK",
        ])
    for t in result.bank_only:
        rows.append([
            t.txn_date.isoformat(),
            _cell(t.ref or t.utr),
            _money(t.amount),
            _cell(t.utr),
            "UNEXPECTED_CREDIT",
        ])
    return _write(rows, ["date", "reference", "amount_inr", "bank_utr", "status"])


def export_gst_worksheet(lines: list[ReconLine]) -> str:
    """Per-batch gross/fee/tax netting for GST worksheets.

    MDR (fee) and GST-on-MDR (tax) are the merchant's expense side; gross
    payment amount is the outward-supply side. One row per settlement batch.
    """
    rows = []
    for b in group_batches(lines):
        rows.append([
            _cell(b.settlement_id),
            _cell(b.utr),
            _money(b.gross),
            _money(b.fees),
            _money(b.taxes),
            _money(b.refunds),
            _money(b.net),
        ])
    return _write(
        rows,
        ["settlement_id", "utr", "gross_inr", "fee_inr", "tax_on_fee_inr",
         "refunds_inr", "net_settled_inr"],
    )


# Income-tax Act 2025, s.393(1), Schedule Table Sl.8(v) — payment code 1035
# (ex-section 194O, Income-tax Act 1961). E-commerce operators deduct TDS on
# the GROSS sale amount; rate 0.1% from 1 Oct 2024 (was 1%). Individual/HUF
# sellers below Rs 5,00,000 cumulative annual sales are exempt.
TDS_1035_CODE = "1035"
TDS_1035_RATE = Decimal("0.001")


def export_tds_1035(
    lines: list[ReconLine],
    *,
    seller_pan: str | None = None,
    seller_type: str = "company",  # company | firm | llp | individual | huf
    annual_gross_sales: Decimal = Decimal("0"),
) -> str:
    """TDS code-1035 deduction worksheet for e-commerce sellers.

    Computes the 0.1% TDS on gross payment amounts (the amount the operator
    deducts before settling) and flags whether the seller's profile attracts
    TDS (individuals/HUFs are exempt below the Rs 5,00,000 annual threshold).
    Output is a worksheet the CA folds into Form 168 / 26AS matching.
    """
    threshold_exempt = (
        seller_type.lower() in ("individual", "huf")
        and annual_gross_sales < Decimal("500000")
    )
    rows = []
    for line in lines:
        if line.type != "payment":
            continue
        tds = Decimal("0") if threshold_exempt else (line.amount * TDS_1035_RATE).quantize(Decimal("0.01"))
        rows.append([
            line.created_at.isoformat(),
            _cell(line.entity_id),
            _cell(line.order_id),
            _money(line.amount),
            TDS_1035_CODE if not threshold_exempt else "EXEMPT_BELOW_5L",
            _money(tds),
            _money(line.amount - tds),
            _cell(seller_pan),
        ])
    return _write(
        rows,
        ["payment_date", "payment_id", "order_id", "gross_amount_inr",
         "tds_code", "tds_deducted_inr", "net_expected_inr", "seller_pan"],
    )
