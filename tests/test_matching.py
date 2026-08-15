"""Self-check for the library. Run: python tests/test_matching.py"""
import sys
import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from settleflow import (
    MatchStatus,
    Txn,
    build_llm_prompt,
    classify,
    export_gst_worksheet,
    export_tally_csv,
    export_tds_1035,
    group_batches,
    load_bank_statement,
    load_settlement_csv,
    load_vendor_recon_csv,
    match,
    match_orders,
    match_settlements,
    parse_razorpay_recon,
    parse_razorpay_settlements,
)

_TMP = Path(tempfile.mkdtemp(prefix="settleflow-test-"))


def tmp_dir() -> Path:
    return _TMP


def t(utr, amount, day, ref=None):
    return Txn(utr=utr, amount=Decimal(amount), txn_date=date(2026, 8, day), ref=ref)


# ---- Level 1 (settlement -> bank) ----

def test_exact_utr_match():
    s = [t("123456789012", "100.00", 15, ref="order_1")]
    b = [t("1234 5678 9012", "100.00", 16)]
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
    assert settlements[0].amount == Decimal("99736.35")
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
    bank = [Txn("BANKUTR999", Decimal("500.00"), d)]
    r = match_settlements(settlements, bank)
    assert len(r.matched) == 1
    assert r.matched[0].status == MatchStatus.AMOUNT_DATE
    assert r.matched[0].settlement.ref == "setl_X"


# ---- Level 2 (recon lines -> orders): verbatim docs sample ----

def _recon_docs_sample():
    """Verbatim shape of Razorpay GET /v1/settlements/recon/combined."""
    return {
        "entity": "collection",
        "count": 4,
        "items": [
            {"entity_id": "pay_DEXrnipqTmWVGE", "type": "payment", "debit": 0,
             "credit": 97100, "amount": 100000, "currency": "INR", "fee": 2900,
             "tax": 0, "on_hold": False, "settled": True, "created_at": 1567692556,
             "settled_at": 1568176960, "settlement_id": "setl_DGlQ1Rj8os78Ec",
             "posted_at": None, "credit_type": "default", "description": None,
             "notes": "Beam me up Scotty.", "payment_id": None,
             "settlement_utr": "1568176960vxp0rj", "order_id": "order_DEXrnRiR3SNDHA",
             "order_receipt": None, "method": "card", "card_network": "AMEX",
             "card_issuer": "AMEX", "card_type": "credit", "dispute_id": None},
            {"entity_id": "rfnd_DGRcGzZSLyEdg1", "type": "refund", "debit": 242500,
             "credit": 0, "amount": 242500, "currency": "INR", "fee": 0, "tax": 0,
             "on_hold": False, "settled": True, "created_at": 1568107224,
             "settled_at": 1568176960, "settlement_id": "setl_DGlQ1Rj8os78Ec",
             "posted_at": None, "credit_type": "default", "description": None,
             "notes": "Beam me up Scotty.", "payment_id": "pay_DEXq1pACSqFxtS",
             "settlement_utr": "1568176960vxp0rj", "order_id": "order_DEXpmZgffXNvuI",
             "order_receipt": None, "method": "card", "card_network": "AMEX",
             "card_issuer": "AMEX", "card_type": "credit", "dispute_id": None},
            {"entity_id": "trf_DEUoCEtdsJgvl7", "type": "transfer", "debit": 100296,
             "credit": 0, "amount": 100000, "currency": "INR", "fee": 296, "tax": 46,
             "on_hold": False, "settled": True, "created_at": 1567681786,
             "settled_at": 1568176960, "settlement_id": "setl_DGlQ1Rj8os78Ec",
             "posted_at": None, "credit_type": "default", "description": None,
             "notes": None, "payment_id": "pay_DEApNNTR6xmqJy",
             "settlement_utr": "1568176960vxp0rj", "order_id": None,
             "order_receipt": None, "method": None, "card_network": None,
             "card_issuer": None, "card_type": None, "dispute_id": None},
            {"entity_id": "adj_EhcHONhX4ChgNC", "type": "adjustment", "debit": 0,
             "credit": 1012, "amount": 1012, "currency": "INR", "fee": 0, "tax": 0,
             "on_hold": False, "settled": True, "created_at": 1567681786,
             "settled_at": 1568176960, "settlement_id": "setl_DGlQ1Rj8os78Ec",
             "posted_at": None, "description": "test reason", "notes": None,
             "payment_id": None, "settlement_utr": None, "order_id": None,
             "order_receipt": None, "method": None, "card_network": None,
             "card_issuer": None, "card_type": None, "dispute_id": None},
        ],
    }


