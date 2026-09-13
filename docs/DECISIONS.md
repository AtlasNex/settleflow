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

### D-24: Gateway settlement files are merchant-private; verified schemas + Kotak bankii-B wired
- **Why:** ATL-90 — "search the full internet and find the sample files" (Sanjay,
  24.08.26). Exhaustive public search (vendor docs, GitHub repo+code search, the
  vetted bank-fixture repos raptar231 and jasimmk/bankii, and real production
  reconcilers aravindsiva13 + SaiYadav1818/Karatly) CONCLUSIVELY found NO public
  sample FILE for the Cashfree/PhonePe/Juspay/PayU settlement or recon CSVs, nor
  IDFC. Every vendor report is generated from an authenticated Merchant Dashboard
  (and contains real transaction/PII data), so these files are never published
  the way anonymised bank-statement text is. D-19's "get the files yourself"
  precedent therefore does NOT extend to them; the gate is real, not a search gap.
- **Verified from real sources (not guessed, D-7):** Kotak "bankii" variant B
  schema transcribed from the production parser `jasimmk/bankii/in_kotak.py`
  (`Serial | Transaction date | Value date | Description | Chq / Ref No. |
  Debit amount | Credit amount | Balance | Dr/Cr`, `%d-%m-%Y`); Cashfree orders
  report (13 cols, from a production `CashfreeSettlementCsvParser`); PhonePe 14
  fields + Juspay 25 cols (already captured in SCHEMAS.md from official docs).
- **Wired:** Kotak bankii-B as a `BankColumnMap` + content auto-detect in
  `load_bank_statement` (header tokens "Debit amount"/"Credit amount"), so the
  existing `kotak` key auto-handles a bankii export. The Dr/Cr flag is redundant
  (only one amount column populated per row). Self-check 38 -> 39.
- **Deferred (honest):** parse-from-real-file verification for bankii-B (needs a
  real Kotak bankii CSV export; D-7 no synthetic fixtures); Cashfree/PhonePe/
  Juspay/PayU settlement+recon parsers (need a real dashboard export from any
  merchant account); IDFC; scanned/OCR PDFs; hosted SaaS. UNBLOCK = one real
  dashboard export per gateway (see the ATL-90 comment for the exact list).
- **Model:** deepseek-v4-flash-vision-exp (build + search). **Date:** 2026-08-24.

### D-25: Rigorous stress test found + fixed 2 real bugs; documented ceilings
- **Why:** ATL-91 — Sanjay: "check for anything missing, stress test this to the core."
  Ran two adversarial harnesses (34 + 16 checks) against the invariants in CONSTRAINTS:
  Decimal money, deterministic matching (incl. 500-line fuzz), trust boundaries, expose
  /classify/parse edge cases, Level-2 netting + order matching, hostile-input fuzz, and a
  real generated PDF.
- **Bug 1 (fixed):** exports emitted money inconsistently — a whole-number amount printed
  as `1000` while a fractional one printed `1000.00`, and an exempt TDS printed `0` vs
  `0.00`. For accountant-facing CSVs (Tally/GST/TDS) that's a real defect. Fixed with a
  single `_money()` helper (quantize to `0.01`) applied to every money cell; all existing
  '100.00'/'-2446.84'/'1.00' asserts stay green.
- **Bug 2 (fixed):** `extract_pdf_text` silently accepted a NON-PDF file. pymupdf
  leniently opens plain text as a 1-page doc, so the library returned the raw text instead
  of failing — the "silently coerce" anti-pattern CONSTRAINTS #2 forbids. Fixed by guarding
  on `doc.is_pdf` after open and raising a clear `ValueError` (D-7 trust boundary).
