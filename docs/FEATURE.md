# Feature

A start-to-finish trail anyone can pick up cold.

## In progress

### SBI bank-statement PDF parser (ATL-72)

- **What:** parse an SBI statement **PDF** (not CSV) into `Txn` rows. `pypdf` +
  `pymupdf` already installed. Resolve on the real file: password (SBI PDFs often
  locked), text-vs-scanned (OCR path), table layout.
- **Why:** Sanjay's own SBI statement is a PDF; the library has no PDF path yet.
- **Status:** blocked — needs Sanjay's actual PDF (path + password).

## Done (this session, 2026-08-16)

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

## Backlog (ordered)

| # | Feature | Notes |
|---|---|---|
| 9 | SBI statement **PDF** parser | blocked on real file (ATL-72) |
| 10 | Cashfree settlement-recon (two-section file) | dedicated parser; schema in `docs/SCHEMAS.md` |
| 11 | PhonePe settlement report | confirm `PaymentType`/date format first |
| 12 | Juspay settlement file | confirm money unit first |
| 13 | Kotak statement variant B (auto-detect) | schema in `docs/SCHEMAS.md` |
| 14 | LLM triage call wired into the SaaS layer | core has `build_llm_prompt`; call is SaaS-side |
| 15 | Hosted SaaS deployment (auth, multi-user) | later stage |

## Feature template

```markdown
## Feature: <one line>

- **Why:** <the problem / who has it>
- **Files touched:** <list>
- **Model + date:** <who made the call>
- **Test:** <which check proves it works>
- **Status:** planned / in progress / done
```