def test_parse_recon_lines_verbatim():
    lines = parse_razorpay_recon(_recon_docs_sample())
    assert len(lines) == 4
    types = [l.type for l in lines]
    assert types == ["payment", "refund", "transfer", "adjustment"]
    # paise -> rupees
    assert lines[0].credit == Decimal("971.00")
    assert lines[0].amount == Decimal("1000.00")
    assert lines[0].fee == Decimal("29.00")
    assert lines[1].debit == Decimal("2425.00")
    assert lines[0].settlement_utr == "1568176960vxp0rj"
    assert lines[0].created_at == datetime.fromtimestamp(1567692556, tz=timezone.utc).date()


def test_parse_recon_rejects_unknown_fields():
    sample = _recon_docs_sample()
    sample["items"][0]["brand_new_field"] = "surprise"
    try:
        parse_razorpay_recon(sample)
        raise AssertionError("expected ValueError for unknown field")
    except ValueError as e:
        assert "brand_new_field" in str(e)


def test_parse_recon_rejects_missing_required():
    sample = _recon_docs_sample()
    del sample["items"][0]["settlement_id"]
    try:
        parse_razorpay_recon(sample)
        raise AssertionError("expected ValueError for missing required key")
    except ValueError as e:
        assert "settlement_id" in str(e)


def test_group_batches_nets_correctly():
    lines = parse_razorpay_recon(_recon_docs_sample())
    batches = group_batches(lines)
    assert len(batches) == 1
    b = batches[0]
    assert b.settlement_id == "setl_DGlQ1Rj8os78Ec"
    assert b.gross == Decimal("1000.00")          # payment amount only
    assert b.fees == Decimal("31.96")             # 29.00 + 2.96
    assert b.taxes == Decimal("0.46")
    assert b.refunds == Decimal("2425.00")
    # net = credits - debits = 971.00 - 2425.00 - 1002.96 + 10.12
    assert b.net == Decimal("-2446.84")


def test_match_orders_exact_and_unmatched():
    lines = parse_razorpay_recon(_recon_docs_sample())
    payment_day = datetime.fromtimestamp(1567692556, tz=timezone.utc).date()
    orders = [
        Txn(utr=None, amount=Decimal("1000.00"), txn_date=payment_day,
            ref="order_DEXrnRiR3SNDHA"),
        Txn(utr=None, amount=Decimal("500.00"), txn_date=payment_day, ref="order_NONE"),
    ]
    r = match_orders(lines, orders)
    assert len(r.matched) == 1
    assert r.matched[0].status == MatchStatus.EXACT
    assert r.matched[0].line.entity_id == "pay_DEXrnipqTmWVGE"
    # adjustment is kept separately, not matched against orders
    assert len(r.adjustments) == 1 and r.adjustments[0].type == "adjustment"
    # the order with no payment line is unmatched
    assert len(r.unmatched_orders) == 1 and r.unmatched_orders[0].ref == "order_NONE"


def test_match_orders_amount_mismatch_and_amount_date_fallback():
    lines = parse_razorpay_recon(_recon_docs_sample())
    payment_day = datetime.fromtimestamp(1567692556, tz=timezone.utc).date()
    # mismatch: same order_id, different amount
    orders = [Txn(utr=None, amount=Decimal("999.00"), txn_date=payment_day,
                  ref="order_DEXrnRiR3SNDHA")]
    r = match_orders(lines, orders)
    assert r.matched[0].status == MatchStatus.AMOUNT_MISMATCH

    # fallback: no order_id match but same amount+date (create a synthetic
    # payment line with no order_id)
    from settleflow import ReconLine
    synthetic = ReconLine(
        entity_id="pay_SYNTH", type="payment", debit=Decimal("0"),
        credit=Decimal("250.00"), amount=Decimal("250.00"), currency="INR",
        fee=Decimal("0"), tax=Decimal("0"), on_hold=False, settled=True,
        created_at=payment_day, settled_at=None, settlement_id="setl_SYNTH",
        order_id=None,
    )
    orders2 = [Txn(utr=None, amount=Decimal("250.00"), txn_date=payment_day, ref="order_X")]
    r2 = match_orders([synthetic], orders2)
    assert len(r2.matched) == 1 and r2.matched[0].status == MatchStatus.AMOUNT_DATE


