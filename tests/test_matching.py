"""Self-check for the library. Run: python tests/test_matching.py"""
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from upirecon import MatchStatus, Txn, match, match_settlements, parse_razorpay_settlements


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


def test_razorpay_settlements_parse_and_match():
    # Verbatim sample from Razorpay 'Fetch All Settlements' docs.
    data = {
        "entity": "collection",
        "items": [
            {"id": "setl_DGlQ1Rj8os78Ec", "entity": "settlement", "amount": 9973635,
             "status": "processed", "fees": 0, "tax": 0, "utr": "1568176960vxp0rj",
             "created_at": 1568176960},
            {"id": "setl_4xbSwsPABDJ8oK", "entity": "settlement", "amount": 50000,
             "status": "processed", "fees": 0, "tax": 0, "utr": "RZRP173069230702",
             "created_at": 1509622306},
        ],
    }
    settlements = parse_razorpay_settlements(data)
    assert len(settlements) == 2
    assert settlements[0].amount == Decimal("99736.35")  # paise -> rupees
    assert settlements[0].settlement_id == "setl_DGlQ1Rj8os78Ec"

    bank = [t("1568176960vxp0rj", "99736.35", 11)]
    r = match_settlements(settlements, bank)
    assert len(r.matched) == 1
    assert r.matched[0].settlement.ref == "setl_DGlQ1Rj8os78Ec"
    assert len(r.settlement_only) == 1 and r.settlement_only[0].ref == "setl_4xbSwsPABDJ8oK"


def test_razorpay_settlement_matches_by_amount_date_when_bank_utr_differs():
    epoch = 1509622306
    d = datetime.fromtimestamp(epoch, tz=timezone.utc).date()
    data = {"items": [{"id": "setl_X", "entity": "settlement", "amount": 50000,
                       "fees": 0, "tax": 0, "utr": "RZRP123", "created_at": epoch}]}
    settlements = parse_razorpay_settlements(data)
    # The bank UTR is the correspondent bank's, not Razorpay's settlement_utr.
    bank = [Txn("BANKUTR999", Decimal("500.00"), d)]
    r = match_settlements(settlements, bank)
    assert len(r.matched) == 1
    assert r.matched[0].status == MatchStatus.AMOUNT_DATE
    assert r.matched[0].settlement.ref == "setl_X"


if __name__ == "__main__":
    test_exact_utr_match()
    test_amount_mismatch_flag()
    test_amount_date_fallback_when_no_utr()
    test_unmatched_flows_to_correct_buckets()
    test_totals_reconcile()
    test_razorpay_settlements_parse_and_match()
    test_razorpay_settlement_matches_by_amount_date_when_bank_utr_differs()
    print("all 7 checks passed")
