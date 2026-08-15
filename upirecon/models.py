"""Core data model for UPI settlement reconciliation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


class MatchStatus(str, Enum):
    """How a settlement line was matched to a bank line."""

    EXACT = "exact"                    # UTR/RRN matched, amounts agree
    AMOUNT_MISMATCH = "amount_mismatch"  # UTR matched, amounts disagree (flag)
    AMOUNT_DATE = "amount_date"        # no UTR match; amount + date agree
    UNMATCHED = "unmatched"


@dataclass(frozen=True)
class Txn:
    """One side of a reconciliation: a settlement line or a bank line."""

    utr: str | None
    amount: Decimal
    txn_date: date
    ref: str | None = None  # order id / narration / description

    @property
    def key(self) -> str:
        return normalize_utr(self.utr)


@dataclass
class Match:
    settlement: Txn
    bank: Txn
    status: MatchStatus


@dataclass
class ReconResult:
    """Outcome of a reconciliation run."""

    matched: list[Match] = field(default_factory=list)
    settlement_only: list[Txn] = field(default_factory=list)
    bank_only: list[Txn] = field(default_factory=list)

    @property
    def matched_total(self) -> Decimal:
        return sum((m.settlement.amount for m in self.matched), Decimal("0"))

    @property
    def unmatched_settlement_total(self) -> Decimal:
        return sum((t.amount for t in self.settlement_only), Decimal("0"))

    @property
    def unmatched_bank_total(self) -> Decimal:
        return sum((t.amount for t in self.bank_only), Decimal("0"))


def normalize_utr(value: str | None) -> str:
    """Return the alphanumeric, uppercased form of a UTR/RRN.

    UTRs and RRNs carry no meaningful punctuation, so this lets us match
    "1234 5678 9012" against "123456789012".
    """
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isalnum()).upper()