def test_refund_links_to_payment():
    from settleflow import ReconLine
    d = date(2026, 8, 15)
    payment = ReconLine(entity_id="pay_1", type="payment", debit=Decimal("0"),
                        credit=Decimal("100.00"), amount=Decimal("100.00"),
                        currency="INR", fee=Decimal("0"), tax=Decimal("0"),
                        on_hold=False, settled=True, created_at=d, settled_at=None,
                        settlement_id="s1", order_id="o1")
    refund = ReconLine(entity_id="rfnd_1", type="refund", debit=Decimal("100.00"),
                       credit=Decimal("0"), amount=Decimal("100.00"), currency="INR",
                       fee=Decimal("0"), tax=Decimal("0"), on_hold=False, settled=True,
                       created_at=d, settled_at=None, settlement_id="s1",
                       payment_id="pay_1", order_id="o1")
    orders = [Txn(utr=None, amount=Decimal("100.00"), txn_date=d, ref="o1")]
    r = match_orders([payment, refund], orders)
    assert len(r.refund_links) == 1
    assert r.refund_links[0][0].entity_id == "rfnd_1"
    assert r.refund_links[0][1].entity_id == "pay_1"


# ---- Exports ----

def test_export_tds_1035():
    lines = parse_razorpay_recon(_recon_docs_sample())
    csv_out = export_tds_1035(lines, seller_type="company")
    rows = [r for r in csv_out.strip().split("\n")[1:] if r]
    assert len(rows) == 1  # only the payment line
    assert ",0.1%," not in csv_out
    # 0.1% of 1000.00 = 1.00
    assert "1.00" in rows[0]
    # exempt individual under 5L
    csv_exempt = export_tds_1035(lines, seller_type="individual",
                                 annual_gross_sales=Decimal("100000"))
    assert "EXEMPT_BELOW_5L" in csv_exempt


def test_export_gst_and_tally():
    lines = parse_razorpay_recon(_recon_docs_sample())
    gst = export_gst_worksheet(lines)
    assert "setl_DGlQ1Rj8os78Ec" in gst
    assert "-2446.84" in gst  # net settled
    # tally export needs a ReconResult
    s = [t("U1", "100.00", 15, ref="order_1")]
    b = [t("U1", "100.00", 16)]
    r = match(s, b)
    tally = export_tally_csv(r)
    assert "MATCHED" in tally and "100.00" in tally


# ---- Exceptions ----

def test_classify_fee_drift_and_direct_transfer():
    s = [t("U1", "100.00", 15), t("U2", "50.00", 15)]
    b = [t("U1", "95.00", 16), t("U3", "777.00", 16)]
    r = match(s, b)
    exceptions = classify(r, as_of=date(2026, 8, 20))
    cats = {e.category for e in exceptions}
    assert "FEE_DRIFT" in cats        # U1 matched but 100 vs 95
    assert "DIRECT_TRANSFER" in cats  # U3 bank-only credit
    assert "STALE_SETTLEMENT" in cats or any(
        e.category == "MANUAL_REVIEW" for e in exceptions)  # U2 unmatched


def test_build_llm_prompt():
    s = [t("U1", "100.00", 15)]
    b = [t("U1", "95.00", 16)]
    r = match(s, b)
    prompt = build_llm_prompt(classify(r, as_of=date(2026, 8, 20)))
    assert "reconciling UPI settlement" in prompt
    assert "FEE_DRIFT" in prompt


# ---- Phase 3: bank-statement + vendor CSV parsers (verbatim headers) ----

