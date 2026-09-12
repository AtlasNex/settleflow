"""Self-check for the library. Run: python tests/test_matching.py"""
import contextlib
import csv
import io
import sys
import time
import tempfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# The thin SaaS layer's pure helpers. Imported here (not from a separate test
# file) so the repo keeps ONE runnable check — and with no third-party import, so
# this still runs on a machine where the [saas] extra was never installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "saas"))

from helpers import (  # noqa: E402
    decode_text,
    guess_columns,
    human_bytes,
    md_to_html,
    valid_email,
)

from settleflow import (
    CASHFREE_RECON_MARKER,
    MatchStatus,
    Txn,
    PdfEncryptedError,
    PdfLayoutError,
    PdfScannedError,
    build_llm_prompt,
    classify,
    export_gst_worksheet,
    export_tally_csv,
    export_tds_1035,
    extract_pdf_text,
    group_batches,
    load_bank_statement,
    load_cashfree_recon_report,
    load_juspay_settlement_csv,
    load_payu_json,
    load_phonepe_settlement_csv,
    load_settlement_csv,
    load_vendor_recon_csv,
    match,
    match_orders,
    match_settlements,
    parse_payu_settlement_range,
    parse_payu_transaction_details,
    parse_razorpay_recon,
    parse_razorpay_settlements,
    parse_sbi_statement,
    triage_exceptions,
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
    assert lines[0].created_at == datetime.fromtimestamp(1567692556, tz=timezone(timedelta(hours=5, minutes=30))).date()


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


def test_kotak_bankii_bank_statement_parse():
    # Kotak "bankii" variant B (ATL-90): separate Debit amount / Credit amount
    # columns + a Dr/Cr flag, date %d-%m-%Y. Schema transcribed from the real
    # parser jasimmk/bankii in_kotak.py (Serial|Transaction date|Value date|
    # Description|Chq / Ref No.|Debit amount|Credit amount|Balance|Dr/Cr), so
    # this tests parser LOGIC against a verified header — not a guessed schema.
    # load_bank_statement content-routes it (header "Debit amount"/"Credit
    # amount"), so the "kotak" key auto-handles a bankii export. Parse-from-realfile
    # verification is pending a real bankii fixture (D-7).
    csv = (
        "Serial,Transaction date,Value date,Description,Chq / Ref No.,Debit amount,Credit amount,Balance,Dr/Cr\n"
        "1,01-04-2026,01-04-2026,UPI PAYMENT,,99.00,,501.00,DR\n"
        "2,02-04-2026,02-04-2026,REFUND RECEIVED,,,199.00,700.00,CR\n"
    )
    p = _write(Path(tmp_dir()) / "kotak_bankii.csv", csv)
    txns = load_bank_statement(str(p), "kotak")
    assert len(txns) == 2
    assert txns[0].amount == Decimal("-99.00")  # DR -> debit
    assert txns[1].amount == Decimal("199.00")  # CR -> credit
    assert txns[0].utr is None or txns[0].utr == ""
    assert txns[0].ref == "UPI PAYMENT"


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


# ---- Phase 3.5: SBI bank-statement PDF parser (text layer, YONO layout) ----

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sbi"


def _fixture(name):
    return (_FIXTURES / name).read_text(encoding="utf-8")


def test_sbi_yono_multi_parse():
    txns = parse_sbi_statement(_fixture("yono_savings_multi_jan_2026.txt"))
    assert len(txns) == 2
    # APY debit -> negative
    assert txns[0].txn_date == date(2025, 12, 4)
    assert txns[0].amount == Decimal("-90.00")
    assert txns[0].utr is None
    assert "APY_DEC25" in txns[0].ref
    # interest credit -> positive
    assert txns[1].txn_date == date(2025, 12, 25)
    assert txns[1].amount == Decimal("3.00")
    assert txns[1].ref == "INTEREST CREDIT"


def test_sbi_yono_combined_parse():
    # two tables (loan account + savings account) in one statement -> 5 rows
    txns = parse_sbi_statement(_fixture("yono_savings_combined_sep_2025.txt"))
    assert len(txns) == 5
    amounts = [t.amount for t in txns]
    assert amounts == [
        Decimal("6829.00"),   # interest repayment (credit)
        Decimal("77171.00"),  # principal repayment (credit)
        Decimal("41000.00"),  # principal repayment (credit)
        Decimal("-5976.00"),  # interest (debit)
        Decimal("-90.00"),    # APY debit
    ]
    assert txns[0].txn_date == date(2025, 8, 1)
    assert txns[3].ref == "INTEREST"


def test_sbi_pdf_text_extraction_and_detection():
    # The PDF layer (extract_pdf_text) needs pymupdf; skip quietly if absent
    # so the stdlib-only self-check still passes without the optional dep.
    try:
        import pymupdf
    except ImportError:
        return

    # 1) a text PDF round-trips through extract_pdf_text
    text_pdf = Path(tmp_dir()) / "sbi_text.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Date Transaction Reference Balance")
    doc.save(str(text_pdf))
    doc.close()
    assert "Transaction Reference" in extract_pdf_text(str(text_pdf))

    # 2) a password-locked PDF is detected, not silently opened
    enc_pdf = Path(tmp_dir()) / "sbi_locked.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "secret statement")
    doc.save(str(enc_pdf), encryption=pymupdf.PDF_ENCRYPT_AES_256,
             owner_pw="pw", user_pw="pw")
    doc.close()
    try:
        extract_pdf_text(str(enc_pdf))
        raise AssertionError("expected PdfEncryptedError")
    except PdfEncryptedError:
        pass

    # 3) an image-only (no text layer) PDF is detected as scanned
    scan_pdf = Path(tmp_dir()) / "sbi_scanned.pdf"
    doc = pymupdf.open()
    doc.new_page()  # blank page -> no text layer
    doc.save(str(scan_pdf))
    doc.close()
    try:
        extract_pdf_text(str(scan_pdf))
        raise AssertionError("expected PdfScannedError")
    except PdfScannedError:
        pass


