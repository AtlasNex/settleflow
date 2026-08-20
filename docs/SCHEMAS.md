# Verified schemas (Phase 3)

Every column map in `settleflow/schemas.py` traces here: the verbatim header
row, the money unit, the date format, and the source. D-7: nothing below is
invented. Sources are official sample files, official docs pages, or
open-source parsers that read that exact vendor's real export. Cross-check
`docs/DECISIONS.md` D-16/D-19 for the policy.

## Gateways

### Razorpay — Settlements report (wired)

- Header (7 cols): `id, amount, status, fees, tax, utr, created_at`
- Money unit: sample file shows decimal rupees (1.91); the API is paise. CSV
  parser follows the sample (rupees).
- Date: `YYYY-MM-DDTHH:MM:SS` (sample).
- Source: official sample `razorpay.com/docs/build/browser/assets/images/sample-settlements-report.xlsx`
  (linked from the "List of Reports" docs page).

### Razorpay — Settlement Recon report (wired)

- Header (27 cols): `transaction_entity, entity_id, amount, currency, fee (exclusive tax), tax, debit, credit, payment_method, card_type, issuer_name, entity_created_at, payment_captured_at, payment_notes, refund_notes, arn, entity_description, order_id, order_receipt, order_notes, dispute_id, dispute_created_at, dispute_reason, settlement_id, settled_at, settlement_utr, settled_by`
- Money unit: sample shows decimal rupees (1.0, 0.01, 0.99); API JSON is paise.
- Date: mixed `YYYY-MM-DDTHH:MM:SS` and `DD/MM/YYYY HH:MM:SS` — parser must accept both.
- Note: header differs from the recon API keys (`transaction_entity`, `settled_by`,
  `arn`, `payment_notes` don't exist in the API JSON).
- Source: official sample `razorpay.com/docs/build/browser/assets/images/sample-settlements-recon-report.xlsx`.

### Cashfree — Settlement Recon report (NOT wired — two-section file)

- Settlements section (14 cols): `ID, Total Transaction Amount, Settlement Amount, Adjustment, Net Settlement Amount, From, Till, Status, UTR No., Settlement Date, Settlement Type, Settlement Charge, Settlement Tax, Remarks`
- Transaction details section (48 cols): `Event ID, Event Type, Sale Type, Event Currency, Event Time, Processed On, Status, Event Amount, Event Settlement Amount, Settlement Date, UTR, Refund Type, Refund ARN, Adjustment Remarks, Merchant Reference ID, Customer Reference ID, Cashfree Reference ID, Customer Name, Customer Phone, Customer Email, Currency, Transaction Amount, Transaction Service Charge, Txn ST/GST, Net Settlement Amount, Transaction Time, Payment Mode, Bank Name, Auth ID, Card Type (Scheme), Vendor ID 1..5, Vendor Amount 1..5, Key_1, Value_1, Key_2, Value_2, Key_3, Value_3, Order Amount, Payment Mode SubType`
- Money unit: rupees (2 decimals).
- Date: `YYYY-MM-DD HH:MM:SS`.
- Why not wired: one file has two different header sections; needs a dedicated
  two-section parser, not a flat column map.
- Source: `cashfree.com/docs/partners/embedded/reports/settlement-recon-reports`.
- Public API alternative: settlement-reconciliation API JSON (`event_id, event_type, event_amount, event_settlement_amount, ...`).

### PayU — settlement export (NOT public)

- The export lets the merchant pick columns (no fixed header). Public instead:
  `get_settlement_details` API JSON (`txnid, transaction_amount, payu_fee, payu_fee_tax, net_amount, settlementId, settlementUTR, ...`), rupees, `YYYY-MM-DD HH:MM:SS`.
- Source: `docs.payu.in/docs/export-the-settlement-records`, `docs.payu.in/reference/settlement-details`.

### PhonePe — settlement report (verified fields, NOT wired)

- 14 fields: `PaymentType, MerchantReferenceId, PhonePeReferenceId, From, Instrument, CreationDate, Amount, Fee, TransactionDate, SettlementDate, BankReferenceNo, IGST, CGST, SGST`
- Money: rupees (two decimals); fee and taxes are negative-valued;
  `Settled amount = Amount + Fee + IGST + CGST + SGST`.
- Why not wired: `PaymentType` values undocumented, date format undocumented →
  resolve against a real file before building the parser.
- Source: `developer.phonepe.com/docs/settlements`.

### Juspay — settlement file (verified schema, NOT wired)

- 25 cols: `Merchant ID, Transaction Amount, Fee, Tax, Credit, Debit, Settlement Date, UPI Request Id, Transaction Type, Type, SS Adjustment Type, SS Credit/Debit, Transaction Date, Account Number, Status, Payer Vpa, Payee Vpa, RRN, Settlement Status, Order ID, Transaction Description, Account Type, Sub Merchant ID, Refund Request Id, MCC`
- Money: datatype "Integer"; paise vs rupees not stated → unverified → resolve
  against a real file before wiring.
- Date: `dd/mm/yyyy`.
- Source: `juspay.io/pe/docs/upi-merchant-stack-pe/docs/resources/settlement-files`.

## Bank statements (wired)

All: INR, plain decimal, no ₹ symbol. Two-column debit/credit, one populated
per row. Header may sit below preamble rows — the loader detects it by matching
the date+debit+credit names (HDFC ~2-3 rows, Axis ~row 20).

| Bank | Header (verbatim) | Date format | Sources |
|---|---|---|---|
| HDFC | `Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance` | `dd/mm/yy` (some `dd/mm/yyyy`) | RajaBabu15/stmt `fixtures/hdfc_csv.csv`; pratik1235/burnrate; kamthamc/wealth-wise; suryanshsrivastava/fipro |
| SBI | `Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance` | `dd/mm/yyyy` or `dd MMM yyyy` | Jayeshecs/money-insight `sbi_savings.rs`+fixture; RajaBabu15/stmt `fixtures/sbi_csv.csv` |
| ICICI | `S No., Value Date, Transaction Date, Cheque Number, Transaction Remarks, Withdrawal Amount(INR), Deposit Amount(INR), Balance(INR)` | `dd-MMM-yyyy` or `dd/mm/yyyy` | khanfarhan10/bank-ledger-dashboard `icici_excel_parser.py`; burnrate; sandy-ms/financebot |
| Axis | `Tran Date, CHQNO, PARTICULARS, DR, CR, BAL, SOL` | `dd-MM-yyyy` | pratik1235/burnrate `axis_bank_csv.py`; sagarbehere/finzytrack `axis-bank-nro.yaml` |
| Kotak | Variant A: `Transaction Date, Description, Chq./Ref.No., Withdrawal Amt., Deposit Amt., Closing Balance` | `dd-MM-yyyy` | omprakash201194/spend-stack `kotak/csv-parser.ts` |
| Kotak | Variant B: `Serial, Transaction date, Value date, Description, Chq / Ref No., Debit amount, Credit amount, Balance, Dr/Cr` | `%d-%m-%Y` | jasimmk/bankii `in_kotak.py` |
| PNB | `Transaction Date, Cheque Number, Withdrawal, Deposit, Balance, Narration` (collapsed columns — sign from running balance) | `YYYY/MM/DD` | raptar231 `fixtures/pnb/pnb_savings-may-2023.txt` |
| DBS | `Date, Transaction Details, Withdrawal (INR), Deposit (INR), Balance (INR)` (collapsed columns — sign from running balance) | `DD/MM/YYYY` | raptar231 `fixtures/dbs/dbs_savings-may-2019.txt` |

Notes: SBI native download is tab-separated ".xls" with BOM/CRLF and an
`OPENING BALANCE` row (skipped by the loader). ICICI has no native CSV export
(Excel/ZIP only); the "CSV" users get is the Excel saved-as-CSV. Kotak variant
B (bankii) is documented above but not yet wired — auto-detect when a real
sample lands. PNB/DBS use separate Withdrawal/Deposit columns whose blank cells
collapse in the extracted text, so the sign is recovered from running-balance
arithmetic (`parse_bank_text`, D-23), not a two-column map.

Kotak also ships a **combined-amount** netbanking statement:
`Date, Narration, Chq/Ref No., Withdrawal (Dr) / Deposit (Cr), Balance` — a
single amount column with an explicit Dr/Cr marker ("347.00 Dr" = debit,
"35,000.00 Cr" = credit). `load_bank_statement` auto-detects this layout
(header carries "(Dr)" and "(Cr)") and routes to `parse_drcr_statement` (D-22).
Source: `raptar231` fixture `tests/fixtures/kotak/kotak_savings-jul-2025.txt`.

## Bank statements (PDF / text, SBI — YONO, netbanking, credit card)

Sanjay's SBI statement is a PDF, not a CSV. `settleflow/pdf.py` parses three
SBI layouts from the text layer, auto-dispatched by `parse_sbi_statement`:

- **YONO / e-statement** (modern default): `Date, Transaction Reference,
  Ref.No./Chq.No., Credit, Debit, Balance` (Credit before Debit). Rows are
  reconstructed from the trailing money columns; narrations may wrap.
- **Legacy netbanking**: `Txn Date, Value Date, Description, Ref No./Cheque
  No., Debit, Credit, Balance`; dates are `dd MMM` with the year split onto a
  following `yyyy yyyy` line (PDF text-extraction artifact). Sign from
  description heuristics (BY = credit, TO = debit).
- **Credit card**: `Date, Description, Amount (Rs.)`; payments/refunds carry a
  trailing `Cr` marker (credit), everything else is debit.

Money: INR rupees, plain decimal. Password-locked PDFs -> `PdfEncryptedError`;
image-only (scanned) PDFs -> `PdfScannedError` (OCR is a separate unbuilt
layer). Source: anonymised text fixtures from the Apache-2.0
`raptar231/indian-bank-statement-parser` (`tests/fixtures/sbi/`, see NOTICE.md).