def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return path


def test_hdfc_bank_statement_parse():
    csv = (
        "HDFC Bank Limited\n"
        "Account No: 1234\n"
        "Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        "01/07/26,UPI-RAHUL SHARMA-RAHUL@OKAXIS-123456,0000112233,01/07/26,250.00,,10450.25\n"
        "02/07/26,SALARY CREDIT,,02/07/26,,85000.00,95450.25\n"
    )
    p = _write(Path(tmp_dir()) / "hdfc.csv", csv)
    txns = load_bank_statement(str(p), "hdfc")
    assert len(txns) == 2
    assert txns[0].amount == Decimal("-250.00")   # withdrawal -> negative
    assert txns[0].utr == "0000112233"
    assert txns[0].txn_date == date(2026, 7, 1)
    assert txns[1].amount == Decimal("85000.00")  # deposit -> positive
    assert txns[1].ref == "SALARY CREDIT"


def test_sbi_bank_statement_parse():
    csv = (
        "Txn Date,Value Date,Description,Ref No./Cheque No.,Debit,Credit,Balance\n"
        "07/03/2026,07/03/2026,IMPS/416000123456/UPI-ZOMATO,416000123456,350.00,,199650.00\n"
        "08/03/2026,08/03/2026,OPENING BALANCE,,,,\n"
        "09/03/2026,09/03/2026,NEFT CREDIT,99887766,,5000.00,204650.00\n"
    )
    p = _write(Path(tmp_dir()) / "sbi.csv", csv)
    txns = load_bank_statement(str(p), "sbi")
    # OPENING BALANCE row (both empty) is skipped
    assert len(txns) == 2
    assert txns[0].amount == Decimal("-350.00")
    assert txns[0].utr == "416000123456"
    assert txns[1].amount == Decimal("5000.00")


def test_sbi_tab_separated_xls_parse():
    # SBI's native "CSV" download is actually tab-separated ".xls" text.
    # The loader must sniff the delimiter and still parse it.
    lines = [
        "Txn Date\tValue Date\tDescription\tRef No./Cheque No.\tDebit\tCredit\tBalance",
        "07/03/2026\t07/03/2026\tIMPS/416000123456/UPI-ZOMATO\t416000123456\t350.00\t\t199650.00",
        "08/03/2026\t08/03/2026\tUPI CREDIT\t99887766\t\t250.00\t199900.00",
    ]
    p = _write(Path(tmp_dir()) / "sbi.xls", "\n".join(lines))
    txns = load_bank_statement(str(p), "sbi")
    assert len(txns) == 2
    assert txns[0].amount == Decimal("-350.00")
    assert txns[1].amount == Decimal("250.00")
    assert txns[1].utr == "99887766"


def test_axis_bank_statement_parse():
    csv = (
        "Tran Date,CHQNO,PARTICULARS,DR,CR,BAL,SOL\n"
        "05-01-2026,,UPI/TRANSFER/123456,,200.00,10500.00,SOL123\n"
        "06-01-2026,000045,POS DEBIT,150.00,,10350.00,SOL123\n"
    )
    p = _write(Path(tmp_dir()) / "axis.csv", csv)
    txns = load_bank_statement(str(p), "axis")
    assert len(txns) == 2
    assert txns[0].amount == Decimal("200.00")   # CR -> positive
    assert txns[1].amount == Decimal("-150.00")  # DR -> negative
    assert txns[1].txn_date == date(2026, 1, 6)


def test_kotak_bank_statement_parse():
    csv = (
        "Transaction Date,Description,Chq./Ref.No.,Withdrawal Amt.,Deposit Amt.,Closing Balance\n"
        "01-04-2026,UPI PAYMENT,123456789,99.00,,501.00\n"
        "02-04-2026,REFUND RECEIVED,,,199.00,700.00\n"
    )
    p = _write(Path(tmp_dir()) / "kotak.csv", csv)
    txns = load_bank_statement(str(p), "kotak")
    assert len(txns) == 2
    assert txns[0].amount == Decimal("-99.00")
    assert txns[1].amount == Decimal("199.00")


