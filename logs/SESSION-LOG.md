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

## 2026-08-24 — Session 10 ("fix all" — IST epoch, date format, CLI PDF gating)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** "Fix all, complete all." Fixed the remaining gaps from the D-25 stress report:
  (1) `_epoch_date` -> IST (+05:30) so the (amount,date) fallback aligns with Indian bank
  statement dates (was one day off near midnight UTC); (2) `parse_date` accepts `%d-%b-%y`
  ("01-Jul-25"); (3) CLI `--bank != sbi` + .pdf now raises a clear error instead of a
  confusing SBI-layout error. Added 2 permanent self-check tests (IST epoch + two-digit
  month name; CLI PDF gating). Version 0.7.1 -> 0.7.2. Self-check 39 -> 41.
- **Deliberately kept (documented D-26):** `_is_money` exactly-2-decimals (a numeric refno
  would be misread as money if widened); DUPLICATE_SUSPECT conservative over-flag.
- **Deferred (needs inputs):** Cashfree/PhonePe/Juspay/PayU + IDFC parsers (real dashboard
  exports); OCR scanned PDFs; hosted SaaS deployment.
- **Verified:** 41/41 suite; both D-25 stress harnesses were already green; hermes verify
  --skip-start green (0.7.2 wheel). Commit follows.

## 2026-08-24 — Session 11 (OCR via Tesseract + SaaS deployable)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** Sanjay challenged the "OCR = separate build / SaaS = not a library fix"
  deferrals and corrected me that Tesseract is already installed (C:/Program Files/
  Tesseract-OCR/tesseract.exe, not on bash PATH; S1 used it). PIVOTED off a custom
  RapidOCR+parser approach (uninstalled rapidocr_onnxruntime/onnxruntime/opencv/pyclipper/
  flatbuffers; removed parse_ocr_statement). Built OCR on Tesseract via subprocess: new
  settleflow/ocr.py (ocr_pdf_text, parse_sbi_scanned_pdf, OcrUnavailableError, OcrError,
  optional [ocr] extra = pymupdf), parse_sbi_pdf(path, ocr=True) auto-fallback, CLI --ocr.
  Verified: scanned PDF -> PdfScannedError -> tesseract -> native parse (2 rows); CLI
  --ocr reconcile 2/2 matched. SaaS: added Dockerfile + docker-compose.yml (127.0.0.1:8091)
  + .dockerignore; booted locally, /health 200 {"status":"ok","version":"0.7.3"} (fixed
  stale hardcoded "0.3.0"). Version 0.7.2 -> 0.7.3, self-check 41 -> 42.
- **Deferred:** live VPS host deploy (needs a confirmed target + Cloudflare Tunnel/port);
  Cashfree/PhonePe/Juspay/PayU+IDFC parsers (real dashboard exports).
- **Verified:** 42/42 suite; import smoke (ocr exports, no circular import); Dockerfile/
  compose READY; uvicorn /health green. Commit follows.

## 2026-08-25 — Session 12 (live deploy: settleflow.atlasnex.com via systemd + CF tunnel)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** Sanjay: "i already have a domain na. can u use that or what?" — yes, and did.
  Loaded the cloudflare-vps-deploy pattern (CF Tunnel -> VPS localhost). Probed the VPS
  (root@<vps-host>:<port>: Ubuntu 24.04.4, Docker 29.7.2, cloudflared). The existing
  `atlasnex-vps` tunnel already maps trade-ui -> 127.0.0.1:8091, so chose host port **8093**
  + subdomain **settleflow.atlasnex.com**; set docker-compose.yml to 8093. Shipped context
  to /opt/settleflow. `docker compose up -d --build` **FAILED** — this LXC has **no
  AppArmor** (even `--security-opt apparmor=unconfined` fails), so Docker build can't run.
  PIVOTED to the proven hot-patch: wrote the systemd unit `settleflow.service`
  (`uvicorn saas.app:app --host 127.0.0.1 --port 8093`, venv /opt/settleflow/.venv),
  enabled it -> service active, internal /health 200. Created the DNS CNAME
  `settleflow.atlasnex.com -> 9a8936c6-…cfargotunnel.com` (proxied). Added a local ingress
  + restarted cloudflared -> external **404**. DIAGNOSED: cloudflared is REMOTE-managed
  (log "Updated to new configuration ... version=10"; the local config.yml edit was
  ignored). Fixed via `PUT /accounts/{acct}/cfd_tunnel/{tun}/configurations` to add
  `settleflow.atlasnex.com -> http://localhost:8093` (plus the CNAME/proxy).
