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

## Session 16 — 2026-09-11 — the review, then every finding fixed

Sanjay: *"do a very rigorous, critical review of entire Conjunction/SettleFlow… give me a very
detailed report"*, then *"Fix all"*.

**The review.** v1 of the report leaned on three parallel subagent reviews; they ran past the
session boundary and died without delivering, so v1 was triage of transcript fragments plus spot
checks, and two of its claims outran the evidence. Sanjay pushed back (*"I don't think the review
happened properly. do it again"*) and v2 was run entirely in-session: ~230 HTTP requests against an
isolated local copy, 10 matching edge cases, 6 hash seeds for determinism, 19 hostile
`parse_amount` inputs, 15 `parse_date` inputs, 13 malformed-payload cases, a 50k+50k scale run, an
8-way concurrency test, 20k token draws, and a factual-claim sweep of all 17 doc files.
`settleflow-review-2026-09-11-v2.md` holds it, deliberately OUTSIDE the repo (it is an abuse
write-up and this repo is public).

**v1 claims retracted in v2, two of them my own errors:** the "58MB spooled -> disk exhaustion"
impact (measured 0 MB disk and 0 MB RSS on a 210 MB request — the request was accepted, the
resource cost was not demonstrated); the run-page header conclusion (my probe used a
case-sensitive lookup; re-verified case-insensitively as correct); and a mid-review
"concurrency cross-contamination" finding that I disproved before publishing — it was `'100'` vs
`'100.00'` formatting. v1 also claimed the happy path "works end to end" while its own probe had
printed `location=None` and never fetched the page; v2 actually fetched it.

**Then all of it was fixed**, nine findings plus the minor ones, self-check 64 -> 74:

| Fix | Evidence |
|---|---|
| deploy/rollback no longer ship `saas/*.db` or `.deploy.env`; a tripwire fails the deploy if the run count drops | exact tar membership shows zero db/env entries; remote quoting proved with a stub `ssh`; the tripwire's extraction + verdicts tested against 4 synthetic health bodies |
| rate limit keyed on CF-Connecting-IP only | rotating `X-Forwarded-For`: was 70 ok / 0 rejected, now 60 ok / 10 rejected |
| whole-body request cap | 25MB of unnamed parts was 303, now 413 (via curl; urllib reports an abort on early rejection) |
| `parse_amount` strict; non-finite and absurd money refused | `'Rs.100'` was `Decimal('0.100')`, now `Decimal('100')`; `NaN`/`Infinity`/`1e400`/`1_000`/`١٢٣` all raise |
| wrong-shaped payloads are 400, not 500 | all 8 malformed cases now 4xx (was 4 x 500) |
| CLI refuses a JSON settlement file instead of reporting zero rows | exit 2 with a message on stderr (was exit 0, `settlements : 0`) |
| `exceptions.csv` via csv.writer; CRLF no longer doubled | comma-in-narration rows aligned; no CR-CRLF bytes |
| `match()` linear on duplicate UTRs | 8k: 0.655s -> 0.033s (20x); linear to 32k |
| exports defuse leading `=`/`+`/`@`; money formatting unified | formula cell now quoted-defused; page and CSV agree at `100.00` |
| hosted service exposes all six wired formats | all six kinds accepted (303) against a local boot |
| docs: ROLLBACK/README/BUG/ARCHITECTURE/TESTING/MASTER-PLAN/CONSTRAINTS + 6 stale test counts | every count now says "the command prints it" |
| CI: security scan runs on master too, least-privilege token, installer pinned to the real v1.6.2 tag | `usestrix/strix` v1.6.2 verified to exist and resolve |

**Two honest notes about this session's process.** (1) I wrote a made-up commit SHA into the
security workflow's pinned installer URL, caught it before committing, verified the real project
(`usestrix/strix`) and pinned to the actual release tag `v1.6.2` instead. A fabricated pin is worse
than no pin. (2) The three subagents never delivered; do not read their absence as their having
found nothing — their assignments (docs vs reality, core-library adversarial, hosted security) are
now covered by direct work, but nothing of theirs was used.

**State at close:** HEAD is the fix series; self-check 74 checks; zero-dependency core green;
canary 5/5 on the live service (which still runs the pre-fix 0.7.3 — nothing was deployed this
session). Board: ATL-234 (review, in_review), ATL-235 (critical deploy + abuse, corrected),
ATL-237 (library/CLI correctness), ATL-238 (this remediation).

## Session 16 (continued) — 2026-09-11 — Strix as an independent second opinion, and the gate that lied

Picked up after the v2 review and its remediation (previous entry). Sanjay: *"Use commandcode for
strix security thing"*, then *"Use deepseek v4.1 flash from commandcode"*, then *"is strix done?"*,
then *"Devise out a plan to finish the remaining tasks"*.

### What the Strix work actually produced

**A working security gate that had never run, and then a finding that the gate itself was lying.**

Wiring: `STRIX_LLM` now points at CommandCode (the OpenAI-compatible gateway already configured in
Hermes) via **`LLM_API_BASE`** — the documented env var, not `OPENAI_BASE_URL`. The first attempt
followed the shipped skill verbatim, which configures a direct vendor key and no base URL, and the
inheritied `deepseek` key had **no balance** — so every run died at `LLM CONNECTION FAILED` and
`master` was red for a billing reason, having scanned nothing.

Model selection was done on evidence, not preference:
- `claude-sonnet-5`, `gpt-5.5` → **403 MODEL_NOT_IN_PLAN** on this CommandCode plan.
- `deepseek/deepseek-v4.1-flash` → 200 with real tool calls, so it was wired first.
- It then **failed mid-scan** (run `34600087325`, 27 min): `400 "The reasoning_content in the
  thinking mode must be passed back to the API"`, preceded by `429 Provider is at capacity`. That is
  a thinking-mode model against a client that does not round-trip `reasoning_content` — structural,
  and it surfaces on the *retry*, so the first run (49 min, 12 findings) succeeded only because its
  first provider attempt happened to land. Swapped to **`zai-org/GLM-5.3`** (Strix's own documented
  default, verified 200 + `finish_reason=tool_calls`). Verified-working substitutes if needed:
  `moonshotai/Kimi-K3`, `Qwen/Qwen3.8-Max`, `xiaomi/mimo-v2.5-pro`.

**The finding that matters most: the gate reported success while hiding 12 vulnerabilities.**
Run `34595883781` (49 min, on `b14c87a`) concluded **success** while the artifact held
**12 findings — 1 high, 5 medium, 5 low, 1 info**. Cause: the `case` branch for exit code 2 only
echoed a `::warning` and fell through. A security gate that finds issues and reports success is
worse than no gate, because it manufactures false assurance. Fixed in `264c254` (exit 2 now fails).

**Findings (durable copy: `E:/Sanjay Files/StartUp/open source/strix-settleflow-2026-09-11/`, 19
files, 2.6 MB — the CI artifact expires in 30 days; also filed as ATL-242).**

Independently reproduced by us, so these are facts not claims:
- `parse_sbi_netbanking` uses `date.today()` but `pdf.py` imports only `re` + `pymupdf` →
  **`NameError: name 'date' is not defined`** on an SBI netbanking statement with no recoverable
  year. A latent crash in a shipped parser that 74 self-checks never touched.
- `_paise(True) -> 0.01`, `_paise(False) -> 0` — a JSON boolean silently priced as money.
- CSV formula injection **survives for a leading `-`**: `'-2+3'` is written unneutralised, while
  `=`, `+`, `@` are defused. Our own code comment called leaving `-` alone deliberate; Strix is
  right and the rationale was wrong (`-2+3` evaluates in Excel).
- `POST /r/{token}/notify` (`saas/app.py:1129`) has **no rate limit** and writes an unpruned
  `leads` row per call; the required token is free from the unauthenticated reconcile endpoint.

Not yet reproduced (recorded as unverified, NOT as fact): 0006 (quadratic narration reassembly),
0008 (money bound skipped in text/SBI parsers), 0011 (notify email recipient injection),
0012 (PDF/OCR resource exhaustion), 0003 (some malformed inputs still 500).

The **HIGH** (0010) is an availability chain: the rate-limit identity is caller-supplied, and one
8.5 MB upload inside every advertised limit blocks the single worker ~7 s, allocates ~881 MB peak
and writes ~72 MB durably. Measured: 4 concurrent worst-case requests with rotating identity → 28 s
at a full core, `/health` answered 7 times, DB +289 MB (~37 GB/h if sustained). **Whether a caller
can supply `CF-Connecting-IP` through the Cloudflare tunnel is the premise, and only a live test
settles it.** That is the single most important open question from this scan.

What the scan **confirmed as already solid** (it tried to refute and failed): the whole-request size
cap added earlier this session, per-run token authorization, template auto-escaping, export-route
SQL — and no SQL injection, XSS, SSRF, XXE, deserialization or path traversal anywhere. Its own
summary: confidentiality and auth controls are strong, **resource bounding is the weakness**.

### Deploy recommendation revised

`b14c87a` was intended to be the deploy target. It is still a **strict improvement** over live
(the live build additionally lacks the whole-body cap and has the spoofable rate-limit identity),
but it is **no longer the end state**: the HIGH is reachable on it. Sequence becomes
**deploy → remediate ATL-242 → deploy again**, not one deploy closing the security work. Still
Sanjay's call; nothing was deployed.

### Discipline notes (things done or caught late)

- A commit message asserted the >1 MB field returned the branded page. It did not — raw framework
  JSON, because FastAPI matches exception handlers by exact class and the multipart parser raises
  *Starlette's* exception. Fixed properly, then re-verified.
- Enabling the scan on `master` turned it red for a billing reason; the gate now distinguishes
  "did not run" from "found nothing", which are otherwise indistinguishable from outside.
- The `case` exit-2 branch was written to warn rather than fail. Caught only because a real run
  produced real findings.
- The 3-subagent delegation dispatched at 05:31 finally reported at the end of the session:
  `outcome unknown — delegation owner exited before recording a terminal result`. As suspected, it
  delivered nothing. Not re-dispatched: the review it fed was redone in-session, and Strix has since
  supplied the independent second opinion it was meant to be.

### State at close

- Repo clean at **`acc5275`** (8 commits this session), pushed, CI green.
- `hermes verify --skip-start` → `ok: true`, bootstrap exit 0, test exit 0, **all 74 checks passed**,
  port 8000 clear before and after.
- Live service untouched at **v0.7.3, 165 runs** (was 147 at session start — ~96/day).
- GLM-5.3 scan `34604701290` in flight at close.
- Board: ATL-234/235/237/238 `in_review`; **ATL-241** (plan to finish, `in_review`); **ATL-242**
  (the 12 Strix findings, `todo`); ATL-218 `blocked` (owner-gated); ATL-230 `todo` (rename).
- Skill `ci-security-scanning-with-strix` corrected: `LLM_API_BASE`, the three failures that
  masquerade as auth errors, the thinking-mode incompatibility, and the gate-killers.

### Session 16 (closeout addendum) — the Strix runs, and the credits wall

Recorded after the main entry, because these outcomes arrived late and a cold session must not have
to rediscover them.

**Three security runs, three different lessons.**

| Run | On | Outcome | Lesson |
|---|---|---|---|
| `34595883781` | `b14c87a` | completed, 49 min, **12 findings** (1 high, 5 medium) — but the job reported **success** | the exit-2 gate was broken and fabricated assurance; fixed in `264c254` |
| `34600087325` | `264c254` | failed after 27 min, `400 reasoning_content ... must be passed back` | deepseek's thinking mode is structurally incompatible with Strix's OpenAI client; swapped to GLM-5.3 in `acc5275` |
| `34604701290` | `acc5275` | failed after 5 min, `400 "You have insufficient credits"` | **a `quick` scan cost 85.5M tokens and drained the CommandCode account** |

**The credits wall is the current blocker on the security gate.** Run 1 consumed 557 requests /
84.75M input (83.45M cached) / 779k output = **85,532,346 tokens**. That is a real cost, and a
`quick` scan is not cheap — worth knowing before anyone re-runs it. Until the account is funded (or
the scan is pointed at another funded provider), the gate cannot run at all.

**What is still unproven:** the exit-2 path. `264c254` made findings fail the build, but no run has
*completed with findings* since, so that branch has never actually fired. Runs 2 and 3 never reached
it. The first run to complete with findings is the proof, and it should be treated as an explicit
acceptance test rather than an assumption.

**The gate's failure behaviour is correct, and worth noting.** All three runs failed loudly and
distinguishably: a connection failure says the scan did not run (rather than reading as "no
vulnerabilities"), and the completion gate reports `run.json` status `failed` and says the run proves
nothing either way. That distinction was worth building — a red job for a billing reason is
otherwise indistinguishable from a red job for a finding.

**Durable artifacts.** All 12 findings, the report, SARIF, `run.json` and the 12 per-finding write-ups
are copied to `E:/Sanjay Files/StartUp/open source/strix-settleflow-2026-09-11/` (19 files, 2.6 MB),
because the CI artifact expires in 30 days and these are an abuse write-up against a public repo.
Filed as ATL-242; the credits blocker was added to the owner-gated list (ATL-218).

**State at final close.** Repo clean at the closeout commit, pushed, CI green apart from the credits
blocker. `hermes verify --skip-start` → `ok: true`, **all 74 checks passed**, port 8000 clear before
and after. Live service untouched: **v0.7.3, 165 runs**. Nothing deployed.

## 2026-09-11 — Session 17 (the probe, the deploy, and the Nous pivot) — glm-5.3-flash

Continued from session 16's cold-start prompt (`docs/PROMPT-continue-settleflow.md`). Model:
glm-5.3-flash (baibase). Board: ATL-244 (probe), ATL-246 (deploy) — both done with evidence
comments.

### 1. The single most important open question is ANSWERED (ATL-244)

**Can a caller supply `CF-Connecting-IP` through the Cloudflare tunnel? → NO.** Method: origin-side
header-echo listener (temp `/tmp/cf_passthrough_probe.py` on the VPS, tunnel ingress retargeted
settleflow→:8097 via CF API `PUT cfd_tunnel/{id}/configurations`, backed up first, restored verbatim
~2 min later, health re-verified after).

- Any request with a client-supplied CCI → **403 `error code 1000` at the edge** (`Server:
  cloudflare`), six value variants, GET and POST. Origin echo log: **zero** CCI-carrying requests
  passed. Cloudflare sets CCI itself.
- **`X-Forwarded-For` IS caller-controlled**: client value passes through as FIRST hop, real IP
  appended (echo-proved).
- Direct-to-origin: port 8093 does not accept internet connections (loopback bind) — tunnel is the
  only ingress.

Consequences: vuln-0010's HIGH chain breaks at its identity link **on this topology** (Strix tested
a local instance with no Cloudflare in front) — but re-arms the moment the origin is ever exposed
directly, so "127.0.0.1 bind + tunnel-only ingress" is a binding deploy invariant (D-41). The bypass
IS live on v0.7.3 via first-hop XFF → deploy urgency raised with evidence. vuln-0002 (amplification:
~7 s stall, ~881 MB peak, ~72 MB durable DB per in-limits request) is unaffected — top ATL-242 item.
Residual: IPv6 callers rotate real CCI naturally → the cost ceiling (0002's fix) is the honest
defense. Evidence: `strix-settleflow-2026-09-11/PROBE-cf-connecting-ip.md` (outside the repo; no
origin IP in it). Also confirmed live `scripts/deploy.sh` was PRE-`7fc77ef` (the DB-overwrite bug was
still armed on the server copy) — fixed by the deploy below.

### 2. DEPLOYED — v0.7.4 is live (ATL-246, Sanjay authorised)

Version bump 0.7.3→0.7.4 (pyproject + `settleflow/__init__.py`, release commit `85a0f2f`) so
`/health` proves the cutover (canary only asserts a version is reported — checked). `bash
scripts/deploy.sh` run (moved to background mid-flight by an incoming message, exited 0); every
claim below verified independently of the script's stdout:

- `/health` → `{"status":"ok","version":"0.7.4","runs":173}`; runs never dropped (169→173; delta is
  canary traffic). Tripwire holds.
- Origin `/opt/settleflow/saas/app.py`: zero `x-forwarded-for` references; `_client_ip` delegates to
  `helpers.pick_client_ip` (`TRUSTED_CLIENT_IP_HEADER = "cf-connecting-ip"`). **Live XFF bypass
  closed.** `__init__.py` = 0.7.4. Backup: `/opt/settleflow-backups/20260911-142122.tar.gz`
  (rollback: `bash scripts/rollback.sh latest`).
- Watchdog canary vs public URL: exit 0, silent = all checks passed. (Running `scripts/canary.py`
  directly FAILS on a laptop — it targets 127.0.0.1:8093; use the wrapper
  `C:/Users/sanja/AppData/Local/hermes/scripts/settleflow_canary.py`.)
- CI green on `85a0f2f` (Security Scan still red on CommandCode credits only).
- `hermes verify --skip-start` → ok:true, 74 checks, port 8000 clear before/after.

### 3. The D-40 order is now mid-flight

deploy ✅ → **remediate ATL-242 (next)** → deploy again (0.7.5). Remediation order on the board:
vuln-0002 (work bounds), 0001/0011 (/notify), 0005/0007/0009, the rest. A second deploy re-arms the
run-count tripwire correctly (it only fails if runs DROP).

### 4. Strix provider: CommandCode is dead, the Nous Portal pivot is half-proven

Sanjay's call: "Run on any free llm from nous. with long context and smart one." Findings:

- Hermes' Nous auth is OAuth at `C:/Users/sanja/AppData/Local/hermes/auth.json`
  (`providers.nous`): 1-h `access_token` + rotating `refresh_token`. The 1-h JWT **works on
  `inference-api.nousresearch.com/v1`**: `z-ai/glm-5.3` → HTTP 200, `finish_reason=tool_calls`,
  correct tool args (the Strix contract, D-39-compatible). `moonshotai/kimi-k3` answered but no
  tool_calls in that probe; `qwen/qwen3.8-max-0902` → 400.
- **A 1-h JWT cannot live in CI** (scan ≈ 49+ min, token expires, and the refresh token ROTATES on
  use — racing it from CI would break this laptop's auth). The static `OPENAI_API_KEY` in .env is
  NOT a Nous inference key (401 invalid/blocked).
- **CI needs a durable Portal API key** (`NOUS_API_KEY` is a supported static credential per
  hermes_cli code + doctor.py). Minting is dashboard-only: portal.nousresearch.com/api-docs ("Manage
  your account and API keys here"). No public mint endpoint found (probed). Browser attempts to open
  the dashboard stalled on Chrome's "Allow remote debugging?" approval — **needs Sanjay's click**.
- **NEXT SESSION, Strix = two owner-gated clicks away:** (1) Sanjay creates an API key at
  portal.nousresearch.com/api-docs (or Settings → API keys), (2) paste it to Hermes (vault), (3) flip
  `security.yml` env: `STRIX_LLM: openai/z-ai/glm-5.3`, `LLM_API_BASE:
  https://inference-api.nousresearch.com/v1`, `LLM_API_KEY: ${{ secrets.NOUS_API_KEY }}` (same
  pattern as the CommandCode wiring in `b14c87a`), commit, watch the run. Know the cost: the last
  `quick` scan was 85.5M tokens; "free" on Nous means billed to the subscription, not unmetered.
  Keep D-39's contract: non-thinking model, tool-calling verified, 403 error-1010 = Cloudflare bot
  wall.

### State at close (2026-09-11, session 17)

- Repo clean at `85a0f2f`, pushed. Live: **v0.7.4, 173 runs**, canary green, watchdog active.
- Board: ATL-244 done, ATL-246 done (evidence comments), ATL-242 has the re-ranked order comment,
  ATL-218 blocked (owner-gated, now including the Portal API key), ATL-230 (rename) still deferred
  behind the real-money trial.
- Cold-start for the next session: `docs/PROMPT-continue-settleflow.md` (updated for this close).

## 2026-09-13 — Session 18 (ATL-242: all twelve findings remediated) — qwen3.8-flash

- **Started** from the session-17 cold-start brief. Verified the recorded way: git clean at
  `1a9c14f`, 74/74 checks, `/health` 0.7.4 / runs 303, CI as expected, ATL-242 todo, D-41 read.
- **Did:** remediated ALL 12 Strix findings in five commits (`b5122b5`, `610b3be`, `7ea65ea`,
  `7437518`, `8cf4d3d`, +D-42 `a200656`), pushed. Highlights and the two design corrections:
  1. **The write-up's loopback gate was wrong for the repo's documented docker topology** — with
     userland port-mapping every container-side peer is the bridge gateway (private, constant),
     so a loopback-only gate collapses all clients into one shared bucket. Shipped rule: CCI is
     trusted for an INTERMEDIARY peer (loopback *or* private — identical outcome on the live
     systemd+loopback box), a public peer keys on itself. Verified on the box that prod is
     settleflow.service on 127.0.0.1:8093 (NOT docker — compose is a dev artifact). D-42.
  2. **The derived-work ceiling is a line count, not a byte count** (`MAX_STATEMENT_ROWS=200k`,
     env-tunable): 8MB/250k rows sat INSIDE the old caps and cost ~900MB/~72MB-persisted. Sync
     handler + 2-slot semaphore: health worst 594ms during a 150k-row reconcile (was 6.3s stall).
  3. vuln-0012 got real ceilings incl. the 40MP raster guard computed BEFORE get_pixmap; the
     39KB/100-page bomb Strix measured at 125s is refused in <1ms.
- **Verified:** self-check 74→77 (all assert-based, one runnable: `python tests/test_matching.py`);
  every fix had a LIVE gate against a locally started instance (rate-limit matrices, notify
  throttle + prune, the full 12-case vuln-0003 PoC matrix with 0 unhandled server log lines,
  the served-CSV formula defusal, the flood->rejection behaviour). `hermes verify --skip-start`
  ok; port 8000 clear before/after. CI green on the pushed head.
- **Process notes (each already cost time once):** the patch tool mangled a `"\r\n"` literal in
  a test (known trap — repaired by byte-exact execute_code); a `&&`-chained commit slipped past
  a piped test failure (the pipeline exit-code trap — the follow-up commit restored honesty,
  amended before push, nothing broken shipped); `--content-file` needs a same-drive path.
- **Not done (and why):** the verifying Strix RE-scan (needs the owner-gated Nous
  `NOUS_API_KEY`; Security Scan red = LLM CONNECTION FAILED, i.e. no scan happened — per D-38
  read run.json, not the colour); the 0.7.5 deploy (session-17 brief says ask again — awaiting
  Sanjay's go); a compose/systemd MemoryLimit (prod box has 17GB available, 2 slots x ~900MB
  worst-case fits; revisit at scale).
- **Board:** ATL-242 in_review with the full remediation ledger comment (12-row table, evidence
  per finding). ATL-218 unchanged (blocked, owner-gated, now the gate for the re-scan too).
- **State at close:** repo clean at `a200656`, pushed; live still 0.7.4 (303+ runs) with canary
  green; next unit = Sanjay's 0.7.5 deploy go + the Portal key, then the re-scan as the gate for
  a second deploy.
