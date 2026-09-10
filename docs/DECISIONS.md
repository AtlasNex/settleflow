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
