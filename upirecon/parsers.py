"""CSV loaders. Column names are explicit so any vendor/bank format plugs in."""
from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Txn

_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y")


def parse_date(value: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).date()
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
