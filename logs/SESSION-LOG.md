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

## 2026-08-20 — Session 5 (continued) (Kotak Dr/Cr combined-amount parser)

- **Model:** deepseek-v4-pro.
- **Did:** continued the bank-coverage push (ATL-80). Sourced a real anonymised Kotak
  netbanking statement (Apache-2.0, `raptar231` fixture) and found Kotak uses a SINGLE
  combined amount column with an explicit Dr/Cr marker ("347.00 Dr" = debit,
  "35,000.00 Cr" = credit) — distinct from the two-column variant A already wired.
  Added `parse_drcr_statement` + `load_bank_statement_drcr` to `parsers.py`, and made
  `load_bank_statement` auto-detect the Dr/Cr layout so `bank="kotak"` works for either
  variant. Version 0.5.0 -> 0.6.0.
- **Deferred (honest):** PNB's separate Withdrawal/Deposit columns collapse ambiguously
  in flattened text (same trap as the legacy SBI netbanking layout) — needs
  coordinate-aware extraction or the raw PDF. Kotak's "bankii" variant B likewise still
  needs a real sample.
- **Verified:** self-check 33/33 (Kotak Dr/Cr auto-detect; totals reconcile with the
  statement's own sub-totals 10,069.00 Dr / 55,125.00 Cr).
- **Docs:** SCHEMAS (Kotak Dr/Cr note), DECISIONS D-22, FEATURE, HANDOVER.

## 2026-08-21 — Session 6 (complete end-to-end: banks, LLM triage, CLI)

- **Model:** deepseek-v4-pro.
- **Did:** "complete all the things end to end." Sourced real anonymised fixtures for
  PNB, DBS, SBI netbanking and SBI credit card from `raptar231` (Apache-2.0) and adopted
  its running-balance technique — which reverses D-22's earlier "PNB deferred" call.
  Added `parse_bank_text` (PNB+DBS), `parse_sbi_credit_card`, `parse_sbi_netbanking`;
  `parse_sbi_statement` now auto-dispatches YONO/netbanking/credit-card.
  `load_bank_statement` content-routes Dr/Cr, PNB/DBS and SBI text. Added
  `triage_exceptions` (provider-agnostic LLM hook) and a CLI
  (`python -m settleflow reconcile` -> tally.csv + exceptions.csv). Version 0.6.0 -> 0.7.0.
- **Deferred (honest):** Cashfree/PhonePe/Juspay settlement files (no public sample;
  schemas already in SCHEMAS.md), scanned/OCR PDFs, Kotak "bankii" variant B, hosted SaaS.
- **Verified:** self-check 38/38; CLI exercised end-to-end (match + classify + export);
  `hermes verify --skip-start` OK (full run still hangs in the Windows start-phase
  teardown — a harness issue, not a code defect; /health returns 200 during a live run).
- **Docs:** SCHEMAS (PNB/DBS + SBI netbanking/credit), DECISIONS D-23, FEATURE, HANDOVER,
  README, CONSTRAINTS, SESSION-LOG.

## 2026-08-24 — Session 7 (docs consistency: pdf.py coverage)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** picked up the offer left hanging at the end of Session 6. `docs/ARCHITECTURE.md`
  and `docs/FLOW.md` predated v0.7.0's `settleflow/pdf.py` and never mentioned PDF /
  parse_sbi / pymupdf / scanned / OCR at all. Refreshed both: added `pdf.py` to the package
  layout tree and import graph, a "PDF layer (pdf.py)" architecture section, the PDF branch
  in the data-flow diagram, the zero-runtime-deps invariant (now "core stdlib-only, `[pdf]`
  extra"), and flow sections for `extract_pdf_text` / `parse_sbi_statement` / `parse_sbi_pdf`.
- **Verified:** self-check 38/38; git commit `0d1ad63` (docs-only, 2 files, +70/-9).
- **Docs:** ARCHITECTURE.md, FLOW.md, SESSION-LOG.md.

## 2026-08-24 — Session 8 (ATL-90: gateway settlement files + Kotak bankii-B)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** Sanjay said the sample file won't open and told me to find it on the full
  internet. Exhaustive search (vendor docs, GitHub repo+code search, the vetted bank-
  fixture repos raptar231/jasimmk/bankii, real production reconcilers aravindsiva13 +
  SaiYadav1818/Karatly) CONCLUSIVELY found NO public sample FILE for Cashfree/PhonePe/
  Juspay/PayU settlement+recon CSVs or IDFC — they're merchant-private dashboard exports
  (contain real transaction/PII data). Verified real schemas instead: Kotak bankii-B
  (transcribed from jasimmk/bankii in_kotak.py), Cashfree orders (13 cols, production
  parser), PhonePe 14 + Juspay 25 (already in SCHEMAS.md). Per Sanjay's "do A", WIRED
  Kotak bankii variant B: `kotak_bankii` BankColumnMap + header content auto-detect in
  load_bank_statement (tokens "Debit amount"/"Credit amount"), so the "kotak" key
  auto-handles a bankii export; Dr/Cr flag redundant (one amount col per row).
  Version 0.7.0 -> 0.7.1. Self-check 38 -> 39.
- **Deferred (honest):** parse-from-real-file test for bankii-B (needs a real Kotak
  bankii export; D-7 no synthetic); Cashfree/PhonePe/Juspay/PayU settlement+recon
  parsers (need one real dashboard export each); IDFC; scanned/OCR PDFs; hosted SaaS.
- **Verified:** 39/39 checks pass; `python -m settleflow` import + version 0.7.1.
- **Docs:** SCHEMAS (bankii-B wired note), DECISIONS D-24, HANDOVER (bankii-B + gated
  list), SESSION-LOG.

## 2026-08-24 — Session 9 (ATL-91: rigorous gap audit + stress test to the core)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** Sanjay: "check for anything missing, stress test this to the core, I want
  Settleflow very successful." Read the full codebase (models/matching/parsers/exports/
  exceptions/pdf/schemas/CLI + CONSTRAINTS), then ran TWO adversarial harnesses (34 + 16
  checks): Decimal money traps, deterministic matching (incl 500-line fuzz), duplicate-UTR
  consumption, colliding (amount,date), classify rule edges (fee drift/stale boundary/
  duplicate suspect), trust-boundary fuzz (malformed money/dates/recon CSV/unicode/control
  chars), Level-2 netting + order/refund matching, a real generated-PDF extract+parse, and
  the UTC-vs-IST day shift.
- **Fixed (2 real bugs):** (1) exports money printed inconsistently (1000 vs 1000.00; 0 vs
  0.00) — added `_money()` quantize-to-0.01, applied to every money cell in
  tally/gst/tds; (2) `extract_pdf_text` silently accepted a non-PDF (pymupdf opens plain
  text as a 1-page doc) — guarded on `doc.is_pdf` and raise a clear ValueError (trust
  boundary, D-7).
- **Verified ceilings (kept, documented in D-25):** (amount,date) mis-pair on collisions;
  DUPLICATE_SUSPECT over-flag (conservative); `_epoch_date` UTC day near midnight (IST +5:30)
  — changing it would ripple through tests/docs, so deferred for a deliberate call.
- **Doc drift fixed:** README + HANDOVER "38 checks" -> 39; README bank coverage now lists
  Kotak bankii-B.
- **Verified:** both stress harnesses green; canonical self-check 39/39; hermes verify
  --skip-start green (0.7.1 wheel). Commit follows (D-25).