- **Verified ceilings (kept, not fixed — documented):** (a) `match()` (amount,date)
  fallback can mis-pair when two bank lines share (amount,date) — already in CONSTRAINTS;
  (b) `classify()` DUPLICATE_SUSPECT does not decrement the bank-side count, so it can
  over-flag (conservative; flagged for human review, so safe); (c) `_epoch_date` converts
  Razorpay's UTC epoch to a UTC date, which can skew the (amount,date) fallback by one day
  for settlements near midnight UTC (IST is +5:30; primary UTR match unaffected). Fixing
  (c) switches `created_at` to IST and would ripple through tests/docs — deferred for a
  deliberate call, not a silent change.
- **Self-check:** 39 -> still 39 (no regression); both stress harnesses green.
- **Model:** deepseek-v4-flash-vision-exp. **Date:** 2026-08-24.

### D-26: Fix the remaining found gaps — IST epoch, date format, CLI PDF gating
- **Why:** Sanjay: "fix all, complete all" after the D-25 stress test's gap report.
- **(1) `_epoch_date` now returns the IST (+05:30) date.** Razorpay's epoch is UTC;
  Indian bank statements are IST. The UTC date was one calendar day behind IST for any
  transaction within ~05:30 of midnight UTC, which skewed the (amount, date) fallback
  (the primary UTR match was unaffected). Now aligns with the statement's IST date.
- **(2) Date parser accepts `%d-%b-%y`** (e.g. "01-Jul-25") — added after `%d-%b-%Y` so
  a 4-digit year still matches first; no ambiguity.
- **(3) CLI `.pdf` gating:** `--bank` != sbi with a .pdf statement now raises a clear
  error ("PDF parser only handles SBI") instead of running the SBI parser and throwing a
  confusing SBI-layout error.
- **Deliberately KEPT (not bugs):** `_is_money`'s exactly-2-decimals requirement — widening
  it to accept integers would let a numeric reference (e.g. YONO "500") be misread as a
  money amount and break real statements; it's a disambiguator, not a bug. `classify()`
  DUPLICATE_SUSPECT over-flagging stays conservative (better to over-flag for human review
  than under-report genuine duplicates).
- **Self-check:** 39 -> 41 (2 new: IST epoch + two-digit month name; CLI PDF gating).
  Version 0.7.1 -> 0.7.2. **Model:** deepseek-v4-flash-vision-exp. **Date:** 2026-08-24.

### D-27: OCR for scanned SBI PDFs (Tesseract) + SaaS deploy-ready
- **Why:** Sanjay (24.08.26): "OCR scanned PDFs — needs an OCR layer" and "Hosted SaaS —
  needs deployment" — challenged the earlier deferrals as things I should just do. Also
  corrected me: Tesseract is ALREADY installed (not on bash PATH; it's at
  C:/Program Files/Tesseract-OCR/tesseract.exe) — so use it, don't invent a new OCR stack.
- **OCR (settleflow/ocr.py, optional [ocr] extra):** rasterises each page with pymupdf and
  runs the Tesseract CLI via subprocess (--psm 6). The recovered text feeds the existing
  `parse_sbi_statement` dispatcher. On a clean scan Tesseract preserves the statement's
  columns/header, so the native parser works (verified: 2 rows recovered). Added
  `ocr_pdf_text`, `parse_sbi_scanned_pdf`, `OcrUnavailableError`, `OcrError`;
  `parse_sbi_pdf(path, ocr=True)` auto-falls back on `PdfScannedError`; CLI `--ocr` flag.
  Honest ceiling: OCR recovers a text layer, not perfect columns — a noisy scan can merge
  columns and the parser raises `PdfLayoutError` rather than guessing. The `[ocr]` extra is
  just pymupdf (Tesseract is a system binary, invoked via CLI, no pip OCR package).
- **SaaS deploy-ready:** added `Dockerfile` (python:3.11-slim, install `.[saas]`, run
  uvicorn) + `docker-compose.yml` (binds 127.0.0.1:8091:8000, container_name settleflow) +
  `.dockerignore`. Verified the app boots locally and `/health` returns
  {"status":"ok","version":<library version>} (fixed a stale hardcoded "0.3.0" to use
  `settleflow.__version__`). Actual live host deploy is a separate infra step (Cloudflare
  Tunnel/port), to be confirmed with Sanjay.
