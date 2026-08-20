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
import sys
from datetime import date
from pathlib import Path

from .exceptions import classify
from .exports import export_tally_csv
from .matching import match
from .pdf import parse_sbi_pdf
from .schemas import load_bank_statement, load_settlement_csv


def _load_statement(path: str, bank: str):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return parse_sbi_pdf(p)
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

    args = ap.parse_args(argv)

    settlements = load_settlement_csv(args.settlements, args.vendor)
    bank = _load_statement(args.statement, args.bank)
    result = match(settlements, bank)

    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    exceptions = classify(result, as_of=as_of)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    tally = export_tally_csv(result)
    (out / "tally.csv").write_text(tally, encoding="utf-8")

    wrote = [str(out / "tally.csv")]
    if exceptions:
        rows = "\n".join(
            f"{e.category},{e.amount},{e.utr or ''},{e.ref or ''},{e.detail}"
            for e in exceptions
        )
        (out / "exceptions.csv").write_text(
            "category,amount,utr,ref,detail\n" + rows + "\n", encoding="utf-8",
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
