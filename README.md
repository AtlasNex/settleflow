# settleflow

> Working name. Open-source UPI/NPCI settlement reconciliation for India.

Parse payment-gateway settlement files and bank statements, then match them so a
merchant can reconcile "what the gateway says I received" against "what actually landed
in my bank." Open-core, MIT, zero runtime dependencies.

## Status

Phases 1, 2, 4, 5 done; Phase 3 done for the formats with public evidence.

- **Level 1**: two-pass matching engine (exact UTR → amount+date fallback → unmatched).
- **Level 2**: settlement-recon line-item parsing (Razorpay 24-param schema) + order-ledger matching + netting.
- **Parsers (Phase 3)**: Razorpay settlement CSV + recon CSV, HDFC/SBI/ICICI/Axis/Kotak/PNB/DBS bank statements + Kotak Dr/Cr + Kotak bankii-B + SBI YONO/netbanking/credit-card. All headers verified in `docs/SCHEMAS.md`.
- **PDF bank statements**: `parse_sbi_pdf` reads SBI YONO/netbanking/credit-card statements (optional `[pdf]` extra).
- **Exports**: Tally CSV, GST worksheet, TDS code-1035 (ex-194O) worksheet.
- **Exceptions**: rule-based classifier + LLM-prompt builder + provider-agnostic `triage_exceptions` hook.
- **CLI**: `python -m settleflow reconcile` (match → classify → export in one command).
- **Thin SaaS**: FastAPI reconcile/expose/export loop (`saas/`).
- Self-check: 41 checks.

## Quickstart

```bash
cd "E:/Sanjay Files/StartUp/open source/settleflow"
python tests/test_matching.py     # self-check (41 checks)

# one-command reconciliation:
python -m settleflow reconcile \
    --settlements settlements.csv --vendor razorpay_settlement_csv \
    --bank sbi --statement statement.csv --out-dir ./out
```

```python
from decimal import Decimal
from datetime import date

from settleflow import Txn, match

settlements = [Txn("123456789012", Decimal("100.00"), date(2026, 8, 15), ref="order_1")]
bank = [Txn("1234 5678 9012", Decimal("100.00"), date(2026, 8, 16))]
result = match(settlements, bank)
print(result.matched)             # one exact match (UTR normalized)
```

Line-item (order-level) reconciliation:

```python
from settleflow import parse_razorpay_recon, group_batches, match_orders

lines = parse_razorpay_recon(api_response_dict)   # GET /v1/settlements/recon/combined
batches = group_batches(lines)                    # one BatchRecon per settlement_id
orders = [Txn(None, Decimal("1000.00"), date(2026, 8, 15), ref="order_123")]
result = match_orders(lines, orders)              # joins payments to your order ledger
```

## The model

Two levels of reconciliation:

1. **Settlement -> bank credit**: match a settlement batch to a bank NEFT credit by
   `settlement_utr`, falling back to (date + net amount).
2. **Line items -> orders**: decompose a batch into order/payment rows (gross - MDR -
   GST - refunds = net) and match against your order management system.

## Run the thin SaaS

```bash
python -m uvicorn saas.app:app --host 127.0.0.1 --port 8091
```

## Monetize

See `docs/MONETIZATION.md` (deep research) and `docs/COMMERCIAL.md` (licensing). Short
version: MIT core stays free; money is in a Sidekiq-style commercial license for
embedding, a ₹4-7k/mo thin SaaS through CAs, and support retainers.

## Docs

| File | What |
|---|---|
| `MASTER-PLAN.md` | strategy, roadmap, market, monetization |
| `AGENTS.md` | working rules for any AI touching this repo |
| `docs/ARCHITECTURE.md` | system map: files, data model, algorithm, data flow |
| `docs/CONSTRAINTS.md` | never-touch rules |
| `docs/FLOW.md` | execution trace |
| `docs/DECISIONS.md` | the why behind every decision |
| `docs/HANDOVER.md` | where the last session stopped |
| `docs/MONETIZATION.md` | monetization deep-research |
| `docs/COMMERCIAL.md` | the paid layer on top of MIT |
| `docs/SCHEMAS.md` | verified vendor/bank column layouts + sources |
| `docs/BUG.md` / `docs/FEATURE.md` | bug/feature trails |
| `docs/ROLLBACK.md` | the way out |
| `docs/TESTING.md` | test checklist |

## License

MIT. See `LICENSE`. The core library is free; the hosted service, support, and
embedding license are paid (see `docs/COMMERCIAL.md`).
