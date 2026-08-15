"""Self-check for the matching engine. Run: python tests/test_matching.py"""
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upirecon import MatchStatus, Txn, match


def t(utr, amount, day, ref=None):
    return Txn(utr=utr, amount=Decimal(amount), txn_date=date(2026, 8, day), ref=ref)


def test_exact_utr_match():
    s = [t("123456789012", "100.00", 15, ref="order_1")]
    b = [t("1234 5678 9012", "100.00", 16)]  # normalized UTR matches
    r = match(s, b)
    assert len(r.matched) == 1
    assert r.matched[0].status == MatchStatus.EXACT
    assert not r.settlement_only and not r.bank_only


def test_amount_mismatch_flag():
    s = [t("123456789012", "100.00", 15)]
    b = [t("123456789012", "90.00", 16)]
    r = match(s, b)
    assert r.matched[0].status == MatchStatus.AMOUNT_MISMATCH


def test_amount_date_fallback_when_no_utr():
    s = [t(None, "50.00", 15, ref="order_2")]
    b = [t(None, "50.00", 15)]
    r = match(s, b)
    assert r.matched[0].status == MatchStatus.AMOUNT_DATE


def test_unmatched_flows_to_correct_buckets():
    s = [t("AAA", "100.00", 15), t("BBB", "200.00", 16)]
    b = [t("AAA", "100.00", 15), t("CCC", "999.00", 20)]
    r = match(s, b)
    assert len(r.matched) == 1
    assert len(r.settlement_only) == 1 and r.settlement_only[0].utr == "BBB"
    assert len(r.bank_only) == 1 and r.bank_only[0].utr == "CCC"


def test_totals_reconcile():
    s = [t("A1", "100.00", 15), t("A2", "200.00", 15)]
    b = [t("A1", "100.00", 15)]
    r = match(s, b)
    assert r.matched_total == Decimal("100.00")
    assert r.unmatched_settlement_total == Decimal("200.00")
    assert r.unmatched_bank_total == Decimal("0")


if __name__ == "__main__":
    test_exact_utr_match()
    test_amount_mismatch_flag()
    test_amount_date_fallback_when_no_utr()
    test_unmatched_flows_to_correct_buckets()
    test_totals_reconcile()
    print("all 5 matching-engine checks passed")
