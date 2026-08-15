"""Deterministic RRN/UTR matching engine."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from .models import Match, MatchStatus, ReconResult, Settlement, Txn


def match(settlements: list[Txn], bank: list[Txn]) -> ReconResult:
    """Reconcile settlement lines against bank-statement lines.

    Strategy (deterministic; Decimal throughout; no floats):

      1. Exact match on normalized UTR. Same UTR with different amounts is
         kept but flagged AMOUNT_MISMATCH so a human sees it.
      2. For lines whose UTR did not match, fall back to an (amount, date)
         match.
      3. Anything left is settlement_only or bank_only.

    Bank lines are tracked by list index (not object identity) so two rows
    with identical values are still treated as distinct.
    """
    result = ReconResult()

    bank_by_utr: dict[str, list[tuple[int, Txn]]] = defaultdict(list)
    for i, b in enumerate(bank):
        if b.key:
            bank_by_utr[b.key].append((i, b))

    consumed: set[int] = set()

    def take(candidates: list[tuple[int, Txn]], amount: Decimal) -> Txn | None:
        # Prefer a same-amount line, else the first free line.
        for i, c in candidates:
            if i not in consumed and c.amount == amount:
                consumed.add(i)
                return c
        for i, c in candidates:
            if i not in consumed:
                consumed.add(i)
                return c
        return None

    pending: list[Txn] = []
    for s in settlements:
        if s.key:
            b = take(bank_by_utr.get(s.key, []), s.amount)
            if b is not None:
                status = (
                    MatchStatus.EXACT
                    if b.amount == s.amount
                    else MatchStatus.AMOUNT_MISMATCH
                )
                result.matched.append(Match(s, b, status))
                continue
        pending.append(s)

    # Amount + date fallback among the still-free bank lines.
    by_amount_date: dict[tuple[Decimal, object], list[tuple[int, Txn]]] = defaultdict(list)
    for i, b in enumerate(bank):
        if i not in consumed:
            by_amount_date[(b.amount, b.txn_date)].append((i, b))

    for s in pending:
        b = take(by_amount_date.get((s.amount, s.txn_date), []), s.amount)
        if b is not None:
            result.matched.append(Match(s, b, MatchStatus.AMOUNT_DATE))
        else:
            result.settlement_only.append(s)

    result.bank_only = [b for i, b in enumerate(bank) if i not in consumed]
    return result


def match_settlements(settlements: list[Settlement], bank: list[Txn]) -> ReconResult:
    """Reconcile settlement batches against bank credits.

    Each Settlement becomes a Txn (ref = settlement_id) and is matched with
    match(). The bank credit carries the correspondent bank's UTR, which often
    differs from the gateway's settlement_utr, so the (amount, date) fallback in
    match() is what actually pairs them in practice.
    """
    txns = [
        Txn(utr=s.utr, amount=s.amount, txn_date=s.created_at, ref=s.settlement_id)
        for s in settlements
    ]
    return match(txns, bank)