def test_kotak_drcr_statement_auto_detect():
    # Kotak netbanking: single combined amount column with Dr/Cr marker.
    # load_bank_statement auto-detects "(Dr)"/"(Cr)" and routes to the Dr/Cr
    # parser instead of the two-column map.
    p = Path(__file__).resolve().parent / "fixtures" / "kotak" / "kotak_savings-jul-2025.txt"
    txns = load_bank_statement(str(p), "kotak")
    assert len(txns) == 10
    assert txns[0].amount == Decimal("-347.00")     # UPI debit (Dr)
    assert txns[0].txn_date == date(2025, 7, 1)
    assert txns[1].amount == Decimal("35000.00")    # NEFT credit (Cr)
    # wrapped narration is preserved (interest credit on 18-Jul)
    assert txns[6].amount == Decimal("125.00")
    assert txns[6].ref == "NEFT/INWARD/CR-ICICI/INTEREST CREDIT SB-A/1234567890/INT JUL25"
    # totals reconcile with the statement's own sub-totals
    dr = sum((-t.amount for t in txns if t.amount < 0), Decimal("0"))
    cr = sum((t.amount for t in txns if t.amount > 0), Decimal("0"))
    assert dr == Decimal("10069.00")   # "Sub Total : 10,069.00 Dr"
    assert cr == Decimal("55125.00")   # "55,125.00 Cr"


def test_sbi_netbanking_parse():
    # legacy netbanking layout (dates split "dd MMM" / "yyyy yyyy" lines)
    txns = parse_sbi_statement(_fixture("netbanking_2021_22.txt"))
    assert len(txns) == 5
    amounts = [t.amount for t in txns]
    assert amounts == [
        Decimal("4000.00"),   # BY UPI -> credit
        Decimal("-2500.00"),  # TO UPI -> debit
        Decimal("-1000.00"),  # NEFT-OTH -> debit
        Decimal("5000.00"),   # BY TRANSFER-INB -> credit
        Decimal("-3000.00"),  # ATM WDL -> debit
    ]
    assert txns[0].txn_date == date(2021, 4, 1)
    assert txns[0].utr == "412345678901"


def test_sbi_credit_card_parse():
    txns = parse_sbi_statement(_fixture("sbi_credit-jan-2025.txt"))
    assert len(txns) == 8
    # purchases/fees are debit (negative); payments/refunds carry a "Cr" marker
    assert txns[0].amount == Decimal("-1234.56")
    assert txns[3].amount == Decimal("5000.00")     # PAYMENT RECEIVED ... Cr
    assert txns[3].txn_date == date(2025, 1, 8)
    assert txns[4].amount == Decimal("1234.56")     # REFUND ... Cr
    assert txns[7].amount == Decimal("-53.82")      # GST


def test_pnb_statement_parse():
    # collapsed Withdrawal/Deposit columns -> sign from running-balance arithmetic
    p = Path(__file__).resolve().parent / "fixtures" / "pnb" / "pnb_savings-may-2023.txt"
    txns = load_bank_statement(str(p), "pnb")
    assert len(txns) == 7
    amounts = [t.amount for t in txns]
    assert amounts == [
        Decimal("-25000.00"), Decimal("40000.00"), Decimal("-2000.00"),
        Decimal("59500.00"), Decimal("-8500.00"), Decimal("16200.00"),
        Decimal("-66700.00"),
    ]
    assert txns[1].utr == "N042718362538143"
    assert txns[2].utr == "426784531012"


def test_dbs_statement_parse():
    p = Path(__file__).resolve().parent / "fixtures" / "dbs" / "dbs_savings-may-2019.txt"
    txns = load_bank_statement(str(p), "dbs")
    assert len(txns) == 10
    # net movement = closing - opening = 27,995.89 - 3,435.89 = 24,560.00
    assert sum((t.amount for t in txns), Decimal("0")) == Decimal("24560.00")
    assert txns[2].amount == Decimal("20000.00")   # NEFT credit
    assert txns[7].amount == Decimal("-6200.00")   # ATM debit


def test_triage_exceptions():
    s = [t("U1", "100.00", 15)]
    b = [t("U1", "95.00", 16)]
    r = match(s, b)
    exc = classify(r, as_of=date(2026, 8, 20))
    seen = []
    out = triage_exceptions(exc, lambda p: seen.append(p) or "OK")
    assert out == "OK"
    assert seen and "FEE_DRIFT" in seen[0]
    assert triage_exceptions([], lambda p: "unused") == ""


def test_cli_reconcile_end_to_end():
    from settleflow.__main__ import main
    d = tmp_dir()
    sett = _write(Path(d) / "sett.csv",
        "id,amount,status,fees,tax,utr,created_at\n"
        "setl_1,3.00,processed,0.0,0.0,UTR1,2025-12-25T00:00:00\n"
        "setl_2,999.00,processed,0.0,0.0,UTR2,2025-12-26T00:00:00\n")
    bank = Path(__file__).resolve().parent / "fixtures" / "sbi" / "yono_savings_multi_jan_2026.txt"
    outdir = Path(d) / "cli-out"
    rc = main(["reconcile", "--settlements", str(sett), "--vendor", "razorpay_settlement_csv",
               "--bank", "sbi", "--statement", str(bank), "--out-dir", str(outdir)])
    assert rc == 0
    assert (outdir / "tally.csv").exists()
    assert "MATCHED" in (outdir / "tally.csv").read_text(encoding="utf-8")
    assert (outdir / "exceptions.csv").exists()


def test_ist_epoch_and_two_digit_month_name():
    from settleflow import parse_date
    from settleflow.parsers import _epoch_date
    # 2026-01-01 23:30 UTC == 2026-01-02 05:30 IST -> IST calendar date is the 2nd
    e = int(datetime(2026, 1, 1, 23, 30, tzinfo=timezone.utc).timestamp())
    assert _epoch_date(e) == date(2026, 1, 2), f"_epoch_date = {_epoch_date(e)}"
    # month-name with a 2-digit year parsed via the new %d-%b-%y format
    assert parse_date("01-Jul-25") == date(2025, 7, 1)


