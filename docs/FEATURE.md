# Feature

A start-to-finish trail anyone can pick up cold.

## In progress

_(none — every tracked item is either done below or deferred with a reason in the backlog.)_

## Done (this session, 2026-08-20)

| # | Feature | Status | Commit |
|---|---|---|---|
| 1 | Level-1 matching engine + Razorpay settlement parser | done | `ccf753b`/`aad10fc` |
| 2 | Line-item decomposition (Razorpay recon 24-param schema) + order matching | done | `9becf0e` |
| 3 | Bank-statement parsers HDFC/SBI/ICICI/Axis/Kotak + Razorpay CSV/recon | done | `14c6824` |
| 4 | Thin SaaS (FastAPI reconcile/export/exception queue) | done (local) | `9becf0e` |
| 5 | Exception classifier + LLM prompt builder | done | `9becf0e` |
| 6 | Tally / GST / TDS-1035 exports | done | `9becf0e` |
| 7 | Monetization research + commercial license + funding.json | done | `9becf0e` |
| 8 | SBI tab-separated `.xls` delimiter fix | done | `e2f16e4` |
| 9 | SBI bank-statement **PDF** parser (YONO text layout) | done | D-21 |
| 10 | Kotak Dr/Cr combined-amount statement (auto-detect) | done | D-22 |
| 11 | PNB + DBS bank statements (running-balance sign recovery) | done | D-23 |
| 12 | SBI legacy netbanking + SBI credit-card parsers | done | D-23 |
| 13 | LLM triage hook (`triage_exceptions`, provider-agnostic) | done | D-23 |
| 14 | End-to-end CLI (`python -m settleflow reconcile`) | done | D-23 |

## Backlog (ordered)

| # | Feature | Notes |
|---|---|---|
| 15 | Scanned SBI PDFs (OCR) | deferred — `PdfScannedError`; OCR is a separate unbuilt layer |
| 16 | Cashfree settlement-recon (two-section file) | deferred — no public sample; schema in `docs/SCHEMAS.md` |
| 17 | PhonePe settlement report | deferred — no public sample; confirm `PaymentType`/date format |
| 18 | Juspay settlement file | deferred — no public sample; confirm money unit |
| 19 | Kotak "bankii" variant B (Serial + separate Debit/Credit amount + Dr/Cr flag) | deferred — needs a real sample |
| 20 | Hosted SaaS deployment (auth, multi-user) | later stage |

## Feature template

```markdown
## Feature: <one line>

- **Why:** <the problem / who has it>
- **Files touched:** <list>
- **Model + date:** <who made the call>
- **Test:** <which check proves it works>
- **Status:** planned / in progress / done
```
