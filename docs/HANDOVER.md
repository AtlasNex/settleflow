# Handover

Incremental context so the next session starts warm, not from zero. Read this first,
then `MASTER-PLAN.md`, then `docs/ARCHITECTURE.md`.

## Where things are

- Project root: `E:/Sanjay Files/StartUp/open source/settleflow`
- Package: `settleflow/` (models.py, matching.py, parsers.py, exports.py,
  exceptions.py, schemas.py, pdf.py, ocr.py, `__main__.py` = CLI)
- Tests: `tests/test_matching.py` (assert-based self-check, 64 checks) +
  `tests/fixtures/{sbi,kotak,pnb,dbs}/` (real anonymised statement text, NOTICE.md) and
  `tests/fixtures/{phonepe,cashfree,payu,juspay}/` (synthetic rows on real verbatim headers)
- SaaS: `saas/app.py` + `saas/templates/` + `saas/requirements.txt` + sample files
- Docs: `docs/` (architecture, constraints, flow, decisions, bug, feature, rollback,
  testing, monetization, commercial, handover)
- Logs: `logs/SESSION-LOG.md`
- Money docs: `docs/MONETIZATION.md` (deep-research) + `docs/COMMERCIAL.md` (Sidekiq
  licensing) + `funding.json` + `.github/FUNDING.yml`

## Current state (2026-09-11)

### ✅ RESOLVED — the name is **Conjunction**; the rename is planned, not executed

He chose it on 2026-09-11 (session 15), from three finalists presented with their costs. `settleflow`
is now a **deprecated placeholder**. The evidence he decided on, the accepted cost, and the ordered
rename sequence (repo first and verified, then the live host, then the Cloudflare ingress and the
Hermes watchdog) are in `docs/NAMING-SHORTLIST.md`; `DECISIONS.md` D-37 records the choice.