def test_cli_pdf_gating_non_sbi():
    from settleflow.__main__ import _load_statement
    import tempfile as _tf
    d = _tf.mkdtemp()
    p = Path(d) / "stmt.pdf"
    p.write_bytes(b"%PDF-1.4 fake")
    try:
        _load_statement(str(p), "hdfc")
        raise AssertionError("expected ValueError for non-SBI PDF")
    except ValueError as e:
        assert "only handles SBI" in str(e)


def test_ocr_scanned_sbi_pdf():
    # OCR is an optional extra; skip cleanly when tesseract or pymupdf is absent
    # so the suite stays green everywhere, but actually exercise it here.
    import shutil
    try:
        import pymupdf
    except ImportError:
        print("      (ocr) pymupdf absent — skipped")
        return
    tess_raw = shutil.which("tesseract")
    tess = Path(tess_raw) if tess_raw else Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if not tess.exists():
        print("      (ocr) tesseract absent — skipped")
        return
    from settleflow import parse_sbi_scanned_pdf
    d = tempfile.mkdtemp()
    body = ("Transaction Reference  Ref.No./Chq.No.  Credit  Debit  Balance\n"
            "01-04-2026  UPI PAYMENT  500.00  -  1000.00\n")
    src = pymupdf.open(); pg = src.new_page(width=800, height=600); y = 60
    for ln in body.splitlines():
        pg.insert_text((60, y), ln, fontsize=10); y += 22
    png = Path(d) / "p.png"; pg.get_pixmap(dpi=300).save(str(png)); src.close()
    out = pymupdf.open(); op = out.new_page(width=800, height=600)
    op.insert_image(op.rect, filename=str(png))
    scan = Path(d) / "scanned.pdf"; out.save(str(scan)); out.close()
    txns = parse_sbi_scanned_pdf(str(scan))
    assert any(t.amount == Decimal("500.00") and t.txn_date == date(2026, 4, 1) for t in txns), \
        f"OCR parse got {[(str(t.amount), t.txn_date) for t in txns]}"


# ---------------------------------------------------------------------------
# SaaS-layer helpers (saas/helpers.py)
#
# These decide what a user's uploaded file actually is. A wrong column mapping
# produces a confident, wrong reconciliation, so the guessing logic is worth a
# check of its own.
# ---------------------------------------------------------------------------

def test_saas_decode_text_is_total_and_bom_aware():
    # A BOM must be stripped, not left inside the first column name — a header
    # '\ufeffAmount' would defeat column detection on a perfectly good export.
    assert decode_text(b"\xef\xbb\xbfAmount") == "Amount"
    # cp1252 text with a byte UTF-8 cannot decode must not raise.
    assert decode_text(b"Merch\x80nt") == "Merch\u20acnt"
    # Real UTF-8 (rupee sign) round-trips.
    assert decode_text("\u20b91,00,000".encode("utf-8")) == "\u20b91,00,000"
    # Undecodable in every listed encoding still returns text rather than raising.
    assert isinstance(decode_text(b"header\n\xff\xfe\x00"), str)


def test_saas_guess_columns_prefers_exact_over_substring():
    # 'Value Date' must win for date even though 'Amount' also contains 'a'... and
    # critically, exact matches must be chosen before any substring pass runs.
    got = guess_columns(["Value Date", "Description", "Amount", "UTR No"])
    assert got == {"utr": "UTR No", "amount": "Amount", "date": "Value Date"}, got


def test_saas_guess_columns_ignores_short_substrings():
    # 'cr' (2 chars) appears inside 'Description'; without the min-length guard
    # the amount column would be silently mapped to a text field.
    got = guess_columns(["Description"])
    assert got["amount"] is None, got
    assert got["utr"] is None and got["date"] is None, got


def test_saas_guess_columns_returns_none_rather_than_guessing():
    got = guess_columns(["alpha", "beta", "gamma"])
    assert got == {"utr": None, "amount": None, "date": None}, got
    assert guess_columns([]) == {"utr": None, "amount": None, "date": None}


def test_saas_email_validation_is_strict_at_the_boundary():
    assert valid_email("  Sanjay@AtlasNex.com ") == "sanjay@atlasnex.com"
    for bad in ("nope", "a@b", "@b.co", "a@.co", "", "   ", "a b@c.co",
                ("x" * 260) + "@b.co"):
        assert valid_email(bad) is None, bad


def test_saas_md_to_html_escapes_before_converting():
    out = md_to_html("<script>alert(1)</script>")
    assert "<script>" not in out, out
    assert "&lt;script&gt;" in out, out
    # A link written in raw HTML must not survive as a live tag either.
    assert "<img" not in md_to_html('<img src=x onerror=alert(1)>')


def test_saas_md_to_html_renders_the_documented_subset():
    out = md_to_html(
        "# Title\n\n"
        "Text with **bold**, `code` and [a link](https://example.test/x).\n\n"
        "- one\n- two\n\n"
        "1. first\n"
    )
    assert "<h1>Title</h1>" in out, out
    assert "<strong>bold</strong>" in out and "<code>code</code>" in out, out
    assert '<a href="https://example.test/x" rel="noopener">a link</a>' in out, out
    assert "<ul>" in out and "<li>one</li>" in out and "</ul>" in out, out
    assert "<ol>" in out and "<li>first</li>" in out, out
    # Lists must be closed, or the legal pages nest every later paragraph.
    assert out.count("<ul>") == out.count("</ul>"), out
    assert out.count("<ol>") == out.count("</ol>"), out


def test_saas_human_bytes_reads_like_a_person_says_it():
    assert human_bytes(10) == "10 B"
    assert human_bytes(2048) == "2.0 KB"
    assert human_bytes(10 * 1024 * 1024) == "10.0 MB"