- **Self-check:** 41 -> 42 (OCR test, guarded to skip if tesseract/pymupdf absent).
  Version 0.7.2 -> 0.7.3. **Model:** deepseek-v4-flash-vision-exp. **Date:** 2026-08-24.

### D-28: SettleFlow SaaS deployed live at settleflow.atlasnex.com
- **Why:** Sanjay said he has a domain — "can u use that or what?" (yes). And gave the go.
  Hosted the thin SaaS (FastAPI reconcile/expose/export) publicly.
- **How (pivots discovered):** (1) This VPS is a Proxmox **LXC → Docker build FAILS** with an
  AppArmor error (`unable to apply apparmor profile`), even with `--security-opt
  apparmor=unconfined` — the existing images were built elsewhere; the proven pattern here
  is **hot-patch / run directly** (memory: "NexOS deploy=hot-patch not build"). So instead
  of Docker, I ran the SaaS as a **systemd service** (`/etc/systemd/system/settleflow.service`,
  venv at /opt/settleflow/.venv, `uvicorn saas.app:app --host 127.0.0.1 --port 8093`).
  (2) The tunnel is **remotely-managed** (Cloudflare pushes the ingress config, version=10—
  my local /etc/cloudflared/config.yml edit was IGNORED). So the public hostname had to be
  added via the Cloudflare API: `PUT /accounts/{acct}/cfd_tunnel/{tun}/configurations`
  (adds `settleflow.atlasnex.com -> http://localhost:8093`), plus a **DNS CNAME**
  `settleflow.atlasnex.com -> 9a8936c6-…cfargotunnel.com` (proxied).
- **Whys on keys:** port **8093** (8091 is the trade-ui tunnel slot, 8092/8093 free);
  bind 127.0.0.1 for the tunnel to reach it, never expose the port directly.
- **Verified:** internal `curl http://127.0.0.1:8093/health` -> 200; external
  `https://settleflow.atlasnex.com/health` -> {"status":"ok","version":"0.7.3"} 200;
  external `/` renders the UI. cloudflared log shows version=11 config with settleflow.
- **Deployment is host-run (not containerized) on this box**; the Dockerfile/compose remain
  for hosts where AppArmor/LXC is not a Docker-build blocker.
- **Model:** deepseek-v4-flash-vision-exp. **Date:** 2026-08-24.

### D-29: A run is reached by an unguessable token, not an account and not a listing
- **Why:** `/runs` listed every uploaded statement to anyone, and `/runs/<id>/export/tally.csv`
  downloaded the workpaper. Integer ids made it enumerable, so the exposure was one `for` loop
  wide. Any real merchant's first upload would have been world-readable.
- **What:** `secrets.token_urlsafe(24)` (~144 bits) per run; results at `/r/<token>`, exports at
  `/r/<token>/export/<name>.csv`. No accounts, no login — that would be a different product and
  the thinnest thing that closes the hole is a capability URL.
- **Consequence accepted:** no account means no recovery. Lose the URL and the run is gone. The
  results page says so in as many words ("Bookmark this page") rather than pretending otherwise.
- **Legacy rows:** predate the column, keep a NULL token, and are unreachable. That is the intended
  outcome, not a migration gap.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-30: Run responses are `no-store`, and the canary asserts it
- **Why (evidence, not theory):** after the route was removed, the live site still served the leaked
  CSV from Cloudflare's edge — `cf-cache-status: HIT`, `Age: 2079`, `max-age=14400`. Reminiscent of
  the real lesson: **removing a route does not un-publish what a CDN already holds**. `.csv` is in
  Cloudflare's default cacheable-extension list.