def test_icici_bank_statement_parse():
    csv = (
        "S No.,Value Date,Transaction Date,Cheque Number,Transaction Remarks,Withdrawal Amount(INR),Deposit Amount(INR),Balance(INR)\n"
        "1,02-Jan-2024,01-Jan-2024,,UPI CREDIT,,1500.00,1500.00\n"
        "2,03-Jan-2024,02-Jan-2024,000111,ATM WITHDRAWAL,500.00,,1000.00\n"
    )
    p = _write(Path(tmp_dir()) / "icici.csv", csv)
    txns = load_bank_statement(str(p), "icici")
    assert len(txns) == 2
    assert txns[0].amount == Decimal("1500.00")
    assert txns[1].amount == Decimal("-500.00")
    assert txns[0].txn_date == date(2024, 1, 1)


def test_razorpay_settlement_csv_parse():
    csv = (
        "id,amount,status,fees,tax,utr,created_at\n"
        "setl_K4eBPTyLTnLCGr,1.91,processed,0.0,0.0,sample utr,2022-12-08T13:26:44\n"
    )
    p = _write(Path(tmp_dir()) / "rzp_settle.csv", csv)
    txns = load_settlement_csv(str(p), "razorpay_settlement_csv")
    assert len(txns) == 1
    assert txns[0].ref == "setl_K4eBPTyLTnLCGr"
    assert txns[0].amount == Decimal("1.91")
    assert txns[0].utr == "sample utr"
    assert txns[0].txn_date == date(2022, 12, 8)


def test_razorpay_recon_csv_parse():
    # 27 columns, verbatim from the official sample header (docs/SCHEMAS.md).
    # Build with DictWriter so column alignment cannot drift.
    import csv as _csv
    import io as _io
    fields = [
        "transaction_entity", "entity_id", "amount", "currency", "fee (exclusive tax)",
        "tax", "debit", "credit", "payment_method", "card_type", "issuer_name",
        "entity_created_at", "payment_captured_at", "payment_notes", "refund_notes",
        "arn", "entity_description", "order_id", "order_receipt", "order_notes",
        "dispute_id", "dispute_created_at", "dispute_reason", "settlement_id",
        "settled_at", "settlement_utr", "settled_by",
    ]
    row = dict.fromkeys(fields, "")
    row.update({
        "transaction_entity": "payment",
        "entity_id": "pay_JpAZjJN9O1lKuG",
        "amount": "1.0",
        "currency": "INR",
        "fee (exclusive tax)": "0.01",
        "tax": "0.0",
        "debit": "0.0",
        "credit": "0.99",
        "payment_method": "bank_transfer",
        "entity_created_at": "2022-06-07T13:33:57",
        "settlement_id": "setl_Jq0XZksg0i2Fat",
        "settled_at": "2022-06-07T13:33:57",
        "settlement_utr": "sample utr",
        "settled_by": "Razorpay",
    })
    buf = _io.StringIO()
    w = _csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    w.writerow(row)
    p = _write(Path(tmp_dir()) / "rzp_recon.csv", buf.getvalue())
    lines = load_vendor_recon_csv(str(p), "razorpay_recon_csv")
    assert len(lines) == 1
    l = lines[0]
    assert l.type == "payment"
    assert l.entity_id == "pay_JpAZjJN9O1lKuG"
    assert l.amount == Decimal("1.0")
    assert l.credit == Decimal("0.99")
    assert l.fee == Decimal("0.01")
    assert l.settlement_id == "setl_Jq0XZksg0i2Fat"
    assert l.settlement_utr == "sample utr"


def test_bank_statement_unknown_bank_raises():
    p = _write(Path(tmp_dir()) / "x.csv", "a,b,c\n1,2,3\n")
    try:
        load_bank_statement(str(p), "notabank")
        raise AssertionError("expected KeyError")
    except KeyError:
        pass


def test_settlement_csv_unverified_vendor_raises():
    p = _write(Path(tmp_dir()) / "payu.csv", "a,b,c\n1,2,3\n")
    try:
        load_settlement_csv(str(p), "payu_settlement_csv")
        raise AssertionError("expected ValueError (map not filled)")
    except ValueError:
        pass


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"all {len(fns)} checks passed")