def test_phonepe_settlement_report_aggregates_per_bank_credit():
    # PhonePe's settlement report is one row per TRANSACTION; a bank credit is one
    # per settlement. Rows sharing a BankReferenceNo (the settlement UTR) must net
    # together (Amount + Fee + IGST + CGST + SGST) into a single Txn. Feeding the
    # per-row amounts to the matcher would try to match each transaction against one
    # bank credit — a wall of false unmatched rows, and the (amount, date) fallback
    # could pair the wrong ones outright.
    fixture = (Path(__file__).resolve().parent / "fixtures" / "phonepe"
               / "settlement_report_synthetic.csv")
    txns = load_phonepe_settlement_csv(str(fixture))

    # The fixture's last row has no BankReferenceNo: not settled to any credit yet,
    # so it must not produce a Txn.
    assert len(txns) == 2, [(t.utr, str(t.amount)) for t in txns]
    by_utr = {t.utr: t for t in txns}

    a = by_utr["AXNPNTESTUTR0001"]
    assert a.amount == Decimal("1284.90"), a.amount     # 989.93 + 494.97 - 200.00
    assert a.txn_date == date(2025, 10, 2), a.txn_date
    assert a.ref == "MREF-TEST-1001", a.ref

    b = by_utr["AXNPNTESTUTR0002"]
    assert b.amount == Decimal("1979.86"), b.amount     # 2000 - 14.80 - 2.66 - 1.34 - 1.34
    assert b.txn_date == date(2025, 10, 4), b.txn_date

    # And it must be reachable through the registered vendor name, not a special
    # case the caller has to know about.
    routed = load_settlement_csv(str(fixture), "phonepe_settlement_csv")
    assert [t.utr for t in routed] == [t.utr for t in txns]
    assert [t.amount for t in routed] == [t.amount for t in txns]


def test_phonepe_settlement_report_rejects_a_bad_date_loudly():
    # Trust boundary: a malformed date must raise naming the column and the
    # settlement, never coerce silently.
    import tempfile as _tf
    bad = ("PaymentType,MerchantReferenceId,PhonePeReferenceId,From,Instrument,"
           "Flow Type,CreationDate,TransactionDate,SettlementDate,BankReferenceNo,"
           "Amount,Fee,IGST,CGST,SGST\n"
           "PAYMENT,M1,P1,S,UPI_FULFILMENT,CREDIT,01-10-2025,01-10-2025,"
           "not-a-date,AXNPNTESTUTR0009,100.00,-1.00,0,0,0\n")
    with _tf.NamedTemporaryFile("w", suffix=".csv", delete=False,
                                encoding="utf-8") as fh:
        fh.write(bad)
        path = fh.name
    try:
        load_phonepe_settlement_csv(path)
        raise AssertionError("a malformed SettlementDate was accepted")
    except ValueError as exc:
        assert "SettlementDate" in str(exc), exc
        assert "AXNPNTESTUTR0009" in str(exc), exc
    finally:
        Path(path).unlink(missing_ok=True)


@contextlib.contextmanager
def _temp_text(text, suffix=".csv"):
    """Write text to a temp file for a trust-boundary check; always cleaned up."""
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False,
                                     encoding="utf-8", newline="") as fh:
        fh.write(text)
        path = fh.name
    try:
        yield path
    finally:
        Path(path).unlink(missing_ok=True)


@contextlib.contextmanager
def _temp_assert(failure_message):
    """Fail the check unless the wrapped block raises ValueError."""
    try:
        yield
    except ValueError:
        return
    raise AssertionError(failure_message)


# ---- Cashfree Settlement Recon (two reports in one file) ----

_CF_RECON_FIXTURE = (Path(__file__).resolve().parent / "fixtures" / "cashfree"
                     / "settlement_recon_synthetic.csv")


def _cf_two_section(batch_rows: str, event_rows: str) -> str:
    """A minimal Cashfree recon file: batch header, marker, event header."""
    return (
        "Id,UTR No.,Net Settlement Amount,Settlement Date\n"
        f"{batch_rows}"
        f"{CASHFREE_RECON_MARKER}\n"
        "Event Id,Event Type,Sale Type,Event Amount,Event Settlement Amount,"
        "Event Time,UTR,Merchant Reference Id\n"
        f"{event_rows}"
    )


def test_cashfree_recon_report_reads_both_sections_and_they_reconcile():
    # The report is two reports concatenated: 14-column settlement batches, a
    # marker line, then 63-column per-event rows. Both sections are asserted,
    # and the assertion that matters is the last one: netting the event section
    # (the `Sale Type` flag applied to `Event Settlement Amount`, which Cashfree
    # prints NEGATIVE on a refund) must reproduce the batch section's Net
    # Settlement Amount total. Applying the flag to the gross `Event Amount`
    # instead — the obvious first implementation — fails exactly here, because
    # then the fee on every payment is lost.
    batches, lines = load_cashfree_recon_report(str(_CF_RECON_FIXTURE))

    assert len(batches) == 2, [(t.utr, str(t.amount)) for t in batches]
    first, second = batches
    assert first.utr == "AXNCFTESTUTR0001", first.utr
    assert first.amount == Decimal("4890.56"), first.amount
    assert first.txn_date == date(2025, 10, 13), first.txn_date
    assert first.ref == "SETTLETEST001", first.ref
    assert second.utr == "AXNCFTESTUTR0002", second.utr
    assert second.amount == Decimal("990.56"), second.amount
    assert second.txn_date == date(2025, 10, 14), second.txn_date

    assert len(lines) == 3, [(l.entity_id, l.type) for l in lines]
    payment, refund, other = lines
    assert payment.type == "payment" and payment.entity_id == "EVT-TEST-0001", payment
    assert payment.credit == Decimal("4990.56"), payment.credit   # net of fee/tax
    assert payment.debit == Decimal("0"), payment.debit
    assert payment.amount == Decimal("5000.00"), payment.amount   # gross stays gross
    assert payment.fee == Decimal("8.00"), payment.fee
    assert payment.tax == Decimal("1.44"), payment.tax
    assert payment.currency == "INR", payment.currency
    assert payment.created_at == date(2025, 10, 12), payment.created_at
    assert payment.order_id == "ORDER-TEST-1001", payment.order_id
    assert payment.settlement_utr == "AXNCFTESTUTR0001", payment.settlement_utr
    assert refund.type == "refund", refund.type
    assert refund.debit == Decimal("100.00"), refund.debit         # magnitude, not -100
    assert refund.net == Decimal("-100.00"), refund.net
    assert other.settlement_id == "AXNCFTESTUTR0002", other.settlement_id

    line_total = sum((x.net for x in lines), Decimal("0"))
    batch_total = sum((b.amount for b in batches), Decimal("0"))
    assert line_total == batch_total == Decimal("5881.12"), (line_total, batch_total)


