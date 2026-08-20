# Session Log

Append-only trail. One entry per working session, newest at the bottom. Tag model + date.

## 2026-08-15 — Session 1 (build origin)

- **Model:** deepseek-v4-pro (orchestration/build), deepseek-v4-flash (research subagents).
- **Decided:** build UPI/NPCI settlement reconciliation open-core (see `docs/DECISIONS.md`).
- **Built (Phase 1):** data model (`Txn`, `Match`, `MatchStatus`, `ReconResult`,
  `Settlement`), two-pass matching engine, `match_settlements`, generic CSV loader,
  Razorpay settlement parser (real API schema).
- **Verified:** self-check 8/8 (7 file checks + CSV round-trip). Fresh verification
  script, exit 0.
- **Committed:** `ccf753b` baseline, `aad10fc` Razorpay parser, `f2a9b92`
  relocate+rename to `open source/settleflow`.
- **Repo:** relocated to `E:/Sanjay Files/StartUp/open source/settleflow`; package
  `upirecon` renamed `settleflow`.
- **Next:** Phase 2 line-item decomposition (Razorpay `Fetch Settlement Recon`).

## 2026-08-15 — Session 2 (formalize + docs + GitHub)

- **Model:** deepseek-v4-pro.
- **Did:** wrote full doc/process set (MASTER-PLAN, ARCHITECTURE, CONSTRAINTS, FLOW,
  DECISIONS, HANDOVER, BUG, FEATURE, ROLLBACK, TESTING, AGENTS, SESSION-LOG) + README
  rewrite; created the private GitHub repo and pushed.
- **Note:** Firecrawl web allowance was billing-blocked this session; research used Exa
  MCP + curl against GitHub/PyPI APIs. Recorded so future sessions do not thrash on it.

## 2026-08-16 — Session 3 (monetization research + Phases 2-5)

- **Model:** deepseek-v4-pro (build/synthesis), deepseek-v4-flash (3 research subagents).
- **Research:** fan-out of 3 subagents (competitor pricing, market size + TDS-1035, OSS
  monetization + grants). Persisted to `docs/MONETIZATION.md`. Key findings: SMB price
  ceiling ₹4-7k/mo; "Gini" is not a recon vendor (removed); Paxcom is Paymentus-owned;
  TDS code 1035 (ex-194O, 1-Apr-2026) is the sharpest demand wedge; grants are a
  deferred harvest (₹0-5 lakh year-1).
- **Built:** Phase 2 (recon parser + group_batches + match_orders), Phase 3 registry
  (schemas.py), Phase 4 (saas/app.py FastAPI), Phase 5 (exceptions.py). Razorpay recon
  schema verified via Wayback snapshot (D-14).
- **Verified:** self-check 18/18; SaaS booted + exercised end-to-end (reconcile ->
  exceptions -> Tally/GST/TDS-1035 exports) against sample files.
- **Money wiring:** docs/COMMERCIAL.md (Sidekiq licensing), funding.json,
  .github/FUNDING.yml, MASTER-PLAN competitive/monetization refresh.
- **Deferred (honest):** Phase 3 vendor/bank column maps (needs real sample files);
  SaaS hosting/auth (later-stage).

## 2026-08-16 — Session 4 (Phase 3 schemas sourced + wired)

- **Model:** deepseek-v4-pro (build), deepseek-v4-flash (2 research subagents).
- **Did:** Sanjay said "get the files yourself." Sourced VERIFIED column layouts from
  public evidence (official Razorpay sample xlsx files on razorpay.com/docs, Cashfree/
  PhonePe/Juspay docs, and open-source parsers reading real bank exports). Wired
  Razorpay settlement CSV (7 cols) + recon CSV (27 cols) + HDFC/SBI/ICICI/Axis/Kotak
  statements into `schemas.py`. Added `BankColumnMap` + `load_bank_statement_csv`
  (two-column debit/credit, preamble auto-detect) and extended `parse_date` (dd/mm/yy,
  dd MMM yyyy, dd-MMM-yyyy, ISO datetime-with-time). All headers + sources in
  `docs/SCHEMAS.md`.
- **Verified:** self-check 27/27; `hermes verify` ok:true; package imports clean.
- **Deferred (honest):** Cashfree recon (two-section file), PhonePe (undocumented
  type/date), Juspay (unstated money unit), PayU (user-configurable columns) — all
  documented in `docs/SCHEMAS.md`, not fabricated.

## 2026-08-16 — Session 4 closeout (PDF parser discovered + queued)

- **Model:** deepseek-v4-pro.
- **Did:** fixed SBI's native tab-separated ".xls" export (auto-detect delimiter via
  `csv.Sniffer` in `load_bank_statement_csv`) — committed `e2f16e4`, self-check 28/28,
  `hermes verify` ok:true.
- **Discovery:** Sanjay's SBI statement is a **PDF**, not CSV. The library has no PDF
  path yet. Created **ATL-72** (SBI bank-statement PDF parser). `pypdf` and `pymupdf`
  are both already installed locally, so no new dependency needed.
- **Blocking input (needs Sanjay):** his actual SBI PDF — path + password (SBI PDFs are
  often locked) + whether it is text-based or a scanned image (OCR path).
- **Next session starts here:** build `parse_*_pdf` against his real file, never guess
  the layout (D-7).

## 2026-08-20 — Session 5 (SBI PDF parser, YONO text layer)

- **Model:** deepseek-v4-pro.
- **Did:** unblocked ATL-72 without Sanjay's file by sourcing real (anonymised,
  Apache-2.0) SBI statement text fixtures from
  `raptar231/indian-bank-statement-parser` (the D-19 "get the files yourself"
  precedent). Built `settleflow/pdf.py`: `extract_pdf_text` (lazy pymupdf import;
  password + scanned detection), `parse_sbi_statement` (modern YONO/e-statement
  table, rows reconstructed from the trailing money columns — never a guessed
  column width), `parse_sbi_pdf`. pymupdf is an OPTIONAL `[pdf]` extra, so the core
  stays stdlib-only (CONSTRAINTS #6 preserved). Version 0.4.0 -> 0.5.0.
- **Deferred (honest):** the legacy netbanking PDF layout (`PdfLayoutError` — the
  day/month/year values split across wrapped lines; its CSV export is already wired
  via the `sbi` bank map) and scanned/image-only PDFs (`PdfScannedError` — OCR is a
  separate unbuilt layer). Parser still to be validated against Sanjay's actual file.
- **Verified:** self-check 32/32 (4 new checks: YONO multi-account, YONO combined
  two-table, netbanking rejection, extraction + password + scanned detection);
  end-to-end `parse_sbi_pdf` on a generated PDF. `hermes verify` ok.
- **Docs:** SCHEMAS (SBI PDF section), DECISIONS D-21, FEATURE (ATL-72 -> done),
  CONSTRAINTS (#6 note + known-ceiling), HANDOVER, README.