**The rename has NOT been done.** It is a real diff whose last steps move `/opt/settleflow`, the
`settleflow.service` unit, and the deploy script's path allowlist — a rename that drifts is how a
live service quietly stops being deployable. Nothing was purchased either: re-check the domain and
reserve the PyPI name (both are Sanjay's calls) before starting.

### Session 15 — the three unblocked gateway parsers are wired

The 2026-09-11 research pass unblocked three gateway formats (D-33); all three are now wired,
and the self-check went 52 -> 64 checks:

- **Cashfree Settlement Recon** — `load_cashfree_recon_report()` reads BOTH sections of the
  two-report file (14-col batches, marker line, 63-col events). The event section has no
  debit/credit pair: direction is `Sale Type` applied to `Event Settlement Amount` (the money
  movement), while `Event Amount` stays the gross. Netting the events must equal the batch
  total — the fixture asserts it, and a mutation probe confirmed the assertion fails if the
  flag is applied to the gross column (D-34).
- **PayU** — `parse_payu_settlement_range` (UTR-level, so rows level-1 match) and
  `parse_payu_transaction_details` (signed per-transaction ReconLines). The CSV export can
  never be wired: the merchant picks its columns per report (D-35).
- **Juspay** — `load_juspay_settlement_csv()` nets per bank credit for both real variants.
  Three assumptions are stated in the docstring rather than hidden: the rupee unit
  (vendor-code corroboration), one-date-is-one-credit for the variant with no UTR column, and
  the `Settled`-only status filter. **Nothing has been checked against a real file** (D-36).

**No deploy and no version bump:** the change is library-level and `saas/app.py`'s own column
detection is untouched, so the live service is unchanged at 0.7.3.

### Session 14 — hosted layer hardened, repo published, v0.7.3 shipped

**The headline risk is closed.** The thin SaaS had a public `/runs` listing and
integer-id `/runs/<id>/export/*.csv` downloads: every uploaded statement's matched UTRs,
amounts and exception text were readable by anyone, unauthenticated. Runs are now
reachable only via an unguessable `/r/<run_token>` (D-29), and the old rows are
unreachable. The same file also wrote every upload to one fixed path, so concurrent
reconciliations clobbered each other (fixed, with a 12-way regression test).

Found by probing from **outside** after the fix shipped: Cloudflare kept serving the leaked
CSV from its edge cache (`cf-cache-status: HIT`) for the rest of a 4-hour TTL. Cached
objects purged; run responses are now `no-store` and the canary asserts it (D-30).

**The repo is now genuinely open source:** PUBLIC on GitHub, MIT, CI green on
3.10/3.11/3.12 (self-check + zero-dependency-core + a boot-the-app integration job that runs
the canary), CONTRIBUTING / SECURITY / issue templates, legal drafts in `docs/legal/`
(marked DRAFT), `brand-context.md`, real pages at `/about`, `/pricing`, `/contact`,
`/privacy`, `/terms`, plus `sitemap.xml` and `llms.txt`. Release `v0.7.3`. Note: the origin
host is deliberately **not** in the repo (D-31) — set `SETTLEFLOW_HOST` or
`scripts/.deploy.env`.

**Ops:** `scripts/deploy.sh` (idempotent, refuses to ship on a red self-check, backs up,
restarts, then asserts health + the end-to-end canary + the public URL) and
`scripts/rollback.sh` (exercised for real this session; that drill is what found that it
validated a restored release with the *rolled-back* canary, D-32). A 15-minute Hermes
watchdog runs the canary against the public URL and alerts on Telegram.

**Read `docs/COMPLETION.md` first** — it is the item-by-item DONE / PARTIAL / DEFERRED /
BLOCKED record with the evidence for each, and it lists what is still blocked and on whom.

### Earlier state (2026-08-25)

All phases done; bank + gateway parser coverage is complete for every format
with a public sample. The library is end-to-end usable via a CLI.

- **Level 1**: `Txn`/`Match`/`ReconResult` + two-pass match + `match_settlements`.
- **Level 2**: `ReconLine`/`BatchRecon`/`OrderMatch` + `group_batches` + `match_orders`
  + `parse_razorpay_recon` (verified 24-param schema, fails closed on unknown fields).
- **Phase 3 (banks)**: HDFC/SBI/ICICI/Axis/Kotak (variant A two-column CSV) + Kotak
  Dr/Cr (D-22) + Kotak "bankii" variant B (D-24, wired 2026-08-24; schema transcribed
  from jasimmk/bankii in_kotak.py, auto-detected by header) + PNB/DBS (running-balance,
  D-23). All headers + sources in `docs/SCHEMAS.md`. NOT wired (no public sample):
  Cashfree/PhonePe/Juspay/PayU settlement + recon files (confirmed merchant-private
  dashboard exports, D-24), IDFC.
- **PDF (D-21 + D-23)**: `settleflow/pdf.py` — `extract_pdf_text` (lazy pymupdf,
  password + scanned detection), `parse_sbi_pdf`, and `parse_sbi_statement` which
  auto-dispatches SBI **YONO / netbanking / credit-card** layouts. pymupdf is an
  optional `[pdf]` extra; core stays stdlib-only.
- **Phase 4**: `saas/app.py` — FastAPI reconcile/expose/export loop, sqlite3 storage,
  Tally + GST + TDS-1035 CSV exports. **LIVE** at https://settleflow.atlasnex.com (host-run
  systemd service, port 8093, Cloudflare Tunnel; not Docker — this LXC blocks Docker build
  via AppArmor, D-28).
- **Phase 5**: `exceptions.py` — `classify()` (5 rule categories), `build_llm_prompt()`,
  and `triage_exceptions(exc, call_llm)` (provider-agnostic LLM hook; core still
  makes no network call).
- **CLI (D-23)**: `python -m settleflow reconcile --settlements X --vendor v
  --bank b --statement Y --out-dir out` -> `tally.csv` + `exceptions.csv`.

Git history (recent head): `a73c1df` v0.7.3 OCR+Docker, `aef79db` port 8093,
`3a0a818` D-28 live deploy (HEAD). Earlier: `dd68089` complete end-to-end CLI,
`d56fdd0` v0.7.2 IST/date/PDF-gating, `12173f1` v0.7.1 Kotak bankii-B, `a73c1df` head.

## How to run

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py            # self-check, 42 checks

# CLI — one-command reconciliation:
python -m settleflow reconcile \
    --settlements settlements.csv --vendor razorpay_settlement_csv \
    --bank sbi --statement statement.csv --out-dir ./out

# SaaS:
python -m uvicorn saas.app:app --host 127.0.0.1 --port 8091

