"""Exception classification for the unmatched 1-3%.

Deterministic rule engine first; an OPTIONAL LLM hook formats a prompt for the
unmatched exceptions so a model (or a human) can triage them. No network, no
LLM dependency in the core — classification is rules + the prompt builder.

The rules encode the real-world reasons settlement reconciliation breaks, in
priority order:
  1. amount_mismatch   -> FEE_DRIFT (gateway changed MDR between order and settlement)
  2. same-day duplicate amount -> DUPLICATE_SUSPECT
  3. settlement older than the bank window -> STALE_SETTLEMENT
  4. bank credit with no settlement -> DIRECT_TRANSFER (non-gateway NEFT/IMPS)
  5. everything else -> MANUAL_REVIEW
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .models import Match, MatchStatus, ReconResult


@dataclass(frozen=True)
class Exception:
    """One classified reconciliation exception."""

    category: str          # FEE_DRIFT | DUPLICATE_SUSPECT | STALE_SETTLEMENT
                           # | DIRECT_TRANSFER | MANUAL_REVIEW
    amount: Decimal
    detail: str
    utr: str | None = None
    ref: str | None = None


def classify(
    result: ReconResult,
    *,
    as_of: date | None = None,
    stale_after_days: int = 7,
) -> list[Exception]:
    """Classify every unmatched/mismatched item in a ReconResult.

    as_of: the statement date; settlement lines older than
    stale_after_days are flagged STALE_SETTLEMENT. Deterministic — same
    input, same output, no randomness.
    """
    out: list[Exception] = []
    as_of = as_of or date.today()

    # Fee drift: UTR matched, amounts differ.
    for m in result.matched:
        if m.status == MatchStatus.AMOUNT_MISMATCH:
            diff = m.settlement.amount - m.bank.amount
            out.append(Exception(
                category="FEE_DRIFT",
                amount=m.settlement.amount,
                detail=f"UTR matched but amounts differ by {diff} (likely MDR/fee change)",
                utr=m.settlement.utr,
                ref=m.settlement.ref,
            ))

    # Duplicate suspects: identical (amount, date) pairs left over on both sides.
    bank_only_by_key: dict[tuple[Decimal, date], int] = {}
    for t in result.bank_only:
        key = (t.amount, t.txn_date)
        bank_only_by_key[key] = bank_only_by_key.get(key, 0) + 1
    for t in result.settlement_only:
        if bank_only_by_key.get((t.amount, t.txn_date), 0) > 0:
            out.append(Exception(
                category="DUPLICATE_SUSPECT",
                amount=t.amount,
                detail="unmatched settlement AND bank line with same amount+date — check for duplicate posting",
                utr=t.utr,
                ref=t.ref,
            ))

    # Stale settlements.
    cutoff = as_of - timedelta(days=stale_after_days)
    for t in result.settlement_only:
        if t.txn_date < cutoff:
            out.append(Exception(
                category="STALE_SETTLEMENT",
                amount=t.amount,
                detail=f"settlement dated {t.txn_date.isoformat()} is {stale_after_days}+ days old with no bank credit",
                utr=t.utr,
                ref=t.ref,
            ))

    # Bank credits with no settlement at all.
    for t in result.bank_only:
        out.append(Exception(
            category="DIRECT_TRANSFER",
            amount=t.amount,
            detail="bank credit with no gateway settlement — NEFT/IMPS/salary/other?",
            utr=t.utr,
            ref=t.ref,
        ))

    # Remaining unmatched with no other signal.
    flagged = {(e.amount, e.utr, e.ref) for e in out}
    for t in result.settlement_only:
        if (t.amount, t.utr, t.ref) not in flagged:
            out.append(Exception(
                category="MANUAL_REVIEW",
                amount=t.amount,
                detail="no matching bank credit and no rule matched",
                utr=t.utr,
                ref=t.ref,
            ))

    return out


def build_llm_prompt(exceptions: list[Exception]) -> str:
    """Format a triage prompt for an LLM (or a human) from the exceptions.

    The core never calls an LLM; the SaaS layer pipes this prompt to one.
    """
    lines = [
        "You are reconciling UPI settlement files against a bank statement.",
        "Classify each exception and suggest the most likely cause and the",
        "single best next action for the accountant.",
        "",
    ]
    for i, e in enumerate(exceptions, 1):
        lines.append(
            f"{i}. [{e.category}] amount={e.amount} utr={e.utr or '-'} "
            f"ref={e.ref or '-'} :: {e.detail}"
        )
    return "\n".join(lines)
