# Decisions

The "why" behind every choice, not just the "what". Read before you reverse a
decision. Each entry is version-pinned: who made the call and when.

## Version pinning (context)

| Role | Model | What it did |
|---|---|---|
| Orchestration + build | deepseek-v4-pro | decided the project, wrote all code and docs, made the commits |
| Research subagents | deepseek-v4-flash | ran the market/gap deep-dives (3 rounds) that produced the evidence |

The research that led here ran 2026-08-15 in three rounds: broad landscape -> two-path
shortlist -> deep-dive head-to-head. The deep-dive *killed* three of four candidate
wedges (a Postgres job queue was already owned by `pgqueuer`; GST was already owned by
Frappe's India Compliance; SEBI algo compliance had the wrong buyer). UPI reconciliation
survived because the OSS component layer is genuinely un-owned.

## Decisions

### D-1: Build UPI/NPCI reconciliation (not geo, not crypto, not AI tooling)
- **Why:** the only wedge where (a) the gap is real and un-owned, (b) there are paying
  buyers (fintechs, CAs, D2C sellers), (c) it maps to the exact stack (FastAPI/Postgres/
  Python), (d) low regulatory risk (no license, no filing liability).
- **Rejected:** geo-agent core (Nova's vectorized zoning was broken + `1acre.in` already
  ships parcel zoning); crypto OSS (usage != income, 30% tax kills domestic); MCP
  security (Snyk/Cisco/Invariant already ship); a Postgres job queue (`pgqueuer` owns it).
- **Model:** deepseek-v4-pro + deepseek-v4-flash research. **Date:** 2026-08-15.

### D-2: Open-core + thin SaaS, not a platform
- **Why:** the enterprise recon *platform* layer is crowded (Gini, UnPay, ReconPe,
  Cointab, Paxcom). The un-owned thing is the *component layer* (parsers + matching).
  OSS core = trust + distribution; the paid layer is a thin SaaS + consulting.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-3: `Decimal` for money, never `float`
- **Why:** reconciliation math must be exact; `float` produces rounding drift
  (₹0.1 + ₹0.2 != ₹0.3). Non-negotiable.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-4: Two-pass matching (exact UTR -> amount+date fallback)
- **Why:** the real Razorpay flow uses `settlement_id` as the batch key, and the bank
  statement's UTR is the *correspondent bank's* UTR, not the gateway's `settlement_utr`.
  So UTR match alone under-matches; the (amount, date) fallback is what actually pairs
  most batches.
- **Source:** Razorpay `Fetch All Settlements` docs + Terra Insight reconciliation guide.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-5: `settlement_id` rides through as `Txn.ref`
- **Why:** `match_settlements` converts `Settlement` -> `Txn` with `ref=settlement_id`,
  so a matched/unmatched result still tells you *which batch* without a separate mapping.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-6: paise -> rupee conversion lives only in the parser
- **Why:** Razorpay returns money in the smallest currency unit (paise). Keeping the
  model in rupees and converting at the parser boundary means the matcher never has to
  know about paise.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-7: Generic CSV loader with explicit column mapping (no vendor-specific classes)
- **Why:** the Razorpay CSV column names were not verifiable in raw docs (JS-rendered),
  and fabricating a schema is exactly the failure mode that broke Nova's zoning layer
  (20 fabricated `(GUESS)` legend rows). So `load_csv` takes column names as explicit
  arguments; the vendor mapping is data, filled from a real sample, never guessed.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-8: Assert-based self-check, no pytest/tox
- **Why:** ponytail rule: non-trivial logic leaves one runnable check, no frameworks.
  `python tests/test_matching.py` is the whole suite. Add pytest only if Sanjay asks.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-9: Working name `settleflow`
- **Why:** Sanjay names products at the end. `settleflow` is a placeholder (settlement +
  flow). Rename is a known, cheap, traceable diff (see D-10).
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-10: MIT license
- **Why:** maximally permissive for an open-core strategy (OSS core MIT, paid SaaS on
  top). Copyright holder = Sanjay R.U. Kumar.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-11: Private GitHub repo until complete
- **Why:** Sanjay wants it private until the project is done, then public. Avoids a
  half-finished repo being the first public impression.
- **Model:** deepseek-v4-pro (per Sanjay's instruction). **Date:** 2026-08-15.

### D-12: Relocate under `E:/Sanjay Files/StartUp/open source/<name>`
- **Why:** Sanjay wants a dedicated "open source" home, separate from the product
  ventures (Geospatial, Trading, etc.), and a named project folder.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-15.

### D-13: The research used Exa MCP + GitHub/PyPI API via curl, not Firecrawl
- **Why:** Firecrawl's managed web allowance hit a billing-402 mid-session. The fallback
  (Exa search + curl against GitHub/PyPI APIs + primary sources) was actually *stronger*
  verification. Recorded so a future session does not thrash on a dead tool.
- **Model:** deepseek-v4-pro (fallback) + deepseek-v4-flash (used Exa in subagents).
  **Date:** 2026-08-15.

### D-14: Phase 2 schema verified via Wayback snapshot of the Razorpay recon docs
- **Why:** Razorpay's live docs are JS-rendered (no schema in raw HTML) and Firecrawl
  was billing-blocked. The June-2026 Wayback snapshot of
  `razorpay.com/docs/api/settlements/fetch-recon/` served the full page, yielding the
  **24 documented response parameters** of `GET /v1/settlements/recon/combined` and the
  verbatim sample response. This is the verified schema for `parse_razorpay_recon`, not
  a guess (D-7 satisfied).
- **Model:** deepseek-v4-pro. **Date:** 2026-08-16.

### D-15: Recon parser is strict — unknown fields raise, never silently ignored
- **Why:** the parser validates against the known key set and raises on unknown or
  missing-required fields. If Razorpay adds a field, the parser fails loudly instead of
  dropping data — the failure mode that corrupted Nova's zoning layer was silent
  fabrication, so the opposite default (fail closed) is deliberate.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-16.

### D-16: Vendor/bank formats are a registry of column maps, data not code
- **Why:** Phase 3 (Cashfree/PayU/PhonePe/Juspay + bank statements) cannot be built
  without real sample files; their CSV headers are not verifiable from JS-rendered docs.
  The registry (`settleflow/schemas.py`) ships the loader + empty slots that raise a
  clear "needs a real sample" error instead of shipping a fabricated schema. This is the
  correct D-7 posture: the *mechanism* is done, the *data* is DEFERRED pending real
  samples. Never marked as done.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-16.

### D-17: The SaaS layer (saas/) may use FastAPI/uvicorn/Jinja2; the library stays stdlib-only
- **Why:** CONSTRAINTS.md #6 (zero runtime deps) protects the library's installability
  and the "MIT, zero-dependency" positioning. The thin SaaS is a separate optional
  layer (`pyproject` `[project.optional-dependencies].saas`), so the core's zero-dep
  invariant is preserved while the paid layer can use FastAPI + sqlite3 (stdlib).
- **Model:** deepseek-v4-pro. **Date:** 2026-08-16.

### D-18: Monetization corrects the competitive table and ranks licensing #1
- **Why:** research (2026-08-16) found (a) "Gini" is not a recon vendor — gini.co.in is
  a Pune construction firm, so it is removed; (b) Paxcom is Paymentus-owned, not PayU;
  (c) the SMB recon price ceiling is ₹4-7k/mo (ReconPe public pricing) with Zoho Books
  anchoring the bundle at ₹749-899/mo; (d) the highest-leverage money move is
  Sidekiq-style commercial licensing (OEM/white-label), not more SaaS seats. Full
  evidence in `docs/MONETIZATION.md`. Grants are a deferred harvest (year-1 ₹0-5 lakh).
- **Model:** deepseek-v4-pro (synthesis) + deepseek-v4-flash (3 research subagents).
  **Date:** 2026-08-16.

### D-19: Phase 3 column maps sourced from public evidence, not private accounts
- **Why:** Sanjay asked to "get the files yourself." His own settlement/statement files
  do not exist (the library is for *other* merchants' files), but the formats are
  verifiable from public sources: official sample files (Razorpay's xlsx samples still
  hosted on razorpay.com/docs), official docs (Cashfree/PhonePe/Juspay field tables),
  and open-source parsers that read the exact real exports (bank fixtures). Two research
  subagents cross-corroborated every header from ≥2 independent sources. Wired: Razorpay
  settlement CSV (7 cols) + recon CSV (27 cols), HDFC/SBI/ICICI/Axis/Kotak statements.
  NOT wired (honest): Cashfree recon (two-section file), PhonePe (undocumented type/date
  values), Juspay (unstated money unit), PayU (user-configurable columns). Full headers
  + sources in `docs/SCHEMAS.md`.
- **Structural change:** bank statements use TWO columns (debit/credit), so a
  `BankColumnMap` and `load_bank_statement_csv` were added (credits positive, debits
  negative, preamble rows auto-detected). `parse_date` extended for `dd/mm/yy`,
  `dd MMM yyyy`, `dd-MMM-yyyy`, and ISO/datetime-with-time.
- **Model:** deepseek-v4-pro (build) + deepseek-v4-flash (2 research subagents).
  **Date:** 2026-08-16.

### D-20: Bank statements arrive as PDF too — PDF parser is a separate layer
- **Why:** Sanjay's SBI statement is a PDF, not CSV. The library currently has no PDF
  path. PDF extraction is a different trust boundary (layout parsing, password, possible
  OCR) and must be built against a REAL file (D-7), never a guessed layout. `pypdf` and
  `pymupdf` are already installed, so no new dependency. Tracked as ATL-72; blocked on
  Sanjay providing the actual PDF.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-16.

### D-21: SBI PDF parser v1 = YONO text layer only; netbanking + OCR deferred
- **Why:** ATL-72 was blocked on Sanjay's real SBI PDF. Following D-19 ("get the
  files yourself"), the real SBI statement text layouts were sourced from the
  Apache-2.0 `raptar231/indian-bank-statement-parser` fixtures (already
  anonymised), so the parser is built against real layouts, never a guess (D-7).
  SBI has two statement layouts: the modern YONO/e-statement table
  (`Date | Transaction Reference | Ref.No./Chq.No. | Credit | Debit | Balance`)
  and the legacy netbanking table (`Txn Date | Value Date | Description |
  Ref No./Cheque No. | Debit | Credit | Balance`). v1 parses YONO only; the
  netbanking PDF's day/month/year values split across wrapped lines in the text
  layer (and its CSV export is already wired via the `sbi` bank map), so the
  parser raises `PdfLayoutError` rather than half-parsing it. Scanned PDFs (no
  text layer) raise `PdfScannedError` — OCR is a separate, unbuilt layer.
- **Structural change:** new `settleflow/pdf.py` (D-20's separate layer) with
  `extract_pdf_text` (lazy pymupdf import; password + scanned detection),
  `parse_sbi_statement`, `parse_sbi_pdf`. pymupdf is an OPTIONAL dependency
  (`[project.optional-dependencies].pdf`), so CONSTRAINTS #6 (stdlib-only core)
  still holds. Fixtures vendored under `tests/fixtures/sbi/` with a NOTICE.md
  (Apache-2.0 attribution). Version bumped 0.4.0 -> 0.5.0.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-20.

### D-22: Kotak Dr/Cr combined-amount statement — auto-detected
- **Why:** Kotak's netbanking statement uses a SINGLE combined amount column
  with an explicit Dr/Cr marker ("347.00 Dr" = debit, "35,000.00 Cr" = credit)
  — a different layout from the two-column variant A already wired. The marker
  makes the sign unambiguous in flattened text, so it is parseable without
  coordinates (unlike PNB's separate Withdrawal/Deposit columns, whose empty
  cells collapse ambiguously — deferred). Real anonymised fixture sourced from
  `raptar231/indian-bank-statement-parser` (the D-19/D-21 precedent).
- **Structural change:** `settleflow/parsers.py` gained `parse_drcr_statement`
  (a trailing "amount Dr|Cr balance" trio, narration accumulated across wrapped
  lines) + `load_bank_statement_drcr`. `load_bank_statement` now auto-detects
  the Dr/Cr format (header carries "(Dr)" and "(Cr)") and routes to it, so
  `bank="kotak"` works for either variant. PNB is deferred (ambiguous flattened
  text — needs coordinate-aware extraction or the raw PDF).
- **Model:** deepseek-v4-pro. **Date:** 2026-08-20.

### D-23: Complete bank coverage + LLM triage + CLI (end-to-end)
- **Why:** "complete all the things end to end." Applied the D-19 "get the files
  yourself" precedent to source real anonymised fixtures for PNB, DBS, SBI
  netbanking and SBI credit card from `raptar231/indian-bank-statement-parser`
  (Apache-2.0), and adopted its proven technique: recover the debit/credit sign
  from running-balance arithmetic when separate Debit/Credit columns collapse in
  the extracted text (this reverses D-22's earlier "PNB deferred" call).
- **Added:** `parse_bank_text` (generic collapsed-column parser with
  narration-before vs narration-after) -> PNB + DBS wired via TEXT_BANK_PARSERS;
  `parse_sbi_credit_card` (Date|Description|Amount + trailing Cr marker);
  `parse_sbi_netbanking` (legacy "Txn Date|Value Date|..." with the year split
  onto a "yyyy yyyy" line); `parse_sbi_statement` now auto-dispatches
  YONO/netbanking/credit-card; `triage_exceptions` (provider-agnostic LLM hook,
  `call_llm(prompt) -> str`, core still makes no network call); a CLI
  (`python -m settleflow reconcile -> tally.csv + exceptions.csv`).
  `load_bank_statement` now content-routes Dr/Cr, PNB/DBS and SBI text.
  Reference numbers (UPI/UTR/12+ digit) are extracted into Txn.utr.
- **Deferred (honest):** Cashfree/PhonePe/Juspay settlement files (no public
  sample exists; their schemas are already captured in SCHEMAS.md from official
  docs); scanned/image-only PDFs (OCR is a separate unbuilt layer); the hosted
  SaaS (later stage). Kotak "bankii" variant B still needs a real sample.
- **Model:** deepseek-v4-pro. **Date:** 2026-08-21.
