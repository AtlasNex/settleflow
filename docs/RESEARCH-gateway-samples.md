# Research: public schemas & sample files for Cashfree / PhonePe / Juspay / PayU / IDFC

**Date:** 2026-09-11 · **Task:** test D-7/D-24's conclusion that these formats are
merchant-private and unverifiable. **Method:** GitHub code search (`gh api search/code`
with exact header tokens), repo-tree mining for committed fixtures, live fetch of the
vendor docs pages, plus general web search. Every claim below was read out of a file I
fetched in this session (URLs given); nothing is paraphrased from memory.

**Headline: D-24 is partially wrong.** Real, publicly committed sample files for
**PhonePe** (2 files, 1038 rows of real data) and **Cashfree** (1 header-only recon file,
structure-verified) exist on GitHub, and the PhonePe blockers D-19 listed (undocumented
`PaymentType` values, undocumented date format) are resolved by those files. PayU and
Juspay have official docs pages with **complete** field tables/sample payloads that render
fine via plain fetch (no JS wall — the SCHEMAS.md note "not verifiable in raw docs" is
out of date). Only **IDFC** and the **Cashfree plain-settlements CSV** genuinely stay
deferred.

## Verdict table

Verdict key: **(a)** real sample file publicly downloadable · **(b)** official doc page
with complete example payload/field table · **(c)** community/third-party code hardcoding
the fields (corroboration only) · **(d)** nothing verifiable.