def test_cashfree_recon_report_refuses_a_file_without_the_marker():
    # Trust boundary: the two sections have different column maps, so without the
    # marker there is no way to know which one a file is. It must raise rather
    # than read the file as whichever section it resembles.
    with _temp_text("Id,Total Transaction Amount\nSETTLETEST001,10.00\n") as path:
        try:
            load_cashfree_recon_report(path)
            raise AssertionError("a file with no section marker was accepted")
        except ValueError as exc:
            assert "Settlement Reconciliation Details" in str(exc), exc


def test_cashfree_recon_rejects_an_unknown_sale_type():
    # Sale Type decides which side money lands on, so an unrecognised value must
    # raise instead of being defaulted to one side: a guessed sign flips the
    # direction of a real refund, which is worse than a loud failure.
    raw = _cf_two_section(
        "SETTLETEST001,AXNCFTESTUTR0001,10.00,2025-10-13\n",
        "EVT-TEST-1,PAYMENT,SIDEways,10.00,9.80,2025-10-12 10:00:00,"
        "AXNCFTESTUTR0001,ORDER-TEST-1\n",
    )
    with _temp_text(raw) as path:
        try:
            load_cashfree_recon_report(path)
            raise AssertionError("an unknown Sale Type was accepted")
        except ValueError as exc:
            assert "SIDEways" in str(exc) and "CREDIT or DEBIT" in str(exc), exc


# ---- PayU settlement APIs (no CSV exists: the export's columns are picked in ----
# ---- the dashboard, so these two documented APIs are the integration surface) ----


def test_payu_settlement_range_reads_utr_level_rows():
    # Money arrives as rupee STRINGS here, and the row that reconciles against a
    # bank credit is the UTR-level one: settlementAmount is the net that lands in
    # the bank and utrNumber is the bank reference.
    raw = load_payu_json(str(Path(__file__).resolve().parent / "fixtures" / "payu"
                            / "settlement_range_synthetic.json"))
    rows = parse_payu_settlement_range(raw)

    assert len(rows) == 2, [r.settlement_id for r in rows]
    first, second = rows
    assert first.settlement_id == "SETTLETEST20251013001", first.settlement_id
    assert first.utr == "TESTUTR0000000001", first.utr
    assert first.amount == Decimal("4890.56"), first.amount
    assert first.created_at == date(2025, 10, 13), first.created_at
    assert first.fees == Decimal("8.00"), first.fees    # 0.0 service + 8.00 additional
    assert first.tax == Decimal("1.44"), first.tax      # 0.0 service + 1.44 additional
    assert second.utr == "TESTUTR0000000002", second.utr
    # This row has the fees in the non-"additional" pair instead; both pairs are
    # summed, so the total is the same shape either way.
    assert second.fees == Decimal("8.00") and second.tax == Decimal("1.44"), second
    assert isinstance(first.amount, Decimal), type(first.amount)


def test_payu_settlement_range_matches_a_bank_credit_on_the_utr():
    # The point of the UTR-level API: these rows reach match() at level 1 (exact
    # UTR), not through the amount+date fallback that can pair the wrong rows.
    raw = load_payu_json(str(Path(__file__).resolve().parent / "fixtures" / "payu"
                            / "settlement_range_synthetic.json"))
    settlements = parse_payu_settlement_range(raw)
    settlement_txns = [
        Txn(utr=s.utr, amount=s.amount, txn_date=s.created_at) for s in settlements
    ]
    bank = [
        Txn(utr="TESTUTR0000000001", amount=Decimal("4890.56"),
            txn_date=date(2025, 10, 13)),
        Txn(utr="TESTUTR0000000002", amount=Decimal("990.56"),
            txn_date=date(2025, 10, 14)),
    ]

    result = match(settlement_txns, bank)
    assert len(result.matched) == 2, (len(result.matched), result.settlement_only)
    assert all(m.status is MatchStatus.EXACT for m in result.matched), result.matched
    assert not result.settlement_only and not result.bank_only


def test_payu_settlement_range_fails_closed_on_a_failure_envelope():
    # PayU answers with status 1 and a message; a parser that read result as data
    # would report an empty run (or crash later) instead of the real reason.
    with _temp_assert("status=1 envelope accepted"):
        parse_payu_settlement_range(
            {"status": 1, "message": "Unauthorized: Invalid signature", "result": None}
        )


def test_payu_settlement_range_refuses_an_unknown_field():
    # D-7 in API form: PayU adding a field is a schema change, and quietly
    # ignoring it is how a reconciler starts reporting wrong numbers after a
    # vendor release. The documented field set is closed.
    payload = {
        "status": 0,
        "result": {"page": 1, "size": 1, "totalCount": 1, "data": [{
            "settlementId": "S1",
            "settlementCompletedDate": "2025-10-13 02:51:22.000000",
            "settlementAmount": "10.00",
            "utrNumber": "TESTUTR0000000009",
            "newUndocumentedField": "surprise",
        }]},
    }
    with _temp_assert("an unknown PayU field was accepted"):
        parse_payu_settlement_range(payload)


def test_payu_transaction_details_signs_refunds_and_maps_status():
    # settlementAmount is SIGNED here (refunds and chargebacks are negative) and
    # the sign has to survive into debit/credit, or every refund reads as income.
    # This endpoint also carries no currency field, and an unsettled transaction
    # may have no UTR yet.
    raw = load_payu_json(str(Path(__file__).resolve().parent / "fixtures" / "payu"
                            / "transaction_details_synthetic.json"))
    lines = parse_payu_transaction_details(raw)

    assert len(lines) == 3, [(l.entity_id, l.type) for l in lines]
    capture, refund, chargeback = lines
    assert capture.type == "capture" and capture.credit == Decimal("990.56"), capture
    assert capture.debit == Decimal("0"), capture.debit
    assert capture.settled is True and capture.on_hold is False, capture
    assert capture.settlement_utr == "TESTUTR0000000001", capture.settlement_utr
    assert capture.currency == "INR", capture.currency
    assert capture.created_at == date(2025, 10, 13), capture.created_at
    assert refund.debit == Decimal("990.56") and refund.credit == Decimal("0"), refund
    assert refund.net == Decimal("-990.56"), refund.net
    assert chargeback.on_hold is True and chargeback.settled is False, chargeback
    assert chargeback.settlement_utr is None, chargeback.settlement_utr
    assert chargeback.amount == Decimal("50.0"), chargeback.amount


