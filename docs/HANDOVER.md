# Handover

Incremental context so the next session starts warm, not from zero. Read this first,
then `MASTER-PLAN.md`, then `docs/ARCHITECTURE.md`.

## Where things are

- Project root: `E:/Sanjay Files/StartUp/open source/settleflow`
- Package: `settleflow/` (models.py, matching.py, parsers.py, exports.py,
  exceptions.py, schemas.py)
- Tests: `tests/test_matching.py` (assert-based self-check, 18 checks)
- SaaS: `saas/app.py` + `saas/templates/` + `saas/requirements.txt` + sample files
- Docs: `docs/` (architecture, constraints, flow, decisions, bug, feature, rollback,
  testing, monetization, commercial, handover)
- Logs: `logs/SESSION-LOG.md`
- Money docs: `docs/MONETIZATION.md` (deep-research) + `docs/COMMERCIAL.md` (Sidekiq
  licensing) + `funding.json` + `.github/FUNDING.yml`

## Current state (2026-08-16)

Phases 1, 2, 4, 5 done; Phase 3 done for the formats with public evidence:

- **Level 1**: `Txn`/`Match`/`ReconResult` + two-pass match + `match_settlements`.
- **Level 2**: `ReconLine`/`BatchRecon`/`OrderMatch` + `group_batches` + `match_orders`
  + `parse_razorpay_recon` (verified 24-param schema, fails closed on unknown fields).
- **Phase 3**: `schemas.py` registry now WIRED with verified maps — Razorpay settlement
  CSV (7 cols) + recon CSV (27 cols), HDFC/SBI/ICICI/Axis/Kotak bank statements (two
  column debit/credit, preamble auto-detected). All headers + sources in
  `docs/SCHEMAS.md`. NOT wired (needs a dedicated parser or a real file): Cashfree recon
  (two-section file), PhonePe (undocumented type/date), Juspay (unstated money unit),
  PayU (user-configurable columns).
- **Phase 4**: `saas/app.py` — FastAPI reconcile/expose/export loop, sqlite3 storage,
  Tally + GST + TDS-1035 CSV exports. Runs locally, not hosted.
- **Phase 5**: `exceptions.py` — `classify()` (5 rule categories) + `build_llm_prompt()`.
  The actual LLM call is a SaaS-layer concern, not in the core.

Git history (chronological): `ccf753b` baseline, `aad10fc` Razorpay parser,
`f2a9b92` relocate+rename, `ca3f592` docs; 2026-08-16 work: `9becf0e` Phases 2-5 +
`04eceba` verify manifest; Phase-3 maps are the next commit.

## How to run

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py            # self-check, 18 checks

# SaaS:
python -m uvicorn saas.app:app --host 127.0.0.1 --port 8091
```

## What is next

**Immediate (blocked on Sanjay's file):** his SBI statement is a **PDF**, not CSV. Build
a PDF statement parser (`parse_sbi_pdf` or generic `parse_bank_pdf`) against his real
file. `pypdf` + `pymupdf` are already installed. Resolve on the file: password (SBI PDFs
often locked), text-vs-scanned (OCR), and the table layout. Tracked as ATL-72. Never
guess the layout (D-7).

**Then, in priority order** (each still needs a dedicated parser or a real sample —
see `docs/SCHEMAS.md`):

1. **Cashfree settlement-recon** — two-section file (14 + 48 cols); dedicated parser.
2. **PhonePe settlement report** — 14 verified fields; confirm `PaymentType`/date format.
3. **Juspay settlement file** — 25 verified columns; confirm money unit.
4. **Kotak variant B** — second documented layout; add auto-detect.

The single most valuable thing Sanjay can drop in: his SBI PDF (path + password) and one
real Razorpay recon CSV export.

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
- Full provenance in `docs/DECISIONS.md` (D-1 through D-18).