| # | Target | Artifact | Verdict | Exact source URL | What it gives us | Build+test parser this session? |
|---|--------|----------|---------|------------------|------------------|-------------------------------|
| 1a | Cashfree | Settlement **Recon** report — real committed CSV export (header-only, both sections) | **a** | `https://github.com/suryaansh001/sabrang_self_backend/blob/main/csvFiles/teams/Settlement Recon Report 12 Oct 2025 - 12 Oct 2025.csv` (fetched via Contents API; 1152 bytes) | Verbatim two-section header: sec-1 14 cols (first col literally `Id`); sec-2 **63 cols** — SCHEMAS.md's "48 cols" undercounts (`Key_4..Value_10`, `Surcharge Amount`, `Tax on Surcharge` present). Confirms the section marker line `** Settlement Reconciliation Details **` and CRLF/blank-line structure a two-section parser must handle | **Yes** for the section-splitting parser (fixture = real header + docs sample values below); data-row money/date formatting still untested |
| 1b | Cashfree | Same report — official docs, full parameter table with per-column sample values | **b** | `https://cashfree.com/docs/partners/embedded/reports/settlement-recon-reports` (fetched; renders fully via web_extract — no JS wall) | Every column's sample value: `208386848`, `110.00`, `2025-10-08 18:18:03`, `AXISCN1169361047`, `STANDARD`, `Event Type ∈ {PAYMENT, REFUND, CHARGEBACK, CHARGEBACK_REVERSE, DISPUTE, DISPUTE_REVERSE, RISK, RISK_REVERSE, OTHER_ADJUSTMENT}`, `Sale Type ∈ {CREDIT, DEBIT}` — rupees 2-dec, `YYYY-MM-DD HH:MM:SS` | **Yes** — enough to synthesize correct-typed data rows; values are rupees (settled amount = total − charge − tax + adjustment semantics stated) |
| 1c | Cashfree | Plain **Settlements** report (non-recon) CSV header | **d** | searched (see §dead-ends); docs page `.../reports/settlement-reports` lists only Settlement ID/Status/Date/UTR narratively, no column table; D-24's "13 cols from a production parser" is the Orders report, not this | — | No — stays deferred; use the public `GET /settlements` API instead (documented JSON) |
| 2a | PhonePe | Settlement report — **two real merchant CSVs with data rows** (418 + 620 rows) | **a** | `https://github.com/GunalThiru/KCMS/blob/main/uploads/complaints/Merchant_Settlement_Report_KADAMBASCARDONLINE_20251004_AXNPN27701342567_1.csv` and `.../Merchant_Settlement_Report_ITERATIONKTCLDQR_20251211_AXNPN34554189917_1.csv` (fetched via Contents API) | File 1 header (15 cols): `PaymentType, MerchantReferenceId, PhonePeReferenceId, From, Instrument, Flow Type, CreationDate, TransactionDate, SettlementDate, BankReferenceNo, Amount, Fee, IGST, CGST, SGST`. File 2 header (23 cols): adds `MerchantOrderId, OriginalMerchantReferenceId, OriginalTransactionId, OriginalTransactionDate, TransactionUTR, StoreId, StoreName, TerminalId, TerminalName`. Real value spaces: `PaymentType ∈ {PAYMENT, REFUND, CONVENIENCE_FEE}`; `Instrument ∈ {UPI_FULFILMENT, UPI_WALLET_FULFILMENT, PG_CC_FULFILMENT, PG_DC_FULFILMENT, PG_CC_ADDITIONAL_FEE_REVENUE, PG_DC_ADDITIONAL_FEE_REVENUE, MERCHANT_FULFILMENT_REVERSAL}`; dates `dd-MM-yyyy` (`CreationDate`) and `dd-MM-yyyy hh:mm:ss AM/PM` (`TransactionDate` in file 2); fee/tax negative as docs claim (`Fee=-7.4, IGST=-1.332`) | **Yes — proven**: `load_csv(file1, utr_col="BankReferenceNo", amount_col="Amount", date_col="SettlementDate", ref_col="MerchantReferenceId")` → 418 `Txn` rows, `Decimal('100.0')`, `date(2025,10,4)`. D-19/D-24 blockers gone |
| 2b | PhonePe | Official docs settlement-report field table | **b** | `https://developer.phonepe.com/docs/settlements` (fetched) | 14-field table + `Settled amount = Amount + Fee + IGST + CGST + SGST`; its `Instrument` enum list is the **online/Switch** vocabulary (`UPI_REDEMPTION`, …) and does NOT match the real-file values (`*_FULFILMENT`) — real files are authoritative for in-store/PG exports | **Yes** (with 2a) |
| 2c | PhonePe | Official column-description CSV (74 column docs) | **b**-adjacent (a: committed file, vendor-authored) | `https://github.com/GunalThiru/KCMS/blob/main/uploads/complaints/Learn_more_about_column_description.csv` | PhonePe-format column glossary incl. `SettlementDate … formatted as dd-MM-yyyy (IST)`, `BankReferenceNo = the settlement UTR` | corroboration for 2a |
| 3a | Juspay | Official **Settlement Files** docs — complete 25-col schema table | **b** | `https://juspay.io/pe/docs/upi-merchant-stack-pe/docs/resources/settlement-files` (fetched; renders fully, no JS wall) | All 25 headers verbatim + value enums: `Transaction Type ∈ {CREDIT, DEBIT, Dispute/Adjustment}`, `Type ∈ {COLLECT, PAY, Credit Adjustment, RET, Online Refund, Chargeback Acceptance, …}`, `Settlement Status ∈ {Sent for settlement, Settled, Pending, Failed}`, full Status-code map (`0, RB, C, A, AP, ACA, …`) and Account-Type map (`01=SAVINGS, …`); dates `dd/mm/yyyy`; file format .csv via dashboard **or SFTP** | **Yes** with caveat: money unit "Integer" is still unstated in docs — resolved only by 3b corroboration (rupees decimals). Testable via docs-derived fixture |
| 3b | Juspay | **Juspay's own production parser** (Namma Yatri shared-kernel, © Juspay India Ltd, AGPL-3.0) for the YesBiz/PE settlement CSV | **c** (strong — written by the vendor) | `https://github.com/nammayatri/shared-kernel/blob/main/lib/mobility-core/src/Kernel/External/Settlement/YesBiz/PaymentTypes.hs` (+ `YesBiz/PaymentParser.hs`) | Real header names it matches on: `Merchant ID, Transaction Amount, Fee, Tax, Credit, Debit, Partner Amount, Settlement Date, UPI Request Id, Transaction Type, Type, Transaction Date, Merchant Account Number, Status, Payer Vpa, Payee Vpa, RRN, Settlement Status, Order ID, Transaction Description, UTR Number` — 3 columns differ from docs (`Partner Amount` added; `Merchant Account Number`/`UTR Number` vs `Account Number`; `SS Adjustment Type`/`SS Credit/Debit` absent). Amounts fed to `parseAmount`/`HighPrecMoney` with **no ÷100** → treated as rupee decimals | corroboration only (AGPL — do not copy code; transcribe facts) |
| 3c | Juspay | HyperPG (Juspay PG) settlement/recon CSV — production column map, 34 cols | **c** | `https://github.com/nammayatri/shared-kernel/blob/main/lib/mobility-core/src/Kernel/External/Settlement/HyperPG/PaymentTypes.hs` | `Order Id, Transaction Id, Transaction Date, RRN, Order Type, Transaction Type, Transaction Status, Settlement Mode, Payment Method Type, Payment Method Sub Type, Refund Id, Refund Date, Hold Status, Type, Dispute Id, Dispute Type, Overall Txn Amount, Overall Fee, Overall Tax, Overall Settlement Amount, Vendor Id, Unique Split Id, Vendor Settlement Id, Vendor Utr, Vendor Txn Amount, Vendor MDR Fees, Vendor Tax Amount, Merchant Commission, Vendor Settlement Amount, Vendor Settlement Date, UDF1..5` | **Yes** — enough to register a flat recon column map |
| 3d | Juspay | Portal transaction-export CSV (`portal.juspay.in/api/q/download`) | **c** | `https://github.com/nammayatri/shared-kernel/blob/main/lib/mobility-core/src/Kernel/External/Settlement/JuspayApi/PaymentParser.hs` | ~40 header names (`Order Id, Txn Uuid, Rrn, Gateway Reference Id, Payment Status, Settlement Amount, Settlement Epg Id, Execution Date, Sub Vendor Id, …`); module docstring: "Field set and column ordering may vary between exports" → header-lookup parsing, not positional | reference for a tolerant portal parser |
| 3e | Juspay | Hyperswitch (Juspay's OSS gateway) | **d** | repo tree grep of `juspay/hyperswitch` (17916 paths) | No settlement/recon file fixtures — only `juspaythreedsserver` 3DS connector (irrelevant) | No |
| 4a | PayU | Official **Settlement Detail Range API** — complete sample response + every field documented | **b** | `https://docs.payu.in/reference/settlement-detail-range-api.md` (fetched via the `.md` trick; no JS wall) | UTR-level batch: `settlementId, settlementCompletedDate, settlementAmount, merchantId, utrNumber, transactionAmount, adjustmentAmount, refundAmount, chargebackAmount, refundReversalAmount, chargebackReversalAmount, serviceFee, serviceTax, additionalServiceFee, additionalServiceTax, numberOfTransactions` + per-txn array: `action, payuId, requestId, transactionAmount, merchantServiceFee, merchantServiceTax, merchantNetAmount, sgst, cgst, igst, merchantTransactionId, mode, paymentStatus, transactionDate, requestDate, requestedAmount, bankName, offerServiceFee, offerServiceTax, forexAmount, discount, additionalTdrFee, additionalTdrTax, totalServiceTax, totalProcessingFee, transactionCurrency, settlementCurrency` — rupees strings, `YYYY-MM-DD HH:MM:SS[.ffffff]` | **Yes — API JSON parser** (mirror `parse_razorpay_recon`); this is the real fix for PayU: D-24 kept asking for a CSV that has no fixed shape |
| 4b | PayU | Official **Settlement Transaction Details API** — complete sample payloads | **b** | `https://docs.payu.in/reference/settlement_transaction_details_api.md` (fetched) | Per-txn: `merchantId, merchantTransactionId, payuId, transactionType ∈ {capture, refund, chargeback, chargebackreversal, adjustment, cancel}, settlementStatus ∈ {Settled, Pending, On Hold, Failed}, settlementUTR, settlementDate (YYYY-MM-DDTHH:MM:SS), settlementId, settlementAmount` (signed: refunds negative) | **Yes** with 4a |
| 4c | PayU | Settlements **CSV export** | **d by design** (confirmed) | `https://docs.payu.in/docs/export-the-settlement-records` (fetched) | Confirms export = merchant picks columns in a "Column Settings" dialog → **no fixed public header can exist**; D-24's "needs a real dashboard export" is structurally unfixable by search — only per-merchant column config | No — and it never will be; wire 4a/4b instead |
| 4d | PayU | Payments-report (not settlement) column set from a production reconciler | **c** | `https://github.com/sjchoudhury/Reconciliation-Tool/blob/main/backend/modules/payment/pr_loader.py` (fetched) | `Mihpayid / Transaction ID, Date, Amount, Status, Mode(pg_type), Email, Firstname, Lastname, Productinfo, Udf1..5, Bank Ref No` + detection key "mihpayid is the canonical PayU field"; amounts in rupees | corroboration for a transactions-report map, not settlement |
| 5a | IDFC First | **Real sample statement file (any format)** | **d** | searched (see §dead-ends); the official bank PDF `Statement-Request-V-2.pdf` (idfcfirst.bank.in) is a *request form*, not a statement sample | — | **No — stays deferred** (honest gate: no public real IDFC file found by any method) |
| 5b | IDFC | Production PDF-text parsers for the savings e-statement layout | **c** (×4 independent) | `https://github.com/mdsdqk/nook` (`packages/parsers/src/idfc/savings.ts` + `__tests__/idfc-savings.test.ts` + `fixtures/idfc/savings/expected.json`) · `https://github.com/sureshdsk/finn-parse/blob/main/src/finn_parse/parsers/bank_statement/idfc.py` (MIT; `tests/conftest.py` holds its text fixture) · `https://github.com/akhilnarang/bank-statement-parser` (MIT; `parsers/idfc.py`) · `https://github.com/pratik1235/burnrate/blob/main/backend/parsers/idfc_first.py` (Apache-2.0; credit-card PDF) | Converging layout signature (nook's is the richest): header `STATEMENT OF ACCOUNT / ACCOUNT NO : / STATEMENT PERIOD : YYYY-MM-DD TO YYYY-MM-DD / IFSC / Opening Balance Total Debit Total Credit Closing Balance`, table `Transaction Date | Value Date | Cheque No | Particulars | Debit | Credit | Balance`, dates `DD-MMM-YYYY`, sign recovered from running-balance delta (same technique as our `parse_bank_text`, D-23). **BUT** nook's test text is hand-written (`MR SAMPLE USER`), finn-parse's is explicitly "Mock" — these are synthetic reproductions of a real layout, not the layout itself | No (no real file to verify against); the four independent corroborations mean a map is *ready to wire* the moment one real file arrives |
| 5c | IDFC | Savings **CSV/netbanking-export** header claim | **c** | `https://github.com/ishitachamoli/WhereIsMyMoney/blob/main/backend/app/services/bank_parser.py` (docstring: `Transaction Date, Value Date, Transaction Remarks, Withdrawal Amount, Deposit Amount, Balance`) · `https://github.com/abhinay-hat/FinTrack/blob/main/src/services/import/bankTemplates.ts` (different set: `Transaction Date/Date, Transaction Amount, Debit, Credit, Transaction Remarks/Description, Balance`) — the two **disagree** | two conflicting community guesses → not verifiable; do NOT wire either | No |
| 5d | IDFC | `jasimmk/bankii` | **d** | repo tree: `bankii/banks/` = `ae_emiratesislamic, in_federal, in_hsbc, in_kotak, in_sbi` only | no IDFC parser exists there (confirms D-24 on this point) | No |

## Corrections to SCHEMAS.md this research establishes

1. **Cashfree recon, transaction-details section = 63 columns, not 48** (verbatim from the
   real file): after `Key_3/Value_3` come `Key_4..Value_10`, then `Surcharge Amount`,
   `Tax on Surcharge`, `Payment Mode SubType`. Section 1 first header is `Id` (not `ID`).
2. **PhonePe real export ≠ docs table**: files carry a `Flow Type` column and (23-col
   variant) `MerchantOrderId/OriginalTransactionUTR/StoreId/StoreName/TerminalId/TerminalName/...`
   not in `developer.phonepe.com/docs/settlements`; the docs' Instrument enum is the
   Switch vocabulary, real files use `UPI_FULFILMENT`-style values. Column order differs
   too (`CreationDate` before the amount columns in file 1, mid-stream in file 2) →
   parse by header name, never position.
3. **PayU has two official settlement APIs with complete documented sample JSON**
   (`/settlement/range`, `/settlement/transactionDetails`) — the "only `get_settlement_details`"
   note is outdated.
4. **Juspay money unit**: official docs still say only "Integer"; the vendor's own
   production parser reads the values as plain rupee decimals (no ÷100). Rupees, pending a
   real file (confidence: high, verdict-c).

## Licensing / PII handling before vendoring anything found here

**Citation is not vendoring.** This document records URLs and column names as evidence — the
same way a technical writeup cites a public source. Two of those source *paths* contain a
merchant identifier because the path is the citation (the files were committed publicly by
someone else). That is not a reason to copy the files, and copying them is what would be wrong.
Everything below is about not doing that.

- `GunalThiru/KCMS`, `suryaansh001/sabrang_self_backend`, `mdsdqk/nook`: **no license**.
  Do not copy files into settleflow. CSV *headers and value semantics* are facts and are
  fine to transcribe into `schemas.py`/SCHEMAS.md (as done for bankii variant B). Any
  committed fixture must be regenerated synthetic (real header, made-up rows) — that is
  how D-19 handled bank fixtures, and the real files above cannot ship: KCMS contains a
  named merchant's real UTRs/order refs (AXNPN…, KTCL-…) — publishing them re-exposes
  someone's data.
- `nammayatri/shared-kernel`: AGPL-3.0, © Juspay — transcribe column names only, never code.
- `finn-parse` (MIT), `bank-statement-parser` (MIT), `burnrate` (Apache-2.0): safe to
  vendor with NOTICE (raptar231 precedent, D-21).

## Verdict summary (one line per target)

1. **Cashfree recon — UNBLOCKED (a+b):** real header file + official per-column sample
   values → build the two-section parser now; data rows remain synthetic-grade until a
   real populated export is seen.
2. **Cashfree plain settlements CSV — still (d):** deferred by evidence, not by search
   gap; public API covers it.
3. **PhonePe — UNBLOCKED (a):** two real exports resolve every documented blocker;
   loader already proven on one of them (418 rows).
4. **Juspay — UNBLOCKED to (b)+vendor(c):** official docs page fully fetchable with
   enums/status maps; money unit corroborated rupees by Juspay's own parser → buildable
   with docs-derived fixture; mark unit caveat in map until a real file.
5. **PayU — PIVOT (b):** no CSV exists to find (user-configurable columns, confirmed);
   ship the two official settlement-API JSON parsers instead.
6. **IDFC — REMAINS DEFERRED (c at best):** four production parsers corroborate the PDF
   text layout, but no real sample file or official doc exists; the two CSV claims
   contradict each other. The gate in D-24 is correct for IDFC specifically.

## Search log — queries that returned nothing useful

GitHub code search (`gh api search/code`):
**Correction (re-tested 2026-09-11, and the original claim in this line was wrong):** an earlier
draft of this document stated that `gh search code` returns `[]` silently "because the keyring token
lacks the `read:user` scope". That is **not** the mechanism — with the same token, `gh search code`
returns hits for `'BankReferenceNo'`, `'PhonePeReferenceId'`, `'Merchant_Settlement_Report'` and
`'AXNPN'`. What actually happened is query semantics, reproduced exactly:
`gh api -f q='cashfree settlement csv parser'` (terms, ANDed) → **122** results, while
`q='"cashfree settlement csv parser"'` (a literal phrase) → **0**. The empty CLI result was a
multi-word query matching no literal phrase; the big REST number was the words being ANDed.
**So an empty code-search result is never evidence of absence, and a large REST count is not
evidence the CLI broke — check whether the query was a phrase before concluding a format does not
exist.** Misreading an empty search as "nothing is out there" is exactly the error D-24 made and
this document exists to correct.
- `"Event Settlement Amount" "Merchant Reference ID"` → 1 hit (the sabrang file, useful) but
- `cashfree settlement csv parser` / `cashfree_order_id settlement` /
  `payu settlement csv parser` / `juspay settlement` (broad `gh search code` variants) → `[]`
  — these were literal-phrase misses, not a tool fault (see the correction above; the REST
  endpoint ANDs the same words and returns 122/… hits)
- `"SS Adjustment Type" "Settlement Status"` → 0 (only in docs sites, not code)
- `juspay settlement path:*.csv`, `payu settlement path:*.csv`, `idfc statement path:*.csv`,
  `path:*.csv "CashFree Reference Id"`, `path:*.csv "Merchant_Settlement_Report"`,
  `path:*.csv "bank_ref_no" settlement`, `path:*.csv idfc bank statement`,
  `path:*.csv "IDFC" "Transaction Date"`, `filename:settlement csv "PaymentType" "Instrument"`,
  `idfc first bank csv parser filename:*.py` → all **0**
- `"Settlement UTR" "Merchant UTR" payu` → 1 (no sample file); `"settlement_id" "txn" "mihpayid" csv` → 2 (no sample)
- `"IDFC First" "Withdrawal Amt"` → 66 hits, all generic multi-bank parsers/templates, zero real IDFC files
- `idfc path:fixtures` → the useful hit was `mdsdqk/nook` only; Kaggle/HF search
  `IDFC bank statement dataset sample csv` → nothing IDFC-specific
- Web: `IDFC FIRST bank statement sample PDF download idfcfirstbank.com` → only the statement-*request form* PDF;
  `PayU settlement file format "bankers report" columns` → only foreign vendors' docs (PayPal/Rapyd/Klarna)
- `juspay/hyperswitch` full tree grep → no settlement fixtures (connector test fixtures
  are payment-flow JSON only); `Amal-David/docingest` hyperswitch-snapshot mention of
  "settlement … sftp csv" → docs index noise
- bjain102/hisaab corpus → empty tier1 dir (no committed statements)

## Recommended next steps for the build session (not done here — research only)

1. Wire `phonepe_settlement_csv` map + a header-name-tolerant loader; add an
   anonymized 3-row fixture generated from the verified header (D-7-clean).
2. Add `parse_cashfree_recon_report` (two-section splitter keyed on the
   `** Settlement Reconciliation Details **` marker) + register both sections' maps
   (14 / 63 cols verbatim from the sabrang file).
3. Add `parse_payu_settlement_range` / `parse_payu_settlement_txn` API-JSON parsers
   (strict, D-15 style) from the two docs pages; close PayU-CSV as *by-design deferred*.
4. Register `juspay_settlement_csv` map (25 cols) flagged `money_unit: rupees (vendor-code
   corroboration)` until a real file lands; consider the 34-col HyperPG map too.
5. IDFC: keep `None` + the four corroborating source URLs recorded in SCHEMAS.md so the
   next session doesn't re-run this search.
6. Update D-24 with a correction note (this file is the evidence).
