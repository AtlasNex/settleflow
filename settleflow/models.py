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


@dataclass(frozen=True)
class Settlement:
    """A gateway settlement batch (e.g. one Razorpay payout)."""

    settlement_id: str
    amount: Decimal          # net amount settled, in rupees
    created_at: date
    utr: str | None = None
    fees: Decimal = Decimal("0")
    tax: Decimal = Decimal("0")


@dataclass(frozen=True)
class ReconLine:
    """One line of a gateway settlement recon report (Razorpay recon schema).

    Field set = the 24 documented response parameters of Razorpay
    GET /v1/settlements/recon/combined (verified against the docs page
    2026-08-16). Money fields are Decimal RUPEES (paise converted in the
    parser); created_at/settled_at are dates from epoch seconds.
    """

    entity_id: str
    type: str                 # payment | refund | transfer | adjustment
    debit: Decimal            # rupees debited from the merchant account
    credit: Decimal           # rupees credited to the merchant account
    amount: Decimal           # gross amount (pre-fee), rupees
    currency: str
    fee: Decimal
    tax: Decimal
    on_hold: bool
    settled: bool
    created_at: date
    settled_at: date | None
    settlement_id: str
    credit_type: str | None = None
    description: str | None = None
    notes: str | None = None
    payment_id: str | None = None
    settlement_utr: str | None = None
    order_id: str | None = None
    order_receipt: str | None = None
    method: str | None = None
    card_network: str | None = None
    card_issuer: str | None = None
    card_type: str | None = None
    dispute_id: str | None = None

    @property
    def net(self) -> Decimal:
        """Net effect of this line on the merchant account."""
        return self.credit - self.debit


@dataclass
class BatchRecon:
    """All recon lines of one settlement batch, with netting math."""

    settlement_id: str
    utr: str | None
    lines: list[ReconLine] = field(default_factory=list)

    @property
    def gross(self) -> Decimal:
        return sum((l.amount for l in self.lines if l.type == "payment"), Decimal("0"))

    @property
    def fees(self) -> Decimal:
        return sum((l.fee for l in self.lines), Decimal("0"))

    @property
    def taxes(self) -> Decimal:
        return sum((l.tax for l in self.lines), Decimal("0"))

    @property
    def refunds(self) -> Decimal:
        return sum((l.debit for l in self.lines if l.type == "refund"), Decimal("0"))

    @property
    def net(self) -> Decimal:
        """gross credits - gross debits; this is what lands in the bank."""
        return sum((l.net for l in self.lines), Decimal("0"))


@dataclass
class OrderMatch:
    """A recon line matched to a merchant order-ledger line."""

    line: ReconLine
    order: Txn
    status: MatchStatus


@dataclass
class OrderReconResult:
    """Level-2 outcome: recon lines vs the merchant order ledger."""

    matched: list[OrderMatch] = field(default_factory=list)
    refund_links: list[tuple[ReconLine, ReconLine]] = field(default_factory=list)
    unmatched_lines: list[ReconLine] = field(default_factory=list)
    unmatched_orders: list[Txn] = field(default_factory=list)
    adjustments: list[ReconLine] = field(default_factory=list)


def normalize_utr(value: str | None) -> str:
    """Return the alphanumeric, uppercased form of a UTR/RRN.

    UTRs and RRNs carry no meaningful punctuation, so this lets us match
    "1234 5678 9012" against "123456789012".
    """
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isalnum()).upper()