- **Verified:** internal `curl 127.0.0.1:8093/health` 200; external
  `https://settleflow.atlasnex.com/health` -> {"status":"ok","version":"0.7.3"} 200;
  external `/` renders the UI. Re-verified at session end (still 200).
- **Decisions (D-28):** hot-patch over Docker on this LXC (AppArmor-blocked build);
  remote-managed CF tunnel -> any ingress change via the API, never local config.yml;
  port 8093 (8091 is trade-ui's slot), bind 127.0.0.1 only.
- **Deferred:** SaaS auth/login + landing polish (not requested); Cashfree/PhonePe/Juspay/
  PayU + IDFC parsers (still need one real dashboard export each).
- **Committed:** `aef79db` (port 8093), `3a0a818` (docs D-28). Version stays 0.7.3.

## 2026-08-25 — Session 13 (docs closeout: log every session + refresh handover)

- **Model:** deepseek-v4-flash-vision-exp. Provider: opencode-go.
- **Did:** Sanjay: "Do all logs in docs. all the convo logs and all." Compared git log
  against logs/SESSION-LOG.md — Sessions 1-11 were logged but the **live-deploy** session
  (aef79db/3a0a818, D-28) was not. Added Session 12 (live deploy). Confirmed D-28 is in
  docs/DECISIONS.md. Refreshed docs/HANDOVER.md ("Current state" date 2026-08-21 ->
  2026-08-25; refreshed the stale git-history line). Cleaned the stray temp
  `settleflow.service` (already deleted) and re-confirmed git clean, tree in sync with
  origin/master, and the live endpoint still 200.
- **Verified:** `hermes verify --skip-start --json` green (bootstrap settleflow-0.7.3,
  test 42/42, source: manifest); `/health` 200. Commit follows.

## 2026-09-11 — Session 14 (hosted-layer hardening + publish the repo)

- **Model:** deepseek-v4.1-flash. Provider: nous.
- **Asked:** "Work on Settleflow. Complete it end to end. 100%." with the six-phase prompt
  written in the previous turn. NexTrade parked (no capital) and left alone.

- **Did (Phase 1, the blocker):** `/runs` and `/runs/<id>/export/*.csv` were public and
  unauthenticated, enumerable by integer id — every uploaded statement's matched UTRs, amounts
  and exception text were readable by anyone. Replaced with a per-run capability URL
  `/r/<token>` (~144 bits, D-29). Also fixed a genuine correctness bug: every upload was written
  to ONE fixed path (`saas/upload_bank.csv`), so concurrent reconciliations clobbered each
  other's statement. Plus upload caps, suffix checks, 400s that name the columns found, enforced
  30-day retention (the disk is at 91%), per-IP rate limiting (60/h), and Swagger/redoc off.

- **Found by probing from OUTSIDE after the fix shipped:** the live site still served the leaked
  CSV. Cloudflare had cached it at the edge — `cf-cache-status: HIT`, `Age: 2079`,
  `max-age: 14400` — because `.csv` is in CF's default cacheable-extension list. **Removing a
  route does not un-publish what the CDN already holds.** Purged via the API (`prefixes`), then
  made run responses `no-store` and added a canary check so it cannot regress silently (D-30).
  This is the single most valuable finding of the session and it came from not trusting loopback.

- **Did (Phases 2-4):** results page with totals/exceptions/downloads; bank-column auto-detection
  with an Advanced override; real pages (`/about`, `/pricing`, `/contact`, `/privacy`, `/terms`)
  plus `sitemap.xml` and `llms.txt`; lead capture (stored + shown honestly, delivery blocked on
  SMTP creds); CONTRIBUTING / SECURITY / issue templates; `brand-context.md`; CI.

- **Published:** repo flipped PUBLIC (owner-approved), release `v0.7.3`, CI green 6/6 including a
  job that boots the app and runs the end-to-end canary on a clean runner. Before flipping, a
  secret scan over the tree and full history (clean) — and one real find: `scripts/deploy.sh`
  hardcoded the origin IP, which is deliberately absent from public DNS. Committing it would have
  handed out a route around the Cloudflare rules in front of the origin. Redacted; host now comes
  from env (D-31).

- **Did (Phase 5):** `scripts/deploy.sh` (idempotent, refuses on red self-check, backs up,
  restarts, asserts health + canary + public URL) and `scripts/rollback.sh`. A 15-minute Hermes
  watchdog runs the canary against the public URL with Telegram alerting.

- **The rollback drill earned its place.** Running `rollback.sh latest` for real exposed two bugs:
  `--list` fell through and was treated as a target, and it validated the restored release with
  the canary *inside the archive* — so a drill passes while the release is broken, because the old
  tool shares the old release's blind spot (D-32). Fixed and re-verified live.

- **Fixed from the delegated content work (checked files, not the summary):** the CI workflow
  targeted branch `main` (repo is `master`, so it would never have run on a push) and its
  zero-dependency job failed on any Windows machine because `pywin32` bootstraps itself before
  user code — a permanently-red check teaches people to ignore it. Replaced with
  `tests/test_zero_dependency_core.py`, which diffs what *settleflow* imports. Also the README's
  headline example called `result.unmatched`, which does not exist on `ReconResult` — the first
  code a stranger would run raised `AttributeError`.

- **Verified:** `python tests/test_matching.py` → 50/50 (was 42). A 40-check local battery
  including a 12-way concurrent-upload regression (12 distinct tokens, zero cross-contamination).
  Live from outside: the six leak paths 404, run responses no-store, pages 200, GitHub release and
  raw LICENSE 200 anonymously. Full item-by-item record: `docs/COMPLETION.md`.

- **Not done:** PayU/PhonePe/Juspay/Cashfree parsers (`docs/RESEARCH-gateway-samples.md` — a
  guessed schema is forbidden and is how silently wrong ledgers get made), PyPI (no account/token),
  workpaper email delivery (Proton SMTP creds), Cloudflare managed-robots.txt (zone policy),
  uptime-kuma monitor (no login). Each is named in COMPLETION.md with what would unblock it.

## 2026-09-11 — Session 14 CLOSEOUT ADDENDUM (post-mid-session state)

The Session 14 entry above was written mid-session. This addendum records what happened after it,
so the log matches the shipped state. Final revision at close: **`7344c30`** (13 commits in session).

- **PhonePe settlement is WIRED** (`load_phonepe_settlement_csv`). The research subagent proved
  `load_csv(file, utr_col="BankReferenceNo", amount_col="Amount", date_col="SettlementDate")` reads a real
  merchant export (418 rows). But a map alone would have been *harmful*: PhonePe's report is one row per
  transaction while a bank credit is one per settlement, so the rows are netted
  (`Amount + Fee + IGST + CGST + SGST`) per `BankReferenceNo` before the matcher sees them — otherwise it
  is a wall of false unmatched rows and the (amount, date) fallback can pair the wrong ones. Two new
  checks cover it (aggregation + a malformed date raising a named ValueError). **Caveat kept in the
  docstring: the aggregate has never been compared against a real bank credit.**
- **Corrected a wrong claim made by the research subagent** — and this one matters more than it looks.
  Its report stated `gh search code` returns `[]` silently because the token lacks `read:user`. Re-tested:
  **false.** The same token returns hits for `BankReferenceNo`, `PhonePeReferenceId`,
  `Merchant_Settlement_Report`, `AXNPN`. Real mechanism, reproduced exactly:
  `gh api -f q='cashfree settlement csv parser'` (terms ANDed) → **122**, vs
  `q='"cashfree settlement csv parser"'` (literal phrase) → **0**. It read its own phrase-miss as a
  permissions bug. Fixed in `docs/RESEARCH-gateway-samples.md`, and the rule recorded in the
  `research-source-access` skill: **an empty code-search result is never evidence of absence** — that is
  exactly the error D-24 made, and it gated the parser work for weeks.
- **Decisions added:** D-29 (capability-URL access model), D-30 (no-store + the CF cache finding),
  D-31 (origin host never committed), D-32 (canary must do a real reconcile), D-33 (D-24 was partly
  wrong; a negative result expires).
- **Delivered and pushed:** `scripts/deploy.sh`, `scripts/rollback.sh`, `scripts/canary.py`,
  `tests/test_zero_dependency_core.py`, `.gitattributes`, `docs/COMPLETION.md`,
  `docs/RESEARCH-gateway-samples.md`, `brand-context.md`, `docs/legal/*`, CONTRIBUTING/SECURITY,
  `.github/` templates + CI, README rewrite, and the two prompt docs.

### Verification at close (all re-run, unpiped)

| Check | Result |
|---|---|
| `python tests/test_matching.py` | **52/52 passed** (was 42 at session start) |
| `python tests/test_zero_dependency_core.py` | PASS (24 modules, all stdlib) |
| 40-check local battery (input bounds, leak paths, lead capture) | **40 pass / 0 fail** |
| 12-way concurrent-upload regression | 12 requests → 12 distinct tokens → **0 cross-contamination** |
| `hermes verify --skip-start --json` | `ok: true`, source=manifest, bootstrap exit 0, test exit 0 |
| GitHub CI | **6/6 jobs success** |
| Live canary (public URL) | **5/5 PASS** |
| `/health` | `{"status":"ok","version":"0.7.3","runs":56,"retention_days":30}` |

### Two process-level findings from the verification pass

1. **A `hermes verify` FULL run left an orphan `uvicorn` holding port 8000** — its command line matched
   the manifest's `start` string verbatim and it was created inside the repo-hygiene subagent's execution
   window. It answered `/health` with **200** while `POST /reconcile` returned **500**: a liveness check
   passing against a broken *stale* process. My first canary run hit that orphan, not my code; I isolated
   it (killed the listener, re-booted the current revision on the same port) and re-proved 5/5. The
   `hermes-verify` skill now records both the orphan hazard and the "kill the listener PID, not the
   wrapper" rule.
2. **Piping a verification script through `tail` masks its exit code.** A run that printed `fail=3` and
   internally exited 1 was reported as "exit code 0" — the pipeline returns the last command's status.
   Re-ran unpiped so the exit code means something.

### Open thread carried forward (Sanjay's outstanding request)

He asked for the **product name**: *"think of names from space, like how OpenAI and Anthropic names their
products, also we have similar projects Nova and brand new one Kessler."* The session ended before this
was answered. `settleflow` remains the documented placeholder (`CONSTRAINTS.md` #10 forbids renaming
without a diff + `DECISIONS.md` entry). A starter shortlist (Conjunction, Equinox, Parallax, Pulsar,
Epoch, Syzygy) and the full rename blast-radius list are in
`docs/PROMPT-continue-settleflow.md` §1. **He chooses the name — present finalists, do not decide.**

### State at close

Repo `7344c30`, in sync with origin, working tree clean, **PUBLIC** (MIT), release `v0.7.3`.
No background processes or orphaned listeners left on the laptop; VPS services
(`settleflow`, `s1-capital-map`, `nextrade-terminal`, `cloudflared`) all active.

## Session 15 — 2026-09-11 — the three unblocked gateway parsers wired

Sanjay: *"Continue working on Settleflow."* Baseline checked before touching anything:
`python tests/test_matching.py` -> all 52 checks passed, and
`python scripts/canary.py --base https://settleflow.atlasnex.com` -> 5/5 PASS on v0.7.3.

**Shipped** (self-check 52 -> 64 checks; zero-dependency core still green):

| Vendor | What landed | Evidence |
|---|---|---|
| Cashfree | `load_cashfree_recon_report()` reads both sections of the two-report file (14-col batches / marker / 63-col events); `split_cashfree_recon_report()` raises without the marker | `tests/fixtures/cashfree/settlement_recon_synthetic.csv` -> 2 batches, 3 lines, batch total == netted event total (5881.12) |
| PayU | `parse_payu_settlement_range` (UTR-level -> `Settlement`) and `parse_payu_transaction_details` (signed -> `ReconLine`), both fail-closed | `tests/fixtures/payu/*.json`, incl. a `match()` run that pairs both settlements to bank lines at `MatchStatus.EXACT` |
| Juspay | `load_juspay_settlement_csv()` nets per bank credit for both real variants (documented 25-col; the `UTR Number` variant Juspay's own parser reads) | `tests/fixtures/juspay/*.csv` -> 1296.93 by date, 897.64 by UTR |

Also: `ReconColumnMap` gained `direction_col` / `direction_amount_col`, and the two CSV row
builders were split out of `load_csv` / `load_recon_csv` so a multi-section file can reuse one
map per section instead of duplicating the loop.

**The bug the fixture caught, worth remembering.** Cashfree's event section has no debit/credit
column pair, so direction comes from `Sale Type`. The first implementation applied that flag to
`Event Amount` (the gross). Netting the event section then missed the batch section's total by
exactly the fees — 5900.00 against 5881.12. Credit/debit have to carry the money MOVEMENT
(`Event Settlement Amount`, printed negative on a refund); `amount` stays the gross. Fixed with a
separate `direction_amount_col`. The assertion that catches a regression is the fixture's
"batch total == netted event total", and it was **mutation-probed**: swapping the column makes it
fail, so the check is known to be sensitive rather than merely green.

**PayU's CSV is un-wireable by design, not un-found.** Their export lets the merchant pick the
columns per report, so no fixed public header can exist — every earlier "no sample file found"
conclusion was right by outcome and wrong by reasoning, and that is what sent the previous
session searching again. Recorded as D-35.

**Juspay is wired with its limits written down.** Three assumptions are named in the loader
docstring and in SCHEMAS.md instead of being hidden: the rupee unit (the docs say only
"Integer"; Juspay's own production parser reads rupee decimals), one `Settlement Date` being one
bank credit for the variant with no UTR column, and the `Settled`-only status filter. No real
populated Juspay file has been seen — a Juspay run needs review until one and its bank credit
agree (D-36).

**Fixtures.** Synthetic rows on real verbatim headers (D-19), with a NOTICE.md per vendor. The
real Cashfree and PhonePe exports were deliberately NOT vendored: they carry a named merchant's
UTRs and order references. Juspay's column names came from AGPL-3.0 vendor code — names
transcribed, no code copied.

**Commits:** `22db550` (parsers + fixtures + tests), `d022dec` (SCHEMAS.md, incl. the 63-not-48
column correction), `fd2c538` (DECISIONS D-34/D-35/D-36), plus the handover and this log entry.

**Not deployed, no version bump:** the change is library-level and `saas/app.py`'s own column
detection is untouched, so the live service is unchanged on 0.7.3. A release tag is a separate
call for Sanjay.

**Still open (unchanged by the parser work):** IDFC statements (no real public sample exists — the
gate held), Cashfree's plain settlements report (no public column table; use its JSON API), and
PhonePe's per-settlement aggregate still unjoined to a real bank credit.

**Named later in this same session:** Sanjay chose **Conjunction** as the product name (D-37), and
the rename plan is in `docs/NAMING-SHORTLIST.md` — planned, deliberately not executed.