- **What:** middleware sets `Cache-Control: no-store, private` and `X-Robots-Tag: noindex` on
  `/r/*`, `/reconcile`, `/health` and `*/notify`. `/health` is included because a cached health
  check is the "process is up" illusion. The canary's `cache_headers` check fails if this regresses.
- **Verification:** through the public URL — `/r/<token>` → `cf-cache-status: DYNAMIC`,
  export → `BYPASS`; the previously cached URL now 404s. Purge was by API `prefixes`
  (`<host>/runs/`).
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-31: The origin host is never committed
- **Why:** `scripts/deploy.sh` had `root@<origin-ip>` as a default. The repo is now public and that
  address is deliberately absent from public DNS (Cloudflare proxies the hostname), so publishing it
  hands out a route that bypasses the Cloudflare rules in front of the origin. Two docs named it too;
  both were redacted.
- **What:** the host comes from `SETTLEFLOW_HOST` or a gitignored `scripts/.deploy.env`. `--help`
  works with no target set; the scripts refuse to run without one and say how to set it.
- **Side benefit:** the deploy scripts are now genuinely usable by anyone self-hosting, which the
  hardcoded address made impossible.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-32: A canary does a real reconcile, because a health check cannot see a broken product
- **Why:** the failure mode this project keeps hitting is "process up, product broken" — a container
  heartbeating for weeks, a dashboard rendering blank, an app answering 200 on `/health` while the
  results page is wrong. A liveness probe is blind to all of it.
- **What:** `scripts/canary.py` (stdlib only) uploads a real settlement file and bank statement,
  follows the private run URL, reads the tally export, asserts every path from the 11 Sep incident is
  still 404, and asserts run responses are still `no-store`. It runs in CI (proving the app boots on
  a clean runner), on the server after every deploy, and every 15 minutes from a Hermes watchdog
  against the public URL.
- **Design choice:** the checks live in the repo, not the watchdog, so they move with the product.
  The watchdog only does alerting (first failure, every 6th, recovery).
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-33: D-24's "merchant-private" conclusion was wrong for PhonePe, and PayU was the wrong shape
- **What D-24 said (2026-08-24):** Cashfree/PhonePe/Juspay/PayU settlement and recon files are
  merchant-private dashboard exports; no public sample is obtainable; D-7's gate therefore blocks
  all four.
- **What the 2026-09-11 search found (docs/RESEARCH-gateway-samples.md):** two real committed
  PhonePe merchant exports with 1,038 data rows (which also resolve the undocumented `PaymentType`
  values and date formats D-19 was blocked on); a real Cashfree recon export proving 63 columns,
  not 48; two official PayU settlement **APIs** with complete documented sample JSON; and a
  readily-fetchable Juspay docs page with the full 25-column schema.
- **Why D-24 was wrong:** it searched for a *CSV* for PayU, and no CSV can exist — PayU's export
  columns are chosen per merchant in a dashboard dialog, so the correct target was always the API.
  For PhonePe it appears no one had looked at committed merchant exports in unrelated repositories.
- **Consequence:** PhonePe is now wired (with the per-settlement netting the file shape requires);
  PayU's fix is API parsers; Cashfree recon needs a two-section parser; IDFC remains genuinely
  deferred — for IDFC the gate held up.
- **Lesson for this repo:** "not publicly available" is a conclusion that expires. Re-test a
  blocking claim before treating it as a constraint, and record *what was searched*, not just the
  verdict — the negative results in the research doc are as useful as the positives.
