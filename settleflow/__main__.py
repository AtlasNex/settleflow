"""`python -m settleflow` — one-command reconciliation CLI.

The core flow, end to end, without writing Python:

    python -m settleflow reconcile \\
        --settlements settlements.csv --vendor razorpay_settlement_csv \\
        --bank sbi --statement statement.csv --out-dir ./out

Writes `tally.csv` (matched + unmatched bank-receipt rows) and, when there are
exceptions, `exceptions.csv`, then prints a one-line summary.
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from datetime import date
from pathlib import Path

from .exceptions import classify
from .exports import export_tally_csv, format_money
from .matching import match
from .pdf import parse_sbi_pdf
from .schemas import load_bank_statement, load_settlement_csv


def _load_statement(path: str, bank: str, ocr: bool = False):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        if bank != "sbi":
            raise ValueError(
                f"--bank {bank} with a .pdf statement isn't supported: the PDF parser "
                "only handles SBI (YONO/netbanking/credit-card). Export the statement "
                "as CSV for other banks."
            )
        return parse_sbi_pdf(p, ocr=ocr)
    return load_bank_statement(path, bank)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="settleflow",
        description="Open-source UPI/NPCI settlement reconciliation for India",
    )
    sub = ap.add_subparsers(dest="command", required=True)

    rec = sub.add_parser("reconcile", help="match gateway settlements against a bank statement")
    rec.add_argument("--settlements", required=True, help="gateway settlement CSV")
    rec.add_argument("--vendor", default="razorpay_settlement_csv",
                     help="vendor key from SETTLEMENT_CSV_MAPS")
    rec.add_argument("--bank", required=True,
                     help="bank key: sbi | hdfc | icici | axis | kotak | pnb | dbs")
    rec.add_argument("--statement", required=True, help="bank statement CSV/text/PDF")
    rec.add_argument("--out-dir", default=".", help="output directory")
    rec.add_argument("--as-of", help="statement date (YYYY-MM-DD) for the stale-settlement flag")
    rec.add_argument("--ocr", action="store_true",
                     help="OCR a scanned (image-only) SBI statement PDF (needs 'settleflow[ocr]')")

    args = ap.parse_args(argv)

    try:
        settlements = load_settlement_csv(args.settlements, args.vendor)
        bank = _load_statement(args.statement, args.bank, ocr=args.ocr)
        result = match(settlements, bank)
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        exceptions = classify(result, as_of=as_of)
    except ValueError as exc:
        # A bad input file is the caller's, not a crash. Without this the loader's
        # refusal surfaced as a traceback, which is non-zero but tells the user
        # nothing; and the failure it replaces was worse — a JSON settlement file
        # used to read as an empty CSV and be reported as a clean, successful run.
        print(f"settleflow: {exc}", file=sys.stderr)
        return 2

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tally = export_tally_csv(result)
    # newline="" so the csv module's own CRLF line endings are written verbatim.
    # Without it, text mode translates the '\r\n' again on Windows and the file
    # contains CR-CRLF bytes — malformed for anything that reads it strictly.
    (out / "tally.csv").write_text(tally, encoding="utf-8", newline="")

    wrote = [str(out / "tally.csv")]
    if exceptions:
        # csv.writer, not string joins: a narration or reference containing a comma
        # (e.g. "NEFT CR ACME, PVT LTD") used to shift every column after it, so the
        # whole row was misaligned in the file the accountant opens.
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["category", "amount", "utr", "ref", "detail"])
        for e in exceptions:
            writer.writerow([e.category, format_money(e.amount), e.utr or "",
                             e.ref or "", e.detail])
        (out / "exceptions.csv").write_text(
            buf.getvalue(), encoding="utf-8", newline="",
        )
        wrote.append(str(out / "exceptions.csv"))

    print(f"settlements : {len(settlements)}")
    print(f"bank lines  : {len(bank)}")
    print(f"matched     : {len(result.matched)}")
    print(f"unmatched   : {len(result.settlement_only)} settlement / {len(result.bank_only)} bank")
    print(f"exceptions  : {len(exceptions)}")
    print("wrote       : " + ", ".join(wrote))
    return 0


if __name__ == "__main__":
    sys.exit(main())