def test_payu_transaction_details_requires_the_documented_keys():
    with _temp_assert("a PayU transaction row missing its id was accepted"):
        parse_payu_transaction_details({
            "status": 0,
            "result": [{"transactionType": "capture", "settlementAmount": 8.0}],
        })


# ---- Juspay settlement file (wired with its limits stated) ----


def test_juspay_settlement_nets_per_bank_credit_both_variants():
    # Juspay's file is per TRANSACTION (like PhonePe's), so rows must net into
    # one Txn per bank credit before match() sees them. Both real shapes are
    # covered: the documented 25-column schema, which has separate Credit/Debit
    # columns and NO bank-UTR column, and the variant Juspay's own production
    # parser reads, which carries UTR Number.
    base = Path(__file__).resolve().parent / "fixtures" / "juspay"

    documented = load_juspay_settlement_csv(
        str(base / "settlement_docs_schema_synthetic.csv")
    )
    # Grouped by Settlement Date: 997.64 + 498.82 - 199.53. The Pending row on
    # the 13th is skipped (no funds at the bank yet), so no second Txn appears.
    assert len(documented) == 1, [(t.utr, str(t.amount)) for t in documented]
    only = documented[0]
    assert only.utr is None, only.utr          # the documented schema has no UTR
    assert only.amount == Decimal("1296.93"), only.amount
    assert only.txn_date == date(2025, 10, 12), only.txn_date
    assert only.ref == "ORDER-TEST-1001", only.ref

    variant = load_juspay_settlement_csv(
        str(base / "settlement_utr_variant_synthetic.csv")
    )
    # Grouped by UTR Number: 997.64 - 100.00. The row with no UTR and the Pending
    # row both drop out.
    assert len(variant) == 1, [(t.utr, str(t.amount)) for t in variant]
    v = variant[0]
    assert v.utr == "TESTUTR0000000011", v.utr
    assert v.amount == Decimal("897.64"), v.amount
    assert v.txn_date == date(2025, 10, 12), v.txn_date


def test_juspay_settlement_reads_a_partner_amount_file():
    # A variant with no Credit/Debit pair: Partner Amount is the money movement.
    # Refusing this file ("unknown variant") would be defensible, silently
    # summing the wrong column would not — so it is parsed and asserted.
    header = "Merchant ID,Partner Amount,Settlement Date,Order ID,Settlement Status\n"
    rows = ("MERCHANT-TEST,100.00,12/10/2025,ORDER-TEST-1,Settled\n"
            "MERCHANT-TEST,50.00,12/10/2025,ORDER-TEST-2,Settled\n")
    with _temp_text(header + rows) as path:
        txns = load_juspay_settlement_csv(path)
    assert len(txns) == 1, [(t.utr, str(t.amount)) for t in txns]
    assert txns[0].amount == Decimal("150.00"), txns[0].amount
    assert txns[0].utr is None, txns[0].utr
    assert txns[0].txn_date == date(2025, 10, 12), txns[0].txn_date


def test_juspay_settlement_refuses_an_unknown_status():
    # Only "Settled" means the funds reached the bank. A status Juspay adds later
    # must not be silently included or silently dropped, so an unrecognised value
    # raises with the file's own vocabulary named.
    header = ("Merchant ID,Credit,Debit,Settlement Date,Settlement Status\n")
    rows = "MERCHANT-TEST,100.00,0.00,12/10/2025,Partially Settled\n"
    with _temp_text(header + rows) as path:
        try:
            load_juspay_settlement_csv(path)
            raise AssertionError("an unknown Settlement Status was accepted")
        except ValueError as exc:
            assert "Partially Settled" in str(exc), exc


# ---- v2 review remediation: money, shapes, JSON-as-CSV, exports, linearity ----

def test_parse_amount_is_strict_at_the_boundary():
    # The tolerant version stripped "Rs" before its dot, so 'Rs.100' became '.100' —
    # a 1000x understatement with no error — and whatever Decimal() accepted came
    # through, including non-finite values that later crash the exports' quantize().
    from settleflow import parse_amount

    # must parse, with the RIGHT value
    assert parse_amount("Rs.100") == Decimal("100"), parse_amount("Rs.100")
    assert parse_amount("Rs.250") == Decimal("250"), parse_amount("Rs.250")
    assert parse_amount("Rs.100.00") == Decimal("100.00")
    assert parse_amount("Rs 100.00") == Decimal("100.00")
    assert parse_amount("INR 100.00") == Decimal("100.00")
    assert parse_amount("₹100.00") == Decimal("100.00")
    assert parse_amount("1,23,456.78") == Decimal("123456.78")
    assert parse_amount("(100.00)") == Decimal("-100.00")   # accounting negative
    assert parse_amount("+25.00") == Decimal("25.00")
    assert parse_amount("  100.00  ") == Decimal("100.00")

    # must refuse rather than reinterpret
    for bad in ("NaN", "Infinity", "-Infinity", "1_000", "\u0661\u0662\u0663",
                "1e400", "1E+400", "", "abc", "100.00 Cr"):
        try:
            got = parse_amount(bad)
        except ValueError:
            continue
        raise AssertionError(f"parse_amount({bad!r}) should have raised, returned {got!r}")

    # an absurd magnitude is refused, because quantize() would raise later and the
    # user would see a 500 for what is really a bad file
    try:
        parse_amount("999999999999999999999999")
        raise AssertionError("an out-of-range amount was accepted")
    except ValueError:
        pass


