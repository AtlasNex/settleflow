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

## Backlog (ordered)

| # | Feature | Notes |
|---|---|---|
| 9 | SBI statement **PDF** parser | done for YONO text layout (D-21); netbanking + OCR deferred below |
| 10 | SBI legacy netbanking PDF layout | deferred — `PdfLayoutError`; day/month/year split across wrapped lines; use the CSV export |
| 11 | Scanned SBI PDFs (OCR) | deferred — `PdfScannedError`; OCR is a separate unbuilt layer |
| 12 | Cashfree settlement-recon (two-section file) | dedicated parser; schema in `docs/SCHEMAS.md` |
| 13 | PhonePe settlement report | confirm `PaymentType`/date format first |
| 14 | Juspay settlement file | confirm money unit first |
| 15 | Kotak statement variant B (auto-detect) | schema in `docs/SCHEMAS.md` |
| 16 | LLM triage call wired into the SaaS layer | core has `build_llm_prompt`; call is SaaS-side |
| 17 | Hosted SaaS deployment (auth, multi-user) | later stage |

## Feature template

```markdown
## Feature: <one line>

- **Why:** <the problem / who has it>
- **Files touched:** <list>
- **Model + date:** <who made the call>
- **Test:** <which check proves it works>
- **Status:** planned / in progress / done
```