# PDF bank statements (optional extra):
pip install "settleflow[pdf]"            # pymupdf
from settleflow import parse_sbi_pdf
parse_sbi_pdf("statement.pdf")           # SBI YONO / netbanking / credit card
```

## What is next

0. **Name the product** (Sanjay's outstanding request — see the OPEN THREAD block above). Then the
   rename is a real diff across `pyproject.toml`, the `settleflow/` package dir, README, MASTER-PLAN,
   all `docs/`, the CLI entry point, the live copy, and the VPS service name — plan it, don't improvise it.
1. **Gateway parsers** — PhonePe settlement is **wired** (`load_phonepe_settlement_csv`, and it is
   the one case where the file shape differs from ours: rows are per-transaction, so they net per
   `BankReferenceNo`). Still to build, all specified with verbatim sources in
   `docs/RESEARCH-gateway-samples.md`: the Cashfree two-section recon parser (14 + 63 cols, marker
   `** Settlement Reconciliation Details **`), PayU's two official settlement **APIs** as JSON
   parsers, and the Juspay 25-column map (money unit corroborated rupees, not officially stated).
   IDFC stays `None`: no real file or official sample exists, and the two community CSV claims
   contradict each other. Never guess a schema (`docs/CONSTRAINTS.md` #2).
2. **PyPI** — blocked on an account/token. `pip install git+https://github.com/AtlasNex/settleflow.git`
   works today (verified in a clean venv).
3. **Email delivery of the workpaper pack** — the capture writes rows and the code never fakes a
   send; wiring needs Proton SMTP creds as `SETTLEFLOW_SMTP_{HOST,PORT,USER,PASS,FROM}`.
4. **Cloudflare managed robots.txt** — the origin file now allows AI crawlers on the public pages,
   but the zone's *managed* policy takes precedence, so citability is unchanged until that is
   switched off in the dashboard.
5. **uptime-kuma monitor** — needs the kuma admin login to create.

### Older "what is next" (2026-08-25, kept for context)

**Parser coverage is complete** for every format with a public sample. The
remaining items are gated on real files that D-24 definitively confirmed are
NOT publicly sampleable (they are merchant-private dashboard exports):

1. **Cashfree / PhonePe / Juspay settlement + recon files** — schemas are captured in
   `docs/SCHEMAS.md` from official docs, and I verified the real field sets against
   production parsers (D-24), but there is no public sample file to build/test against
   (D-7). A real export from any of these dashboards unlocks the parser.
2. **IDFC bank statement** — no verified schema source found yet.
3. **Live SaaS host deploy** — the app is deploy-ready (`Dockerfile` + `docker-compose.yml`,
   binds 127.0.0.1:8091; `/health` verified 200). The actual VPS/Cloudflare-Tunnel push is
   a separate infra step to confirm with Sanjay.

The single most valuable thing Sanjay can drop in: **one real settlement-recon CSV
export from any Cashfree / PhonePe / Juspay merchant dashboard he can access**, plus
his actual SBI PDF to validate the YONO/netbanking/credit-card parsers. (Kotak
"bankii" variant B is wired — D-24. Scanned SBI PDFs are handled via the `[ocr]`
extra — D-27 — using the already-installed Tesseract.)

## Gotchas / pitfalls

- **Money is `Decimal` in rupees.** Paise->rupee only in parsers. Never `float`.
- **The bank UTR != the gateway `settlement_utr`.** Match on (date + net amount), not UTR.
- **Razorpay amounts are integers in paise.** Divide by 100 at the parser.
- **Recon parser fails closed**: unknown/missing fields raise `ValueError`. If Razorpay
  changes its schema, the parser tells you loudly — update `RAZORPAY_RECON_KEYS` + add a
  test before loosening it.
- **Firecrawl web tools can be billing-blocked.** Fallback: Exa MCP search + curl against
  the GitHub/PyPI APIs, or Wayback snapshots for JS-rendered docs (see D-14).
- **Library is stdlib-only; SaaS is FastAPI.** Keep the split (D-17). The `saas/` deps
  are optional-dependencies, not core deps.
- Git identity is set locally in this repo (`kumarrusanjay@gmail.com` / `Sanjay Kumar`).

## What NOT to do

See `docs/CONSTRAINTS.md`. The short list: no `float` for money, no fabricated schemas,
no test framework, no re-license, no force-push, no package rename without a decision.
Also: do not fill the empty schema-registry slots from memory — only from real samples.

## Models in play

- Orchestration/build: deepseek-v4-pro.
- Research subagents: deepseek-v4-flash.
- Full provenance in `docs/DECISIONS.md` (D-1 through D-23).
