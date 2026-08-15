# Handover

Incremental context so the next session starts warm, not from zero. Read this first,
then `MASTER-PLAN.md`, then `docs/ARCHITECTURE.md`.

## Where things are

- Project root: `E:/Sanjay Files/StartUp/open source/settleflow`
- Package: `settleflow/` (models.py, matching.py, parsers.py)
- Tests: `tests/test_matching.py` (assert-based self-check)
- Docs: `docs/` (architecture, constraints, flow, decisions, bug, feature, rollback, testing)
- Logs: `logs/SESSION-LOG.md`

## Current state (2026-08-15)

Phase 1 is complete and verified:

- Data model: `Txn`, `Match`, `MatchStatus`, `ReconResult`, `Settlement`.
- Matching engine: exact UTR -> amount+date fallback -> unmatched (`match`).
- Settlement-level matcher (`match_settlements`).
- Generic CSV loader (`load_csv`) + Razorpay settlement parser
  (`parse_razorpay_settlements`, real API schema, paise->rupee + epoch->date).
- Self-check passes: 8 checks (7 in the file + a CSV round-trip verify).

Git history (chronological): `ccf753b` baseline, `aad10fc` Razorpay parser,
`f2a9b92` relocate+rename to `open source/settleflow`.

## What is next (Phase 2)

Line-item decomposition: parse Razorpay `Fetch Settlement Recon` (the per-transaction
rows: `entity_id`, `type` payment/refund/transfer/adjustment, `debit`/`credit`,
`amount`, `fee`, `tax`, `settlement_id`, `payment_id`, `order_id`) and match each batch's
line items to the order management system. The schema is already captured in research.

## How to run

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py
```

## Gotchas / pitfalls

- **Money is `Decimal` in rupees.** Paise->rupee only in parsers. Never `float`.
- **The bank UTR != the gateway `settlement_utr`.** Match on (date + net amount), not UTR.
- **Razorpay amounts are integers in paise.** Divide by 100 at the parser.
- **Firecrawl web tools can be billing-blocked.** Fallback: Exa MCP search + curl against
  the GitHub/PyPI APIs.
- **Do not fabricate vendor schemas.** If the format is not verifiable, raise; do not
  guess (this is the exact Nova zoning failure).
- Git identity is set locally in this repo (`kumarrusanjay@gmail.com` / `Sanjay Kumar`).

## What NOT to do

See `docs/CONSTRAINTS.md`. The short list: no `float` for money, no fabricated schemas,
no test framework, no re-license, no force-push, no package rename without a decision.

## Models in play

- Orchestration/build: deepseek-v4-pro.
- Research subagents: deepseek-v4-flash.
- Full provenance in `docs/DECISIONS.md`.