- **Also decided:** the real files must not be vendored (they carry a named merchant's real UTRs);
  fixtures are regenerated from the real header with invented values, as D-19 did for banks.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-34: The Cashfree recon file is read whole — two sections, two maps, and the flag applies to the SETTLEMENT amount
- **Why:** the export is literally two reports concatenated: a 14-column batch section, the marker
  line `** Settlement Reconciliation Details **`, then a 63-column event section. Reading either
  through the other's map states wrong money confidently, so `load_cashfree_recon_report()` splits
  on the marker first and raises when it is absent.
- **The non-obvious part, and the bug it produced:** the event section has no debit/credit pair.
  Direction comes from `Sale Type ∈ {CREDIT, DEBIT}` and the amount it applies to must be
  `Event Settlement Amount` — the money movement, net of the fee/tax columns beside it and printed
  NEGATIVE on a refund — while `Event Amount` is the gross. The first implementation applied the
  flag to the gross, so netting the event section did not equal the batch total: it was out by
  exactly the fees (5900.00 vs 5881.12 on the fixture). The fix is a separate
  `direction_amount_col`; the check that catches a regression is the fixture assertion that the
  netted event total equals the batch total, which is verified to fail when the column is wrong.
- **Also decided:** the movement is taken as a magnitude and the flag sets the side, so a vendor
  printing a refund as `-100.00` and one printing it `100.00` land identically; and the `UTR` is
  both the line's settlement_utr and its batch key, because the event section carries no batch id.
- **Consequence:** `cashfree_recon_csv` (63 cols) and `cashfree_settlement_csv` (14 cols) are both
  filled, replacing two `None` placeholders.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-35: PayU's settlement CSV is closed as un-wireable BY DESIGN; the two APIs are the surface
- **Why:** PayU's own docs say the export's columns are chosen per report in a dashboard dialog, so
  no fixed public header can exist. Every earlier "no sample file found" conclusion about PayU was
  right in outcome and wrong in reasoning — the search could not have succeeded, and recording it
  as a search gap is what made the next session search again.
- **Instead:** `parse_payu_settlement_range` (UTR-level → `Settlement`: `settlementAmount` is the
  net credited to the merchant's bank account and `utrNumber` is the bank reference, so these rows
  reach `match()` at level 1 rather than through the amount+date fallback) and
  `parse_payu_transaction_details` (per transaction → `ReconLine`; `settlementAmount` arrives as a
  JSON number and SIGNED, so the magnitude goes to `amount` and the sign to debit/credit).
- **Fail-closed, deliberately:** PayU's `status: 1` envelope raises with PayU's own message, and an
  unknown field raises. A vendor adding a field is a schema change, and ignoring it silently is how
  a reconciler ships wrong numbers after a release nobody connected to the vendor.
- **Rejected:** leaving `payu_settlement_csv` open "awaiting a sample". It can never be filled.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-36: Juspay is wired with its limits written into the loader, not left awaiting a perfect file
- **Why:** the 25-column schema is officially documented and Juspay's own production parser names
  the columns it reads, so refusing to build would preserve the blocker, not the correctness.
  Nothing here is guessed: every column name is transcribed from one of those two sources.
- **What is still NOT verified, stated in the loader docstring and in SCHEMAS.md:** the money unit
  (the docs say only "Integer" while Juspay's own parser reads plain rupee decimals → rupees, a
  corroboration rather than a documented fact); one `Settlement Date` being one bank credit for the
  documented variant, which has neither a batch id nor a UTR column to key on; and the status
  filter (only `Settled` means funds reached the bank).
- **Consequence:** a Juspay reconciliation is a run that needs review until a real file and its
  matching bank credit agree. An unrecognised `Settlement Status` raises instead of being silently
  included or dropped, because a row filtered out by a guess is an error nobody ever sees.
- **Rejected:** a `juspay_recon_csv` map from the HyperPG column set. It has no real file behind it
  either, and two speculative maps is twice the unverified surface with none of the evidence.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-37: The product is named **Conjunction**
- **Who:** Sanjay chose it himself on 2026-09-11 from three finalists presented with their costs.
  The agent gathered the evidence and recommended; it did not decide — he names products.
- **Why it won:** the astronomical term for two bodies appearing aligned is literally what the
  product does (a gateway settlement and a bank credit made to agree); it fits the family register
  (Nova, Kessler); it is **free on PyPI**; and no notable company uses the word.
- **The evidence it was decided on** (`docs/NAMING-SHORTLIST.md`): PyPI availability for nine
  candidates, domain registration via RDAP with controls run first, and the free compound `.com`
  forms. Two corrections that mattered: the `.io` results were **discarded** because a control
  (`github.io`) returned 404, so nine candidates falsely looked "available" — a broken lookup, not
  luck; and no registry trademark search (IP India / TMview, classes 9/42) was run, so brand
  clearance is stated as open rather than implied.
- **The cost, accepted and stated once:** it is a common English word, so it will be hard to rank
  for and ambiguous in conversation. Mitigation is a compound domain plus always pairing the word
  with its category, the way Stripe pairs with payments.
- **Rejected:** Equinox (Equinox Group's brand fan-out, and a well-known JAX library), Pulsar
  (Apache Pulsar owns developer mindshare; also a watch brand), Syzygy (SYZYGY AG is listed on the
  Frankfurt exchange; unspellable) — Syzygy stays available as the three-way-match feature name.
- **Consequence:** `settleflow` becomes a deprecated placeholder. The rename is planned in
  `docs/NAMING-SHORTLIST.md` in an ordered sequence (repo first and verified, then the live host)
  and is deliberately **not executed**: the last step moves `/opt/settleflow` and the systemd unit,
  which needs the deploy script's path allowlist changed by hand, and a rename that drifts is how a
  live service quietly stops being deployable. It lands as D-38 when it is done.
- **Model:** deepseek-v4.1-flash. **Date:** 2026-09-11.

### D-38: Strix is the independent security gate, and a gate that finds issues must FAIL

- **Decision.** The Strix OSS CLI runs in `.github/workflows/security.yml` as this project's
  independent security gate, on `pull_request`, on `push` to `master` (the branch we actually deploy
  from — `pull_request`-only was watching a door nobody uses), and on `workflow_dispatch`. Exit
  code **2 (vulnerabilities found) fails the build**; artifacts are uploaded on both paths so a
  failing gate is always actionable.
- **Why the exit-2 branch is load-bearing.** The first version only echoed a `::warning` and fell
  through. The first real scan then concluded **success** while its artifact held 12 findings
  (1 high, 5 medium). A gate that finds issues and reports success is worse than no gate: it
  manufactures false assurance, and it teaches everyone to ignore CI. The rule is general — a
  security gate's pass must mean *no findings*, never *the job didn't error*.
- **Why an independent scanner at all.** It found a latent `NameError` in a shipped SBI parser, a
  `Date`-boolean-to-money path, and CSV formula injection surviving a leading `-` — none of which
  our own 74-check self-check or the in-session manual review caught. The self-check asserts what we
  thought to assert; an adversarial scanner tests what we didn't.
- **Consequence.** A green security run is a claim about *what was analysed*, not a statement that
  the project is secure — and it must be read via the artifacts, not the conclusion. The artifact
  expires after 30 days, so findings get a durable copy outside the repo.
- **Model:** claude-opus-5. **Date:** 2026-09-11.

### D-39: Strix runs on CommandCode via `LLM_API_BASE`, and not on a thinking-mode model

- **Decision.** `STRIX_LLM=openai/zai-org/GLM-5.3`, `LLM_API_BASE=https://api.commandcode.ai/provider/v1`,
  `LLM_API_KEY` from the `COMMANDCODE_API_KEY` repository secret. The model id is not a secret and
  lives in the workflow file where it is reviewable.
- **Why not a direct vendor key.** The configuration inherited from the skill used a direct
  `deepseek` key with no balance, so every run died at `LLM CONNECTION FAILED` and `master` was red
  for a billing reason, having scanned nothing. CommandCode is the OpenAI-compatible gateway already
  configured in Hermes, so it needs no new account or secret beyond the key Hermes already holds.
- **The env var name is `LLM_API_BASE`** — the documented one. `OPENAI_BASE_URL`/`OPENAI_API_BASE`
  are not read.
- **Why GLM-5.3 and not deepseek-v4.1-flash.** deepseek-runs in **thinking mode**, and Strix's
  OpenAI client does not pass `reasoning_content` back on the follow-up turn: the gateway's fallback
  path dies with `400 "The reasoning_content in the thinking mode must be passed back to the API."`,
  usually preceded by a `429 Provider is at capacity` on the first attempt. That is structural, not
  transient — the first scan succeeded only because its first provider attempt happened to land, and
  the next one failed after 27 minutes. GLM-5.3 is Strix's own documented default and was verified
  against this endpoint (200, `finish_reason=tool_calls`, correct arguments) before wiring; Strix is
  entirely tool-driven, so real tool calls matter more than a chat reply.
- **Verified-working substitutes** if it needs swapping: `moonshotai/Kimi-K3`, `Qwen/Qwen3.8-Max`,
  `xiaomi/mimo-v2.5-pro`. **Plan-gated, do not use:** `claude-sonnet-5`, `gpt-5.5`
  (both `403 MODEL_NOT_IN_PLAN`).
- **Consequence.** Sanjay's standing "no deepseek for agentic work" rule turned out to be right for
  a reason nobody had articulated: the thinking-mode round-trip breaks the client.
- **Model:** claude-opus-5. **Date:** 2026-09-11.

### D-40: The Strix findings come BEFORE the deploy, but the deploy is still worth doing first

- **Decision.** The deploy target (`acc5275`) ships as-is once Sanjay authorises it, and ATL-242 is
  remediated as the next unit of work, followed by a second deploy. Ordering is deliberate:
  **deploy → remediate → deploy**, not "remediate everything then deploy once".
- **Why deploy first, given a HIGH is open.** The live build is strictly worse: it additionally
  lacks the whole-request size cap and keys the rate limit on caller-controlled input, so it carries
  every defect in ATL-242 *plus* the ones already fixed. Deferring the deploy to fix the HIGH leaves
  the exposed build in place for longer. Deploying is a strict reduction in exposure, not a
  regression.
- **The premise that decides severity, and how it is settled.** vuln-0010's exploitability rests on
  whether a caller can supply `CF-Connecting-IP` through the Cloudflare tunnel. Source review cannot
  observe that; only a live probe from outside can. Until it is probed, the finding is stated as
  conditional rather than as a live incident. If it IS reachable, the rate-limit fix (D-38's sibling
  work) and the identity-independent ceiling become the top priority, ahead of everything else.
- **Rejected:** treating the HIGH as blocking all other work. It is one conditional chain in a
  system whose remaining fixes are independent and already verified.
- **Model:** claude-opus-5. **Date:** 2026-09-11.

### D-41: The CF-Connecting-IP premise is settled — CCI is unforgeable through the tunnel; the invariant to keep is tunnel-only ingress

- **Decision.** Recorded from the ATL-244 live probe: the Cloudflare edge rejects (403, error code
  1000) any request carrying a client-supplied `CF-Connecting-IP` before it reaches cloudflared, and
  sets the header itself. `pick_client_ip` (CCI-only) is therefore sound **on this topology**, and
  vuln-0010's HIGH chain does not close from outside. The binding invariant: the origin keeps its
  127.0.0.1 bind and tunnel-only ingress — a future direct exposure re-arms the finding.
- **Why it still matters.** XFF passes through with the caller's value as the FIRST hop (origin
  echo-proved), so live v0.7.3's XFF-keyed limit is bypassable today; this decision raises deploy
  urgency with evidence. It also re-ranks ATL-242: vuln-0002's work-bound fix is the top item, not
  the identity fix.
- **Evidence:** `E:/Sanjay Files/StartUp/open source/strix-settleflow-2026-09-11/PROBE-cf-connecting-ip.md`
  (kept outside the public repo; contains the ingress description, not the origin address).
- **Model:** qwen3.8-flash. **Date:** 2026-09-11.

### D-42: Rate-limit identity is deployment-aware (peer evidence + global window); the PDF/OCR layer gets explicit work ceilings

- **Decision (identity).** Strix's suggested fix for vuln-0002 gated the trusted header on a
  LOOPBACK peer — correct for the live topology (verified on the box: settleflow.service runs
  plain uvicorn on 127.0.0.1:8093, cloudflared connects from loopback), but it breaks the repo's
  own documented Docker path: with userland port-mapping the container-side peer of EVERY
  connection is the bridge gateway (172.17.0.1) — private, constant, never loopback — and a
  loopback-only gate would collapse all clients into one shared bucket there. `pick_client_ip
  (headers, peer)` therefore trusts `CF-Connecting-IP` only when the peer is an INTERMEDIARY
  (loopback or RFC1918/link-local) — the address D-41 proved the edge sets — and keys a PUBLIC
  peer on its own socket address, which its owner cannot mint per request. IPv6 spellings
  canonicalize to one bucket. `SETTLEFLOW_GLOBAL_RATE_LIMIT_PER_HOUR` (600) adds the
  identity-independent window (vuln-0010's chain-breaking half): the per-identity key can be
  minted away, this cannot.
- **Decision (work bounds).** The upload caps bound bytes, not work. `MAX_STATEMENT_ROWS` (200k
  lines — ~30x the largest real CA statement; a compact-JSON payload cannot exceed ~190k items
  inside the same 10MB cap, so one check bounds both sides) refuses over-wide uploads with a clear
  400; `reconcile` became a synchronous handler (FastAPI thread pool — the event loop stays
  responsive: health worst 594ms during a 150k-row run, previously a 6.3s full stall) under a
  2-slot semaphore (3 concurrent heavies -> 303/303/429). The PDF/OCR layer (library-only, not
  reachable from the hosted route) gets: 50 pages, 2MB decoded content-stream per page (stored
  compressed length never trusted), 2M accumulated text chars, 40MP raster ceiling computed BEFORE
  get_pixmap (MediaBox is author-chosen), per-page temp-dir release, and a 120s tesseract timeout
  surfaced as `PdfResourceLimitError(ValueError)`. Residual, stated: one page's parse cost cannot
  be bounded inside the process — untrusted-file callers run that layer under an external memory/
  CPU limit. Prod runtime is settleflow.service (plain uvicorn, NOT docker — the compose file is
  a dev artifact), so a compose MemoryLimit would be dead weight; recheck at scale.
- **Why.** Both write-ups' suggested fixes were verified against a topology the service does not
  run; the shipped rules are the deployment-aware generalisations, each with a live gate and a
  self-check assert.
- **Model:** qwen3.8-flash. **Date:** 2026-09-13.

### D-43: The Strix CI gate is retired — a permanently-red gate is worse than no gate

- **Decision.** `.github/workflows/security.yml` deleted (reference wiring: `git show
  3407a5c:.github/workflows/security.yml`); its three repo secrets removed. If a scan is wanted
  again: fund one, run it manually at a milestone, keep the old exit-code + `run.json` discipline.
- **Why.** One completed `quick` scan earned the tool its place once: 12 real defects (1 high,
  5 medium) that the manual review and the 74-check self-check missed — all fixed and shipped
  with live-gated evidence (D-38…D-42, 0.7.5). But the ongoing cost is ~85M tokens per scan with
  no funded provider: CommandCode is bankrupted and Nous needs an owner-minted static key, so the
  job could not run — and a red ✗ on every push that proves nothing about security trains
  contributors and visitors to ignore red. ATL-242 closes on the per-fix live gates, not on a
  re-scan that cannot run.
- **Rejected:** keeping the workflow "for when a key arrives" — dead CI is not a placeholder,
  it is noise on a public repo's landing page.
- **Model:** qwen3.8-flash. **Date:** 2026-09-13.
