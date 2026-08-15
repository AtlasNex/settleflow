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

Phases 1, 2, 4, 5 done; Phase 3 mechanism done, data DEFERRED:

- **Level 1**: `Txn`/`Match`/`ReconResult` + two-pass match + `match_settlements`.
- **Level 2**: `ReconLine`/`BatchRecon`/`OrderMatch` + `group_batches` + `match_orders`
  + `parse_razorpay_recon` (verified 24-param schema, fails closed on unknown fields).
- **Phase 3**: `schemas.py` registry (loaders + verified/empty column-map slots). The
  Cashfree/PayU/PhonePe/Juspay + bank-statement column maps are NOT filled — they need
  real sample files (D-7). Do NOT fill them from memory or from JS-rendered docs.
- **Phase 4**: `saas/app.py` — FastAPI reconcile/expose/export loop, sqlite3 storage,
  Tally + GST + TDS-1035 CSV exports. Runs locally, not hosted.
- **Phase 5**: `exceptions.py` — `classify()` (5 rule categories) + `build_llm_prompt()`.
  The actual LLM call is a SaaS-layer concern, not in the core.

Git history (chronological): `ccf753b` baseline, `aad10fc` Razorpay parser,
`f2a9b92` relocate+rename, `ca3f592` docs; the 2026-08-16 work is the next commit(s).

## How to run

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py            # self-check, 18 checks

# SaaS:
python -m uvicorn saas.app:app --host 127.0.0.1 --port 8091
```

## What is next (Phase 3 data — needs real samples)

The single most valuable next step: get **one real sample** of each of the following,
then fill the registry maps and add a test per format:

1. A real Razorpay settlement CSV (dashboard export header).
2. One real bank statement CSV each: HDFC / SBI / ICICI / Axis / Kotak.
3. Cashfree / PayU / PhonePe / Juspay settlement recon CSV headers.

Without a real sample, do NOT invent the column names (this is the exact Nova zoning
failure mode). The mechanism is built; only the data is missing.

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