def test_paise_refuses_non_finite_and_absurd():
    from settleflow.parsers import _paise
    assert _paise(19100) == Decimal("191")
    assert _paise("191.9") == Decimal("1.919")          # exact, no float noise
    assert _paise(-9900.5) == Decimal("-99.005")
    for bad in (float("inf"), float("-inf"), float("nan"), "Infinity", "NaN", 1e400):
        try:
            got = _paise(bad)
        except ValueError:
            continue
        raise AssertionError(f"_paise({bad!r}) should have raised, returned {got!r}")
    # a lossy float is refused with a message that points at the real cause
    try:
        _paise(191.9)
        raise AssertionError("a float amount was accepted")
    except ValueError as exc:
        assert "decimal places" in str(exc), exc


def test_parse_razorpay_settlements_fails_closed_on_shape():
    # These shapes used to raise AttributeError/KeyError, which the hosted layer
    # correctly refused to label "user error" and turned into a 500. A wrong-shaped
    # file is the caller's, so it must be a ValueError like the recon parser's.
    from settleflow import parse_razorpay_settlements
    for payload in ([1, 2, 3],                                # top-level list
                    {"items": {"a": 1}},                      # items is an object
                    {"items": [1, 2]},                        # entry is not an object
                    {"items": [{"entity": "settlement", "amount": 1, "created_at": 1}]},
                    {"items": [{"entity": "settlement", "id": "x", "created_at": 1}]}):
        try:
            parse_razorpay_settlements(payload)
            raise AssertionError(f"payload accepted: {payload!r}")
        except ValueError:
            continue
    # and the happy path still works
    rows = parse_razorpay_settlements({"items": [
        {"entity": "settlement", "id": "s1", "amount": 9900, "created_at": 1756944000}]})
    assert len(rows) == 1 and rows[0].amount == Decimal("99"), rows


def test_load_csv_refuses_a_json_payload():
    # A JSON payload read as CSV is ONE header field and zero data rows, so the
    # caller got an empty result instead of an error — and an empty reconciliation
    # looks exactly like a clean one.
    from settleflow import load_csv
    with _temp_text('{"items": [{"entity": "settlement"}]}') as path:
        try:
            load_csv(path, "utr", "amount", "date")
            raise AssertionError("a JSON payload was accepted as CSV")
        except ValueError as exc:
            assert "JSON" in str(exc), exc
    # a real CSV still loads
    with _temp_text("utr,amount,date\nUTR1,10.00,2025-09-04\n") as path:
        rows = load_csv(path, "utr", "amount", "date")
    assert len(rows) == 1 and rows[0].amount == Decimal("10.00"), rows


def test_exports_are_consistent_and_defuse_formulas():
    from settleflow import format_money, export_tally_csv
    # one formatter for page and CSV: a raw Decimal drops trailing zeros
    assert format_money(Decimal("100")) == "100.00"
    assert format_money(Decimal("99.5")) == "99.50"

    evil = '=HYPERLINK("http://evil.example/x","click")'
    result = match([t("UTRX1", "100.00", 5, evil)], [t("UTRX1", "100.00", 5)])
    csv_text = export_tally_csv(result)
    # Assert on the PARSED cell, not a raw substring: csv.writer doubles the inner
    # quotes, so the literal text never appears verbatim in the file.
    cells = [row for row in csv.reader(io.StringIO(csv_text))][1:]
    assert cells and cells[0][1] == "'" + evil, cells
    assert all(cell != evil for row in cells for cell in row), "an undefused cell survived"

    # a hyphen-leading reference is ordinary data and must NOT be rewritten
    ok = match([t("UTRX2", "100.00", 5, "-INST-2025-0142")], [t("UTRX2", "100.00", 5)])
    assert "-INST-2025-0142" in export_tally_csv(ok)


def test_cli_refuses_a_json_settlement_file():
    # What the CLI did before: read it as CSV, find nothing, print "settlements : 0"
    # and exit 0 — a confident, empty, wrong answer.
    from settleflow.__main__ import main
    d = Path(tmp_dir()) / "cli-json"
    d.mkdir(parents=True, exist_ok=True)
    sett = _write(d / "set.json", '{"items": [{"entity": "settlement", "id": "s1",'
                                  ' "amount": 9900, "created_at": 1756944000}]}\n')
    bank = _write(d / "bank.csv", "UTR,Amount,Date\nUTR1,99.00,2025-09-04\n")
    outdir = d / "out"
    rc = main(["reconcile", "--settlements", str(sett), "--vendor",
               "razorpay_settlement_csv", "--bank", "hdfc", "--statement", str(bank),
               "--out-dir", str(outdir)])
    assert rc == 2, f"expected a refusal (exit 2), got {rc}"
    assert not (outdir / "tally.csv").exists(), "a refused run still wrote a workpaper"


def test_cli_csv_output_is_well_formed_and_aligned():
    # Two Windows/CSV defects in one place: a narration containing a comma used to
    # shift every later column, and text-mode writes doubled the csv module's CRLF.
    from settleflow.__main__ import main
    d = Path(tmp_dir()) / "cli-csv"
    d.mkdir(parents=True, exist_ok=True)
    sett = _write(d / "set.csv", "utr,amount,created_at,id\n")     # nothing to match
    bank = _write(d / "bank.csv",
                  "Date,Withdrawal Amt.,Deposit Amt.,Chq./Ref.No.,Narration\n"
                  '01/09/2025,,10.00,REF9,"NEFT CR ACME, PVT LTD"\n')
    outdir = d / "out"
    rc = main(["reconcile", "--settlements", str(sett), "--vendor",
               "razorpay_settlement_csv", "--bank", "hdfc", "--statement", str(bank),
               "--out-dir", str(outdir)])
    assert rc == 0, rc

    raw = (outdir / "exceptions.csv").read_bytes()
    assert b"\r\r\n" not in raw, f"double carriage return in exceptions.csv: {raw!r}"
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8"))))
    widths = {len(r) for r in rows}
    assert widths == {5}, f"exceptions.csv rows have mismatched widths: {rows}"

    tally = (outdir / "tally.csv").read_bytes()
    assert b"\r\r\n" not in tally, f"double carriage return in tally.csv: {tally!r}"


