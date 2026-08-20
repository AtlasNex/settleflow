# Handover

Incremental context so the next session starts warm, not from zero. Read this first,
then `MASTER-PLAN.md`, then `docs/ARCHITECTURE.md`.

## Where things are

- Project root: `E:/Sanjay Files/StartUp/open source/settleflow`
- Package: `settleflow/` (models.py, matching.py, parsers.py, exports.py,
  exceptions.py, schemas.py, pdf.py, `__main__.py` = CLI)
- Tests: `tests/test_matching.py` (assert-based self-check, 38 checks) +
  `tests/fixtures/{sbi,kotak,pnb,dbs}/` (real anonymised statement text, NOTICE.md)
- SaaS: `saas/app.py` + `saas/templates/` + `saas/requirements.txt` + sample files
- Docs: `docs/` (architecture, constraints, flow, decisions, bug, feature, rollback,
  testing, monetization, commercial, handover)
- Logs: `logs/SESSION-LOG.md`
- Money docs: `docs/MONETIZATION.md` (deep-research) + `docs/COMMERCIAL.md` (Sidekiq
  licensing) + `funding.json` + `.github/FUNDING.yml`

## Current state (2026-08-21)

All phases done; bank + gateway parser coverage is complete for every format
with a public sample. The library is end-to-end usable via a CLI.

- **Level 1**: `Txn`/`Match`/`ReconResult` + two-pass match + `match_settlements`.
- **Level 2**: `ReconLine`/`BatchRecon`/`OrderMatch` + `group_batches` + `match_orders`
  + `parse_razorpay_recon` (verified 24-param schema, fails closed on unknown fields).
- **Phase 3 (banks)**: HDFC/SBI/ICICI/Axis/Kotak (two-column CSV) + Kotak Dr/Cr
  (D-22) + PNB/DBS (running-balance, D-23). All headers + sources in
  `docs/SCHEMAS.md`. NOT wired (no public sample): Cashfree/PhonePe/Juspay/PayU
  settlement files, Kotak "bankii" variant B.
- **PDF (D-21 + D-23)**: `settleflow/pdf.py` — `extract_pdf_text` (lazy pymupdf,
  password + scanned detection), `parse_sbi_pdf`, and `parse_sbi_statement` which
  auto-dispatches SBI **YONO / netbanking / credit-card** layouts. pymupdf is an
  optional `[pdf]` extra; core stays stdlib-only.
- **Phase 4**: `saas/app.py` — FastAPI reconcile/expose/export loop, sqlite3 storage,
  Tally + GST + TDS-1035 CSV exports. Runs locally, not hosted.
- **Phase 5**: `exceptions.py` — `classify()` (5 rule categories), `build_llm_prompt()`,
  and `triage_exceptions(exc, call_llm)` (provider-agnostic LLM hook; core still
  makes no network call).
- **CLI (D-23)**: `python -m settleflow reconcile --settlements X --vendor v
  --bank b --statement Y --out-dir out` -> `tally.csv` + `exceptions.csv`.

Git history (chronological): `ccf753b` baseline, `aad10fc` Razorpay parser,
`f2a9b92` relocate+rename, `ca3f592` docs; 2026-08-16 work: `9becf0e` Phases 2-5 +
`04eceba` verify manifest; Phase-3 maps are the next commit.

## How to run

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py            # self-check, 38 checks

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

**Parser coverage is complete** for every format with a public sample. The
remaining items are all gated on real files or later-stage infra:

1. **Cashfree / PhonePe / Juspay settlement files** — schemas are captured in
   `docs/SCHEMAS.md` from official docs, but there is no public sample to build
   against (D-7). A real export from any of these would unlock the parser.
2. **Scanned/image-only PDFs** — needs an OCR layer (a separate, unbuilt piece).
3. **Kotak "bankii" variant B** — documented but no real sample.
4. **Hosted SaaS** — auth, multi-user, deployment (later stage).

The single most valuable thing Sanjay can drop in: one real **Razorpay recon CSV
export** and a **Cashfree/PhonePe settlement file**, plus his actual SBI PDF to
validate the YONO/netbanking/credit-card parsers against his real file.

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
