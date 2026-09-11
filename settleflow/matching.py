"""Deterministic RRN/UTR matching engine."""
from __future__ import annotations

from collections import deque
from decimal import Decimal

from .models import (
    BatchRecon,
    Match,
    MatchStatus,
    OrderMatch,
    OrderReconResult,
    ReconLine,
    ReconResult,
    Settlement,
    Txn,
)


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

    Consumption is linear: each bank line sits in at most one per-key queue and one
    per-amount queue, and is popped once. An earlier version rescanned the candidate
    list for every settlement, which went quadratic when many rows share one UTR —
    a real shape (one RRN paying out a whole batch) rather than a synthetic one, and
    it fits comfortably inside the hosted upload cap. Measured before/after at
    n rows sharing a single UTR: 1k=0.011s, 2k=0.066s, 4k=0.161s, 8k=0.655s
    (~4x per doubling) versus linear here.
    """
    result = ReconResult()

    # Per-UTR state: `any` holds every index with this key, `by_amount` indexes the
    # same rows by amount so the same-amount preference is a popleft, not a rescan.
    by_utr: dict[str, dict] = {}
    for i, b in enumerate(bank):
        if b.key:
            slot = by_utr.setdefault(b.key, {"any": deque(), "by_amount": {}})
            slot["any"].append(i)
            slot["by_amount"].setdefault(b.amount, deque()).append(i)

    consumed: set[int] = set()

    def pop_unconsumed(queue: deque) -> int | None:
        """Pop the next index from `queue` that has not already been consumed."""
        while queue:
            i = queue.popleft()
            if i not in consumed:
                consumed.add(i)
                return i
        return None

    def take(key: str, amount: Decimal) -> Txn | None:
        slot = by_utr.get(key)
        if not slot:
            return None
        bucket = slot["by_amount"].get(amount)
        idx = pop_unconsumed(bucket) if bucket is not None else None
        if idx is None:
            idx = pop_unconsumed(slot["any"])
        return bank[idx] if idx is not None else None

    pending: list[Txn] = []
    for s in settlements:
        if s.key:
            b = take(s.key, s.amount)
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
    by_amount_date: dict[tuple[Decimal, object], deque] = {}
    for i, b in enumerate(bank):
        if i not in consumed:
            by_amount_date.setdefault((b.amount, b.txn_date), deque()).append(i)

    for s in pending:
        bucket = by_amount_date.get((s.amount, s.txn_date))
        idx = pop_unconsumed(bucket) if bucket is not None else None
        if idx is not None:
            result.matched.append(Match(s, bank[idx], MatchStatus.AMOUNT_DATE))
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


# ---------------------------------------------------------------------------
# Level 2: line-item decomposition. Recon lines -> settlement batches,
# gross/fee/tax/refund netting, and matching against the merchant's own
# order ledger (order_id -> order row). Deterministic, Decimal throughout.
# ---------------------------------------------------------------------------

def group_batches(lines: list[ReconLine]) -> list[BatchRecon]:
    """Group recon lines into one BatchRecon per settlement_id."""
    batches: dict[str, BatchRecon] = {}
    for line in lines:
        batch = batches.setdefault(
            line.settlement_id,
            BatchRecon(settlement_id=line.settlement_id, utr=line.settlement_utr),
        )
        batch.lines.append(line)
    return [batches[k] for k in sorted(batches)]


def match_orders(lines: list[ReconLine], orders: list[Txn]) -> OrderReconResult:
    """Match per-transaction recon lines against the merchant order ledger.

    orders: merchant-side rows, Txn(ref=order_id, amount=gross order amount,
    txn_date=order date). Pass 1 joins on order_id (exact ref), pass 2 falls
    back to (amount, date). Refund lines are linked to their originating
    payment line via payment_id instead of the order ledger. Adjustment lines
    are kept separately for human review. Amounts compared in rupees.
    """
    result = OrderReconResult()

    # Refund -> payment linkage (payment_id points at the original payment).
    by_entity: dict[str, ReconLine] = {l.entity_id: l for l in lines if l.entity_id}
    for line in lines:
        if line.type == "refund" and line.payment_id:
            src = by_entity.get(line.payment_id)
            if src is not None and src.type == "payment":
                result.refund_links.append((line, src))

    payment_lines = [l for l in lines if l.type == "payment"]
    adjustments = [l for l in lines if l.type == "adjustment"]
    result.adjustments.extend(adjustments)

    orders_by_ref: dict[str, deque] = {}
    for i, o in enumerate(orders):
        if o.ref:
            orders_by_ref.setdefault(normalize_ref(o.ref), deque()).append(i)
    consumed: set[int] = set()

    def pop_unconsumed(queue: deque) -> int | None:
        """Pop the next index from `queue` that has not already been consumed."""
        while queue:
            i = queue.popleft()
            if i not in consumed:
                consumed.add(i)
                return i
        return None

    def take_order(ref: str | None, amount: Decimal) -> tuple[Txn, bool] | None:
        if not ref:
            return None
        bucket = orders_by_ref.get(normalize_ref(ref))
        idx = pop_unconsumed(bucket) if bucket is not None else None
        if idx is None:
            return None
        return orders[idx], orders[idx].amount == amount

    pending: list[ReconLine] = []
    for line in payment_lines:
        hit = take_order(line.order_id, line.amount)
        if hit is not None:
            order, same_amount = hit
            result.matched.append(
                OrderMatch(line, order, MatchStatus.EXACT if same_amount else MatchStatus.AMOUNT_MISMATCH)
            )
            continue
        pending.append(line)

    # Amount + date fallback among the still-free orders.
    by_amount_date: dict[tuple[Decimal, object], deque] = {}
    for i, o in enumerate(orders):
        if i not in consumed:
            by_amount_date.setdefault((o.amount, o.txn_date), deque()).append(i)
    for line in pending:
        bucket = by_amount_date.get((line.amount, line.created_at))
        idx = pop_unconsumed(bucket) if bucket is not None else None
        if idx is not None:
            result.matched.append(OrderMatch(line, orders[idx], MatchStatus.AMOUNT_DATE))
        else:
            result.unmatched_lines.append(line)

    result.unmatched_orders = [o for i, o in enumerate(orders) if i not in consumed]
    return result


def normalize_ref(value: str | None) -> str:
    """Normalize an order ref the same way UTRs are normalized."""
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isalnum()).upper()