def test_match_is_linear_when_many_rows_share_one_utr():
    # One RRN paying out a whole batch is a real shape, and the old implementation
    # rescanned the candidate list per settlement, so it went quadratic: measured
    # 0.011s / 0.066s / 0.161s / 0.655s at 1k / 2k / 4k / 8k. This bound is a
    # regression detector, so it is deliberately loose — 40k under the old code
    # extrapolates to ~16s, while the linear version does it in well under a second
    # even on a slow CI runner.
    n = 40000
    settlements = [t("SAMEUTR", "1.00", 5) for _ in range(n)]
    bank = [t("SAMEUTR", "1.00", 5) for _ in range(n)]

    started = time.monotonic()
    result = match(settlements, bank)
    elapsed = time.monotonic() - started

    assert len(result.matched) == n, len(result.matched)
    assert not result.settlement_only and not result.bank_only
    assert elapsed < 5.0, (
        f"match() took {elapsed:.1f}s for {n} rows sharing one UTR — the quadratic "
        "rescan is back (it should be linear)"
    )

    # the same-amount preference still holds when amounts differ under one UTR
    mixed = match([t("M", "10.00", 5), t("M", "20.00", 5)],
                  [t("M", "20.00", 5), t("M", "10.00", 5)])
    assert all(m.status is MatchStatus.EXACT for m in mixed.matched), mixed.matched


def test_pick_client_ip_trusts_only_the_cloudflare_header():
    # The hosted rate limit keyed on the first X-Forwarded-For hop, which the CALLER
    # writes, so 70 requests claiming 70 addresses each got a fresh bucket (70
    # accepted, 0 rejected). The socket peer is not usable either: uvicorn rewrites
    # scope["client"] from X-Forwarded-For when the connection arrives from a trusted
    # proxy, and the tunnel arrives from loopback — so the peer is just as spoofable.
    # Only the Cloudflare header counts; anything else shares ONE bucket, so no
    # caller can mint a new bucket per request.
    from helpers import UNIDENTIFIED_CLIENT, pick_client_ip

    # a caller-supplied X-Forwarded-For is ignored entirely
    assert pick_client_ip({"x-forwarded-for": "1.2.3.4"}) == UNIDENTIFIED_CLIENT
    assert pick_client_ip({"x-forwarded-for": "1.2.3.4", "cf-connecting-ip": "9.9.9.9"}) == "9.9.9.9"
    # the trusted header wins when present and valid, case-insensitively
    assert pick_client_ip(
        {"cf-connecting-ip": "203.0.113.7", "x-forwarded-for": "1.2.3.4"}) == "203.0.113.7"
    assert pick_client_ip({"CF-Connecting-IP": "203.0.113.8, 10.0.0.1"}) == "203.0.113.8"
    assert pick_client_ip({"cf-connecting-ip": "2001:db8::1"}) == "2001:db8::1"
    # rubbish in the trusted header cannot mint buckets either
    assert pick_client_ip({"cf-connecting-ip": "not-an-ip"}) == UNIDENTIFIED_CLIENT
    assert pick_client_ip({"cf-connecting-ip": ""}) == UNIDENTIFIED_CLIENT
    assert pick_client_ip({}) == UNIDENTIFIED_CLIENT
    # distinct legitimate clients still get distinct buckets
    assert pick_client_ip({"cf-connecting-ip": "203.0.113.1"}) != \
        pick_client_ip({"cf-connecting-ip": "203.0.113.2"})
    # (peer=None above: legacy helpers callers) --- now the peer-aware rule.
    # Peer is an intermediary (loopback / the docker bridge gateway): the edge-set
    # trusted header is the identity, canonicalized so one IPv6 address has ONE
    # bucket across its textual spellings (vuln-0002).
    from helpers import _is_intermediary_peer, pick_client_ip as _pcip
    assert _is_intermediary_peer("127.0.0.1")
    assert _is_intermediary_peer("172.17.0.1")   # docker bridge gateway
    assert _is_intermediary_peer("10.0.0.5")
    assert _is_intermediary_peer("::1")
    assert not _is_intermediary_peer("8.8.8.8")   # genuinely public peer
    assert not _is_intermediary_peer(None)
    assert not _is_intermediary_peer("not-an-ip")
    assert _pcip({"cf-connecting-ip": "203.0.113.7"}, "127.0.0.1") == "203.0.113.7"
    assert _pcip({"cf-connecting-ip": "203.0.113.7"}, "172.17.0.1") == "203.0.113.7"
    assert _pcip({"cf-connecting-ip": "::0001"}, "::1") == "::1"
    for spelling in ("0:0:0:0:0:0:0:1", "0000:0000:0000:0000:0000:0000:0000:0001",
                     "::0001", "0::1"):
        assert _pcip({"cf-connecting-ip": spelling}, "127.0.0.1") == "::1"
    # Peer is public: the caller reached the origin WITHOUT the tunnel, so it chose
    # its own headers — it is keyed on its peer, and CCI cannot mint it a bucket.
    assert _pcip({"cf-connecting-ip": "198.51.100.1"}, "8.8.8.8") == "8.8.8.8"
    assert _pcip({"cf-connecting-ip": "198.51.100.2"}, "8.8.8.8") == "8.8.8.8"
    assert _pcip({}, "8.8.8.8") == "8.8.8.8"
    assert _pcip({}, "not-an-ip") == UNIDENTIFIED_CLIENT
    # a public peer with an invalid CCI still gets its own (single) identity
    assert _pcip({"cf-connecting-ip": "junk"}, "8.8.8.8") == "8.8.8.8"


def test_request_size_guard_only_refuses_a_declared_oversize():
    # The 10MB file cap bounded the two FILES the app parses but not the request:
    # extra multipart parts rode through (a 210MB request was accepted with a 303).
    from helpers import max_request_bytes, request_too_large

    limit = max_request_bytes(10 * 1024 * 1024)
    assert limit > 10 * 1024 * 1024, limit          # file cap plus framing slack
    assert request_too_large(str(limit + 1), limit) is True
    assert request_too_large(str(limit), limit) is False
    # no declared length is NOT "large": a chunked request declares nothing, and the
    # streaming guard covers it. Refusing here would reject legitimate uploads.
    assert request_too_large(None, limit) is False
    assert request_too_large("not-a-number", limit) is False
    assert request_too_large("", limit) is False


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"all {len(fns)} checks passed")
